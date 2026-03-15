/**
 * Panel Component
 *
 * Reusable panel wrapper with GSAP animation lifecycle.
 * Supports horizontal sliding transitions and Bauhaus flat design.
 */

import { useRef, useEffect, ReactNode } from 'react';
import gsap from 'gsap';
import { slideInFromRight, slideOutToRight } from '../../lib/animations';

export interface PanelProps {
  children: ReactNode;
  isVisible: boolean;
  width?: string;
  backgroundColor?: string;
  className?: string;
  onAnimationComplete?: () => void;
  animateIn?: 'slide' | 'fade' | 'none';
  animateOut?: 'slide' | 'fade' | 'none';
  zIndex?: number;
}

export function Panel({
  children,
  isVisible,
  width = '33.333%',
  backgroundColor = 'bg-white',
  className = '',
  onAnimationComplete,
  animateIn = 'slide',
  animateOut = 'slide',
  zIndex = 10,
}: PanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousVisibility = useRef<boolean>(isVisible);

  useEffect(() => {
    if (!panelRef.current) return;

    // Only animate if visibility changed
    if (previousVisibility.current === isVisible) return;

    if (isVisible && !previousVisibility.current) {
      // Animate in
      switch (animateIn) {
        case 'slide':
          slideInFromRight(panelRef.current).eventCallback('onComplete', onAnimationComplete);
          break;
        case 'fade':
          gsap.fromTo(
            panelRef.current,
            { opacity: 0 },
            { opacity: 1, duration: 0.6, onComplete: onAnimationComplete }
          );
          break;
        case 'none':
          gsap.set(panelRef.current, { opacity: 1, x: '0%' });
          onAnimationComplete?.();
          break;
      }
    } else if (!isVisible && previousVisibility.current) {
      // Animate out
      switch (animateOut) {
        case 'slide':
          slideOutToRight(panelRef.current).eventCallback('onComplete', onAnimationComplete);
          break;
        case 'fade':
          gsap.to(panelRef.current, {
            opacity: 0,
            duration: 0.6,
            onComplete: onAnimationComplete,
          });
          break;
        case 'none':
          gsap.set(panelRef.current, { opacity: 0, x: '100%' });
          onAnimationComplete?.();
          break;
      }
    }

    previousVisibility.current = isVisible;
  }, [isVisible, animateIn, animateOut, onAnimationComplete]);

  // Initial state
  useEffect(() => {
    if (!panelRef.current) return;

    if (!isVisible) {
      gsap.set(panelRef.current, {
        x: '100%',
        opacity: 0,
      });
    }
  }, []);

  return (
    <div
      ref={panelRef}
      className={`absolute top-0 h-full overflow-y-auto ${backgroundColor} ${className}`}
      style={{
        width,
        zIndex,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </div>
  );
}
