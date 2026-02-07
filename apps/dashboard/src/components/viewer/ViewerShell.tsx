/**
 * ViewerShell Component
 *
 * Main 3-panel container that orchestrates the animation-based UI.
 * Manages panel visibility and coordinates GSAP transitions.
 *
 * Layout progression (left to right = general to specific):
 * - Panel 1 (Left): Aggregate statistics
 * - Panel 2 (Center): File tree
 * - Panel 3 (Right): Content viewer
 */

import { useState, useCallback } from 'react';
import { Panel } from './Panel';
import { AggregatePanel } from './AggregatePanel';
import { FileTreePanel } from './FileTreePanel';
import { ContentViewerPanel } from './ContentViewerPanel';

export interface ViewerShellProps {
  corpusName: string | null;
  onClose?: () => void;
}

export interface SelectedItem {
  id: string;
  relpath: string;
  mediaType: string;
  title?: string;
}

export function ViewerShell({ corpusName, onClose }: ViewerShellProps) {
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);

  const handleItemSelect = useCallback((item: SelectedItem) => {
    setSelectedItem(item);
  }, []);

  const handleCloseViewer = useCallback(() => {
    setSelectedItem(null);
  }, []);

  const handleCloseCorpus = useCallback(() => {
    setSelectedItem(null);
    onClose?.();
  }, [onClose]);

  // Determine panel visibility based on state
  const showAggregate = corpusName !== null;
  const showFileTree = corpusName !== null;
  const showContentViewer = selectedItem !== null;

  // Calculate panel positions and widths
  const aggregateWidth = showContentViewer ? '25%' : showFileTree ? '33.333%' : '100%';
  const fileTreeWidth = showContentViewer ? '35%' : '66.667%';
  const viewerWidth = '40%';

  return (
    <div className="relative w-full h-screen overflow-hidden bg-gray-50">
      {/* Panel 1: Aggregate Statistics (always visible when corpus selected) */}
      {corpusName && (
        <Panel
          isVisible={showAggregate}
          width={aggregateWidth}
          backgroundColor="bg-gray-100"
          className="left-0 rounded-r-3xl"
          zIndex={10}
          animateIn="fade"
          animateOut="fade"
        >
          <AggregatePanel corpusName={corpusName} onClose={handleCloseCorpus} />
        </Panel>
      )}

      {/* Panel 2: File Tree (slides in when corpus selected) */}
      {corpusName && (
        <Panel
          isVisible={showFileTree}
          width={fileTreeWidth}
          backgroundColor="bg-white"
          className="rounded-r-3xl"
          style={{ left: showContentViewer ? '25%' : '33.333%' }}
          zIndex={20}
          animateIn="slide"
          animateOut="slide"
        >
          <FileTreePanel
            corpusName={corpusName}
            onItemSelect={handleItemSelect}
            selectedItemId={selectedItem?.id ?? null}
          />
        </Panel>
      )}

      {/* Panel 3: Content Viewer (slides in when item selected) */}
      {selectedItem && (
        <Panel
          isVisible={showContentViewer}
          width={viewerWidth}
          backgroundColor="bg-gray-50"
          className="right-0 rounded-l-3xl"
          zIndex={30}
          animateIn="slide"
          animateOut="slide"
        >
          <ContentViewerPanel
            corpusName={corpusName!}
            item={selectedItem}
            onClose={handleCloseViewer}
          />
        </Panel>
      )}
    </div>
  );
}
