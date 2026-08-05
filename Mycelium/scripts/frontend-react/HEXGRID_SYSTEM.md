# Hex Grid System Documentation

## Overview
The hex grid system is used across multiple components to visualize bending moves and battlemap positioning. All components use **flat-top hexagons** (pointy sides) for consistency.

## Core Components

### 1. HexGrid.jsx (3D Canvas - for simple visualization)
- Uses `@react-three/fiber` and Three.js for 3D rendering
- **Dimensions:**
  - Hex radius: `0.5`
  - Hex width: `Math.sqrt(3) / 2` 
  - Hex height: `0.75`
- **Purpose:** Simple 3D hex grid visualization (currently used, but may be deprecated in favor of HexGridSVG)

### 2. HexGridSVG.jsx (2D SVG - for bending moves)
- Uses SVG for precise 2D rendering with character avatars
- **Dimensions:**
  - Hex size: `20` (distance from center to vertex)
  - Horizontal spacing: `hexSize * Math.sqrt(3)`
  - Vertical spacing: `hexSize * 1.5`
- **Features:**
  - Renders effect area hexagons
  - Shows character avatar at bender position
  - Displays path hexagons between bender and effect
  - Accounts for hex tessellation (odd rows offset by half-width)

### 3. BattlemapCanvas.jsx (battlemap grid)
- Uses CSS grid for battlemap display
- **Dimensions:** Dynamic based on image and cell size
- **Features:**
  - Background image overlay
  - Paintable grid cells
  - Character token positioning using row/col coordinates
  - Tokens positioned at cell centers

## Hex Grid Pattern System

### Pattern Structure
All area patterns use the same format:
```javascript
{
  type: [
    { count: 3, offset: 0 },  // Row 0: 3 hexes, no offset
    { count: 4, offset: 0 }   // Row 1: 4 hexes, no offset
  ]
}
```

- **count**: Number of hexagons in this row
- **offset**: Horizontal offset in half-width units (for pattern centering, NOT tessellation)

### Tessellation (automatic in HexGridSVG)
Hex grids tessellate naturally:
- **Even rows (0, 2, 4...):** Aligned at base x-position
- **Odd rows (1, 3, 5...):** Offset by `hexWidth / 2` to the right

This creates proper hex grid interlocking without gaps.

### Area Patterns (AREA_PATTERNS in BendingMove.jsx)

#### Cone
```javascript
cone: [
  { count: 1, offset: 0 },  // Starting point (narrow)
  { count: 2, offset: 0 },
  { count: 3, offset: 0 },
  { count: 3, offset: 0 },
  { count: 4, offset: 0 }   // Wide end
]
```
Represents a 15-foot cone expanding from caster. The tessellation naturally creates the cone spread.

#### Melee
```javascript
melee: [
  { count: 2, offset: 1 },  // Top 2 hexes
  { count: 3, offset: 0 },  // Middle 3 hexes (includes sides)
  { count: 2, offset: 1 }   // Bottom 2 hexes
]
```
Creates a ring of 6 hexes around center hex. With tessellation, this properly surrounds a central position.

#### Sphere/Burst
```javascript
sphere: [
  { count: 2, offset: 1 },
  { count: 3, offset: 0 },
  { count: 2, offset: 1 }
]
```
Circular explosion pattern (like Fireball).

#### Line
```javascript
line: [
  { count: 5, offset: 0 }
]
```
Straight horizontal line of hexes.

#### Other patterns
- **aura**: Larger circular area (5 rows)
- **wall**: Two parallel rows (4 hexes each)
- **cluster**: Scattered hexes in diamond pattern
- **self**: Single hex (caster only)

## Rendering Flow in BendingMove.jsx

1. **Parse markdown file** (e.g., "Fireball - Ash.md")
2. **Extract metadata** (Target Range, Effect Range, Damage, etc.)
3. **Detect area type** using `detectAreaInfo()`:
   - Searches metadata for keywords (cone, sphere, line, melee, etc.)
   - Matches to AREA_MATCHERS array
   - Returns corresponding pattern from AREA_PATTERNS
4. **Extract range multiplier** from "Target Range" field:
   - Example: "5 * [[Firebending_slot]] (6) meters" → range = 5
5. **Render HexGridSVG** with:
   - `pattern`: The matched area pattern
   - `color`: Element color (fire, water, air, earth, spirit)
   - `range`: Distance from caster to effect
   - `characterData`: For avatar display

## Future Feature: Connecting to Battlemap

### Goal
Paste animated effect JSON files onto the battlemap's hex grid during combat.

### Implementation Plan

1. **Standardize coordinate system:**
   ```javascript
   // Both systems use row/col coordinates
   battlemap: { row: number, col: number }
   hexEffect: { row: number, col: number, filled: boolean }
   ```

2. **Effect JSON format:**
   ```json
   {
     "effectId": "fireball_ash_001",
     "moveType": "sphere",
     "pattern": [
       { "count": 2, "offset": 1 },
       { "count": 3, "offset": 0 },
       { "count": 2, "offset": 1 }
     ],
     "color": "#ffb3b3",
     "opacity": 0.35,
     "duration": 2000,
     "animation": "fade-in-out"
   }
   ```

3. **Overlay component:**
   ```jsx
   <BattlemapCanvas>
     {/* Existing grid and tokens */}
     
     {/* Effect overlay */}
     <EffectOverlay
       effects={activeEffects}
       gridScale={scale}
       cellSize={cellSize}
     />
   </BattlemapCanvas>
   ```

4. **Position calculation:**
   ```javascript
   // Convert effect pattern to battlemap positions
   const effectCells = pattern.map((row, rowIdx) => {
     return Array(row.count).fill(0).map((_, colIdx) => ({
       row: targetRow + rowIdx,
       col: targetCol + colIdx + row.offset,
       opacity: 0.35,
       color: effectColor
     }));
   });
   ```

5. **Animation system:**
   - Use CSS animations or React Spring for effect animations
   - Support: fade-in, fade-out, pulse, spread (for expanding effects)
   - Timed removal after duration

### Benefits
- Visual feedback for area-of-effect abilities during combat
- Players see exact hexes affected by abilities
- Can preview moves before casting
- Supports animated lingering effects
- Consistent visualization between move preview and actual use

## Key Differences Between Components

| Feature | HexGrid.jsx | HexGridSVG.jsx | BattlemapCanvas.jsx |
|---------|-------------|----------------|---------------------|
| Rendering | Three.js 3D | SVG 2D | CSS Grid |
| Use Case | Simple viz | Bending moves | Combat map |
| Avatars | ❌ | ✅ | ✅ (tokens) |
| Animation | Three.js | CSS/SVG | CSS |
| Tessellation | Manual | Automatic | N/A (square grid) |
| Interactivity | Low | Medium | High |

## Coordinate System Conversion

### HexGridSVG → Battlemap
To paste effect onto battlemap, need to:
1. Get target token position: `{ row, col }`
2. Convert pattern to relative offsets
3. Apply to battlemap grid coordinates
4. Account for hex orientation (HexGridSVG flat-top = Battlemap flat-top ✓)

### Formula
```javascript
// HexGridSVG uses centered coords, Battlemap uses grid indices
function hexPatternToBattlemapCells(pattern, targetRow, targetCol) {
  const cells = [];
  pattern.forEach((row, rowIdx) => {
    const tessellationOffset = (rowIdx % 2 === 1) ? 0.5 : 0;
    for (let i = 0; i < row.count; i++) {
      const colOffset = (i - (row.count - 1) / 2) + row.offset + tessellationOffset;
      cells.push({
        row: targetRow + rowIdx,
        col: targetCol + Math.round(colOffset)
      });
    }
  });
  return cells;
}
```

## Testing Checklist
- [ ] Cone spreads correctly (1 → 2 → 3 → 3 → 4 hexes)
- [ ] Melee shows 6 surrounding hexes (proper ring)
- [ ] Sphere is circular (not diamond)
- [ ] Line is straight horizontal
- [ ] Range displays correct number of path hexes
- [ ] Character avatar appears at bender position
- [ ] Colors match element type
- [ ] Pattern can be exported to JSON
- [ ] JSON can overlay on battlemap grid

## Next Steps
1. ✅ Fix cone and melee patterns
2. Test all pattern types with various ranges
3. Implement effect JSON export from BendingMove
4. Create EffectOverlay component for BattlemapCanvas
5. Add animation system
6. Add effect duration tracking
7. Implement effect preview on hover in combat
