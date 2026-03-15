/**
 * GSAP Animation Library
 *
 * Centralized animation helpers for the Biblicus Corpus Viewer.
 * All animations use GSAP for consistent, performant motion design.
 */

import gsap from 'gsap';

export interface AnimationConfig {
  duration?: number;
  ease?: string;
  delay?: number;
  stagger?: number;
}

const DEFAULT_DURATION = 0.6;
const DEFAULT_EASE = 'power3.out';
const DEFAULT_STAGGER = 0.05;

/**
 * Slide a panel in from the right
 */
export function slideInFromRight(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.fromTo(
    element,
    {
      x: '100%',
      opacity: 0,
    },
    {
      x: '0%',
      opacity: 1,
      duration: config.duration ?? DEFAULT_DURATION,
      ease: config.ease ?? DEFAULT_EASE,
      delay: config.delay ?? 0,
    }
  );

  return tl;
}

/**
 * Slide a panel out to the right
 */
export function slideOutToRight(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    x: '100%',
    opacity: 0,
    duration: config.duration ?? DEFAULT_DURATION,
    ease: config.ease ?? DEFAULT_EASE,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Slide a panel in from the left
 */
export function slideInFromLeft(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.fromTo(
    element,
    {
      x: '-100%',
      opacity: 0,
    },
    {
      x: '0%',
      opacity: 1,
      duration: config.duration ?? DEFAULT_DURATION,
      ease: config.ease ?? DEFAULT_EASE,
      delay: config.delay ?? 0,
    }
  );

  return tl;
}

/**
 * Slide a panel out to the left
 */
export function slideOutToLeft(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    x: '-100%',
    opacity: 0,
    duration: config.duration ?? DEFAULT_DURATION,
    ease: config.ease ?? DEFAULT_EASE,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Fade in children with stagger effect
 */
export function fadeInStagger(
  container: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  // Get the actual container element
  const containerEl = typeof container === 'string'
    ? document.querySelector(container)
    : container;

  if (!containerEl) return tl;

  // Get direct children
  const children = Array.from(containerEl.children);

  if (children.length === 0) return tl;

  tl.fromTo(
    children,
    {
      opacity: 0,
      y: 20,
    },
    {
      opacity: 1,
      y: 0,
      duration: config.duration ?? DEFAULT_DURATION,
      ease: config.ease ?? DEFAULT_EASE,
      stagger: config.stagger ?? DEFAULT_STAGGER,
      delay: config.delay ?? 0,
    }
  );

  return tl;
}

/**
 * Animate panel width change
 */
export function resizePanelWidth(
  element: HTMLElement | string,
  targetWidth: string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    width: targetWidth,
    duration: config.duration ?? DEFAULT_DURATION,
    ease: config.ease ?? DEFAULT_EASE,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Morph panel position and size
 */
export function morphPanelPosition(
  element: HTMLElement | string,
  targetProps: {
    x?: string | number;
    y?: string | number;
    width?: string;
    height?: string;
    opacity?: number;
  },
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    ...targetProps,
    duration: config.duration ?? DEFAULT_DURATION,
    ease: config.ease ?? DEFAULT_EASE,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Pulse animation for emphasis
 */
export function pulse(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    scale: 1.05,
    duration: (config.duration ?? DEFAULT_DURATION) / 2,
    ease: 'power2.out',
    yoyo: true,
    repeat: 1,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Fade in single element
 */
export function fadeIn(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.fromTo(
    element,
    {
      opacity: 0,
    },
    {
      opacity: 1,
      duration: config.duration ?? DEFAULT_DURATION,
      ease: config.ease ?? DEFAULT_EASE,
      delay: config.delay ?? 0,
    }
  );

  return tl;
}

/**
 * Fade out single element
 */
export function fadeOut(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    opacity: 0,
    duration: config.duration ?? DEFAULT_DURATION,
    ease: config.ease ?? DEFAULT_EASE,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Scale in animation
 */
export function scaleIn(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.fromTo(
    element,
    {
      scale: 0.8,
      opacity: 0,
    },
    {
      scale: 1,
      opacity: 1,
      duration: config.duration ?? DEFAULT_DURATION,
      ease: config.ease ?? DEFAULT_EASE,
      delay: config.delay ?? 0,
    }
  );

  return tl;
}

/**
 * Scale out animation
 */
export function scaleOut(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline();

  tl.to(element, {
    scale: 0.8,
    opacity: 0,
    duration: config.duration ?? DEFAULT_DURATION,
    ease: config.ease ?? DEFAULT_EASE,
    delay: config.delay ?? 0,
  });

  return tl;
}

/**
 * Shimmer effect for loading states
 */
export function shimmer(
  element: HTMLElement | string,
  config: AnimationConfig = {}
): gsap.core.Timeline {
  const tl = gsap.timeline({ repeat: -1 });

  tl.to(element, {
    opacity: 0.5,
    duration: (config.duration ?? DEFAULT_DURATION) * 0.75,
    ease: 'sine.inOut',
    yoyo: true,
    repeat: 1,
  });

  return tl;
}

/**
 * Create a coordinated timeline for multiple panels
 */
export function coordinatedPanelTransition(
  animations: Array<{
    element: HTMLElement | string;
    animation: 'slideIn' | 'slideOut' | 'fadeIn' | 'fadeOut';
    direction?: 'left' | 'right';
    config?: AnimationConfig;
  }>
): gsap.core.Timeline {
  const masterTimeline = gsap.timeline();

  animations.forEach(({ element, animation, direction, config }) => {
    let anim: gsap.core.Timeline;

    switch (animation) {
      case 'slideIn':
        anim = direction === 'left' ? slideInFromLeft(element, config) : slideInFromRight(element, config);
        break;
      case 'slideOut':
        anim = direction === 'left' ? slideOutToLeft(element, config) : slideOutToRight(element, config);
        break;
      case 'fadeIn':
        anim = fadeIn(element, config);
        break;
      case 'fadeOut':
        anim = fadeOut(element, config);
        break;
      default:
        anim = fadeIn(element, config);
    }

    masterTimeline.add(anim, config?.delay ?? 0);
  });

  return masterTimeline;
}
