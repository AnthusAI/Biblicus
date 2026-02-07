import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

const schema = a.schema({
  Corpus: a.model({
    name: a.string().required(),
    s3Prefix: a.string().required(),
    lastActivity: a.datetime(),
    status: a.enum(['IDLE', 'ACTIVE', 'SYNCING']),
    createdAt: a.datetime(),
    updatedAt: a.datetime(),
  })
  .authorization((allow) => [
    allow.publicApiKey(),  // Temporary: allow unauthenticated access for testing
    allow.owner(),
    allow.authenticated().to(['read'])
  ]),

  Snapshot: a.model({
    corpusId: a.id().required(),
    snapshotId: a.string().required(),
    type: a.enum(['EXTRACTION', 'ANALYSIS', 'GRAPH', 'RETRIEVAL']),
    status: a.enum(['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']),
    totalItems: a.integer(),
    completedItems: a.integer(),
    startTime: a.datetime(),
    endTime: a.datetime(),
    errorMessage: a.string(),
  })
  .authorization((allow) => [
    allow.publicApiKey(),  // Temporary: allow unauthenticated access for testing
    allow.owner(),
    allow.authenticated().to(['read'])
  ])
  .identifier(['corpusId', 'snapshotId']),

  FileMetadata: a.model({
    corpusId: a.id().required(),
    filePath: a.string().required(),
    status: a.enum(['LOCAL_ONLY', 'UPLOADING', 'AVAILABLE']),
    s3Key: a.string(),
    size: a.integer(),
    uploadedAt: a.datetime(),
  })
  .authorization((allow) => [
    allow.publicApiKey(),  // Temporary: allow unauthenticated access for testing
    allow.owner(),
    allow.authenticated().to(['read'])
  ])
  .identifier(['corpusId', 'filePath']),

  CatalogMetadata: a.model({
    corpusId: a.id().required(),
    catalogHash: a.string().required(),
    itemCount: a.integer().required(),
    lastSyncedAt: a.datetime().required(),
    schemaVersion: a.integer().required(),
    configurationId: a.string(),
    corpusUri: a.string(),
  })
  .authorization((allow) => [
    allow.publicApiKey(),  // Temporary: allow unauthenticated access for testing
    allow.owner(),
    allow.authenticated().to(['read'])
  ]),

  CatalogItem: a.model({
    corpusId: a.id().required(),
    itemId: a.string().required(),
    relpath: a.string().required(),
    sha256: a.string().required(),
    bytes: a.integer().required(),
    mediaType: a.string().required(),
    title: a.string(),
    tags: a.string().array(),
    metadataJson: a.json(),
    createdAt: a.datetime().required(),
    sourceUri: a.string(),
    hasExtraction: a.boolean().default(false),
  })
  .authorization((allow) => [
    allow.publicApiKey(),  // Temporary: allow unauthenticated access for testing
    allow.owner(),
    allow.authenticated().to(['read'])
  ])
  .identifier(['corpusId', 'itemId'])
  .secondaryIndexes((index) => [
    index('mediaType').sortKeys(['createdAt']).queryField('itemsByMediaType'),
  ]),
});

export type Schema = ClientSchema<typeof schema>;
export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'apiKey',  // Temporary: use API key for local testing (no auth required)
    apiKeyAuthorizationMode: { expiresInDays: 365 }
  },
});
