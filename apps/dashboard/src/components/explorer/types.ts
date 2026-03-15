import { Corpus, CatalogItem } from '../../lib/api';

export type ViewType = 'root' | 'corpus' | 'item';

export interface BaseStackItem {
  id: string;
  type: ViewType;
  title: string;
}

export interface RootStackItem extends BaseStackItem {
  type: 'root';
  cachedCorpora?: Corpus[];
}

export interface CorpusStackItem extends BaseStackItem {
  type: 'corpus';
  data: Corpus;
  cachedItems?: CatalogItem[];
}

export interface ItemStackItem extends BaseStackItem {
  type: 'item';
  data: CatalogItem;
}

export type StackItem = RootStackItem | CorpusStackItem | ItemStackItem;

export interface ExplorerState {
  stack: StackItem[];
}
