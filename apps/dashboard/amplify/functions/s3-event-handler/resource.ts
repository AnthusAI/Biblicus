import { defineFunction } from '@aws-amplify/backend';

export const s3EventHandler = defineFunction({
  name: 's3-event-handler',
  entry: './handler.ts',
  runtime: 20,
});
