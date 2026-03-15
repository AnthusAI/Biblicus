import { CfnOutput, CfnResource, RemovalPolicy, Stack, StackProps } from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface ReinforcementMemoryStackProps extends StackProps {
  /**
   * Short prefix that namespaces all resources (e.g. "plexus", "myapp").
   * Must be lowercase alphanumeric + hyphens.
   */
  projectPrefix: string;

  /** Deployment environment name (e.g. "production", "staging", "development"). */
  environmentName: string;

  /**
   * Embedding vector dimension.  Must match the model used by the application.
   * @default 384
   */
  embeddingDimension?: number;
}

function normalizeSlug(value: string, fallback: string): string {
  const normalized = (value || fallback)
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return normalized || fallback;
}

/**
 * Provisions the AWS resources required to run ReinforcementMemory in production:
 *
 * - **S3 Vectors bucket** — stores cluster centroids, queried for semantic
 *   similarity at analysis time.
 * - **S3 Vectors index** — cosine-similarity index over the embeddings.
 * - **S3 embeddings bucket** — caches raw text embeddings to avoid re-embedding
 *   identical texts on subsequent analysis runs.
 *
 * In development environments (environmentName === "development") all resources
 * are created with DESTROY removal policy so they can be torn down cleanly.
 * All other environments use RETAIN.
 *
 * Outputs — set these as environment variables in your application:
 *
 * | Output export                   | Env var                  |
 * |---------------------------------|--------------------------|
 * | `{prefix}S3VectorBucket-{env}`  | `S3_VECTOR_BUCKET_NAME`  |
 * | `{prefix}S3VectorBucketArn-{env}` | (informational)        |
 * | `{prefix}S3VectorIndex-{env}`   | `S3_VECTOR_INDEX_NAME`   |
 * | `{prefix}S3VectorIndexArn-{env}` | `S3_VECTOR_INDEX_ARN`   |
 * | `{prefix}EmbeddingsBucket-{env}` | `EMBEDDING_CACHE_BUCKET` |
 */
export class ReinforcementMemoryStack extends Stack {
  public readonly vectorBucketName: string;
  public readonly vectorIndexName: string;
  public readonly embeddingsBucketName: string;

  constructor(scope: Construct, id: string, props: ReinforcementMemoryStackProps) {
    super(scope, id, props);

    const prefix = normalizeSlug(props.projectPrefix, 'app');
    const env = normalizeSlug(props.environmentName, 'development');
    const dim = props.embeddingDimension ?? 384;
    const isDevelopment = env === 'development';
    const exportPrefix = prefix.charAt(0).toUpperCase() + prefix.slice(1);

    this.vectorBucketName = `${prefix}-vectors-${env}`;
    this.vectorIndexName = `reinforcement-memory-idx-${env}`;
    this.embeddingsBucketName = `${prefix}-embeddings-${env}`;

    // S3 Vectors bucket
    const vectorBucket = new CfnResource(this, 'ReinforcementMemoryVectorBucket', {
      type: 'AWS::S3Vectors::VectorBucket',
      properties: {
        VectorBucketName: this.vectorBucketName,
      },
    });
    vectorBucket.applyRemovalPolicy(
      isDevelopment ? RemovalPolicy.DESTROY : RemovalPolicy.RETAIN,
    );

    // S3 Vectors index
    const vectorIndex = new CfnResource(this, 'ReinforcementMemoryVectorIndex', {
      type: 'AWS::S3Vectors::Index',
      properties: {
        DataType: 'float32',
        Dimension: dim,
        DistanceMetric: 'cosine',
        IndexName: this.vectorIndexName,
        VectorBucketName: this.vectorBucketName,
      },
    });
    vectorIndex.addDependency(vectorBucket);
    vectorIndex.applyRemovalPolicy(
      isDevelopment ? RemovalPolicy.DESTROY : RemovalPolicy.RETAIN,
    );

    // Embeddings cache bucket
    const embeddingsBucket = new s3.Bucket(this, 'EmbeddingsBucket', {
      bucketName: this.embeddingsBucketName,
      removalPolicy: isDevelopment ? RemovalPolicy.DESTROY : RemovalPolicy.RETAIN,
      autoDeleteObjects: isDevelopment,
    });

    // CloudFormation outputs
    new CfnOutput(this, 'S3VectorBucketName', {
      value: this.vectorBucketName,
      description: 'S3 Vectors bucket name — set as S3_VECTOR_BUCKET_NAME',
      exportName: `${exportPrefix}S3VectorBucket-${env}`,
    });

    new CfnOutput(this, 'S3VectorBucketArn', {
      value: vectorBucket.getAtt('VectorBucketArn').toString(),
      description: 'S3 Vectors bucket ARN',
      exportName: `${exportPrefix}S3VectorBucketArn-${env}`,
    });

    new CfnOutput(this, 'S3VectorIndexName', {
      value: this.vectorIndexName,
      description: 'S3 Vectors index name — set as S3_VECTOR_INDEX_NAME',
      exportName: `${exportPrefix}S3VectorIndex-${env}`,
    });

    new CfnOutput(this, 'S3VectorIndexArn', {
      value: vectorIndex.getAtt('IndexArn').toString(),
      description: 'S3 Vectors index ARN — set as S3_VECTOR_INDEX_ARN (optional)',
      exportName: `${exportPrefix}S3VectorIndexArn-${env}`,
    });

    new CfnOutput(this, 'EmbeddingsBucketName', {
      value: embeddingsBucket.bucketName,
      description: 'Embeddings cache bucket — set as EMBEDDING_CACHE_BUCKET',
      exportName: `${exportPrefix}EmbeddingsBucket-${env}`,
    });
  }
}
