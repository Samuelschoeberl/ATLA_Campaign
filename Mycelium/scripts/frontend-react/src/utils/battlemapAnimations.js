import { animate } from 'animejs';

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
export const animateTokenMove = (element, from, to, duration = 400, easing = 'out-cubic') => {
  return animate({
    targets: element,
    left: `${to.x}px`,
    top: `${to.y}px`,
    duration,
    easing,
    complete: () => {
      // Add a slight bounce effect on landing
      animate({
        targets: element,
        scale: [0.9, 1],
        duration: 150,
        easing: 'out-elastic(1, .6)'
      });
    }
  });
};

/**
 * Animate token selection with pulsing glow effect
 * @param {HTMLElement} element - The token element
 * @param {boolean} selected - Whether token is being selected or deselected
 * @returns {Object} Anime.js animation instance
 */
export const animateTokenSelection = (element, selected) => {
  if (selected) {
    return animate({
      targets: element,
      scale: [1, 1.08, 1],
      duration: 300,
      easing: 'out-elastic(1, .6)'
    });
  } else {
    return animate({
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
  return animate({
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
  return animate({
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
  return animate({
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
  
  return animate({
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
  return animate({
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
  return animate({
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
  const timeline = animate.timeline({
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
  return animate({
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
  return animate({
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
  return animate({
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
    return animate({
      targets: element,
      scale: [1, 1.15, 1.05],
      duration: 400,
      easing: 'out-elastic(1, .6)'
    });
  } else {
    return animate({
      targets: element,
      scale: 1,
      duration: 200,
      easing: 'out-quad'
    });
  }
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
  return animate({
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
  return animate({
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
  return animate({
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
  
  return animate({
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
  return animate({
    targets: element,
    scale: [1, 1.15, 1.1],
    duration: 400,
    easing: 'out-elastic(1, .5)',
    complete: () => {
      // Add a pulse glow effect
      animate({
        targets: element,
        boxShadow: [
          `0 0 20px ${glowColor}, 0 6px 12px rgba(0,0,0,0.5)`,
          `0 0 30px ${glowColor}, 0 6px 12px rgba(0,0,0,0.5)`,
          `0 0 20px ${glowColor}, 0 6px 12px rgba(0,0,0,0.5)`
        ],
        duration: 1000,
        easing: 'inOut-sine',
        loop: true
      });
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
  if (isHovering) {
    element.style.background = background;
    return animate({
      targets: element,
      scale: [1, 1.05],
      translateY: [0, -1],
      boxShadow: [`0 3px 6px rgba(0,0,0,0.3)`, `0 0 15px ${glowColor}, 0 4px 8px rgba(0,0,0,0.4)`],
      duration: 200,
      easing: 'out-quad'
    });
  } else {
    element.style.background = background;
    return animate({
      targets: element,
      scale: [1.05, 1],
      translateY: [-1, 0],
      boxShadow: [`0 0 15px ${glowColor}, 0 4px 8px rgba(0,0,0,0.4)`, `0 3px 6px rgba(0,0,0,0.3)`],
      duration: 200,
      easing: 'out-quad'
    });
  }
};
