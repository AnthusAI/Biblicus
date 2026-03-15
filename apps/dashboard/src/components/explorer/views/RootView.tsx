import { useEffect, useState } from 'react';
import { api, Corpus } from '../../../lib/api';
import { Folder, Hash, FileText } from 'lucide-react';

interface RootViewProps {
  onSelect: (corpus: Corpus) => void;
  corpora: Corpus[];
  loading?: boolean;
  stackedCorpora?: string[]; // Corpus names that are in the breadcrumb stack
  isActive?: boolean; // Whether RootView is the active view
}

export function RootView({ onSelect, corpora, loading, stackedCorpora = [], isActive = true }: RootViewProps) {
  if (loading) return <div className="text-muted-foreground p-8">Loading corpora...</div>;

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-2`}>
      {corpora.map((corpus, corpusIndex) => {
        const isInStack = stackedCorpora.includes(corpus.name);

        // If in stack, don't render here - it's rendered in breadcrumb area
        if (isInStack) return null;

        return (
          <div
            key={corpus.name}
            onClick={() => onSelect(corpus)}
            className="h-full"
          >
            {/* Flat Card: No border, shadow-sm, bg-card */}
            <div
              className="p-2 cursor-pointer rounded-xl bg-card shadow-sm hover:bg-muted/50 transition-colors group h-full flex flex-col"
              data-flip-id={`card-corpus-${corpus.name.trim()}`}
            >
            <div className="flex items-baseline gap-2 text-sm">
              {/* Icon Group: Muted background, dark icon */}
              <div 
                className="flex items-center justify-center shrink-0 self-baseline"
                data-flip-id={`icon-corpus-${corpus.name}`}
                style={{ width: '1em', height: '1em' }}
              >
                <Folder className="w-full h-full text-muted-foreground block" strokeWidth={2.25} />
              </div>
              
              <div className="flex flex-col min-w-0 flex-1 pt-1.5">
                <h2 
                    className="text-sm font-bold text-foreground leading-none truncate" 
                    data-flip-id={`title-text-corpus-${corpus.name}`}
                >
                    {corpus.name}
                </h2>
                
                {/* Item Count (Aligned with title, moved here) */}
                <div 
                    className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground font-bold h-4"
                    data-flip-id={`meta-row-corpus-${corpus.name}`}
                >
                    <span className="flex items-center gap-1">
                        <FileText className="w-3 h-3" strokeWidth={2.25} /> {corpus.itemCount || '?'}
                    </span>
                </div>

                {/* Last Updated (Only in Full View) */}
                {corpus.lastActivity && (
                    <span 
                        className="text-[10px] font-medium text-muted-foreground mt-0.5 block flip-animate"
                        data-flip-id={`last-activity-corpus-${corpus.name}`}
                    >
                        Updated {new Date(corpus.lastActivity).toLocaleDateString()}
                    </span>
                )}
              </div>
            </div>
            
            <p className="text-sm text-muted-foreground line-clamp-2 mt-auto pt-4 pl-12 hidden">
               {corpus.s3Prefix || 'Local corpus storage'}
            </p>
          </div>
        </div>
        );
      })}
    </div>
  );
}
