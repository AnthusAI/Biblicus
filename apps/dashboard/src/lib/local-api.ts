/**
 * Local API client for browsing Biblicus corpora from the filesystem
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

export interface Corpus {
  name: string;
  path: string;
  lastModified: string;
  itemCount?: number;
  schemaVersion?: number;
  configurationId?: string;
}

export interface CatalogItem {
  id: string;
  relpath: string;
  sha256: string;
  bytes: number;
  media_type: string;
  title?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  created_at: string;
  source_uri?: string;
}

export interface Snapshot {
  id: string;
  type?: string;
  configuration_id?: string;
  createdAt?: string;
  total_items?: number;
  completed_items?: number;
}

export interface Config {
  corporaRoot: string;
}

class LocalAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }));
      throw new Error(error.error || 'Request failed');
    }

    return response.json();
  }

  // List all corpora
  async listCorpora(): Promise<{ corpora: Corpus[] }> {
    return this.fetch('/corpora');
  }

  // Get a specific corpus
  async getCorpus(name: string): Promise<Corpus> {
    return this.fetch(`/corpora/${name}`);
  }

  // List catalog items with optional filters
  async listCatalogItems(
    corpusName: string,
    filters?: {
      tag?: string;
      mediaType?: string;
      search?: string;
    }
  ): Promise<{ items: CatalogItem[]; total: number }> {
    const params = new URLSearchParams();
    if (filters?.tag) params.set('tag', filters.tag);
    if (filters?.mediaType) params.set('mediaType', filters.mediaType);
    if (filters?.search) params.set('search', filters.search);

    const query = params.toString() ? `?${params.toString()}` : '';
    return this.fetch(`/corpora/${corpusName}/catalog${query}`);
  }

  // Get a specific catalog item
  async getCatalogItem(corpusName: string, itemId: string): Promise<CatalogItem> {
    return this.fetch(`/corpora/${corpusName}/catalog/${itemId}`);
  }

  // List extraction snapshots
  async listSnapshots(corpusName: string): Promise<{ snapshots: Snapshot[] }> {
    return this.fetch(`/corpora/${corpusName}/snapshots`);
  }

  // Get configuration
  async getConfig(): Promise<Config> {
    return this.fetch('/config');
  }

  // Set corpora root path
  async setConfig(config: { corporaRoot: string }): Promise<{ success: boolean; corporaRoot: string }> {
    return this.fetch('/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }
}

export const localAPI = new LocalAPIClient();
