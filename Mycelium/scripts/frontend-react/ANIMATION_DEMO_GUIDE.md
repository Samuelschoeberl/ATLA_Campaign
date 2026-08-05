# Battlemap Animation Demo Guide

## Quick Start

1. **Start the development server:**
   ```bash
   cd Mycelium/scripts/frontend-react
   npm run dev
   ```

2. **Open the battlemap in your browser**

3. **Try these interactions to see the animations:**

## Interactive Demo Checklist

### 🎨 Tool Selection Animations
**What to test:** Click different tool buttons in the Drawing Tools section

**Expected behavior:**
- ✨ Button bounces and scales up when selected
- ✨ Blue gradient highlight appears
- ✨ Glow effect surrounds the button
- ✨ Smooth hover effects on all buttons

**Tools to try:**
- 🖌️ Paint
- 🧹 Eraser
- ✏️ Edit Data
- 📏 Measure
- ⭕ Sphere
- 📐 Cone
- ➖ Line
- ✨ Aura
- 🎭 Place Token
- 👤 Move Tokens

### 🎯 Grid Cell Interactions
**What to test:** Click and drag on grid cells to paint

**Expected behavior:**
- 💫 Ripple effect appears at click location
- 🎨 Cells smoothly transition to new color
- ✨ Slight scale effect on hover
- 🌊 Smooth erase with fade-out effect

**How to test:**
1. Select Paint tool (🖌️)
2. Click a cell - watch for ripple
3. Drag across multiple cells
4. Switch to Eraser (🧹)
5. Erase cells - watch smooth fade

### 🪙 Token Animations
**What to test:** Interact with character tokens on the map

**Expected behavior:**
- ✨ Selected tokens pulse continuously
- 🔆 Hover creates glow effect and lift
- 💓 HP bar changes animate smoothly
- 🎭 Condition rings have smooth transitions

**How to test:**
1. Place or select a token
2. Watch the pulsing blue glow effect
3. Hover over token - see it lift and glow
4. Edit HP values - watch bar animate
5. Add conditions - see rings animate in

### 🎪 Effect Preset Buttons
**What to test:** Click different effect emoji buttons (🔥 ❄️ ☠️ ⚡ etc.)

**Expected behavior:**
- 🎯 Selected button scales up
- 🌈 Gradient background appears
- ✨ Glow effect matches element color
- 🔄 Smooth transitions between selections

**Effects to try:**
- 🔥 Fire (orange glow)
- ❄️ Ice (blue glow)
- ☠️ Poison (purple glow)
- ⚡ Lightning (yellow glow)
- 🪨 Earth (brown glow)
- 🌪️ Air (white glow)
- 🌑 Darkness (dark glow)
- ✨ Healing (golden glow)

### 🎬 Animation Combinations

#### Test Scenario 1: Paint Mode
1. Select Paint tool (🖌️)
2. Choose an effect (🔥 Fire)
3. Click cells rapidly
4. Watch ripples + color transitions combine

#### Test Scenario 2: Token Selection
1. Select Move Tokens tool (👤)
2. Click different tokens
3. Watch each pulse when selected
4. Hover between tokens for smooth transitions

#### Test Scenario 3: HP Changes
1. Have character sheets loaded
2. Select a token
3. Change HP value via edit modal
4. Watch HP bar smoothly transition

#### Test Scenario 4: Tool Switching
1. Rapidly switch between tools
2. Watch bounce animations on each click
3. Notice smooth deselection of previous tool

## Performance Check

While testing, monitor:
- ✅ Animations should be **smooth 60fps**
- ✅ No lag when dragging/painting
- ✅ Transitions should feel **natural** not robotic
- ✅ Hover effects should be **instant**
- ✅ No visual glitches or jumping

## Visual Indicators Guide

### Color Meanings
- **Blue glow** = Selected
- **Blue pulse** = Currently active token
- **Green** = Healthy HP (>66%)
- **Orange** = Damaged HP (33-66%)
- **Red** = Critical HP (<33%)
- **Various colors** = Element types and conditions

### Animation Timing
- **Quick (200ms)** = Cell interactions, hovers
- **Medium (400ms)** = Tool selection, HP changes
- **Slow (600ms+)** = Continuous effects, pulses

## Troubleshooting

### If animations don't appear:
1. Check browser console for errors
2. Verify anime.js is installed: `npm list animejs`
3. Hard refresh browser (Cmd+Shift+R / Ctrl+Shift+R)
4. Check that dev server is running

### If animations are choppy:
1. Close other browser tabs
2. Check CPU usage (should be <10%)
3. Try disabling browser extensions
4. Verify GPU acceleration is enabled

### If buttons don't respond:
1. Check that JavaScript is enabled
2. Try clicking directly on emoji icons
3. Refresh the page
4. Check network tab for loading issues

## Advanced Testing

### Frame Rate Check
Open browser DevTools:
1. Press F12
2. Go to Performance tab
3. Record while interacting
4. Check FPS counter (should be 60fps)

### Animation Inspection
1. Right-click animated element
2. Select "Inspect"
3. Watch Styles panel for transitions
4. See Animations panel for active animations

## Feedback Points

When testing, note:
- [ ] Do animations feel smooth?
- [ ] Are transitions too fast/slow?
- [ ] Do effects feel polished?
- [ ] Any jarring or abrupt changes?
- [ ] Do colors/glows look good?
- [ ] Is visual feedback clear?

## Next Steps

After testing basics, try:
1. **Multi-token selection** - Select several tokens in sequence
2. **Rapid tool switching** - Click tools quickly
3. **Mass painting** - Paint large areas at once
4. **Effect combinations** - Try different element effects
5. **Stress test** - Many tokens with conditions

## Recording Demo

To create a video demo:
1. Use screen recording (QuickTime, OBS, etc.)
2. Show all tool selections with bounces
3. Demonstrate grid painting with ripples
4. Show token selection pulses
5. Highlight HP bar transitions
6. Show effect preset selections

## Known Limitations

Current implementation:
- ✅ Token selection animations
- ✅ Tool button animations  
- ✅ Grid cell paint/erase
- ✅ HP bar transitions
- ✅ Ripple effects
- ⏳ Token drag movement (uses CSS only)
- ⏳ AOE effect stagger (planned)
- ⏳ Condition add/remove (planned)

## Support

If you encounter issues:
1. Check `ANIMATION_IMPLEMENTATION_SUMMARY.md`
2. Review `BATTLEMAP_ANIMATIONS.md` for API docs
3. Check browser console for errors
4. Verify all dependencies installed

---

**Enjoy the smoother battlemap experience! 🎮✨**
