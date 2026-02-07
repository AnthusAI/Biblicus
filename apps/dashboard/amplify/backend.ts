import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';
import { s3EventHandler } from './functions/s3-event-handler/resource';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as iam from 'aws-cdk-lib/aws-iam';

export const backend = defineBackend({
  auth,
  data,
  storage,
  s3EventHandler,
});

// Add S3 event notification for availability phase
// Note: No prefix filter - all objects trigger Lambda
const s3Bucket = backend.storage.resources.bucket;
s3Bucket.addEventNotification(
  s3.EventType.OBJECT_CREATED,
  new s3n.LambdaDestination(backend.s3EventHandler.resources.lambda)
);

// Grant Lambda permissions to call AppSync
backend.s3EventHandler.resources.lambda.addToRolePolicy(
  new iam.PolicyStatement({
    actions: ['appsync:GraphQL'],
    resources: [backend.data.resources.graphqlApi.arn + '/*'],
  })
);
