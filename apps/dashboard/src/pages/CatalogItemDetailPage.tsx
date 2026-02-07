import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { client, type CatalogItem, type FileMetadata } from '../lib/amplify-client';

export default function CatalogItemDetailPage() {
  const { corpusName, itemId } = useParams<{ corpusName: string; itemId: string }>();
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [extractions, setExtractions] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!corpusName || !itemId) return;

    // Load catalog item
    client.models.CatalogItem.get({
      corpusId: corpusName,
      itemId: itemId
    }).then(({ data }) => {
      setItem(data || null);
      setLoading(false);
    });

    // Load extractions for this item
    client.models.FileMetadata.observeQuery({
      filter: {
        corpusId: { eq: corpusName },
        filePath: { contains: itemId }
      }
    }).subscribe({
      next: ({ items }) => {
        setExtractions(items);
      }
    });
  }, [corpusName, itemId]);

  if (loading || !item) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading item...</div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="container mx-auto">
        <div className="mb-8">
          <Link
            to={`/corpus/${corpusName}/catalog`}
            className="text-blue-600 hover:underline mb-2 inline-block"
          >
            ← Back to catalog
          </Link>
          <h1 className="text-4xl font-bold mb-2 text-gray-900">
            {item.title || item.relpath}
          </h1>

          <div className="flex gap-2 flex-wrap">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded">
              {item.mediaType}
            </span>
            {item.tags?.map(tag => (
              <span key={tag} className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-2xl font-semibold mb-4 text-gray-900">Metadata</h2>
              <dl className="space-y-3">
                <div>
                  <dt className="font-semibold text-gray-700">Path:</dt>
                  <dd className="text-gray-600 break-all">{item.relpath}</dd>
                </div>

                <div>
                  <dt className="font-semibold text-gray-700">SHA256:</dt>
                  <dd className="font-mono text-xs text-gray-600 break-all">{item.sha256}</dd>
                </div>

                <div>
                  <dt className="font-semibold text-gray-700">Size:</dt>
                  <dd className="text-gray-600">{(item.bytes / 1024).toFixed(1)} KB</dd>
                </div>

                {item.sourceUri && (
                  <div>
                    <dt className="font-semibold text-gray-700">Source:</dt>
                    <dd className="text-gray-600 break-all">{item.sourceUri}</dd>
                  </div>
                )}

                <div>
                  <dt className="font-semibold text-gray-700">Created:</dt>
                  <dd className="text-gray-600">{new Date(item.createdAt).toLocaleString()}</dd>
                </div>
              </dl>

              {item.metadataJson && (
                <div className="mt-6">
                  <h3 className="text-xl font-semibold mb-2 text-gray-900">Custom Metadata</h3>
                  <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto">
                    {JSON.stringify(item.metadataJson, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-2xl font-semibold mb-4 text-gray-900">Extractions</h2>

              {extractions.length === 0 ? (
                <p className="text-gray-600">No extractions yet.</p>
              ) : (
                <div className="space-y-3">
                  {extractions.map((extraction) => (
                    <div
                      key={extraction.filePath}
                      className="p-4 border rounded hover:border-blue-400 transition"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-sm text-gray-700">
                          {extraction.filePath.split('/').pop()}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          extraction.status === 'AVAILABLE' ? 'bg-green-100 text-green-800' :
                          extraction.status === 'UPLOADING' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {extraction.status}
                        </span>
                      </div>
                      {extraction.size && (
                        <div className="text-xs text-gray-500">
                          {(extraction.size / 1024).toFixed(1)} KB
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
