/**
 * CorpusViewer - Mac-app-style corpus browser with Shadcn UI
 *
 * Layout:
 * - Left: File tree (resizable)
 * - Center: File content viewer
 * - Right: Metadata sidebar with accordions (Extractions, Analysis, Recipes)
 */

import { useState } from 'react';
import { Resizable } from 're-resizable';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { FileTreePanel } from './FileTreePanel';
import { MetadataSidebar } from './MetadataSidebar';
import { AggregateStatsBar } from './AggregateStatsBar';

export interface CorpusViewerProps {
  corpusName: string;
  onClose: () => void;
}

export interface SelectedFile {
  id: string;
  relpath: string;
  mediaType: string;
  title?: string;
}

export function CorpusViewer({ corpusName, onClose }: CorpusViewerProps) {
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Top bar with corpus name and close button */}
      <div className="h-12 border-b flex items-center justify-between px-4 bg-muted/30">
        <h1 className="text-lg font-semibold">{corpusName}</h1>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Aggregate stats bar */}
      <AggregateStatsBar corpusName={corpusName} />

      {/* Main content area with resizable panels */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: File Tree */}
        <Resizable
          defaultSize={{ width: '35%', height: '100%' }}
          minWidth="20%"
          maxWidth="60%"
          enable={{ right: true }}
          handleStyles={{
            right: {
              width: '8px',
              right: '-4px',
              cursor: 'col-resize',
            },
          }}
          handleClasses={{
            right: 'bg-border hover:bg-primary/20 transition-colors',
          }}
        >
          <div className="h-full overflow-auto border-r">
            <div className="p-4">
              <FileTreePanel
                corpusName={corpusName}
                onFileSelect={setSelectedFile}
                selectedFileId={selectedFile?.id ?? null}
              />
            </div>
          </div>
        </Resizable>

        {/* Center Panel: File Viewer (when file selected) */}
        {selectedFile && (
          <Resizable
            defaultSize={{ width: '40%', height: '100%' }}
            minWidth="20%"
            maxWidth="60%"
            enable={{ right: true }}
            handleStyles={{
              right: {
                width: '8px',
                right: '-4px',
                cursor: 'col-resize',
              },
            }}
            handleClasses={{
              right: 'bg-border hover:bg-primary/20 transition-colors',
            }}
          >
            <div className="h-full overflow-auto border-r">
              <div className="p-8">
                <h2 className="text-2xl font-bold mb-4">
                  {selectedFile.title || selectedFile.relpath}
                </h2>
                <p className="text-sm text-muted-foreground mb-4">
                  {selectedFile.mediaType}
                </p>
                <div className="p-6 border rounded-lg bg-muted/30">
                  <p className="text-sm text-muted-foreground">
                    File viewer for {selectedFile.mediaType} coming soon...
                  </p>
                </div>
              </div>
            </div>
          </Resizable>
        )}

        {/* Right Panel: Metadata Sidebar */}
        <div className="flex-1 overflow-auto">
          <MetadataSidebar corpusName={corpusName} selectedFile={selectedFile} />
        </div>
      </div>
    </div>
  );
}
