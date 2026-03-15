import { useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { Moon, Sun, Monitor, X, Zap, ZapOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAppearance } from '../../lib/useAppearance';
import { AnimatedSelector } from '@/components/ui/animated-selector';

interface AppearanceSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AppearanceSidebar({ isOpen, onClose }: AppearanceSidebarProps) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const { theme, mode, reduceMotion, setTheme, setMode, setReduceMotion } = useAppearance();

  // Animation
  useGSAP(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar) return;

    if (isOpen) {
      // In: Sidebar slide right, Push content
      gsap.to(sidebar, { 
        x: 0, 
        duration: 0.4, 
        ease: 'power3.out' 
      });
      
      // Push the main content container
      // Sidebar (320) + Left Offset (8) + Gap (16) - Content Padding (8) = 336
      gsap.to('.main-content-area', {
        x: 336, 
        duration: 0.4,
        ease: 'power3.out'
      });
    } else {
      // Out: Sidebar slide left, Restore content
      gsap.to(sidebar, { 
        x: '-120%', // Move fully offscreen
        duration: 0.3, 
        ease: 'power3.in' 
      });

      // Restore the main content container
      gsap.to('.main-content-area', {
        x: 0,
        duration: 0.3,
        ease: 'power3.in'
      });
    }
  }, [isOpen]);

  return (
    <>
        {/* Sidebar Panel */}
        <div 
            ref={sidebarRef}
            className="fixed top-[84px] left-2 bottom-2 w-80 bg-card z-50 transform -translate-x-[120%] shadow-flat rounded-lg border-0 overflow-y-auto"
        >
            <div className="p-6 h-full flex flex-col relative">
                <div className="flex items-center justify-between mb-8">
                    <h2 className="text-xl font-bold">Appearance</h2>
                    {/* Close button is less needed if we click outside, but good for accessibility. 
                        If hidden under breadcrumbs, maybe we move it or rely on toggle. 
                        Let's keep it but ensure it's clickable. */}
                    <Button variant="ghost" size="icon" onClick={onClose}>
                        <X className="w-5 h-5" />
                    </Button>
                </div>

                <div className="space-y-8">
                    {/* Mode Section */}
                    <div>
                        <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-4">Mode</h3>
                        <AnimatedSelector
                            name="mode"
                            value={mode}
                            onChange={(val) => setMode(val as any)}
                            layout="grid"
                            options={[
                                { id: 'light', label: 'Light', icon: Sun },
                                { id: 'dark', label: 'Dark', icon: Moon },
                                { id: 'system', label: 'System', icon: Monitor },
                            ]}
                        />
                    </div>

                    {/* Theme Section */}
                    <div>
                        <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-4">Theme</h3>
                        <AnimatedSelector
                            name="theme"
                            value={theme}
                            onChange={(val) => setTheme(val as any)}
                            layout="vertical"
                            options={[
                                { 
                                    id: 'neutral', 
                                    label: 'Neutral', 
                                    content: 'Slate gray tones',
                                    icon: ({ className }: { className?: string }) => <div className={`w-4 h-4 rounded-full bg-slate-500 ${className}`} /> 
                                },
                                { 
                                    id: 'cool', 
                                    label: 'Cool', 
                                    content: 'Indigo & blue tones',
                                    icon: ({ className }: { className?: string }) => <div className={`w-4 h-4 rounded-full bg-indigo-500 ${className}`} />
                                },
                                { 
                                    id: 'warm', 
                                    label: 'Warm', 
                                    content: 'Orange & sand tones',
                                    icon: ({ className }: { className?: string }) => <div className={`w-4 h-4 rounded-full bg-orange-500 ${className}`} />
                                },
                            ]}
                        />
                    </div>

                    {/* Motion Section */}
                    <div>
                        <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-4">Motion</h3>
                        <AnimatedSelector
                            name="motion"
                            value={reduceMotion ? 'reduced' : 'gratuitous'}
                            onChange={(val) => setReduceMotion(val === 'reduced')}
                            layout="grid"
                            options={[
                                { id: 'gratuitous', label: 'Gratuitous', icon: Zap },
                                { id: 'reduced', label: 'Reduced', icon: ZapOff },
                            ]}
                        />
                    </div>
                </div>
            </div>
        </div>
    </>
  );
}
