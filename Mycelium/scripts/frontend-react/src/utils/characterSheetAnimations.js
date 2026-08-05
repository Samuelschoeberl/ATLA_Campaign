import * as anime from 'animejs';

/**
 * Character Sheet animation utilities using anime.js
 * Provides smooth, gamified animations for stat changes, resource consumption, and UI interactions
 */

/**
 * Animate HP bar change with color transition
 * @param {HTMLElement} barElement - The HP bar element
 * @param {number} fromValue - Starting HP value
 * @param {number} toValue - Target HP value
 * @param {number} maxValue - Maximum HP value
 * @param {Function} getColorFn - Function to get color based on percentage
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateHPChange = (barElement, fromValue, toValue, maxValue, getColorFn, duration = 800) => {
  if (!barElement) return null;
  
  const obj = { value: fromValue };
  const fromPercentage = (fromValue / maxValue) * 100;
  const toPercentage = (toValue / maxValue) * 100;
  
  return anime({
    targets: obj,
    value: toValue,
    duration,
    easing: 'easeInOutQuad',
    update: () => {
      const currentPercentage = (obj.value / maxValue) * 100;
      barElement.style.width = `${currentPercentage}%`;
      if (getColorFn) {
        barElement.style.backgroundColor = getColorFn(currentPercentage);
      }
    }
  });
};

/**
 * Animate resource (slot/charge) consumption with shake and fade
 * @param {HTMLElement} element - The resource display element
 * @param {number} fromValue - Starting value
 * @param {number} toValue - Target value
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateResourceConsumption = (element, fromValue, toValue, duration = 600) => {
  if (!element) return null;
  
  const obj = { value: fromValue };
  const isConsuming = toValue < fromValue;
  
  // Flash effect for consumption
  if (isConsuming) {
    anime({
      targets: element,
      scale: [1, 1.1, 1],
      backgroundColor: ['', '#ff6b6b', ''],
      duration: 300,
      easing: 'easeOutCubic'
    });
  }
  
  return anime({
    targets: obj,
    value: toValue,
    duration,
    easing: 'easeInOutQuad',
    round: 1,
    update: () => {
      const valueSpan = element.querySelector('.resource-value') || element;
      if (valueSpan && valueSpan.textContent) {
        valueSpan.textContent = valueSpan.textContent.replace(/\d+/, Math.round(obj.value));
      }
    }
  });
};

/**
 * Animate dice roll popup with bounce and rotation
 * @param {HTMLElement} element - The popup element
 * @param {Object} position - {top, left} position
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateDiceRollPopup = (element, position, duration = 500) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    scale: [0, 1.2, 1],
    opacity: [0, 1],
    rotate: ['0deg', '15deg', '0deg'],
    duration,
    easing: 'easeOutElastic(1, .6)',
    begin: () => {
      element.style.top = `${position.top}px`;
      element.style.left = `${position.left}px`;
    }
  });
};

/**
 * Animate section collapse/expand with smooth height transition
 * @param {HTMLElement} element - The section content element
 * @param {boolean} isExpanding - Whether section is expanding or collapsing
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateSectionToggle = (element, isExpanding, duration = 300) => {
  if (!element) return null;
  
  if (isExpanding) {
    const height = element.scrollHeight;
    element.style.height = '0px';
    element.style.opacity = '0';
    element.style.display = 'block';
    
    return anime({
      targets: element,
      height: `${height}px`,
      opacity: [0, 1],
      duration,
      easing: 'easeOutCubic',
      complete: () => {
        element.style.height = 'auto';
      }
    });
  } else {
    return anime({
      targets: element,
      height: '0px',
      opacity: [1, 0],
      duration,
      easing: 'easeInCubic',
      complete: () => {
        element.style.display = 'none';
      }
    });
  }
};

/**
 * Animate condition change with pulse effect
 * @param {HTMLElement} element - The condition element
 * @param {boolean} isActive - Whether condition is being activated or deactivated
 * @param {string} color - Condition color
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateConditionChange = (element, isActive, color, duration = 400) => {
  if (!element) return null;
  
  if (isActive) {
    return anime({
      targets: element,
      scale: [1, 1.15, 1.05],
      backgroundColor: ['', color, ''],
      duration,
      easing: 'easeOutElastic(1, .6)'
    });
  } else {
    return anime({
      targets: element,
      scale: [1, 0.9, 1],
      opacity: [1, 0.5, 1],
      duration,
      easing: 'easeInOutQuad'
    });
  }
};

/**
 * Animate button click with scale effect
 * @param {HTMLElement} element - The button element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateButtonClick = (element, duration = 200) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    scale: [1, 0.95, 1.05, 1],
    duration,
    easing: 'easeInOutQuad'
  });
};

/**
 * Animate move card reveal with slide and fade
 * @param {HTMLElement} element - The move card element
 * @param {number} delay - Delay before animation starts
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateMoveCardReveal = (element, delay = 0, duration = 400) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    translateY: [20, 0],
    opacity: [0, 1],
    scale: [0.95, 1],
    duration,
    delay,
    easing: 'easeOutCubic'
  });
};

/**
 * Animate move usage with flash and shake
 * @param {HTMLElement} element - The move element
 * @param {string} elementColor - The element color for the flash
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateMoveUsage = (element, elementColor, duration = 500) => {
  if (!element) return null;
  
  const timeline = anime.timeline({
    easing: 'easeOutCubic'
  });
  
  timeline
    .add({
      targets: element,
      backgroundColor: [elementColor, ''],
      scale: [1, 1.05],
      duration: duration / 2
    })
    .add({
      targets: element,
      scale: [1.05, 1],
      duration: duration / 2
    }, `-=${duration / 4}`);
  
  return timeline;
};

/**
 * Animate stat tooltip appearance
 * @param {HTMLElement} element - The tooltip element
 * @param {Object} position - {top, left} position
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateTooltipAppear = (element, position, duration = 200) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    translateY: [10, 0],
    opacity: [0, 1],
    duration,
    easing: 'easeOutQuad',
    begin: () => {
      element.style.top = `${position.top}px`;
      element.style.left = `${position.left}px`;
    }
  });
};

/**
 * Animate modal appearance with scale and backdrop fade
 * @param {HTMLElement} modalElement - The modal element
 * @param {HTMLElement} backdropElement - The backdrop element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js timeline instance
 */
export const animateModalAppear = (modalElement, backdropElement, duration = 300) => {
  if (!modalElement) return null;
  
  const timeline = anime.timeline({
    easing: 'easeOutCubic'
  });
  
  if (backdropElement) {
    timeline.add({
      targets: backdropElement,
      opacity: [0, 1],
      duration: duration / 2
    });
  }
  
  timeline.add({
    targets: modalElement,
    scale: [0.8, 1],
    opacity: [0, 1],
    translateY: [-20, 0],
    duration
  }, backdropElement ? `-=${duration / 4}` : 0);
  
  return timeline;
};

/**
 * Animate modal disappear with scale and backdrop fade
 * @param {HTMLElement} modalElement - The modal element
 * @param {HTMLElement} backdropElement - The backdrop element
 * @param {number} duration - Animation duration in ms
 * @returns {Promise} Promise that resolves when animation completes
 */
export const animateModalDisappear = (modalElement, backdropElement, duration = 250) => {
  const timeline = anime.timeline({
    easing: 'easeInCubic'
  });
  
  timeline.add({
    targets: modalElement,
    scale: 0.8,
    opacity: 0,
    translateY: -20,
    duration
  });
  
  if (backdropElement) {
    timeline.add({
      targets: backdropElement,
      opacity: 0,
      duration: duration / 2
    }, `-=${duration / 2}`);
  }
  
  return timeline.finished;
};

/**
 * Animate number change with counting effect
 * @param {HTMLElement} element - The element containing the number
 * @param {number} fromValue - Starting value
 * @param {number} toValue - Target value
 * @param {number} duration - Animation duration in ms
 * @param {string} prefix - Prefix string (e.g., '+', '-')
 * @param {string} suffix - Suffix string (e.g., '%', ' HP')
 * @returns {Object} Anime.js animation instance
 */
export const animateNumberChange = (element, fromValue, toValue, duration = 800, prefix = '', suffix = '') => {
  if (!element) return null;
  
  const obj = { value: fromValue };
  const isIncrease = toValue > fromValue;
  
  // Add pulse effect for significant changes
  if (Math.abs(toValue - fromValue) > 5) {
    anime({
      targets: element,
      scale: [1, 1.15, 1],
      color: [
        '',
        isIncrease ? '#2ecc71' : '#e74c3c',
        ''
      ],
      duration: 400,
      easing: 'easeOutCubic'
    });
  }
  
  return anime({
    targets: obj,
    value: toValue,
    duration,
    easing: 'easeOutQuad',
    round: 1,
    update: () => {
      element.textContent = `${prefix}${Math.round(obj.value)}${suffix}`;
    }
  });
};

/**
 * Animate rest action with healing glow
 * @param {HTMLElement} containerElement - The container element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateRestAction = (containerElement, duration = 1500) => {
  if (!containerElement) return null;
  
  return anime({
    targets: containerElement,
    boxShadow: [
      '0 0 0px rgba(46, 204, 113, 0)',
      '0 0 30px rgba(46, 204, 113, 0.8)',
      '0 0 0px rgba(46, 204, 113, 0)'
    ],
    duration,
    easing: 'easeInOutQuad'
  });
};

/**
 * Animate avatar import with fade and scale
 * @param {HTMLElement} element - The avatar element
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateAvatarChange = (element, duration = 500) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    opacity: [0, 1],
    scale: [0.8, 1],
    rotate: ['0deg', '360deg'],
    duration,
    easing: 'easeOutElastic(1, .6)'
  });
};

/**
 * Pulse animation for active/important elements
 * @param {HTMLElement} element - The element to pulse
 * @param {string} color - Pulse color
 * @param {number} intensity - Pulse intensity (scale multiplier)
 * @returns {Object} Anime.js animation instance
 */
export const animatePulse = (element, color, intensity = 1.05) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    scale: [1, intensity, 1],
    boxShadow: [
      '0 0 0px rgba(0,0,0,0)',
      `0 0 20px ${color}`,
      '0 0 0px rgba(0,0,0,0)'
    ],
    duration: 1500,
    easing: 'easeInOutSine',
    loop: true
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
  if (!element) return null;
  
  return anime({
    targets: element,
    translateX: [
      { value: intensity, duration: duration / 8 },
      { value: -intensity, duration: duration / 8 },
      { value: intensity / 2, duration: duration / 8 },
      { value: -intensity / 2, duration: duration / 8 },
      { value: 0, duration: duration / 2 }
    ],
    easing: 'easeInOutQuad'
  });
};

/**
 * Ripple effect for button clicks
 * @param {HTMLElement} container - Container element
 * @param {number} x - Click X position relative to container
 * @param {number} y - Click Y position relative to container
 * @param {string} color - Ripple color
 * @returns {Object} Anime.js animation instance
 */
export const animateRipple = (container, x, y, color = 'rgba(255, 255, 255, 0.5)') => {
  if (!container) return null;
  
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
  ripple.style.zIndex = '9999';
  
  container.style.position = 'relative';
  container.style.overflow = 'hidden';
  container.appendChild(ripple);
  
  return anime({
    targets: ripple,
    width: '200px',
    height: '200px',
    opacity: [0.8, 0],
    duration: 800,
    easing: 'easeOutQuad',
    complete: () => {
      ripple.remove();
    }
  });
};

/**
 * Success flash animation for successful actions
 * @param {HTMLElement} element - The element to flash
 * @param {string} color - Flash color
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateSuccessFlash = (element, color = '#2ecc71', duration = 600) => {
  if (!element) return null;
  
  return anime({
    targets: element,
    backgroundColor: ['', color, ''],
    scale: [1, 1.02, 1],
    duration,
    easing: 'easeOutCubic'
  });
};

/**
 * Error flash animation for failed actions
 * @param {HTMLElement} element - The element to flash
 * @param {number} duration - Animation duration in ms
 * @returns {Object} Anime.js animation instance
 */
export const animateErrorFlash = (element, duration = 600) => {
  if (!element) return null;
  
  const timeline = anime.timeline();
  
  timeline
    .add({
      targets: element,
      backgroundColor: ['', '#e74c3c'],
      duration: duration / 3,
      easing: 'easeOutCubic'
    })
    .add({
      targets: element,
      translateX: [
        { value: 10, duration: 50 },
        { value: -10, duration: 50 },
        { value: 5, duration: 50 },
        { value: -5, duration: 50 },
        { value: 0, duration: 50 }
      ],
      backgroundColor: ['#e74c3c', ''],
      duration: (duration * 2) / 3,
      easing: 'easeInOutQuad'
    });
  
  return timeline;
};
