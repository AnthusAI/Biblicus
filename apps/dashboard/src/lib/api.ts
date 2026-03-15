/**
 * API abstraction layer that switches between local and cloud backends
 */

import { client } from './amplify-client';
import { localAPI } from './local-api';

const DATA_MODE_KEY = 'biblicus-data-mode';
const isAmplifyHosting = import.meta.env.VITE_AMPLIFY_HOSTING === 'true';

export type DataMode = 'local' | 'cloud';

export const getDataMode = (): DataMode => {
  if (isAmplifyHosting) return 'cloud';
  if (typeof window === 'undefined') return 'local';
  const stored = localStorage.getItem(DATA_MODE_KEY);
  return stored === 'cloud' ? 'cloud' : 'local';
};

export const setDataMode = (mode: DataMode) => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(DATA_MODE_KEY, mode);
};

export interface Corpus {
  name: string;
  path?: string;
  s3Prefix?: string;
  lastModified?: string;
  lastActivity?: string;
  itemCount?: number;
  status?: 'IDLE' | 'ACTIVE' | 'SYNCING';
}

export interface CatalogItem {
  id: string;
  corpusId: string;
  relpath: string;
  sha256: string;
  bytes: number;
  mediaType: string;
  title?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  createdAt: string;
  sourceUri?: string;
  hasExtraction?: boolean;
}

export interface Snapshot {
  id: string;
  corpusId: string;
  snapshotId: string;
  type?: 'EXTRACTION' | 'ANALYSIS' | 'GRAPH' | 'RETRIEVAL';
  status?: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  totalItems?: number;
  completedItems?: number;
  startTime?: string;
  endTime?: string;
}

class APIAdapter {
  async listCorpora(): Promise<{ corpora: Corpus[] }> {
    if (getDataMode() === 'local') {
      return await localAPI.listCorpora();
    }

    // Use Amplify client
    const { data: corpuses } = await client.models.Corpus.list();

    // Deduplicate by name
    const uniqueCorpora = Array.from(
      new Map(corpuses.map(c => [c.name, c])).values()
    );

    return {
      corpora: uniqueCorpora.map(c => ({
        name: c.name,
        s3Prefix: c.s3Prefix,
        lastActivity: c.lastActivity || undefined,
        itemCount: undefined, // TODO: Count from CatalogItems
        status: c.status || undefined,
      })),
    };
  }

  async getCorpus(name: string): Promise<Corpus> {
    if (getDataMode() === 'local') {
      return await localAPI.getCorpus(name);
    }

    // Use Amplify client - find by name
    const { data: corpuses } = await client.models.Corpus.list({
      filter: { name: { eq: name } },
    });

    if (corpuses.length === 0) {
      throw new Error(`Corpus not found: ${name}`);
    }

    const corpus = corpuses[0];
    return {
      name: corpus.name,
      s3Prefix: corpus.s3Prefix,
      lastActivity: corpus.lastActivity || undefined,
      status: corpus.status || undefined,
    };
  }

  async listCatalogItems(
    corpusName: string,
    filters?: {
      tag?: string;
      mediaType?: string;
      search?: string;
    }
  ): Promise<{ items: CatalogItem[]; total: number }> {
    if (getDataMode() === 'local') {
      const result = await localAPI.listCatalogItems(corpusName, filters);
      return {
        items: result.items.map(item => ({
          id: item.id,
          corpusId: corpusName,
          relpath: item.relpath,
          sha256: item.sha256,
          bytes: item.bytes,
          mediaType: item.media_type,
          title: item.title,
          tags: item.tags,
          metadata: item.metadata,
          createdAt: item.created_at,
          sourceUri: item.source_uri,
        })),
        total: result.total,
      };
    }

    // Use Amplify client
    let query;
    if (filters?.mediaType) {
      // Use GSI for media type filtering
      const { data } = await client.models.CatalogItem.itemsByMediaType({
        mediaType: filters.mediaType,
      }, {
        filter: { corpusId: { eq: corpusName } },
      });
      query = data;
    } else {
      // List all items for corpus
      const { data } = await client.models.CatalogItem.list({
        filter: { corpusId: { eq: corpusName } },
      });
      query = data;
    }

    // Client-side filtering for search and tags
    let filtered = query;
    if (filters?.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(item =>
        item.title?.toLowerCase().includes(searchLower) ||
        item.relpath.toLowerCase().includes(searchLower)
      );
    }
    if (filters?.tag) {
      filtered = filtered.filter(item =>
        item.tags?.includes(filters.tag!)
      );
    }

    return {
      items: filtered.map(item => ({
        id: item.itemId,
        corpusId: item.corpusId,
        relpath: item.relpath,
        sha256: item.sha256,
        bytes: item.bytes,
        mediaType: item.mediaType,
        title: item.title || undefined,
        tags: item.tags || undefined,
        metadata: item.metadataJson ? JSON.parse(JSON.stringify(item.metadataJson)) : undefined,
        createdAt: item.createdAt,
        sourceUri: item.sourceUri || undefined,
        hasExtraction: item.hasExtraction || undefined,
      })),
      total: filtered.length,
    };
  }

  async getCatalogItem(corpusName: string, itemId: string): Promise<CatalogItem> {
    if (getDataMode() === 'local') {
      const item = await localAPI.getCatalogItem(corpusName, itemId);
      return {
        id: item.id,
        corpusId: corpusName,
        relpath: item.relpath,
        sha256: item.sha256,
        bytes: item.bytes,
        mediaType: item.media_type,
        title: item.title,
        tags: item.tags,
        metadata: item.metadata,
        createdAt: item.created_at,
        sourceUri: item.source_uri,
      };
    }

    const { data } = await client.models.CatalogItem.list({
      filter: {
        corpusId: { eq: corpusName },
        itemId: { eq: itemId },
      },
    });

    if (!data.length) {
      throw new Error(`Catalog item not found: ${itemId}`);
    }

    const item = data[0];
    return {
      id: item.itemId,
      corpusId: item.corpusId,
      relpath: item.relpath,
      sha256: item.sha256,
      bytes: item.bytes,
      mediaType: item.mediaType,
      title: item.title || undefined,
      tags: item.tags || undefined,
      metadata: item.metadataJson ? JSON.parse(JSON.stringify(item.metadataJson)) : undefined,
      createdAt: item.createdAt,
      sourceUri: item.sourceUri || undefined,
      hasExtraction: item.hasExtraction || undefined,
    };
  }

  async listSnapshots(corpusName: string): Promise<{ snapshots: Snapshot[] }> {
    if (getDataMode() === 'local') {
      const result = await localAPI.listSnapshots(corpusName);
      return {
        snapshots: result.snapshots.map(s => ({
          id: s.id,
          corpusId: corpusName,
          snapshotId: s.id,
          type: s.type as any,
          totalItems: s.total_items,
          completedItems: s.completed_items,
        })),
      };
    }

    // Use Amplify client
    const { data: snapshots } = await client.models.Snapshot.list({
      filter: { corpusId: { eq: corpusName } },
    });

    return {
      snapshots: snapshots.map(s => ({
        id: `${s.corpusId}/${s.snapshotId}`,
        corpusId: s.corpusId,
        snapshotId: s.snapshotId,
        type: s.type || undefined,
        status: s.status || undefined,
        totalItems: s.totalItems || undefined,
        completedItems: s.completedItems || undefined,
        startTime: s.startTime || undefined,
        endTime: s.endTime || undefined,
      })),
    };
  }

  async getConfig(): Promise<{ corporaRoot: string }> {
    if (getDataMode() === 'local') {
      return await localAPI.getConfig();
    }

    // In cloud mode, return a placeholder
    return { corporaRoot: 's3://biblicus-corpus' };
  }
}

export const api = new APIAdapter();
