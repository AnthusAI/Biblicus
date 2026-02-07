/**
 * MetadataSidebar - Photoshop-style accordion panels for metadata
 *
 * Shows expandable sections for:
 * - Extractions
 * - Analysis Results
 * - Recipes
 * - File Info
 */

import { useEffect, useState } from 'react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { FileText, FlaskConical, FileCode, Info } from 'lucide-react';
import type { SelectedFile } from './CorpusViewer';

export interface MetadataSidebarProps {
  corpusName: string;
  selectedFile: SelectedFile | null;
}

interface ExtractionSnapshot {
  id: string;
  createdAt?: string;
}

interface AnalysisRun {
  id: string;
  type: string;
  createdAt?: string;
}

export function MetadataSidebar({ corpusName, selectedFile }: MetadataSidebarProps) {
  const [extractions, setExtractions] = useState<ExtractionSnapshot[]>([]);
  const [analysisRuns, setAnalysisRuns] = useState<AnalysisRun[]>([]);
  const [recipes, setRecipes] = useState<string[]>([]);

  useEffect(() => {
    async function loadMetadata() {
      if (!corpusName) return;

      const API_BASE = 'http://localhost:3001';

      try {
        // Load extraction snapshots
        const snapshotsRes = await fetch(`${API_BASE}/api/corpora/${corpusName}/snapshots`);
        if (snapshotsRes.ok) {
          const snapshotsData = await snapshotsRes.json();
          setExtractions(snapshotsData.snapshots || []);
        }
      } catch (err) {
        console.error('Error loading snapshots:', err);
      }

      try {
        // Load analysis runs
        const analysisRes = await fetch(`${API_BASE}/api/corpora/${corpusName}/analysis`);
        if (analysisRes.ok) {
          const analysisData = await analysisRes.json();
          setAnalysisRuns(analysisData.analysisRuns || []);
        }
      } catch (err) {
        console.error('Error loading analysis:', err);
      }

      try {
        // Load recipes
        const recipesRes = await fetch(`${API_BASE}/api/corpora/${corpusName}/recipes`);
        if (recipesRes.ok) {
          const recipesData = await recipesRes.json();
          setRecipes(recipesData.recipes.map((r: any) => r.path) || []);
        }
      } catch (err) {
        console.error('Error loading recipes:', err);
      }
    }

    loadMetadata();
  }, [corpusName]);

  return (
    <div className="h-full border-l bg-muted/5 flex flex-col">
      <div className="p-4 flex-shrink-0">
        <h2 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wide">
          Metadata
        </h2>
      </div>

      <div className="flex-1 overflow-hidden px-4 pb-4">
        <Accordion type="multiple" defaultValue={['extractions', 'analysis']} className="w-full space-y-2">
          {/* Extractions Panel */}
          <AccordionItem value="extractions" className="border rounded-lg overflow-hidden">
            <AccordionTrigger className="hover:no-underline py-3 px-3">
              <div className="flex items-center gap-2 w-full">
                <FileText className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm font-medium">Extractions</span>
                {extractions.length > 0 && (
                  <Badge variant="secondary" className="ml-auto">
                    {extractions.length}
                  </Badge>
                )}
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3">
              <ScrollArea className="max-h-[300px]">
                {extractions.length > 0 ? (
                  <div className="space-y-2 pb-2 pr-3">
                    {extractions.map((extraction) => (
                      <div
                        key={extraction.id}
                        className="p-2 rounded-md hover:bg-accent cursor-pointer text-sm"
                      >
                        <div className="font-medium truncate">{extraction.id}</div>
                        {extraction.createdAt && (
                          <div className="text-xs text-muted-foreground">
                            {new Date(extraction.createdAt).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground pb-2">
                    No extraction snapshots found
                  </p>
                )}
              </ScrollArea>
            </AccordionContent>
          </AccordionItem>

          {/* Analysis Panel */}
          <AccordionItem value="analysis" className="border rounded-lg overflow-hidden">
            <AccordionTrigger className="hover:no-underline py-3 px-3">
              <div className="flex items-center gap-2 w-full">
                <FlaskConical className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm font-medium">Analysis</span>
                {analysisRuns.length > 0 && (
                  <Badge variant="secondary" className="ml-auto">
                    {analysisRuns.length}
                  </Badge>
                )}
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3">
              <ScrollArea className="max-h-[300px]">
                {analysisRuns.length > 0 ? (
                  <div className="space-y-2 pb-2 pr-3">
                    {analysisRuns.map((run) => (
                      <div
                        key={run.id}
                        className="p-2 rounded-md hover:bg-accent cursor-pointer text-sm"
                      >
                        <div className="font-medium capitalize">{run.type}</div>
                        <div className="text-xs text-muted-foreground truncate">{run.id}</div>
                        {run.createdAt && (
                          <div className="text-xs text-muted-foreground">
                            {new Date(run.createdAt).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground pb-2">
                    No analysis runs found
                  </p>
                )}
              </ScrollArea>
            </AccordionContent>
          </AccordionItem>

          {/* Recipes Panel */}
          <AccordionItem value="recipes" className="border rounded-lg overflow-hidden">
            <AccordionTrigger className="hover:no-underline py-3 px-3">
              <div className="flex items-center gap-2 w-full">
                <FileCode className="h-4 w-4 flex-shrink-0" />
                <span className="text-sm font-medium">Recipes</span>
                {recipes.length > 0 && (
                  <Badge variant="secondary" className="ml-auto">
                    {recipes.length}
                  </Badge>
                )}
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3">
              <ScrollArea className="max-h-[200px]">
                {recipes.length > 0 ? (
                  <div className="space-y-1 pb-2 pr-3">
                    {recipes.map((recipe) => (
                      <div
                        key={recipe}
                        className="p-2 rounded-md hover:bg-accent cursor-pointer text-sm"
                      >
                        <div className="font-mono text-xs truncate">{recipe}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground pb-2">
                    No recipes found
                  </p>
                )}
              </ScrollArea>
            </AccordionContent>
          </AccordionItem>

          {/* File Info Panel - Only shown when file is selected */}
          {selectedFile && (
            <AccordionItem value="info" className="border rounded-lg overflow-hidden">
              <AccordionTrigger className="hover:no-underline py-3 px-3">
                <div className="flex items-center gap-2 w-full">
                  <Info className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm font-medium">File Info</span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-3">
                <div className="space-y-2 pb-2 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Path</div>
                    <div className="font-mono text-xs break-all">{selectedFile.relpath}</div>
                  </div>
                  <Separator />
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Type</div>
                    <Badge variant="outline">{selectedFile.mediaType}</Badge>
                  </div>
                  <Separator />
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">ID</div>
                    <div className="font-mono text-xs">{selectedFile.id}</div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          )}
        </Accordion>
      </div>
    </div>
  );
}
