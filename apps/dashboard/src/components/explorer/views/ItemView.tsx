import type { SpringstackNode } from 'springstack';
import {
  AudioContent,
  GenericContent,
  ImageContent,
  VideoContent
} from 'springstack';
import { CatalogItem, getDataMode } from '../../../lib/api';
import { Badge } from '@/components/ui/badge';
import { formatDisplayName } from '@/lib/utils';

const LOCAL_API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

interface ItemViewProps {
  item: CatalogItem;
}

function contentUrl(item: CatalogItem): string | undefined {
  if (getDataMode() !== 'local' || !item.corpusId) return undefined;
  return `${LOCAL_API_BASE}/corpora/${item.corpusId}/items/${item.id}/content`;
}

function buildContentNode(item: CatalogItem): SpringstackNode<{ url?: string; sizeKb?: number }> {
  const url = contentUrl(item);
  return {
    id: item.id,
    kind: item.mediaType,
    title: item.title || item.relpath,
    data: { url, sizeKb: item.bytes / 1024 },
  };
}

function ContentByMediaType({ item }: { item: CatalogItem }) {
  const node = buildContentNode(item);
  const mt = item.mediaType.toLowerCase();

  if (mt.startsWith('audio/')) {
    return <AudioContent node={node} />;
  }
  if (mt.startsWith('video/')) {
    return <VideoContent node={node} />;
  }
  if (mt.startsWith('image/')) {
    return <ImageContent node={node} />;
  }
  return <GenericContent node={node} />;
}

export function ItemView({ item }: ItemViewProps) {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-card rounded-xl shadow-sm">
        <div className="mb-8 p-2">
          <h2 className="text-3xl font-bold text-foreground mb-4">
            {formatDisplayName(item.title || item.relpath)}
          </h2>
          <div className="flex flex-wrap gap-2">
            <span className="text-muted-foreground uppercase text-sm">{item.mediaType}</span>
            {item.tags?.map(tag => (
              <Badge key={tag} variant="secondary" className="rounded-md font-bold text-muted-foreground bg-muted hover:bg-muted/80">{tag}</Badge>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 px-2">
          <div className="bg-muted/30 rounded-xl">
            <h3 className="text-xs font-bold text-muted-foreground uppercase mb-4 tracking-wider">Metadata</h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <dt className="text-muted-foreground font-medium">Size</dt>
                <dd className="font-bold text-foreground">{(item.bytes / 1024).toFixed(2)} KB</dd>
              </div>
              <div className="flex justify-between items-center">
                <dt className="text-muted-foreground font-medium">Created</dt>
                <dd className="font-bold text-foreground">{new Date(item.createdAt).toLocaleString()}</dd>
              </div>
              <div className="flex justify-between items-center">
                <dt className="text-muted-foreground font-medium">SHA256</dt>
                <dd className="font-mono text-xs text-muted-foreground bg-muted px-2 py-1 rounded truncate w-32" title={item.sha256}>{item.sha256}</dd>
              </div>
            </dl>
          </div>
          <div className="bg-muted/30 rounded-xl">
            <h3 className="text-xs font-bold text-muted-foreground uppercase mb-4 tracking-wider">Provenance</h3>
            <p className="text-sm text-foreground font-medium break-all">{item.sourceUri || 'Unknown Source'}</p>
          </div>
        </div>

        <div className="prose dark:prose-invert max-w-none">
          <h3 className="text-lg font-bold text-foreground mb-4 px-2">Preview</h3>
          <div className="bg-muted/30 rounded-xl min-h-[120px]">
            <ContentByMediaType item={item} />
          </div>
        </div>
      </div>
    </div>
  );
}
