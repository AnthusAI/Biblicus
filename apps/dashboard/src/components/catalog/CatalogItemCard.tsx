import { Link } from 'react-router-dom';
import { type CatalogItem } from '../../lib/amplify-client';

interface CatalogItemCardProps {
  item: CatalogItem;
}

export default function CatalogItemCard({ item }: CatalogItemCardProps) {
  return (
    <Link
      to={`/corpus/${item.corpusId}/catalog/${item.itemId}`}
      className="block p-6 bg-white border rounded-lg hover:shadow-lg transition-shadow"
    >
      <h3 className="text-xl font-semibold mb-2 text-gray-900">
        {item.title || item.relpath}
      </h3>

      <div className="flex gap-2 mb-2 flex-wrap">
        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
          {item.mediaType}
        </span>
        {item.hasExtraction && (
          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
            Extracted
          </span>
        )}
      </div>

      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.tags.slice(0, 3).map(tag => (
            <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
              {tag}
            </span>
          ))}
          {item.tags.length > 3 && (
            <span className="px-2 py-1 text-gray-500 text-xs">
              +{item.tags.length - 3} more
            </span>
          )}
        </div>
      )}

      <p className="text-sm text-gray-500">
        {(item.bytes / 1024).toFixed(1)} KB
      </p>
    </Link>
  );
}
