import { useEffect, useState } from 'react';
import { api, Corpus, CatalogItem } from '../../../lib/api';
import { MediaTypeIcon } from '@/lib/mediaTypeIcon';
import { formatDisplayName } from '@/lib/utils';

interface CorpusViewProps {
  corpus: Corpus;
  onSelect: (item: CatalogItem) => void;
  cachedItems?: CatalogItem[];
  onLoaded?: (items: CatalogItem[]) => void;
}

export function CorpusView({ corpus, onSelect, cachedItems, onLoaded }: CorpusViewProps) {
  const [items, setItems] = useState<CatalogItem[]>(cachedItems || []);
  const [loading, setLoading] = useState(!cachedItems);

  useEffect(() => {
    if (cachedItems) {
        setItems(cachedItems);
        setLoading(false);
        return;
    }

    api.listCatalogItems(corpus.name).then(res => {
      setItems(res.items);
      setLoading(false);
      onLoaded?.(res.items);
    });
  }, [corpus.name, cachedItems]);

  if (loading) return <div className="text-muted-foreground">Loading items...</div>;

  return (
    <div className="flex flex-col">
      <div className="grid grid-cols-1 gap-2">
        {items.map(item => (
               <div
                  key={item.id}
                  className="p-2 rounded-xl bg-card shadow-flat-muted hover:bg-hover transition-colors cursor-pointer"
                  data-flip-id={`card-item-${item.id}`}
                  onClick={() => onSelect(item)}
               >
                  <div className="flex items-baseline gap-2 text-sm">
                    <div
                        className="flex items-center justify-center shrink-0 self-baseline"
                        data-flip-id={`icon-item-${item.id}`}
                        style={{ height: '1em', width: '1em' }}
                    >
                        <MediaTypeIcon mediaType={item.mediaType} className="w-full h-full text-muted-foreground" />
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                        <div className="flex items-baseline gap-2">
                            <span
                              className="font-bold text-foreground truncate block flex-1 leading-none"
                              data-flip-id={`title-text-item-${item.id}`}
                            >
                                {formatDisplayName(item.title || item.relpath)}
                            </span>
                        </div>
                        <div
                          className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground font-bold h-4"
                          data-flip-id={`meta-row-item-${item.id}`}
                        >
                            <span className="uppercase">{item.mediaType}</span>
                            <span>{(item.bytes / 1024).toFixed(0)} KB</span>
                        </div>
                    </div>
                  </div>
               </div>
        ))}
        {items.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">No items found in this corpus.</div>
        )}
      </div>
    </div>
  );
}
