import { useEffect, useState, useRef } from 'react';
import { useGSAP } from '@gsap/react';
import { api, type Corpus } from '../lib/api';
import { CorpusViewer } from '../components/viewer/CorpusViewer';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Folder } from 'lucide-react';
import { fadeInStagger } from '../lib/animations';

export default function HomePage() {
  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [corporaRoot, setCorporaRoot] = useState<string>('');
  const [selectedCorpus, setSelectedCorpus] = useState<string | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadCorpora = async () => {
      try {
        const [corporaData, config] = await Promise.all([
          api.listCorpora(),
          api.getConfig(),
        ]);
        setCorpora(corporaData.corpora);
        setCorporaRoot(config.corporaRoot);
        setLoading(false);
      } catch (err) {
        console.error('Failed to load corpora:', err);
        setError(err instanceof Error ? err.message : 'Failed to load corpora');
        setLoading(false);
      }
    };

    loadCorpora();
  }, []);

  useGSAP(() => {
    if (gridRef.current && corpora.length > 0) {
      fadeInStagger(gridRef.current, { stagger: 0.08 });
    }
  }, [corpora.length]);

  const handleCorpusSelect = (corpusName: string) => {
    setSelectedCorpus(corpusName);
  };

  const handleCorpusClose = () => {
    setSelectedCorpus(null);
  };

  // Show CorpusViewer if corpus is selected
  if (selectedCorpus) {
    return <CorpusViewer corpusName={selectedCorpus} onClose={handleCorpusClose} />;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-xl text-muted-foreground">Loading corpora...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="max-w-2xl mx-auto p-8">
          <h1 className="text-3xl font-bold mb-4">API Server Not Available</h1>
          <p className="text-muted-foreground mb-4">
            Could not connect to the local API server.
          </p>
          <Card className="bg-muted p-6 mb-4">
            <p className="text-sm font-semibold mb-2">To start the server:</p>
            <pre className="bg-muted-foreground/10 p-4 rounded-lg mt-2 text-xs overflow-x-auto">
npm run dev:all
            </pre>
            <p className="text-sm mt-2">
              Or start the server separately:
            </p>
            <pre className="bg-muted-foreground/10 p-4 rounded-lg mt-2 text-xs overflow-x-auto">
npm run server
            </pre>
          </Card>
          <p className="text-sm text-muted-foreground">
            Error details: {error}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="container mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-5xl font-bold">
            Biblicus Corpus Viewer
          </h1>
          <div className="text-sm text-muted-foreground">
            Browsing: <code className="bg-muted px-3 py-1 rounded-lg">{corporaRoot}</code>
          </div>
        </div>

        {corpora.length === 0 ? (
          <Card className="p-8">
            <p className="text-muted-foreground mb-4">No corpora found in the configured folder.</p>
            <p className="text-sm text-muted-foreground">
              Make sure the corpora folder contains valid Biblicus corpora with a <code className="bg-muted px-2 py-1 rounded">metadata/</code> directory.
            </p>
          </Card>
        ) : (
          <div ref={gridRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {corpora.map((corpus) => (
              <Card
                key={corpus.name}
                onClick={() => handleCorpusSelect(corpus.name)}
                className="p-6 cursor-pointer transition-transform hover:scale-105"
              >
                <div className="flex items-center gap-3 mb-3">
                  <Folder className="h-8 w-8 text-muted-foreground" />
                  <h2 className="text-2xl font-semibold">
                    {corpus.name}
                  </h2>
                </div>
                <div className="text-sm space-y-1">
                  {corpus.itemCount !== undefined && (
                    <div className="text-muted-foreground">
                      <span className="font-medium text-foreground">{corpus.itemCount}</span> items
                    </div>
                  )}
                  <div className="text-muted-foreground">
                    Modified {new Date(corpus.lastModified).toLocaleDateString()}
                  </div>
                  {corpus.hasMetadata && (
                    <div className="mt-2">
                      <Badge variant="secondary">Has Metadata</Badge>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
