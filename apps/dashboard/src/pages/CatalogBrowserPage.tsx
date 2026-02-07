import { useEffect, useState, useRef } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { client, type CatalogItem } from '../lib/amplify-client';
import CatalogItemCard from '../components/catalog/CatalogItemCard';
import CatalogFilters from '../components/catalog/CatalogFilters';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export default function CatalogBrowserPage() {
  const { corpusName } = useParams<{ corpusName: string }>();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const tag = searchParams.get('tag');
  const mediaType = searchParams.get('mediaType');
  const search = searchParams.get('search');

  useEffect(() => {
    if (!corpusName) return;

    let subscription: any;

    // Build query based on filters
    if (tag) {
      // Use GSI for single tag
      subscription = client.models.CatalogItem.observeQuery({
        filter: {
          corpusId: { eq: corpusName },
          tags: { contains: tag }
        }
      }).subscribe({
        next: ({ items: fetchedItems }) => {
          let filtered = fetchedItems;

          // Client-side search filter
          if (search) {
            filtered = filtered.filter(item =>
              item.title?.toLowerCase().includes(search.toLowerCase()) ||
              item.relpath.toLowerCase().includes(search.toLowerCase())
            );
          }

          setItems(filtered);
          setLoading(false);
        }
      });
    } else if (mediaType) {
      // Use GSI for media type
      subscription = client.models.CatalogItem.observeQuery({
        filter: {
          corpusId: { eq: corpusName },
          mediaType: { eq: mediaType }
        }
      }).subscribe({
        next: ({ items: fetchedItems }) => {
          let filtered = fetchedItems;

          // Client-side search filter
          if (search) {
            filtered = filtered.filter(item =>
              item.title?.toLowerCase().includes(search.toLowerCase()) ||
              item.relpath.toLowerCase().includes(search.toLowerCase())
            );
          }

          setItems(filtered);
          setLoading(false);
        }
      });
    } else {
      // List all items for corpus
      subscription = client.models.CatalogItem.observeQuery({
        filter: { corpusId: { eq: corpusName } }
      }).subscribe({
        next: ({ items: fetchedItems }) => {
          let filtered = fetchedItems;

          // Client-side search filter
          if (search) {
            filtered = filtered.filter(item =>
              item.title?.toLowerCase().includes(search.toLowerCase()) ||
              item.relpath.toLowerCase().includes(search.toLowerCase())
            );
          }

          setItems(filtered);
          setLoading(false);
        }
      });
    }

    return () => subscription?.unsubscribe();
  }, [corpusName, tag, mediaType, search]);

  // Animate items on load/filter change
  useGSAP(() => {
    if (containerRef.current && items.length > 0) {
      gsap.fromTo(
        containerRef.current.children,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, stagger: 0.05, duration: 0.5, ease: 'power2.out' }
      );
    }
  }, [items.length, tag, mediaType, search]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading catalog...</div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="container mx-auto">
        <div className="mb-8">
          <Link
            to={`/corpus/${corpusName}`}
            className="text-blue-600 hover:underline mb-2 inline-block"
          >
            ← Back to {corpusName}
          </Link>
          <h1 className="text-5xl font-bold text-gray-900">
            {corpusName} Catalog
          </h1>
        </div>

        <CatalogFilters />

        {items.length === 0 ? (
          <div className="bg-white p-8 rounded-lg shadow mt-6">
            <p className="text-gray-600">No items found.</p>
          </div>
        ) : (
          <div
            ref={containerRef}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6"
          >
            {items.map(item => (
              <CatalogItemCard key={item.itemId} item={item} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
