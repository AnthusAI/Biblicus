#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ReinforcementMemoryStack } from '../lib/reinforcement-memory-stack';

const app = new cdk.App();

/**
 * Deploy with:
 *
 *   npx cdk deploy \
 *     --context projectPrefix=myapp \
 *     --context environmentName=production \
 *     --context embeddingDimension=384
 *
 * Or set defaults below and run:
 *
 *   npx cdk deploy
 */
const projectPrefix = app.node.tryGetContext('projectPrefix') ?? 'myapp';
const environmentName = app.node.tryGetContext('environmentName') ?? 'development';
const embeddingDimension = Number(app.node.tryGetContext('embeddingDimension') ?? 384);

new ReinforcementMemoryStack(app, 'ReinforcementMemoryStack', {
  projectPrefix,
  environmentName,
  embeddingDimension,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
