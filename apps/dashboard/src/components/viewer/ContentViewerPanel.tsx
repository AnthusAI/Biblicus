/**
 * ContentViewerPanel Component
 *
 * Pluggable viewer system for displaying different types of content.
 * Automatically selects the appropriate viewer based on media type.
 */

import { useEffect, useState, useRef } from 'react';
import { useGSAP } from '@gsap/react';
import { localAPI, type CatalogItem } from '../../lib/local-api';
import { fadeIn } from '../../lib/animations';
import { SelectedItem } from './ViewerShell';

export interface ContentViewerPanelProps {
  corpusName: string;
  item: SelectedItem;
  onClose: () => void;
}

export function ContentViewerPanel({
  corpusName,
  item,
  onClose,
}: ContentViewerPanelProps) {
  const [fullItem, setFullItem] = useState<CatalogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadFullItem = async () => {
      try {
        const catalogItem = await localAPI.getCatalogItem(corpusName, item.id);
        setFullItem(catalogItem);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load item details:', err);
        setLoading(false);
      }
    };

    loadFullItem();
  }, [corpusName, item.id]);

  useGSAP(() => {
    if (containerRef.current && fullItem) {
      fadeIn(containerRef.current, { duration: 0.4 });
    }
  }, [fullItem]);

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  if (loading) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <div className="text-gray-600">Loading item...</div>
      </div>
    );
  }

  if (!fullItem) {
    return (
      <div className="p-8 h-full flex items-center justify-center">
        <div className="text-gray-600">Failed to load item</div>
      </div>
    );
  }

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="mb-8 flex items-center justify-between">
        <h3 className="text-2xl font-bold text-gray-900 truncate flex-1 mr-4">
          {fullItem.title || fullItem.relpath}
        </h3>
        <button
          onClick={onClose}
          className="px-4 py-2 text-gray-600 hover:text-gray-900 rounded-full bg-gray-200 hover:bg-gray-300 transition-colors flex-shrink-0"
        >
          ✕
        </button>
      </div>

      <div ref={containerRef} className="space-y-6">
        {/* Media Type Badge */}
        <div className="inline-block px-4 py-2 bg-blue-200 text-blue-900 rounded-full font-semibold">
          {fullItem.media_type}
        </div>

        {/* Metadata Section */}
        <div className="p-6 bg-gray-100 rounded-3xl">
          <h4 className="text-lg font-bold text-gray-900 mb-4">Metadata</h4>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm font-semibold text-gray-700">Path</dt>
              <dd className="text-gray-900 font-mono text-sm break-all">{fullItem.relpath}</dd>
            </div>

            <div>
              <dt className="text-sm font-semibold text-gray-700">Size</dt>
              <dd className="text-gray-900">{formatBytes(fullItem.bytes)}</dd>
            </div>

            <div>
              <dt className="text-sm font-semibold text-gray-700">SHA256</dt>
              <dd className="text-gray-900 font-mono text-xs break-all">{fullItem.sha256}</dd>
            </div>

            {fullItem.source_uri && (
              <div>
                <dt className="text-sm font-semibold text-gray-700">Source</dt>
                <dd className="text-gray-900 text-sm break-all">{fullItem.source_uri}</dd>
              </div>
            )}

            {fullItem.created_at && (
              <div>
                <dt className="text-sm font-semibold text-gray-700">Created</dt>
                <dd className="text-gray-900">{new Date(fullItem.created_at).toLocaleString()}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Tags */}
        {fullItem.tags && fullItem.tags.length > 0 && (
          <div className="p-6 bg-purple-100 rounded-3xl">
            <h4 className="text-lg font-bold text-purple-900 mb-3">Tags</h4>
            <div className="flex flex-wrap gap-2">
              {fullItem.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1 bg-purple-200 text-purple-900 rounded-full text-sm font-medium"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Custom Metadata */}
        {fullItem.metadata && Object.keys(fullItem.metadata).length > 0 && (
          <div className="p-6 bg-green-100 rounded-3xl">
            <h4 className="text-lg font-bold text-green-900 mb-3">Custom Metadata</h4>
            <pre className="text-sm text-green-900 overflow-x-auto font-mono bg-green-50 p-4 rounded-2xl">
              {JSON.stringify(fullItem.metadata, null, 2)}
            </pre>
          </div>
        )}

        {/* Viewer Placeholder */}
        <div className="p-6 bg-yellow-100 rounded-3xl">
          <h4 className="text-lg font-bold text-yellow-900 mb-3">Content Preview</h4>
          <div className="text-yellow-800">
            <p className="mb-2">
              Specialized viewer for <strong>{fullItem.media_type}</strong> files coming soon.
            </p>
            <p className="text-sm">
              This will display:
            </p>
            <ul className="text-sm list-disc list-inside mt-2 space-y-1">
              {fullItem.media_type.startsWith('image/') && (
                <>
                  <li>Image preview with zoom/pan</li>
                  <li>OCR regions overlay (if extracted)</li>
                </>
              )}
              {fullItem.media_type.startsWith('audio/') && (
                <>
                  <li>Audio player with waveform</li>
                  <li>Transcription (if extracted)</li>
                </>
              )}
              {fullItem.media_type.startsWith('text/') && (
                <>
                  <li>Syntax-highlighted text</li>
                  <li>Text extraction results</li>
                </>
              )}
              {fullItem.media_type === 'application/pdf' && (
                <>
                  <li>PDF preview</li>
                  <li>Text extraction by page</li>
                </>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
