# Battlemap Animations - Quick Reference

## Import Statement
```javascript
import {
  animateTokenMove,
  animateTokenSelection,
  animateTokenSpawn,
  animateTokenRemove,
  animateTokenPulse,
  animateHPChange,
  animateCellPaint,
  animateCellErase,
  animateAOEEffect,
  animateConditionAdd,
  animateConditionRemove,
  animateMeasurementLine,
  animateToolSelection,
  animateZoom,
  animateShake,
  animateFloat,
  animateRipple
} from '../utils/battlemapAnimations';
```

## Common Patterns

### Token Selection with Animation
```javascript
const [selectedToken, setSelectedToken] = useState(null);
const tokenRef = useRef(null);

useEffect(() => {
  if (tokenRef.current) {
    animateTokenSelection(tokenRef.current, selectedToken !== null);
  }
}, [selectedToken]);
```

### HP Bar Smooth Transitions
```javascript
const prevHpRef = useRef(null);

useEffect(() => {
  if (prevHpRef.current !== null) {
    const hpBar = tokenRef.current?.querySelector('.hp-bar-path');
    if (hpBar) {
      animateHPChange(hpBar, prevHpRef.current, currentHp);
    }
  }
  prevHpRef.current = currentHp;
}, [currentHp]);
```

### Click Ripple Effect
```javascript
onMouseDown={(e) => {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  animateRipple(e.currentTarget, x, y, 'rgba(100, 149, 237, 0.4)');
}}
```

### Tool Button Selection
```javascript
<button
  onClick={(e) => {
    setCurrentTool('paint');
    animateToolSelection(e.currentTarget, true);
  }}
>
  🖌️ Paint
</button>
```

### Grid Cell Paint Animation
```javascript
onMouseEnter={(e) => {
  if (isPainting) {
    const color = currentColor;
    animateCellPaint(e.currentTarget, color);
    updateCellColor(row, col, color);
  }
}}
```

## CSS Transitions

### Smooth Button Hover
```css
button {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

button:hover {
  transform: scale(1.05);
  filter: brightness(1.1);
}
```

### Token Pulse Effect
```css
.token.selected {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    filter: drop-shadow(0 0 8px rgba(52, 152, 219, 0.6));
  }
  50% {
    filter: drop-shadow(0 0 16px rgba(52, 152, 219, 0.9));
  }
}
```

### Grid Cell Transitions
```css
.grid-cell {
  transition: background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.15s ease-out;
}

.grid-cell:hover {
  transform: scale(1.02);
}
```

## Easing Functions

| Easing | Use Case |
|--------|----------|
| `easeOutCubic` | Default, natural motion |
| `easeOutElastic` | Bouncy, playful effects |
| `easeInOutSine` | Smooth, continuous loops |
| `easeOutQuad` | Quick, responsive actions |
| `easeInBack` | Anticipation before movement |
| `easeOutBack` | Overshoot and settle |

## Duration Guidelines

| Duration | Use Case |
|----------|----------|
| 150-200ms | Quick feedback (hover, click) |
| 300-400ms | Standard transitions |
| 600-800ms | Smooth animations (HP, movements) |
| 1000ms+ | Continuous effects (pulse, float) |

## Performance Tips

1. **Use refs for animation targets:**
   ```javascript
   const elementRef = useRef(null);
   animateTokenMove(elementRef.current, from, to);
   ```

2. **Clean up animations on unmount:**
   ```javascript
   useEffect(() => {
     const animation = animateFloat(elementRef.current);
     return () => animation.pause();
   }, []);
   ```

3. **Use `will-change` for animated properties:**
   ```css
   .animated {
     will-change: transform, opacity;
   }
   ```

4. **Hardware acceleration:**
   ```css
   .accelerated {
     transform: translateZ(0);
     backface-visibility: hidden;
   }
   ```

## Common Issues

### Animation not triggering?
- Check element ref is not null
- Verify element is mounted in DOM
- Console log the element to debug

### Choppy animations?
- Check for forced reflows
- Use transform instead of position
- Enable GPU acceleration

### Multiple animations conflict?
- Pause previous animation first
- Use timelines for sequences
- Check z-index stacking

## Debugging

```javascript
// Log animation state
const anim = animateTokenMove(el, from, to);
console.log('Animation state:', {
  began: anim.began,
  completed: anim.completed,
  currentTime: anim.currentTime,
  duration: anim.duration
});

// Pause animation
anim.pause();

// Resume animation  
anim.play();

// Seek to specific time
anim.seek(500); // Seek to 500ms
```

## Cheat Sheet

```javascript
// Quick selection animation
animateToolSelection(button, true);

// Quick ripple on click
animateRipple(container, x, y);

// Quick cell paint
animateCellPaint(cell, color);

// Quick HP change
animateHPChange(hpBar, oldValue, newValue);

// Quick token select
animateTokenSelection(token, true);

// Quick shake for error
animateShake(element);
```

## Resources

- [anime.js Documentation](https://animejs.com/documentation/)
- [Easing Functions Reference](https://easings.net/)
- [CSS Tricks - Animations](https://css-tricks.com/almanac/properties/a/animation/)
- [MDN Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API)

---

**Pro Tip:** Always test animations at different speeds and on different devices to ensure smooth performance! 🚀
