# Battlemap Animations with anime.js

This document describes the smooth animations integrated into the battlemap using anime.js.

## Installation

```bash
npm install animejs
```

## Available Animations

### Token Animations

#### `animateTokenMove(element, from, to, duration, easing)`
Smoothly animates a token moving from one grid position to another with a subtle bounce effect on landing.

**Parameters:**
- `element`: The token DOM element
- `from`: Starting position `{x, y}`
- `to`: Target position `{x, y}`
- `duration`: Animation duration in ms (default: 400)
- `easing`: Easing function (default: 'easeOutCubic')

#### `animateTokenSelection(element, selected)`
Animates token selection with a scale and bounce effect.

#### `animateTokenSpawn(element, duration)`
Animates a token appearing on the map with rotation and scale.

#### `animateTokenRemove(element, duration)`
Animates a token disappearing with reverse rotation and fade.

#### `animateTokenPulse(element)`
Continuous subtle pulse animation for selected tokens.

### HP and Condition Animations

#### `animateHPChange(element, fromPercentage, toPercentage, duration)`
Smoothly transitions HP bar changes over time.

#### `animateConditionAdd(element, duration)`
Animates condition ring appearing with rotation.

#### `animateConditionRemove(element, duration)`
Animates condition ring disappearing.

### Grid Cell Animations

#### `animateCellPaint(element, color, duration)`
Animates painting a grid cell with color and subtle scale effect.

#### `animateCellErase(element, duration)`
Animates erasing a grid cell.

#### `animateRipple(container, x, y, color)`
Creates a ripple effect at click position (visual feedback).

### AOE Effect Animations

#### `animateAOEEffect(elements, color, duration, pattern)`
Animates area of effect patterns (sphere, cone, line) with staggered delays.

**Patterns:**
- `'radial'`: Expands from center outward
- `'linear'`: Animates in sequence
- `'random'`: Random stagger effect

### Tool Animations

#### `animateToolSelection(element, selected)`
Animates tool button selection with bounce and scale.

#### `animateMeasurementLine(element, duration)`
Animates measurement line drawing with stroke-dashoffset.

### Utility Animations

#### `animateZoom(element, fromScale, toScale, duration)`
Smoothly animates zoom/scale transitions.

#### `animateShake(element, intensity, duration)`
Shake animation for errors or invalid actions.

#### `animateFloat(element, distance)`
Floating animation for hover effects.

## CSS Enhancements

The following CSS improvements have been added for smoother interactions:

### Grid Cells
- Smooth background color transitions
- Hover scale effect with z-index elevation
- Cubic bezier easing for natural motion

### Character Tokens
- Pulse animation for selected tokens
- Glow effects on hover
- Drop shadow transitions
- Smooth HP bar path transitions

### Tool Buttons
- Bounce animation on selection
- Hover scale and transform effects
- Gradient background transitions

### Performance Optimizations
- Hardware acceleration with `translateZ(0)`
- `will-change` properties for animated elements
- Backface visibility hidden for smooth 3D transforms

## Usage Examples

### Animating Token Movement
```javascript
import { animateTokenMove } from '../utils/battlemapAnimations';

const tokenElement = document.querySelector('.token');
animateTokenMove(tokenElement, {x: 100, y: 100}, {x: 200, y: 200});
```

### Animating Tool Selection
```javascript
import { animateToolSelection } from '../utils/battlemapAnimations';

const toolButton = e.currentTarget;
animateToolSelection(toolButton, true);
```

### Creating Ripple Effect on Click
```javascript
import { animateRipple } from '../utils/battlemapAnimations';

onMouseDown={(e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  animateRipple(e.currentTarget, x, y, 'rgba(100, 149, 237, 0.4)');
}}
```

### Animating HP Changes
```javascript
import { animateHPChange } from '../utils/battlemapAnimations';

useEffect(() => {
  if (prevHpRef.current !== null && prevHpRef.current !== hpData.percentage) {
    const hpBarPath = tokenRef.current?.querySelector('.hp-bar-path');
    if (hpBarPath) {
      animateHPChange(hpBarPath, prevHpRef.current, hpData.percentage);
    }
  }
  prevHpRef.current = hpData.percentage;
}, [hpData.percentage]);
```

## Integration Status

### ✅ Completed
- [x] Token selection animations
- [x] HP bar smooth transitions
- [x] Grid cell paint/erase animations
- [x] Tool button selection animations
- [x] Ripple click feedback
- [x] CSS transitions and hover effects
- [x] Character token pulse animations

### 🔄 Future Enhancements
- [ ] Token movement drag animations
- [ ] AOE effect animations (sphere, cone, line)
- [ ] Condition ring animations on add/remove
- [ ] Token spawn/despawn animations
- [ ] Measurement line drawing animation
- [ ] Camera zoom animations

## Performance Notes

All animations use:
- Hardware-accelerated CSS transforms
- RequestAnimationFrame for smooth 60fps
- Easing functions for natural motion
- Minimal repaints and reflows
- `will-change` hints for browser optimization

## Browser Support

Requires:
- Modern browsers with CSS3 support
- ES6+ JavaScript support
- anime.js library

Compatible with: Chrome, Firefox, Safari, Edge (latest versions)
