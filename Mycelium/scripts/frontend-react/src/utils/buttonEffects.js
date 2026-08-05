/**
 * Utility function to add ripple effect to buttons
 * Call this on button click events to create a Material Design-style ripple
 */

import { animateRipple } from './characterSheetAnimations';

/**
 * Add ripple effect to a button click
 * @param {MouseEvent} event - The click event
 * @param {string} color - Ripple color (defaults to semi-transparent white)
 */
export const addButtonRipple = (event, color = 'rgba(255, 255, 255, 0.5)') => {
  const button = event.currentTarget;
  if (!button) return;
  
  const rect = button.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  
  animateRipple(button, x, y, color);
};

/**
 * Wrap onClick handler to add ripple effect
 * @param {Function} onClick - Original onClick handler
 * @param {string} rippleColor - Ripple color
 * @returns {Function} Enhanced onClick handler with ripple
 */
export const withRipple = (onClick, rippleColor = 'rgba(255, 255, 255, 0.5)') => {
  return (event) => {
    addButtonRipple(event, rippleColor);
    if (onClick) {
      onClick(event);
    }
  };
};

/**
 * Add click animation to any element
 * @param {MouseEvent} event - The click event
 */
export const addClickAnimation = (event) => {
  const element = event.currentTarget;
  if (!element) return;
  
  // Scale animation
  element.style.transform = 'scale(0.95)';
  setTimeout(() => {
    element.style.transform = 'scale(1)';
  }, 100);
};
