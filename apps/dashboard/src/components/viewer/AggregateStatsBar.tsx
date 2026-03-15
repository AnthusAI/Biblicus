/**
 * AggregateStatsBar - Horizontal stats bar showing corpus overview
 */

import { useEffect, useState } from 'react';
import { localAPI } from '@/lib/local-api';
import { Card } from '@/components/ui/card';

export interface AggregateStatsBarProps {
  corpusName: string;
}

interface Stats {
  totalFiles: number;
  totalBytes: number;
  mediaTypeCounts: Record<string, number>;
}

export function AggregateStatsBar({ corpusName }: AggregateStatsBarProps) {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const { items } = await localAPI.listCatalogItems(corpusName);

        const mediaTypeCounts: Record<string, number> = {};
        let totalBytes = 0;

        items.forEach((item) => {
          mediaTypeCounts[item.media_type] = (mediaTypeCounts[item.media_type] || 0) + 1;
          totalBytes += item.bytes;
        });

        setStats({
          totalFiles: items.length,
          totalBytes,
          mediaTypeCounts,
        });
      } catch (err) {
        console.error('Failed to load stats:', err);
      }
    };

    loadStats();
  }, [corpusName]);

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  if (!stats) return null;

  return (
    <div className="border-b bg-muted/10 px-4 py-2">
      <div className="flex gap-6 items-center text-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Files:</span>
          <span className="font-semibold">{stats.totalFiles.toLocaleString()}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Total Size:</span>
          <span className="font-semibold">{formatBytes(stats.totalBytes)}</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Types:</span>
          <div className="flex gap-2">
            {Object.entries(stats.mediaTypeCounts)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 3)
              .map(([type, count]) => (
                <span key={type} className="text-xs px-2 py-0.5 bg-muted rounded-full">
                  {type.split('/')[1] || type}: {count}
                </span>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
