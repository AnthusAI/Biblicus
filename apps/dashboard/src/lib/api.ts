/**
 * API abstraction layer that switches between local and cloud backends
 */

import { client } from './amplify-client';
import { localAPI } from './local-api';
import type { Corpus as LocalCorpus, CatalogItem as LocalCatalogItem, Snapshot as LocalSnapshot } from './local-api';

// Check if running in local mode (localhost or with local API available)
// Set VITE_USE_AMPLIFY=true to use production backend from local dev
const forceAmplify = import.meta.env.VITE_USE_AMPLIFY === 'true';
const isLocalMode = !forceAmplify && (import.meta.env.MODE === 'development' || import.meta.env.VITE_USE_LOCAL_API === 'true');

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
    console.log('[API] listCorpora called, isLocalMode:', isLocalMode, 'forceAmplify:', forceAmplify);

    if (isLocalMode) {
      try {
        console.log('[API] Trying local API...');
        return await localAPI.listCorpora();
      } catch (err) {
        console.warn('[API] Local API failed, falling back to Amplify:', err);
        // Fall through to Amplify client
      }
    }

    // Use Amplify client
    console.log('[API] Using Amplify client...');
    const { data: corpuses } = await client.models.Corpus.list();
    console.log('[API] Amplify returned', corpuses.length, 'corpuses:', corpuses);

    return {
      corpora: corpuses.map(c => ({
        name: c.name,
        s3Prefix: c.s3Prefix,
        lastActivity: c.lastActivity || undefined,
        itemCount: undefined, // TODO: Count from CatalogItems
        status: c.status || undefined,
      })),
    };
  }

  async getCorpus(name: string): Promise<Corpus> {
    if (isLocalMode) {
      try {
        return await localAPI.getCorpus(name);
      } catch (err) {
        console.warn('Local API failed, falling back to Amplify:', err);
      }
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
    if (isLocalMode) {
      try {
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
      } catch (err) {
        console.warn('Local API failed, falling back to Amplify:', err);
      }
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

  async listSnapshots(corpusName: string): Promise<{ snapshots: Snapshot[] }> {
    if (isLocalMode) {
      try {
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
      } catch (err) {
        console.warn('Local API failed, falling back to Amplify:', err);
      }
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
    if (isLocalMode) {
      try {
        return await localAPI.getConfig();
      } catch (err) {
        console.warn('Local API failed:', err);
      }
    }

    // In cloud mode, return a placeholder
    return { corporaRoot: 's3://biblicus-corpus' };
  }
}

export const api = new APIAdapter();
