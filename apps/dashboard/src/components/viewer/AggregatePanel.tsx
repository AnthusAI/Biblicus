/**
 * AggregatePanel Component
 *
 * Displays aggregate statistics for a corpus.
 * Shows file counts by type, total bytes, average sizes, distributions.
 */

import { useEffect, useState, useRef } from 'react';
import { useGSAP } from '@gsap/react';
import { localAPI, type CatalogItem } from '../../lib/local-api';
import { fadeInStagger } from '../../lib/animations';

export interface AggregatePanelProps {
  corpusName: string;
  onClose: () => void;
}

interface AggregateStats {
  totalFiles: number;
  totalBytes: number;
  averageSize: number;
  mediaTypeCounts: Record<string, number>;
  tagCounts: Record<string, number>;
}

export function AggregatePanel({ corpusName, onClose }: AggregatePanelProps) {
  const [stats, setStats] = useState<AggregateStats | null>(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const { items } = await localAPI.listCatalogItems(corpusName);

        // Calculate aggregate statistics
        const mediaTypeCounts: Record<string, number> = {};
        const tagCounts: Record<string, number> = {};
        let totalBytes = 0;

        items.forEach((item: CatalogItem) => {
          // Count media types
          mediaTypeCounts[item.media_type] = (mediaTypeCounts[item.media_type] || 0) + 1;

          // Count tags
          item.tags?.forEach((tag) => {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
          });

          // Sum bytes
          totalBytes += item.bytes;
        });

        const aggregateStats: AggregateStats = {
          totalFiles: items.length,
          totalBytes,
          averageSize: items.length > 0 ? totalBytes / items.length : 0,
          mediaTypeCounts,
          tagCounts,
        };

        setStats(aggregateStats);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load aggregate stats:', err);
        setLoading(false);
      }
    };

    loadStats();
  }, [corpusName]);

  useGSAP(() => {
    if (containerRef.current && stats) {
      fadeInStagger(containerRef.current, { stagger: 0.08 });
    }
  }, [stats]);

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  if (loading) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <div className="text-gray-600">Loading statistics...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <div className="text-gray-600">Failed to load statistics</div>
      </div>
    );
  }

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-3xl font-bold text-gray-900">{corpusName}</h2>
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 hover:text-gray-900 rounded-full bg-gray-200 hover:bg-gray-300 transition-colors"
        >
          ←
        </button>
      </div>

      <div ref={containerRef} className="space-y-6">
        {/* Total Files */}
        <div className="p-6 bg-blue-100 rounded-3xl">
          <div className="text-sm text-blue-800 font-semibold mb-1">Total Files</div>
          <div className="text-4xl font-bold text-blue-900">{stats.totalFiles.toLocaleString()}</div>
        </div>

        {/* Total Size */}
        <div className="p-6 bg-green-100 rounded-3xl">
          <div className="text-sm text-green-800 font-semibold mb-1">Total Size</div>
          <div className="text-4xl font-bold text-green-900">{formatBytes(stats.totalBytes)}</div>
        </div>

        {/* Average Size */}
        <div className="p-6 bg-purple-100 rounded-3xl">
          <div className="text-sm text-purple-800 font-semibold mb-1">Average Size</div>
          <div className="text-4xl font-bold text-purple-900">{formatBytes(stats.averageSize)}</div>
        </div>

        {/* Media Types */}
        {Object.keys(stats.mediaTypeCounts).length > 0 && (
          <div className="p-6 bg-orange-100 rounded-3xl">
            <div className="text-sm text-orange-800 font-semibold mb-3">Media Types</div>
            <div className="space-y-2">
              {Object.entries(stats.mediaTypeCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span className="text-orange-900 font-medium">{type}</span>
                    <span className="text-2xl font-bold text-orange-900">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Top Tags */}
        {Object.keys(stats.tagCounts).length > 0 && (
          <div className="p-6 bg-pink-100 rounded-3xl">
            <div className="text-sm text-pink-800 font-semibold mb-3">Top Tags</div>
            <div className="space-y-2">
              {Object.entries(stats.tagCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([tag, count]) => (
                  <div key={tag} className="flex items-center justify-between">
                    <span className="text-pink-900 font-medium truncate">{tag}</span>
                    <span className="text-2xl font-bold text-pink-900">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
