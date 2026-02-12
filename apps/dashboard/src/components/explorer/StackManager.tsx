import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatedSelector, Springstack, SpringstackSettings, useSpringstackAppearance } from 'springstack';
import type {
  SpringstackHelpers,
  SpringstackNode,
  SpringstackRenderers,
  SpringstackTimingMode
} from 'springstack';
import { Cloud, Database, Folder, ScrollText, Settings } from 'lucide-react';
import { MediaTypeIcon } from '@/lib/mediaTypeIcon';
import { formatDisplayName } from '@/lib/utils';
import { Corpus, CatalogItem, api, getDataMode, setDataMode, type DataMode } from '../../lib/api';
import { ItemView } from './views/ItemView';

interface ExplorerNodeData {
  corpus?: Corpus;
  item?: CatalogItem;
  corpusName?: string;
}


const buildRootNode = (mode: DataMode): SpringstackNode<ExplorerNodeData> => ({
  id: 'root',
  kind: 'root',
  title: mode === 'cloud' ? 'Cloud' : 'Local'
});

const buildCorpusNode = (corpus: Corpus): SpringstackNode<ExplorerNodeData> => ({
  id: corpus.name,
  kind: 'corpus',
  title: corpus.name,
  data: { corpus }
});

const buildItemNode = (item: CatalogItem, corpusName: string): SpringstackNode<ExplorerNodeData> => ({
  id: String(item.id),
  kind: 'item',
  title: formatDisplayName(item.title || item.relpath),
  data: { item, corpusName }
});

export function StackManager() {
  const { appearance, motion, setAppearance, setMotion } = useSpringstackAppearance({
    storageKey: 'biblicus-appearance',
    motionKey: 'biblicus-motion',
    defaults: { theme: 'cool', mode: 'system', motionPreset: 'system' }
  });
  const { reduceMotion } = appearance;
  const { timingMode } = motion;
  const [dataMode, setDataModeState] = useState<DataMode>(getDataMode());
  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [corporaLoading, setCorporaLoading] = useState(true);
  const [itemsByCorpus, setItemsByCorpus] = useState<Record<string, CatalogItem[]>>({});
  const [itemsLoading, setItemsLoading] = useState<Record<string, boolean>>({});
  const [itemDetailCache, setItemDetailCache] = useState<Record<string, Record<string, CatalogItem>>>({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [stackSnapshot, setStackSnapshot] = useState<SpringstackNode<ExplorerNodeData>[]>([
    buildRootNode(getDataMode())
  ]);
  const helpersRef = useRef<SpringstackHelpers<ExplorerNodeData> | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const durationMap: Record<SpringstackTimingMode, number> = {
      normal: 220,
      reduced: 80,
      gratuitous: 220,
      slow: 880,
      off: 0
    };
    root.style.setProperty('--theme-transition-duration', `${durationMap[timingMode]}ms`);
    return () => {
      root.style.removeProperty('--theme-transition-duration');
    };
  }, [timingMode]);

  useEffect(() => {
    setCorporaLoading(true);
    api
      .listCorpora()
      .then(res => {
        setCorpora(res.corpora);
      })
      .finally(() => setCorporaLoading(false));
  }, [dataMode]);

  const activeNode = stackSnapshot[stackSnapshot.length - 1];
  const activeCorpusNode = [...stackSnapshot].reverse().find(node => node.kind === 'corpus');
  const activeItemNode = activeNode?.kind === 'item' ? activeNode : undefined;
  const activeCorpusName = activeCorpusNode?.id;
  const activeItemCorpusName = activeItemNode?.data?.corpusName ?? activeCorpusName;
  const isAmplifyHosting = import.meta.env.VITE_AMPLIFY_HOSTING === 'true';

  useEffect(() => {
    if (!activeCorpusName) return;
    if (itemsByCorpus[activeCorpusName] || itemsLoading[activeCorpusName]) return;
    setItemsLoading(prev => ({ ...prev, [activeCorpusName]: true }));
    api
      .listCatalogItems(activeCorpusName)
      .then(res => {
        setItemsByCorpus(prev => ({ ...prev, [activeCorpusName]: res.items }));
      })
      .finally(() =>
        setItemsLoading(prev => ({ ...prev, [activeCorpusName]: false }))
      );
  }, [activeCorpusName, itemsByCorpus, itemsLoading]);

  useEffect(() => {
    if (!activeItemNode || !activeItemCorpusName) return;
    const itemId = activeItemNode.id;
    const cachedItem = itemDetailCache[activeItemCorpusName]?.[itemId];
    if (cachedItem) return;
    api.getCatalogItem(activeItemCorpusName, itemId).then(item => {
      setItemDetailCache(prev => ({
        ...prev,
        [activeItemCorpusName]: { ...prev[activeItemCorpusName], [String(item.id)]: item }
      }));
      const helpers = helpersRef.current;
      if (!helpers) return;
      const nextStack = stackSnapshot.map(node => {
        if (node.kind === 'item' && node.id === itemId) {
          return {
            ...node,
            title: formatDisplayName(item.title || item.relpath),
            data: { item, corpusName: activeItemCorpusName }
          };
        }
        return node;
      });
      helpers.setStack(nextStack);
    });
  }, [activeItemNode, activeItemCorpusName, itemDetailCache, stackSnapshot]);

  useEffect(() => {
    const helpers = helpersRef.current;
    if (!helpers) return;
    const nextStack = stackSnapshot.map((node, index) => {
      if (node.kind === 'corpus' && !node.data?.corpus) {
        const corpus = corpora.find(entry => entry.name === node.id);
        if (corpus) {
          return { ...node, title: corpus.name, data: { corpus } };
        }
      }
      if (node.kind === 'item' && !node.data?.corpusName) {
        const corpusNode = [...stackSnapshot.slice(0, index)].reverse().find(entry => entry.kind === 'corpus');
        if (corpusNode) {
          return { ...node, data: { ...node.data, corpusName: corpusNode.id } };
        }
      }
      return node;
    });
    const changed = nextStack.some((node, index) => node !== stackSnapshot[index]);
    if (changed) {
      helpers.setStack(nextStack);
    }
  }, [corpora, stackSnapshot]);

  useEffect(() => {
    if (!activeCorpusName) return;
    if (activeNode?.kind !== 'corpus') return;
    const helpers = helpersRef.current;
    if (!helpers) return;
    const items = itemsByCorpus[activeCorpusName] ?? [];
    if (items.length === 0) return;
    requestAnimationFrame(() => helpers.notifyPanelReady('corpus'));
  }, [activeCorpusName, activeNode?.kind, itemsByCorpus]);


  const renderers = useMemo<SpringstackRenderers<ExplorerNodeData>>(() => {
    const renderRootMeta = () => (
      <span className="text-xs text-muted-foreground">{corpora.length} corpora</span>
    );

    const renderCorpusMeta = (corpus?: Corpus) => (
      <span className="text-xs text-muted-foreground">
        {corpus?.itemCount ?? 0} items
      </span>
    );

    const renderItemMeta = (item?: CatalogItem) => {
      if (!item) return null;
      return (
        <span className="text-xs text-muted-foreground">
          {item.mediaType} · {(item.bytes / 1024).toFixed(0)} KB
        </span>
      );
    };

    const renderBody = (
      icon: React.ReactNode,
      title?: string,
      meta?: React.ReactNode,
      trailing?: React.ReactNode
    ) => (
      <div className="flex w-full items-start gap-1">
        {icon}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-sm font-semibold text-foreground">{title}</span>
            {trailing}
          </div>
          {meta}
        </div>
      </div>
    );

    return {
      list: {
        root: node =>
          renderBody(
            dataMode === 'cloud'
              ? <Cloud className="mt-0.5 h-4 w-4 text-muted-foreground" strokeWidth={2.25} />
              : <Database className="mt-0.5 h-4 w-4 text-muted-foreground" strokeWidth={2.25} />,
            node.title,
            renderRootMeta()
          ),
        corpus: node =>
          renderBody(
            <Folder className="mt-0.5 h-4 w-4 text-muted-foreground" strokeWidth={2.25} />,
            node.title,
            renderCorpusMeta(node.data?.corpus)
          ),
        item: node =>
          renderBody(
            <MediaTypeIcon
              mediaType={node.data?.item?.mediaType ?? ''}
              className="mt-0.5 h-4 w-4 text-muted-foreground"
            />,
            node.title,
            renderItemMeta(node.data?.item)
          )
      },
      crumb: {
        root: node =>
          renderBody(
            dataMode === 'cloud'
              ? <Cloud className="mt-0.5 h-4 w-4 text-muted-foreground" strokeWidth={2.25} />
              : <Database className="mt-0.5 h-4 w-4 text-muted-foreground" strokeWidth={2.25} />,
            node.title,
            renderRootMeta()
          ),
        corpus: node =>
          renderBody(
            <Folder className="mt-0.5 h-4 w-4 text-muted-foreground" strokeWidth={2.25} />,
            node.title,
            renderCorpusMeta(node.data?.corpus)
          ),
        item: node =>
          renderBody(
            <MediaTypeIcon
              mediaType={node.data?.item?.mediaType ?? ''}
              className="mt-0.5 h-4 w-4 text-muted-foreground"
            />,
            node.title,
            renderItemMeta(node.data?.item)
          )
      }
    };
  }, [corpora.length, dataMode]);

  const selectorMotion = useMemo(() => {
    const baseDuration = 560;
    const baseEnter = 130;
    const presets: Record<SpringstackTimingMode, { durationMs: number; ease: string; enterDurationMs: number }> = {
      normal: { durationMs: baseDuration, ease: 'back.out(1.6)', enterDurationMs: baseEnter },
      reduced: { durationMs: 200, ease: 'power2.out', enterDurationMs: 80 },
      gratuitous: { durationMs: baseDuration, ease: 'elastic.out(1.6, 0.5)', enterDurationMs: baseEnter },
      slow: { durationMs: baseDuration * 4, ease: 'back.out(1.6)', enterDurationMs: baseEnter * 4 },
      off: { durationMs: 0, ease: 'none', enterDurationMs: 0 }
    };
    return presets[timingMode];
  }, [timingMode]);

  const renderPanels = (helpers: SpringstackHelpers<ExplorerNodeData>) => {
    helpersRef.current = helpers;

    const corpusItems = activeCorpusName ? itemsByCorpus[activeCorpusName] ?? [] : [];
    const activeItem =
      activeItemNode?.data?.item ??
      (activeItemNode && activeItemCorpusName
        ? itemDetailCache[activeItemCorpusName]?.[activeItemNode.id]
        : undefined);

    return (
      <>
        <div className="basis-full shrink-0" {...helpers.getPanelProps('root')}>
          <div className="flex h-full flex-col gap-2 p-2">
            <div className="font-eyebrow text-xs text-muted-foreground">Corpora</div>
            {corporaLoading && <div className="text-sm text-muted-foreground">Loading corpora...</div>}
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
              {corpora.map(corpus => {
                const node = buildCorpusNode(corpus);
                const cardProps = helpers.getCardProps(node, {
                  onSelect: (_node, sourceEl) => helpers.push(node, sourceEl)
                });
                return (
                  <button
                    key={corpus.name}
                    type="button"
                    {...cardProps}
                    className={`flex w-full items-start gap-2 rounded-md bg-muted p-2 text-left text-sm transition-colors hover:bg-hover ${
                      cardProps.className ?? ''
                    }`}
                    data-enter-item
                    data-item-type="corpus"
                    data-item-id={corpus.name}
                  >
                    <div data-card-shell="true" className="flex w-full items-start gap-2">
                      <div data-card-content="true" className="flex w-full items-start gap-2">
                        {(renderers.list?.corpus ?? renderers.list?.default)?.(node)}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="basis-full shrink-0" {...helpers.getPanelProps('corpus')}>
          <div className="flex h-full flex-col gap-2 p-2">
            <div className="font-eyebrow text-xs text-muted-foreground">
              {activeCorpusName ? `Items in ${activeCorpusName}` : 'Items'}
            </div>
            {activeCorpusName && itemsLoading[activeCorpusName] && (
              <div className="text-sm text-muted-foreground">Loading items...</div>
            )}
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
              {activeCorpusName && corpusItems.map(item => {
                const node = buildItemNode(item, activeCorpusName);
                const cardProps = helpers.getCardProps(node, {
                  onSelect: (_node, sourceEl) => helpers.push(node, sourceEl)
                });
                return (
                  <button
                    key={item.id}
                    type="button"
                    {...cardProps}
                    className={`flex w-full items-start gap-2 rounded-md bg-muted p-2 text-left text-sm transition-colors hover:bg-hover ${
                      cardProps.className ?? ''
                    }`}
                    data-enter-item
                    data-item-type="item"
                    data-item-id={item.id}
                  >
                    <div data-card-shell="true" className="flex w-full items-start gap-2">
                      <div data-card-content="true" className="flex w-full items-start gap-2">
                        {(renderers.list?.item ?? renderers.list?.default)?.(node)}
                      </div>
                    </div>
                  </button>
                );
              })}
              {!activeCorpusName && (
                <div className="text-sm text-muted-foreground">Select a corpus to view its items.</div>
              )}
            </div>
          </div>
        </div>

        <div className="basis-full shrink-0" {...helpers.getPanelProps('item')}>
          <div className="p-2">
            {activeItem ? (
              <ItemView item={activeItem} />
            ) : (
              <div className="text-sm text-muted-foreground">Select an item to view details.</div>
            )}
          </div>
        </div>
      </>
    );
  };

  const handleToggleMode = (nextMode: DataMode) => {
    setDataMode(nextMode);
    setDataModeState(nextMode);
    setCorpora([]);
    setCorporaLoading(true);
    setItemsByCorpus({});
    setItemsLoading({});
    setItemDetailCache({});
    const helpers = helpersRef.current;
    if (helpers) {
      helpers.setStack([buildRootNode(nextMode)]);
    } else {
      setStackSnapshot([buildRootNode(nextMode)]);
    }
  };

  const initialStack = useMemo(() => [buildRootNode(dataMode)], [dataMode]);

  return (
    <div className="min-h-screen bg-background text-foreground p-2">
      <Springstack<ExplorerNodeData>
        initialStack={initialStack}
        timingMode={timingMode}
        onStackChange={setStackSnapshot}
        renderers={renderers}
        enterAnimation={{ durationMs: reduceMotion ? 200 : 500, staggerMs: reduceMotion ? 0 : 40 }}
        renderHeader={() => (
          <div className="flex items-center gap-2 p-2 sm:gap-4" style={{ scrollbarGutter: 'stable' }}>
            <div className="flex items-center gap-1 pl-2 font-headline text-sm font-semibold text-foreground">
              <ScrollText
                className="topbar-icon text-muted-foreground"
                strokeWidth={2.25}
                size={16}
                style={{ width: 16, height: 16 }}
              />
              Biblicus
            </div>
            {!isAmplifyHosting && (
              <div className="flex flex-1 items-center justify-end sm:justify-center [&_span.text-xs]:hidden [&_span.text-xs]:sm:inline">
                <div className="min-w-[96px] shrink-0 sm:w-auto">
                  <AnimatedSelector
                    name="data-mode"
                    value={dataMode}
                    onChange={value => handleToggleMode(value as DataMode)}
                    layout="compact"
                    className="grid-cols-2"
                    motionDisabled={timingMode === 'off'}
                    motionDurationMs={selectorMotion.durationMs}
                    motionEase={selectorMotion.ease}
                    motionEnterDurationMs={selectorMotion.enterDurationMs}
                    options={[
                      { id: 'local', label: 'Local', icon: Database },
                      { id: 'cloud', label: 'Cloud', icon: Cloud }
                    ]}
                  />
                </div>
              </div>
            )}
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="flex h-8 w-8 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
            >
              <Settings
                className="topbar-icon text-muted-foreground"
                strokeWidth={2.25}
                size={16}
                style={{ width: 16, height: 16 }}
              />
            </button>
          </div>
        )}
        renderPanels={renderPanels}
        renderOverlay={() =>
          settingsOpen ? (
            <SpringstackSettings
              open={settingsOpen}
              onOpenChange={setSettingsOpen}
              appearance={appearance}
              motion={motion}
              setAppearance={setAppearance}
              setMotion={setMotion}
              selectorMotion={selectorMotion}
            />
          ) : null
        }
      />
    </div>
  );
}
