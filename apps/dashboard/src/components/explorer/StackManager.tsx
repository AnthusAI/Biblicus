import { useRef, useState, useEffect, useLayoutEffect } from 'react';
import { flushSync } from 'react-dom';
import gsap from 'gsap';
import { Flip } from 'gsap/Flip';
import { useGSAP } from '@gsap/react';
import { Settings, Folder, FileText } from 'lucide-react';
import { StackItem } from './types';
import { RootView } from './views/RootView';
import { CorpusView } from './views/CorpusView';
import { ItemView } from './views/ItemView';
import { Breadcrumb } from './Breadcrumb';
import { AppearanceSidebar } from './AppearanceSidebar';
import { useAppearance } from '../../lib/useAppearance';
import { formatDisplayName } from '@/lib/utils';
import { Corpus, CatalogItem, api } from '../../lib/api'; // Added import for Corpus/CatalogItem and api

gsap.registerPlugin(Flip);

export function StackManager() {
  const [stack, setStack] = useState<StackItem[]>([
    { id: 'root', type: 'root', title: 'Biblicus' }
  ]);
  
  // Centralized Data Cache to prevent "pop" animations/loading states during navigation
  const [corpusCache, setCorpusCache] = useState<Corpus[] | undefined>(undefined);
  const [itemCache, setItemCache] = useState<Record<string, CatalogItem[]>>({});

  // Track which corpus items to display
  const [activeCorpusItems, setActiveCorpusItems] = useState<CatalogItem[]>([]);
  const activeCorpusNameRef = useRef<string | null>(null);
  const corpusRequestIdRef = useRef(0);
  const exitOverlayRef = useRef<HTMLDivElement | null>(null);
  const exitTimelineRef = useRef<gsap.core.Timeline | null>(null);
  
  // Hoisted fetching for root view data to ensure it's always available synchronously for Flip
  useEffect(() => {
    if (!corpusCache) {
        api.listCorpora().then(res => {
            // STRICT DEDUPLICATION: Ensure unique corpus names
            const unique = Array.from(new Map(res.corpora.map(c => [c.name, c])).values());
            setCorporaState(unique);
            setCorpusCache(unique);
        });
    }
  }, []);

  // Use local state for corpora in StackManager so we can pass it down ready-to-go
  const [corporaState, setCorporaState] = useState<Corpus[]>([]);

  const [isTransitioning, setIsTransitioning] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
      // Use the hook to ensure theme is applied, even if we don't use the setters here directly
  const { reduceMotion } = useAppearance();

  const containerRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<Flip.FlipState | null>(null);
  const previousStackRef = useRef<StackItem[]>(stack);
  const placeholdersRef = useRef<HTMLElement[]>([]);

  // --- Actions ---

  const pushStack = (item: StackItem) => {
    if (!containerRef.current) return;

    // Capture state BEFORE any changes
    stateRef.current = Flip.getState('[data-flip-id]');

    // Force synchronous state update so DOM changes immediately
    flushSync(() => {
      setStack(prev => [...prev, item]);
      if (sidebarOpen) setSidebarOpen(false);
    });
  };

  const cleanupExitOverlay = () => {
    exitTimelineRef.current?.kill();
    exitTimelineRef.current = null;
    if (exitOverlayRef.current) {
      exitOverlayRef.current.remove();
      exitOverlayRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      cleanupExitOverlay();
    };
  }, []);

  const popToIndex = (index: number) => {
    if (!containerRef.current) return;

    // Capture current state BEFORE any changes
    const goingToRoot = index === 0;
    const visibleBefore = goingToRoot
      ? Array.from(
          containerRef.current.querySelectorAll('[data-item-card]')
        )
          .map(el => el as HTMLElement)
          .map(el => ({
            element: el,
            rect: el.getBoundingClientRect()
          }))
      : [];
    if (goingToRoot) {
      cleanupExitOverlay();
      stateRef.current = Flip.getState('[data-flip-id]:not([data-flip-id*="-item-"])');
    } else {
      stateRef.current = Flip.getState('[data-flip-id]');
    }

    // Force synchronous state update so DOM changes immediately
    flushSync(() => {
      setStack(prev => prev.slice(0, index + 1));
      if (goingToRoot) {
        setActiveCorpusItems([]);
      }
      if (sidebarOpen) setSidebarOpen(false);
    });

    if (goingToRoot && visibleBefore.length > 0) {
      const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
      const visibleClones = visibleBefore.filter(({ rect }) => rect.bottom > 0 && rect.top < viewportHeight);
      if (visibleClones.length === 0) return;

      const overlay = document.createElement('div');
      overlay.style.position = 'fixed';
      overlay.style.left = '0';
      overlay.style.top = '0';
      overlay.style.width = '100%';
      overlay.style.height = '100%';
      overlay.style.pointerEvents = 'none';
      overlay.style.zIndex = '9999';
      document.body.appendChild(overlay);
      exitOverlayRef.current = overlay;

      const clones = visibleClones.map(({ element, rect }) => {
        const clone = element.cloneNode(true) as HTMLElement;
        clone.style.position = 'fixed';
        clone.style.left = `${rect.left}px`;
        clone.style.top = `${rect.top}px`;
        clone.style.width = `${rect.width}px`;
        clone.style.height = `${rect.height}px`;
        clone.style.margin = '0';
        clone.style.transform = 'none';
        clone.style.opacity = '1';
        overlay.appendChild(clone);
        return { clone, rect };
      });

      clones.sort((a, b) => b.rect.bottom - a.rect.bottom);

      const stepDuration = reduceMotion ? 0.12 : 0.2;
      const startGap = reduceMotion ? 20 : 40;
      const timeline = gsap.timeline({
        onComplete: () => {
          cleanupExitOverlay();
        }
      });
      clones.forEach((entry, index) => {
        timeline.to(
          entry.clone,
          {
            opacity: 0,
            y: window.innerHeight,
            duration: stepDuration,
            ease: 'power3.in'
          },
          index * startGap / 1000
        );
      });
      exitTimelineRef.current = timeline;
    }
  };

  const handleBreadcrumbClick = (item: StackItem, index: number) => {
    // Navigate back to this item's level
    popToIndex(index);
  };

  const updateActiveItemCache = (cache: Partial<StackItem>) => {
    // Deprecated in favor of centralized state, but kept to prevent breakages if referenced elsewhere
    // No-op for now as we use centralized cache
  };

  const getNavigationType = (prevStack: StackItem[], currStack: StackItem[]): 'forward' | 'immediateParent' | 'skipLevel' | 'same' => {
    const depthChange = currStack.length - prevStack.length;

    // Going deeper into the stack
    if (depthChange > 0) return 'forward';

    // Going back by more than 1 level (e.g., Item → Root, skipping Corpus)
    if (depthChange < -1) return 'skipLevel';

    // Going back exactly 1 level (e.g., Item → Corpus)
    if (depthChange === -1) return 'immediateParent';

    // No change in depth (shouldn't happen in stack navigation)
    return 'same';
  };

  // --- Animation ---

  useGSAP(() => {
    if (!containerRef.current || !stateRef.current) return;

    // Additional guard: ensure we have valid targets
    const targets = containerRef.current.querySelectorAll('[data-flip-id]');
    if (!targets || targets.length === 0) {
      stateRef.current = null;
      return;
    }

    // Debug: Log current state vs captured state
    const currentElements = Array.from(targets).map(el => ({
      id: el.getAttribute('data-flip-id'),
      rect: el.getBoundingClientRect(),
      element: el
    }));
    const currentIds = currentElements.map(e => e.id);
    const capturedIds = stateRef.current.targets.map(t => t.getAttribute('data-flip-id'));

    const leavingIds = capturedIds.filter(id => !currentIds.includes(id));
    const enteringIds = currentIds.filter(id => !capturedIds.includes(id));
    const targetsToMorph = stateRef.current.targets;

    Flip.from(stateRef.current, {
      targets: targetsToMorph,
      duration: reduceMotion ? 0.8 : 2.4,
      ease: reduceMotion ? 'power2.inOut' : 'elastic.out(1, 0.6)',
      stagger: reduceMotion ? 0 : 0.05,
      absolute: true,
      zIndex: 100,
      nested: true,
      simple: false,
      prune: true,
      onStart: () => {

        // Get IDs that are entering (not in previous state)
        const previousIds = new Set(
          stateRef.current?.targets
            .map(t => t.getAttribute('data-flip-id'))
            .filter(Boolean) as string[]
        );

        // Detect if we're going back to root (items should exit)
        const goingToRoot = activeItem.type === 'root';

        // CREATE PLACEHOLDERS for animating elements to prevent flex collapse
        const animatingElements = containerRef.current?.querySelectorAll('[data-flip-id]');

        if (animatingElements && containerRef.current) {
          animatingElements.forEach(el => {
            const flipId = el.getAttribute('data-flip-id');
            const isEntering = flipId && !previousIds.has(flipId);
            const isItemCard = flipId?.startsWith('card-item-');

            // If going to root, kill any morphing on item cards - they should only exit
            if (goingToRoot && isItemCard) {
              gsap.set(el, { clearProps: 'all' }); // Clear any Flip transforms
            }

            const rect = el.getBoundingClientRect();
            const computedStyle = window.getComputedStyle(el);

            // Create invisible placeholder with exact dimensions
            const placeholder = document.createElement('div');
            placeholder.style.width = `${rect.width}px`;
            placeholder.style.height = `${rect.height}px`;
            placeholder.style.flexBasis = computedStyle.flexBasis;
            placeholder.style.order = computedStyle.order;
            placeholder.style.margin = computedStyle.margin;
            placeholder.style.visibility = 'hidden';
            placeholder.style.pointerEvents = 'none';
            placeholder.setAttribute('data-flip-placeholder', 'true');

            // Insert placeholder before the element
            el.parentElement?.insertBefore(placeholder, el);
            placeholdersRef.current.push(placeholder);
          });

        }
      },
      onComplete: () => {
        // Update previous stack after animation completes
        previousStackRef.current = stack;

        // REMOVE PLACEHOLDERS to restore normal layout
        placeholdersRef.current.forEach(placeholder => {
          placeholder.remove();
        });
        placeholdersRef.current = [];
      },
      onEnter: elements => {

        // Filter out elements that are morphing (i.e. their ID was in the previous state)
        // so we don't override the Flip morph animation with a fade-in
        const previousIds = new Set(
            stateRef.current?.targets
                .map(t => t.getAttribute('data-flip-id'))
                .filter(Boolean) as string[]
        );

        const trueEntering = elements.filter(el => {
            const id = el.getAttribute('data-flip-id');
            // If ID exists and was in previous state, it's a morph - skip fade in
            if (id && previousIds.has(id)) return false;
            return true;
        });

        if (trueEntering.length === 0) return;

        // Separate items from other elements
        const itemCards = trueEntering.filter(el => el.getAttribute('data-flip-id')?.startsWith('card-item-'));
        const otherElements = trueEntering.filter(el => !el.getAttribute('data-flip-id')?.startsWith('card-item-'));

        // Animate items flying in from bottom of viewport
        const itemAnimation = itemCards.length > 0 ? gsap.fromTo(itemCards,
          { opacity: 0, y: window.innerHeight },
          {
            opacity: 1,
            y: 0,
            duration: reduceMotion ? 0.2 : 0.5,
            stagger: reduceMotion ? 0 : 0.04,
            ease: 'power3.out'
          }
        ) : null;

        // Animate other elements normally
        const otherAnimation = otherElements.length > 0 ? gsap.fromTo(otherElements,
          { opacity: 0, scale: 0.95 },
          { opacity: 1, scale: 1, duration: reduceMotion ? 0.3 : 0.4, delay: reduceMotion ? 0 : 0.1 }
        ) : null;

        // Return combined animations
        return itemAnimation || otherAnimation;
      },
      onLeave: elements => {

        // Only animate item CARDS (not their children like icon, title, etc)
        // and only if we're going to root (not if item is moving to breadcrumb)
        const goingToRoot = activeItem.type === 'root';
        const itemCards = goingToRoot
          ? elements.filter(el => {
              const id = el.getAttribute('data-flip-id');
              // ONLY cards that start with 'card-item-', not 'icon-item-', 'title-text-item-', 'meta-row-item-'
              return id?.startsWith('card-item-');
            })
          : [];
        const otherElements = elements.filter(el => {
          const id = el.getAttribute('data-flip-id');
          // Everything except item-related elements (card, icon, title, meta)
          return !id?.includes('-item-');
        });

        // Animate items flying out to bottom ONE AT A TIME (LAST/BOTTOM item first)
        const itemAnimation = itemCards.length > 0 ? (() => {
          const sortedCards = Array.from(itemCards).sort((a, b) => {
            const rectA = a.getBoundingClientRect();
            const rectB = b.getBoundingClientRect();
            return rectB.bottom - rectA.bottom;
          });

          // Create a timeline to animate items sequentially
          const timeline = gsap.timeline();
          sortedCards.forEach((card, index) => {
            timeline.to(card, {
              opacity: 0,
              y: window.innerHeight,
              duration: reduceMotion ? 0.2 : 0.5,
              ease: 'power3.in'
            }, index === 0 ? 0 : ">");
          });

          return timeline;
        })() : null;

        // Detect navigation type for other elements
        const navType = getNavigationType(previousStackRef.current, stack);

        // Animate other elements normally
        const otherAnimation = otherElements.length > 0 ? gsap.to(otherElements, {
          opacity: 0,
          scale: navType === 'skipLevel' ? 0.9 : 0.95,
          duration: navType === 'skipLevel' ? 0.4 : 0.3,
          ease: navType === 'skipLevel' ? 'power2.in' : 'power2.out'
        }) : null;

        return itemAnimation || otherAnimation;
      }
    });

    stateRef.current = null;
  }, [stack]);

  const activeItem = stack[stack.length - 1];
  const breadcrumbs = stack.slice(0, stack.length - 1);

  // Update active corpus items when navigating to a corpus
  useEffect(() => {
    if (activeItem.type === 'corpus') {
      const corpusName = (activeItem as any).data.name;
      activeCorpusNameRef.current = corpusName;
      corpusRequestIdRef.current += 1;
      const requestId = corpusRequestIdRef.current;
      if (itemCache[corpusName]) {
        setActiveCorpusItems(itemCache[corpusName]);
      } else {
        api.listCatalogItems(corpusName).then(res => {
          if (requestId !== corpusRequestIdRef.current) return;
          if (activeCorpusNameRef.current !== corpusName) return;
          setItemCache(prev => ({ ...prev, [corpusName]: res.items }));
          setActiveCorpusItems(res.items);
        });
      }
    }
    // Keep items loaded when viewing an item, so they can animate back
  }, [activeItem, itemCache]);

  useEffect(() => {
    if (stack.length === 1 || activeItem.type === 'root') {
      activeCorpusNameRef.current = null;
      corpusRequestIdRef.current += 1;
      setActiveCorpusItems([]);
    }
  }, [activeItem.type, stack.length]);

  // Animate items when they first appear
  useLayoutEffect(() => {
    if (activeCorpusItems.length > 0 && activeItem.type === 'corpus') {
      // Immediately hide items on render
      const itemElements = containerRef.current?.querySelectorAll('[data-flip-id^="card-item-"]');
      if (itemElements && itemElements.length > 0) {
        // Set initial position immediately
        gsap.set(itemElements, { y: window.innerHeight, opacity: 0 });

        // Then animate in
        gsap.to(Array.from(itemElements), {
          y: 0,
          opacity: 1,
          duration: reduceMotion ? 0.2 : 0.5,
          stagger: reduceMotion ? 0 : 0.04,
          ease: 'power3.out'
        });
      }
    }
  }, [activeCorpusItems, activeItem.type, reduceMotion]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col transition-colors duration-300" ref={containerRef}>

      <AppearanceSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Single unified container for breadcrumbs AND corpus grid */}
      <div
        className="flex-1 p-2"
        onClick={() => {
            if (sidebarOpen) setSidebarOpen(false);
        }}
      >
        {/* Unified flex container with wrapping */}
        <div className="flex flex-wrap items-start overflow-x-auto">
          {/* Breadcrumbs row */}
          {stack.map((item, index) => {
            if (item.type === 'root') {
              const isActive = index === stack.length - 1;
              return (
                <div key={item.id} className="mr-2" style={{ order: -1000 }}>
                  <Breadcrumb
                    item={item}
                    onClick={() => handleBreadcrumbClick(item, index)}
                    onSettingsClick={(e) => {
                        e.stopPropagation();
                        setSidebarOpen(true);
                    }}
                    isActive={isActive}
                  />
                </div>
              );
            }
            // Corpus and item breadcrumbs are now rendered inline with their cards
            return null;
          })}

          {/* Full-width break to force new row after breadcrumbs */}
          <div style={{ flexBasis: '100%', height: 0, order: -100 }} />

          {/* Horizontal separator - fixed position between breadcrumbs and grid */}
          <div
            className="py-2"
            style={{
              order: -10,
              flexBasis: '100%',
              marginLeft: '-0.5rem',
              marginRight: '-0.5rem',
              minHeight: 'calc(0.5rem + 0.5rem + 0.25rem)', // py-2 (top + bottom) + h-1
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <div className="h-1 bg-foreground/10" style={{ width: '100%' }} />
          </div>

          {/* Corpus cards - render ALL of them here */}
          {corporaState.map((corpus) => {
            const stackIndex = stack.findIndex(item => item.type === 'corpus' && (item as any).data?.name === corpus.name);
            const isInStack = stackIndex !== -1;
            const isActive = stackIndex === stack.length - 1;

            return (
              <div
                key={corpus.name}
                onClick={() => {
                  if (isInStack) {
                    // Navigate TO this corpus level (not back to root)
                    popToIndex(stackIndex);
                  } else {
                    // Push to stack
                    pushStack({
                      id: `corpus-${corpus.name}`,
                      type: 'corpus',
                      title: corpus.name,
                      data: corpus
                    });
                  }
                }}
                className={isInStack ? "cursor-pointer mr-2" : "cursor-pointer"}
                style={{
                  order: isInStack ? -500 : 0,
                  flexBasis: isInStack ? 'auto' : 'calc(33.333% - 0.5rem)',
                  minWidth: isInStack ? '120px' : '200px',
                  maxWidth: isInStack ? '180px' : 'none'
                }}
              >
                <div
                  className={`p-2 rounded-xl shadow-flat-muted hover:bg-hover transition-colors group cursor-pointer ${isActive ? 'bg-selected' : 'bg-card'}`}
                  data-flip-id={`card-corpus-${corpus.name.trim()}`}
                >
                  <div className="flex items-baseline gap-2 text-sm">
                    <div
                      className="flex items-center justify-center shrink-0 self-baseline"
                      data-flip-id={`icon-corpus-${corpus.name}`}
                      style={{ width: '1em', height: '1em' }}
                    >
                      <Folder className="w-full h-full text-muted-foreground block" strokeWidth={2.25} />
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span
                          className="font-bold text-foreground truncate block flex-1 leading-none"
                          data-flip-id={`title-text-corpus-${corpus.name}`}
                        >
                          {corpus.name}
                        </span>
                      </div>
                      <div
                        className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground font-bold h-4"
                        data-flip-id={`meta-row-corpus-${corpus.name}`}
                      >
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" strokeWidth={2.25} /> {corpus.itemCount || '?'}
                        </span>
                      </div>

                      {!isInStack && corpus.lastActivity && (
                        <span
                          className="text-[10px] font-medium text-muted-foreground mt-0.5 block flip-animate"
                          data-flip-id={`last-activity-corpus-${corpus.name}`}
                        >
                          Updated {new Date(corpus.lastActivity).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Item files - render ALL items from active corpus, always keep them rendered */}
          {activeCorpusItems.length > 0 && activeItem.type !== 'root' && (() => {
            // Always render items from the current corpus (even when viewing an item detail)
            // This allows animations to work when navigating back
            const allItems = [...activeCorpusItems];

            // Also include any items in the stack that might be from a different corpus
            stack.forEach(stackItem => {
              if (stackItem.type === 'item') {
                const itemData = (stackItem as any).data;
                if (!allItems.find(i => i.id === itemData.id)) {
                  allItems.push(itemData);
                }
              }
            });

            return allItems.map((item) => {
              const stackIndex = stack.findIndex(stackItem => stackItem.type === 'item' && (stackItem as any).data?.id === item.id);
              const isInStack = stackIndex !== -1;
              const isActive = stackIndex === stack.length - 1;

              return (
                <div
                key={item.id}
                data-item-shell="true"
                onClick={() => {
                  if (isInStack) {
                    // Navigate TO this item level
                    popToIndex(stackIndex);
                  } else {
                    // Push to stack
                    pushStack({
                      id: `item-${item.id}`,
                      type: 'item',
                      title: formatDisplayName(item.title || item.relpath),
                      data: item
                    });
                  }
                }}
                className={isInStack ? "cursor-pointer mr-2" : "cursor-pointer"}
                style={{
                  order: isInStack ? -400 : 100,
                  flexBasis: isInStack ? 'auto' : '100%',
                  minWidth: isInStack ? '120px' : 'auto',
                  maxWidth: isInStack ? '180px' : 'none',
                  marginBottom: isInStack ? '0' : '0.5rem'
                }}
              >
                <div
                  className={`p-2 min-h-12 rounded-xl shadow-flat-muted hover:bg-hover transition-colors group cursor-pointer ${isActive ? 'bg-selected' : 'bg-card'}`}
                  data-flip-id={`card-item-${item.id}`}
                  data-item-card="true"
                  data-item-id={String(item.id)}
                >
                  <div className="flex items-baseline gap-2 text-sm" data-item-row="true">
                    <div
                      className="flex items-center justify-center shrink-0 self-baseline"
                      data-flip-id={`icon-item-${item.id}`}
                      style={{ height: '1em', width: '1em' }}
                    >
                      <FileText className="w-full h-full text-muted-foreground block" strokeWidth={2.25} />
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span
                          className="font-bold text-foreground truncate block flex-1 leading-none"
                          data-flip-id={`title-text-item-${item.id}`}
                          data-item-title="true"
                        >
                          {formatDisplayName(item.title || item.relpath)}
                        </span>
                      </div>
                      <div
                        className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground font-bold h-4"
                        data-flip-id={`meta-row-item-${item.id}`}
                        data-item-meta="true"
                      >
                        <span className="bg-muted px-1.5 py-0.5 rounded-md uppercase">
                          {item.mediaType}
                        </span>
                        <span>
                          {(item.bytes / 1024).toFixed(0)} KB
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              );
            });
          })()}

          {/* Full-width break before other content */}
          <div style={{ flexBasis: '100%', height: 0 }} />
        </div>

        {activeItem.type === 'item' && (
          <div className="p-2">
            <ItemView item={(activeItem as any).data} />
          </div>
        )}
      </div>
    </div>
  );
}
