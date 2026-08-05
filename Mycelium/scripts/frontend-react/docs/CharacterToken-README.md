# CharacterToken Component - Hexagonal Health Bar & Condition Rings

## Overview

The `CharacterToken` component renders character tokens on the battlemap with:
- **Hexagonal health bars** that visually display current HP as a filled arc around the token
- **Condition rings** that appear as colored hexagonal outlines around the health bar
- **Interactive tooltips** that show condition descriptions on hover
- **Character avatar** display using the PixelAvatar component

## Features

### 1. Hexagonal Health Bar
- Displays as a hexagonal ring around the character avatar
- Fills clockwise from the top based on current HP percentage
- Color-coded by health status:
  - **Green** (>66% HP): `#2ecc71`
  - **Orange** (33-66% HP): `#f39c12`
  - **Red** (1-33% HP): `#e74c3c`
  - **Gray** (0% HP): `#95a5a6`
- Shows exact HP values below the token (e.g., "85/100")

### 2. Condition Rings
- Display as additional hexagonal outlines outside the health bar
- Each condition has a unique color:
  - Bleeding out: Dark red `#8b0000`
  - Blinded: Dark gray `#2c3e50`
  - Dazed: Orange `#f39c12`
  - Immobilised: Gray `#7f8c8d`
  - Paralysed: Purple `#9b59b6`
  - Prone: Light gray `#95a5a6`
  - Slowed: Blue `#3498db`
  - Empowered: Yellow `#f1c40f`
  - Armor Surge: Teal `#16a085`
  - Barrier Surge: Purple `#8e44ad`
  - Harmonic Flow: Pink `#e91e63`
- Multiple conditions stack as concentric hexagonal rings
- Hovering over a condition ring shows a tooltip with:
  - Condition name (colored header)
  - Condition description from markdown files

### 3. Selection Indicator
- Selected tokens display an animated dashed hexagonal outline
- Blue color (`#3498db`) with rotating dash animation

## Usage

### Basic Example

```jsx
import CharacterToken from './components/CharacterToken';

<CharacterToken
  token={{
    id: 'token-1',
    name: 'X_Testchar',
    avatar: pixelArray, // 100x100 pixel array
    color: '#3498db',
    currentHp: 2100,
    maxHp: 2600,
    conditions: [
      { name: 'Empowered', active: true, description: 'Deals extra damage' }
    ]
  }}
  size={60}
  isSelected={false}
  onClick={() => handleTokenClick('token-1')}
  characterSheet={parsedCharacterSheet}
/>
```

### Integration with BattlemapCanvas

The `BattlemapCanvas` component automatically integrates CharacterToken:

```jsx
<BattlemapCanvas
  backgroundUrl="/path/to/map.png"
  tiles={paintedTiles}
  rows={10}
  cols={10}
  cellSize={{ width: 50, height: 50 }}
  scale={1.0}
  tokens={[
    {
      id: 'player-1',
      name: 'X_Testchar',
      row: 5,
      col: 5,
      avatar: avatarPixels,
      color: '#e74c3c'
    }
  ]}
  selectedTokenId={selectedId}
  onTokenSelect={handleTokenSelect}
  // ... other props
/>
```

## Character Sheet Integration

### Automatic Data Loading

The component automatically fetches and parses character sheets:

1. **Character Sheet Parser** (`utils/characterSheetParser.js`):
   - Parses markdown character sheets
   - Extracts vitals (HP, stress, etc.)
   - Parses core stats, bending levels, defensive stats
   - Identifies active conditions

2. **Condition Descriptions**:
   - Loaded from `Player Root/Rules/core rules/Conditions/*.md`
   - Cached for performance
   - Displayed in hover tooltips

### Character Sheet Format

The parser expects character sheets in this format:

```markdown
Name: X_Testchar

## Vitals
| key | value |
|-----|-------|
| current_hp | 2100 |
| max_hp | 2600 |

## Core Stats
| Stat | Value |
|------|-------|
| Strength | 1 |
| Dexterity | 2 |

## Conditions
- Empowered
- Slowed
```

## Props

### CharacterToken Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `token` | Object | Yes | Token data including position, name, avatar, HP |
| `size` | Number | No | Token size in pixels (default: 60) |
| `isSelected` | Boolean | No | Whether token is selected (default: false) |
| `onClick` | Function | No | Click handler for token selection |
| `characterSheet` | Object | No | Parsed character sheet data |

### Token Object Structure

```javascript
{
  id: 'unique-token-id',
  name: 'CharacterName',
  row: 5,                    // Grid row position
  col: 5,                    // Grid column position
  avatar: [[...], ...],      // 100x100 pixel array
  color: '#3498db',          // Token border color
  currentHp: 85,             // Current HP (optional if characterSheet provided)
  maxHp: 100,                // Max HP (optional if characterSheet provided)
  conditions: [              // Optional conditions array
    {
      name: 'Slowed',
      active: true,
      description: 'Initiative halved'
    }
  ]
}
```

## Styling

### Custom CSS Classes

```css
.character-token {
  /* Token container styles */
}

.character-token:hover {
  transform: scale(1.05); /* Hover zoom effect */
}

.character-token.selected {
  z-index: 15; /* Selected token appears above others */
}

.token-overlay {
  /* SVG overlay for health bar and conditions */
}

.hp-text {
  /* HP display text styles */
}

.condition-tooltip {
  /* Condition hover tooltip styles */
}
```

## Performance Considerations

1. **Character Sheet Caching**: Character sheets are cached in state to avoid repeated API calls
2. **Condition Description Loading**: Loaded once on mount and shared across all tokens
3. **SVG Path Generation**: Hexagon paths are memoized using `useMemo`
4. **Lazy Loading**: Character sheets only loaded for tokens that are placed on the map

## Future Enhancements

Potential improvements for the component:

1. **Animated Health Changes**: Smooth transitions when HP changes
2. **Damage/Healing Numbers**: Floating numbers showing HP changes
3. **Status Effect Icons**: Small icons within condition rings
4. **Token Dragging**: Drag and drop to move tokens on grid
5. **Size Variations**: Support for large creatures (2x2, 3x3 hex spaces)
6. **Initiative Indicators**: Show turn order on tokens
7. **Range/Movement Indicators**: Highlight valid movement/attack ranges

## Example: Complete Integration

```jsx
import React, { useState } from 'react';
import BattlemapCanvas from './components/BattlemapCanvas';
import { fetchCharacterSheet } from './utils/characterSheetParser';

function BattlemapViewer() {
  const [tokens, setTokens] = useState([
    {
      id: 'pc-1',
      name: 'X_Testchar',
      row: 5,
      col: 5,
      avatar: testCharAvatar,
      color: '#3498db'
    }
  ]);
  const [selectedToken, setSelectedToken] = useState(null);

  return (
    <BattlemapCanvas
      backgroundUrl="/maps/forest-clearing.png"
      tiles={mapTiles}
      rows={15}
      cols={15}
      cellSize={{ width: 50, height: 50 }}
      scale={1.0}
      tokens={tokens}
      selectedTokenId={selectedToken}
      onTokenSelect={setSelectedToken}
      isPainting={false}
      onStartPaint={() => {}}
      onPaintCell={() => {}}
    />
  );
}
```

## Troubleshooting

### Health bar not displaying correctly
- Ensure `currentHp` and `maxHp` are numeric values
- Check that character sheet vitals table has correct format

### Conditions not showing
- Verify condition names match exactly (case-sensitive)
- Check that condition markdown files exist in `Player Root/Rules/core rules/Conditions/`

### Token positioning issues
- Verify `row` and `col` values are within grid bounds
- Check `cellSize` and `scale` props are set correctly

### Character sheet not loading
- Confirm character name matches folder structure
- Check file path: `Player Root/PCs/{name}/{name} character sheet.md`
- Verify API base URL is configured correctly

## Related Files

- `CharacterToken.jsx` - Main token component
- `CharacterToken.css` - Token styling
- `BattlemapCanvas.jsx` - Canvas with token integration
- `characterSheetParser.js` - Character sheet parsing utilities
- `avatarUtils.js` - Pixel avatar utilities
