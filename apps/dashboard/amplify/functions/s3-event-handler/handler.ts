import type { S3Handler } from 'aws-lambda';

// TODO: These will be injected by Amplify after deployment
const APPSYNC_ENDPOINT = process.env.APPSYNC_ENDPOINT || '';
const API_KEY = process.env.API_KEY || '';

export const handler: S3Handler = async (event) => {
  if (!APPSYNC_ENDPOINT || !API_KEY) {
    console.warn('APPSYNC_ENDPOINT or API_KEY not configured, skipping');
    return;
  }
  for (const record of event.Records) {
    const s3Key = record.s3.object.key;

    // Parse corpus structure: {corpusName}/...
    const parts = s3Key.split('/');
    if (parts.length < 2) continue;

    const [corpusName, ...pathParts] = parts;
    const corpusId = corpusName;
    const filePath = pathParts.join('/');

    // Update FileMetadata to AVAILABLE
    const mutation = `
      mutation UpdateFileMetadata($input: UpdateFileMetadataInput!) {
        updateFileMetadata(input: $input) {
          corpusId
          filePath
          status
        }
      }
    `;

    const variables = {
      input: {
        corpusId,
        filePath,
        status: 'AVAILABLE',
        s3Key,
        size: record.s3.object.size,
        uploadedAt: new Date().toISOString(),
      }
    };

    try {
      await executeGraphQL(mutation, variables);
    } catch (error) {
      console.error('Failed to update file metadata:', error);
    }
  }
};

async function executeGraphQL(query: string, variables: any) {
  const response = await fetch(APPSYNC_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY,
    },
    body: JSON.stringify({ query, variables }),
  });

  const result = await response.json();
  if (result.errors) {
    throw new Error(`GraphQL errors: ${JSON.stringify(result.errors)}`);
  }

  return result.data;
}
