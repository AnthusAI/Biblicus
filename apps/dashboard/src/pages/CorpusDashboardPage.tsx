import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { client, type Snapshot } from '../lib/amplify-client';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export default function CorpusDashboardPage() {
  const { corpusName } = useParams<{ corpusName: string }>();
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!corpusName) return;

    // Subscribe to real-time updates
    const subscription = client.models.Snapshot.observeQuery({
      filter: { corpusId: { eq: corpusName } },
    }).subscribe({
      next: ({ items }) => {
        // Sort by createdAt descending
        const sorted = [...items].sort((a, b) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );
        setSnapshots(sorted);
        setLoading(false);
      },
    });

    return () => subscription.unsubscribe();
  }, [corpusName]);

  // Animate snapshots on load
  useGSAP(() => {
    if (containerRef.current && snapshots.length > 0) {
      gsap.fromTo(
        containerRef.current.children,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, stagger: 0.08, duration: 0.6, ease: 'power2.out' }
      );
    }
  }, [snapshots.length]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading corpus...</div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="container mx-auto">
        <div className="mb-8">
          <Link to="/" className="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to all corpora
          </Link>
          <h1 className="text-5xl font-bold text-gray-900">{corpusName}</h1>
        </div>

        <div className="mb-8">
          <Link
            to={`/corpus/${corpusName}/catalog`}
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Browse Catalog
          </Link>
        </div>

        <h2 className="text-3xl font-semibold mb-6 text-gray-900">Snapshots</h2>

        {snapshots.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow">
            <p className="text-gray-600">No snapshots yet.</p>
          </div>
        ) : (
          <div ref={containerRef} className="space-y-4">
            {snapshots.map((snapshot) => (
              <div
                key={snapshot.snapshotId}
                className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-xl font-semibold mb-2">
                      {snapshot.snapshotId}
                    </h3>
                    <div className="flex gap-3 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <span className={`inline-block w-2 h-2 rounded-full ${
                          snapshot.status === 'COMPLETED' ? 'bg-green-500' :
                          snapshot.status === 'IN_PROGRESS' ? 'bg-yellow-500' :
                          snapshot.status === 'FAILED' ? 'bg-red-500' :
                          'bg-gray-400'
                        }`}></span>
                        {snapshot.status}
                      </span>
                      <span>{snapshot.snapshotType}</span>
                      <span>
                        {snapshot.processedItems} / {snapshot.totalItems} items
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(snapshot.createdAt).toLocaleString()}
                  </div>
                </div>

                {snapshot.status === 'IN_PROGRESS' && snapshot.totalItems > 0 && (
                  <div className="mt-4">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{
                          width: `${(snapshot.processedItems / snapshot.totalItems) * 100}%`
                        }}
                      ></div>
                    </div>
                  </div>
                )}

                {snapshot.errorMessage && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                    {snapshot.errorMessage}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
