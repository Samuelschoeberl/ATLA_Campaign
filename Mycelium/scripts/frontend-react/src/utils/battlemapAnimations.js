import { animate } from 'animejs';

// Respect users who prefer reduced motion
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Shared defaults for a snappy-but-lightweight feel
const BASE_EASING = 'easeOutQuad';
const createMockAnimation = () => ({
  finished: Promise.resolve(),
  pause: () => {},
  play: () => {},
  restart: () => {}
});

const runAnimation = (config = {}) => {
  if (prefersReducedMotion()) {
    if (typeof config.begin === 'function') config.begin();
    if (typeof config.update === 'function') config.update({ progress: 100 });
    if (typeof config.complete === 'function') config.complete();
    return createMockAnimation();
  }

  try {
    return animate({
      easing: BASE_EASING,
      duration: 320,
      ...config
    });
  } catch {
    return createMockAnimation();
  }
};

const runTimeline = (config = {}) => {
  if (prefersReducedMotion()) {
    const mock = createMockAnimation();
    mock.add = () => mock;
    return mock;
  }
  return animate.timeline({ easing: BASE_EASING, duration: 320, ...config });
};

// Track looping glow animations so we can cleanly replace them
const effectPulseRegistry = new WeakMap();

/**
 * Battlemap animation utilities using anime.js
 * Provides smooth, performant animations for tokens, selections, and effects
 */

/**
 * Animate token movement from one position to another
 * @param {HTMLElement} element - The token element to animate
 * @param {Object} from - Starting position {x, y}
 * @param {Object} to - Target position {x, y}
 * @param {number} duration - Animation duration in ms
 * @param {string} easing - Easing function name
 * @returns {Object} Anime.js animation instance
 */
export const animateTokenMove = (element, from, to, duration) => {
  if (!element || !to) return createMockAnimation();

  // Move by translating from the prior position while the element is already laid out at its new left/top.
  const deltaX = from ? from.x - to.x : 0;
  const deltaY = from ? from.y - to.y : 0;
  const distance = Math.hypot(deltaX, deltaY);
  const computedDuration = duration ?? Math.min(900, Math.max(320, distance * 1.35));

  // Set initial offset immediately so the animation has a visible start
  if (element.style) {
    element.style.transform = `translate(${deltaX}px, ${deltaY}px)`;
  }

  return runAnimation({
    targets: element,
    left: `${to.x}px`,
    top: `${to.y}px`,
    translateX: 0,
    translateY: 0,
    duration: computedDuration,
    easing: 'easeOutCubic',
    begin: () => {
      if (element.style) element.style.willChange = 'transform, left, top';
    },
    complete: () => {
      if (element.style) element.style.willChange = '';
      // Add a slight landing settle
      runAnimation({
        targets: element,
        scale: [0.97, 1],
        duration: 180,
        easing: 'easeOutElastic(1, .7)'
      });
    }
  });
};

/**
 * Animate token movement for SVG/group elements using translate deltas
 * Uses Web Animations API for better SVG compatibility
 */
export const animateTokenMoveSvg = (element, from, to, duration) => {
  if (!element || !to || !from) return createMockAnimation();
  
  if (prefersReducedMotion()) {
    element.removeAttribute('transform');
    return createMockAnimation();
  }
  
  const deltaX = from.x - to.x;
  const deltaY = from.y - to.y;
  const distance = Math.hypot(deltaX, deltaY);
  const computedDuration = duration ?? Math.min(900, Math.max(320, distance * 1.35));
  
  // Use Web Animations API which handles SVG transforms natively
  const animation = element.animate(
    [
      { transform: `translate(${deltaX}px, ${deltaY}px)` },
      { transform: 'translate(0px, 0px)' }
    ],
    {
      duration: computedDuration,
      easing: 'cubic-bezier(0.22, 0.61, 0.36, 1)',
      fill: 'forwards'
    }
  );
  
  animation.onfinish = () => {
    element.removeAttribute('transform');
  };
  
  return {
    finished: animation.finished,
    pause: () => animation.pause(),
    play: () => animation.play(),
    restart: () => animation.cancel()
  };
};

/**
 * Animate token selection with pulsing glow effect
 * @param {HTMLElement} element - The token element
 * @param {boolean} selected - Whether token is being selected or deselected
 * @returns {Object} Anime.js animation instance
 */
export const animateTokenSelection = (element, selected) => {
  if (selected) {
    return runAnimation({
      targets: element,
      scale: [1, 1.08, 1],
      duration: 300,
      easing: 'out-elastic(1, .6)'
    });
  } else {
    return runAnimation({
      targets: element,
      scale: 1,
      duration: 200,
      easing: 'out-quad'
    });
  }
};

/**
 * Continuous pulse animation for selected tokens
 * @param {HTMLElement} element - The token element
 * @returns {Object} Anime.js animation instance
 */
export const animateTokenPulse = (element) => {
  return runAnimation({
    targets: element,
    scale: [1, 1.05, 1],
    duration: 1500,
    easing: 'inOut-sine',
    loop: true
  });
};

/**
 * Animate token appearance (spawn)
 * @param {HTMLElement} element - The token element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateTokenSpawn = (element, duration = 500) => {
  return runAnimation({
    targets: element,
    scale: [0, 1],
    opacity: [0, 1],
    rotate: ['-180deg', '0deg'],
    duration,
    easing: 'out-elastic(1, .6)'
  });
};

/**
 * Animate token removal (despawn)
 * @param {HTMLElement} element - The token element
 * @param {number} duration - Animation duration in ms
 * @returns {Promise} Promise that resolves when animation completes
 */
export const animateTokenRemove = (element, duration = 400) => {
  return runAnimation({
    targets: element,
    scale: 0,
    opacity: 0,
    rotate: '180deg',
    duration,
    easing: 'in-back'
  }).finished;
};

/**
 * Animate HP bar change with smooth transition
 * @param {HTMLElement} element - The HP bar element
 * @param {number} fromPercentage - Starting HP percentage
 * @param {number} toPercentage - Target HP percentage
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateHPChange = (element, fromPercentage, toPercentage, duration = 600) => {
  const obj = { value: fromPercentage };
  
  return runAnimation({
    targets: obj,
    value: toPercentage,
    duration,
    easing: 'out-cubic',
    update: () => {
      if (element && element.style) {
        // Update the element's data attribute or style
        element.setAttribute('data-hp-percentage', obj.value);
      }
    }
  });
};

/**
 * Animate grid cell painting/drawing
 * @param {HTMLElement} element - The grid cell element
 * @param {string} color - Target color
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateCellPaint = (element, color, duration = 200) => {
  return runAnimation({
    targets: element,
    backgroundColor: color,
    scale: [0.95, 1],
    duration,
    easing: 'out-quad'
  });
};

/**
 * Animate grid cell erasing
 * @param {HTMLElement} element - The grid cell element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateCellErase = (element, duration = 150) => {
  return runAnimation({
    targets: element,
    backgroundColor: 'rgba(0, 0, 0, 0)',
    scale: [1.05, 1],
    duration,
    easing: 'out-quad'
  });
};

/**
 * Animate AOE effect appearance (sphere, cone, line)
 * @param {HTMLElement[]} elements - Array of affected cell elements
 * @param {string} color - Effect color
 * @param {number} duration - Animation duration in ms
 * @param {string} pattern - Animation pattern ('radial', 'linear', 'random')
 * @returns {Object} Anime.js timeline instance
 */
export const animateAOEEffect = (elements, color, duration = 400, pattern = 'radial') => {
  const timeline = runTimeline({
    easing: 'out-expo'
  });

  if (pattern === 'radial') {
    // Stagger from center outward
    elements.forEach((element, index) => {
      timeline.add({
        targets: element,
        backgroundColor: color,
        scale: [0.8, 1],
        opacity: [0.5, 1],
        duration: duration / 2,
      }, index * 50);
    });
  } else if (pattern === 'linear') {
    // Stagger in sequence
    timeline.add({
      targets: elements,
      backgroundColor: color,
      scale: [0.8, 1],
      opacity: [0.5, 1],
      duration: duration / 2,
        delay: animate.stagger(60)
    });
  } else {
    // Random stagger
    timeline.add({
      targets: elements,
      backgroundColor: color,
      scale: [0.8, 1],
      opacity: [0.5, 1],
      duration: duration / 2,
      delay: animate.stagger(50, { from: 'center', easing: 'out-quad' })
    });
  }

  return timeline;
};

/**
 * Animate condition icon appearance on token
 * @param {HTMLElement} element - The condition icon element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateConditionAdd = (element, duration = 300) => {
  return runAnimation({
    targets: element,
    scale: [0, 1],
    rotate: ['0deg', '360deg'],
    opacity: [0, 1],
    duration,
    easing: 'out-back'
  });
};

/**
 * Animate condition icon removal from token
 * @param {HTMLElement} element - The condition icon element
 * @param {number} duration - Animation duration in ms
 * @returns {Promise} Promise that resolves when animation completes
 */
export const animateConditionRemove = (element, duration = 250) => {
  return runAnimation({
    targets: element,
    scale: 0,
    rotate: '-360deg',
    opacity: 0,
    duration,
    easing: 'in-back'
  }).finished;
};

/**
 * Animate measurement line drawing
 * @param {HTMLElement} element - The line element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateMeasurementLine = (element, duration = 300) => {
  return runAnimation({
    targets: element,
    strokeDashoffset: [animate.setDashoffset, 0],
    opacity: [0, 1],
    duration,
    easing: 'out-cubic'
  });
};

/**
 * Animate tool selection with icon bounce
 * @param {HTMLElement} element - The tool button element
 * @param {boolean} selected - Whether tool is being selected
 * @returns {Object} Anime.js animation instance
 */
export const animateToolSelection = (element, selected) => {
  if (selected) {
    return runAnimation({
      targets: element,
      scale: [1, 1.15, 1.05],
      duration: 400,
      easing: 'out-elastic(1, .6)'
    });
  } else {
    return runAnimation({
      targets: element,
      scale: 1,
      duration: 200,
      easing: 'out-quad'
    });
  }
};

/**
 * Subtle hover lift for toolbar/effect buttons
 */
export const animateToolHover = (element, entering) => {
  return runAnimation({
    targets: element,
    scale: entering ? 1.08 : 1,
    translateY: entering ? -2 : 0,
    duration: entering ? 180 : 140,
    easing: entering ? 'easeOutQuad' : 'easeOutQuad'
  });
};

/**
 * Animate zoom/scale transition
 * @param {HTMLElement} element - The container element to zoom
 * @param {number} fromScale - Starting scale
 * @param {number} toScale - Target scale
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateZoom = (element, fromScale, toScale, duration = 300) => {
  return runAnimation({
    targets: element,
    scale: toScale,
    duration,
    easing: 'out-cubic'
  });
};

/**
 * Shake animation for errors or invalid actions
 * @param {HTMLElement} element - The element to shake
 * @param {number} intensity - Shake intensity in pixels
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateShake = (element, intensity = 10, duration = 400) => {
  return runAnimation({
    targets: element,
    translateX: [
      { value: intensity, duration: duration / 8 },
      { value: -intensity, duration: duration / 8 },
      { value: intensity / 2, duration: duration / 8 },
      { value: -intensity / 2, duration: duration / 8 },
      { value: 0, duration: duration / 2 }
    ],
    easing: 'inOut-quad'
  });
};

/**
 * Floating animation for hover effects
 * @param {HTMLElement} element - The element to float
 * @param {number} distance - Float distance in pixels
 * @returns {Object} Anime.js animation instance
 */
export const animateFloat = (element, distance = 5) => {
  return runAnimation({
    targets: element,
    translateY: [-distance, distance],
    duration: 2000,
    easing: 'inOut-sine',
    loop: true,
    direction: 'alternate'
  });
};

/**
 * Ripple effect animation for clicks
 * @param {HTMLElement} container - Container to append ripple to
 * @param {number} x - Click X position
 * @param {number} y - Click Y position
 * @param {string} color - Ripple color
 * @returns {Object} Anime.js animation instance
 */
export const animateRipple = (container, x, y, color = 'rgba(255, 255, 255, 0.5)') => {
  const ripple = document.createElement('div');
  ripple.style.position = 'absolute';
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;
  ripple.style.width = '10px';
  ripple.style.height = '10px';
  ripple.style.borderRadius = '50%';
  ripple.style.backgroundColor = color;
  ripple.style.transform = 'translate(-50%, -50%)';
  ripple.style.pointerEvents = 'none';
  
  container.appendChild(ripple);
  
  return runAnimation({
    targets: ripple,
    width: '100px',
    height: '100px',
    opacity: [0.8, 0],
    duration: 600,
    easing: 'out-quad',
    complete: () => {
      ripple.remove();
    }
  });
};

/**
 * Animate effect button selection with scale and glow
 * @param {HTMLElement} element - The button element
 * @param {string} glowColor - The glow color for the effect
 * @returns {Object} Anime.js animation instance
 */
export const animateEffectSelection = (element, glowColor) => {
  const existing = effectPulseRegistry.get(element);
  if (existing?.pause) existing.pause();

  return runAnimation({
    targets: element,
    scale: [1, 1.15, 1.1],
    duration: 400,
    easing: 'easeOutElastic(1, .5)',
    complete: () => {
      const loop = runAnimation({
        targets: element,
        boxShadow: [
          `0 0 14px ${glowColor}, 0 6px 12px rgba(0,0,0,0.5)`,
          `0 0 26px ${glowColor}, 0 6px 12px rgba(0,0,0,0.5)`
        ],
        duration: 1100,
        easing: 'easeInOutSine',
        direction: 'alternate',
        loop: true
      });
      effectPulseRegistry.set(element, loop);
    }
  });
};

/**
 * Animate effect button hover with smooth transition
 * @param {HTMLElement} element - The button element
 * @param {string} background - The background gradient/color
 * @param {string} glowColor - The glow color for the effect
 * @param {boolean} isHovering - Whether mouse is entering or leaving
 * @returns {Object} Anime.js animation instance
 */
export const animateEffectHover = (element, background, glowColor, isHovering) => {
  if (!element) return createMockAnimation();
  if (isHovering) {
    element.style.background = background;
    return runAnimation({
      targets: element,
      scale: [1, 1.05],
      translateY: [0, -1],
      boxShadow: [`0 3px 6px rgba(0,0,0,0.3)`, `0 0 15px ${glowColor}, 0 4px 8px rgba(0,0,0,0.4)`],
      duration: 200,
      easing: 'out-quad'
    });
  } else {
    element.style.background = background;
    return runAnimation({
      targets: element,
      scale: [1.05, 1],
      translateY: [-1, 0],
      boxShadow: [`0 0 15px ${glowColor}, 0 4px 8px rgba(0,0,0,0.4)`, `0 3px 6px rgba(0,0,0,0.3)`],
      duration: 200,
      easing: 'out-quad'
    });
  }
};

/**
 * Reveal panels/sections with a quick slide + fade
 */
export const animateSectionReveal = (element) => {
  return runAnimation({
    targets: element,
    opacity: [0, 1],
    translateY: [12, 0],
    duration: 260,
    easing: 'easeOutQuad'
  });
};
