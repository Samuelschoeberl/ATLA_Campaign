# Integration Guide: CharacterToken with Hex Grid

## Current State

The codebase has **two different battlemap systems**:

### 1. BattlemapCanvas (Square Grid)
- **Location**: `src/components/BattlemapCanvas.jsx`
- **Grid Type**: Square/rectangular grid
- **Use Case**: Simple tactical maps with painted tiles
- **Status**: ✅ **Updated with CharacterToken integration**

### 2. BattlemapViewer (Hex Grid)
- **Location**: `src/components/BattlemapViewer.jsx`  
- **Grid Type**: Hexagonal grid (flat-top orientation)
- **Use Case**: Advanced tactical maps with hex movement, effects, and tokens
- **Status**: ⚠️ **Needs CharacterToken adaptation**

## CharacterToken Integration

### Square Grid (BattlemapCanvas) - ✅ Complete

The CharacterToken component is already integrated with `BattlemapCanvas`:

```jsx
<BattlemapCanvas
  backgroundUrl="/maps/tavern.png"
  tiles={gridTiles}
  rows={10}
  cols={10}
  cellSize={{ width: 50, height: 50 }}
  scale={1.0}
  tokens={[
    {
      id: 'pc-1',
      name: 'X_Testchar',
      row: 5,
      col: 5,
      avatar: avatarPixels,
      color: '#3498db'
    }
  ]}
  selectedTokenId={selectedId}
  onTokenSelect={handleSelect}
  // ... other props
/>
```

### Hex Grid (BattlemapViewer) - ⚠️ Needs Adaptation

The `BattlemapViewer` currently renders tokens inline using SVG. To integrate CharacterToken:

## Option 1: Enhance Existing SVG Token Rendering

**Pros**: 
- No breaking changes
- Maintains SVG-based rendering
- Integrates with existing hex math

**Cons**:
- CharacterToken needs SVG version
- More complex implementation

### Implementation Steps:

1. **Create HexCharacterToken Component**
```jsx
// src/components/HexCharacterToken.jsx
import React, { useMemo } from 'react';

const HexCharacterToken = ({ 
  token, 
  centerX, 
  centerY, 
  hexSize,
  characterSheet,
  isSelected,
  onClick 
}) => {
  // Generate hexagonal health bar using SVG paths
  const healthBarPath = useMemo(() => {
    // Similar to CharacterToken but for SVG group
    const percentage = characterSheet?.vitals?.current_hp / characterSheet?.vitals?.max_hp * 100 || 100;
    // ... hex path generation
  }, [characterSheet]);

  return (
    <g onClick={onClick}>
      {/* Health bar ring */}
      <path 
        d={healthBarPath} 
        fill={getHealthColor(percentage)}
        opacity={0.9}
      />
      
      {/* Condition rings */}
      {conditions.map((condition, idx) => (
        <path
          key={idx}
          d={getConditionRingPath(centerX, centerY, hexSize, idx)}
          stroke={getConditionColor(condition)}
          strokeWidth={2}
          fill="none"
        />
      ))}
      
      {/* Avatar */}
      <foreignObject 
        x={centerX - hexSize} 
        y={centerY - hexSize}
        width={hexSize * 2} 
        height={hexSize * 2}
      >
        <PixelAvatar pixels={token.avatar} size={hexSize * 2} />
      </foreignObject>
    </g>
  );
};
```

2. **Update BattlemapViewer Token Rendering**
```jsx
// In BattlemapViewer.jsx, replace token rendering section
{tokens.map(token => {
  const { cx, cy } = getHexCoordinates(token.row, token.col);
  
  return (
    <HexCharacterToken
      key={token.id}
      token={token}
      centerX={cx}
      centerY={cy}
      hexSize={hexSize}
      characterSheet={characterSheets[token.name]}
      isSelected={selectedToken === token.id}
      onClick={() => setSelectedToken(token.id)}
    />
  );
})}
```

## Option 2: HTML Overlay for Tokens

**Pros**:
- Reuse existing CharacterToken component
- Easier to implement
- Better hover effects and tooltips

**Cons**:
- Mixing HTML and SVG rendering
- Positioning can be tricky with zoom/pan

### Implementation Steps:

1. **Add HTML overlay layer to BattlemapViewer**
```jsx
// In BattlemapViewer.jsx
<div style={{ position: 'relative' }}>
  {/* Existing SVG hex grid */}
  <svg>...</svg>
  
  {/* HTML token overlay */}
  <div className="token-overlay-layer">
    {tokens.map(token => {
      const { cx, cy } = getHexCoordinates(token.row, token.col);
      const screenPos = svgToScreenCoordinates(cx, cy, scale, pan);
      
      return (
        <div
          key={token.id}
          style={{
            position: 'absolute',
            left: screenPos.x,
            top: screenPos.y,
            transform: 'translate(-50%, -50%)'
          }}
        >
          <CharacterToken
            token={token}
            size={hexSize * scale}
            characterSheet={characterSheets[token.name]}
            isSelected={selectedToken === token.id}
            onClick={() => setSelectedToken(token.id)}
          />
        </div>
      );
    })}
  </div>
</div>
```

2. **Add coordinate conversion helper**
```javascript
const svgToScreenCoordinates = (svgX, svgY, scale, pan) => {
  // Convert SVG coordinates to screen coordinates
  // accounting for zoom and pan
  return {
    x: (svgX * scale) + pan.x,
    y: (svgY * scale) + pan.y
  };
};
```

## Recommended Approach

**Use Option 1 (SVG-based HexCharacterToken)** because:

1. **Consistency**: Matches existing BattlemapViewer architecture
2. **Performance**: No coordinate conversion overhead
3. **Scaling**: Works seamlessly with SVG zoom/pan
4. **Interaction**: Better integration with existing hex interactions

## Step-by-Step Implementation

### Phase 1: Create HexCharacterToken

```bash
# Create new component
touch src/components/HexCharacterToken.jsx
```

### Phase 2: Adapt CharacterToken Logic

Convert the CharacterToken hexagon generation to work with SVG coordinates:

```javascript
// Instead of viewBox coordinates, use actual SVG coordinates
const generateHexPath = (cx, cy, radius, percentage) => {
  // cx, cy are hex center coordinates from getHexCoordinates()
  // radius is hexSize * scale factor
  // percentage is HP percentage
  
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    points.push({ x, y });
  }
  
  // Generate partial arc based on percentage...
  return svgPathString;
};
```

### Phase 3: Integrate with BattlemapViewer

1. Import HexCharacterToken
2. Load character sheets in BattlemapViewer state
3. Replace existing token rendering with HexCharacterToken
4. Wire up selection, hover, and drag events

### Phase 4: Test

- [ ] Health bars display correctly on hex tokens
- [ ] Condition rings stack properly
- [ ] Tooltips appear on hover
- [ ] Selection indicator works
- [ ] Token dragging still functions
- [ ] Works with different token sizes (1x1, 2x2, etc.)
- [ ] Scales correctly with zoom
- [ ] Character sheet data loads properly

## Migration Path

### For Existing Projects

1. **Keep BattlemapCanvas** for simple square-grid maps
2. **Enhance BattlemapViewer** with HexCharacterToken for hex maps
3. Both systems can coexist

### For New Projects

Choose based on use case:
- **Square grid**: Use BattlemapCanvas with CharacterToken
- **Hex grid**: Use BattlemapViewer with HexCharacterToken

## Code Examples

### Full HexCharacterToken Implementation

```jsx
import React, { useState, useMemo } from 'react';
import PixelAvatar from './PixelAvatar';

const HexCharacterToken = ({
  token,
  centerX,
  centerY,
  hexSize,
  characterSheet,
  isSelected,
  onClick,
  onMouseEnter,
  onMouseLeave
}) => {
  const [hoveredCondition, setHoveredCondition] = useState(null);
  
  // Extract HP data
  const hpData = useMemo(() => {
    if (characterSheet?.vitals) {
      const current = parseFloat(characterSheet.vitals.current_hp) || 0;
      const max = parseFloat(characterSheet.vitals.max_hp) || 100;
      return { current, max, percentage: (current / max) * 100 };
    }
    return { current: 100, max: 100, percentage: 100 };
  }, [characterSheet]);
  
  // Generate health bar hexagon
  const healthBarPath = useMemo(() => {
    const radius = hexSize * 0.9;
    const points = [];
    
    // Calculate hex vertices
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      points.push({ x, y });
    }
    
    // Create arc based on HP percentage
    const pct = hpData.percentage / 100;
    const filledSegments = Math.floor(pct * 6);
    const partial = (pct * 6) % 1;
    
    let path = `M ${centerX},${centerY}`;
    
    for (let i = 0; i <= filledSegments; i++) {
      path += ` L ${points[i].x},${points[i].y}`;
    }
    
    if (partial > 0 && filledSegments < 6) {
      const start = points[filledSegments];
      const end = points[filledSegments + 1];
      const px = start.x + (end.x - start.x) * partial;
      const py = start.y + (end.y - start.y) * partial;
      path += ` L ${px},${py}`;
    }
    
    path += ' Z';
    return path;
  }, [centerX, centerY, hexSize, hpData.percentage]);
  
  // Health bar color
  const healthColor = useMemo(() => {
    const pct = hpData.percentage;
    if (pct > 66) return '#2ecc71';
    if (pct > 33) return '#f39c12';
    if (pct > 0) return '#e74c3c';
    return '#95a5a6';
  }, [hpData.percentage]);
  
  // Condition rings
  const conditions = characterSheet?.conditions?.filter(c => c.active) || [];
  
  return (
    <g onClick={onClick} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}>
      {/* Health bar background ring */}
      <path
        d={healthBarPath}
        fill={healthColor}
        opacity={0.85}
      />
      
      {/* Condition rings */}
      {conditions.map((condition, idx) => {
        const ringRadius = hexSize * (1.0 + idx * 0.1);
        const ringPoints = [];
        
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i - Math.PI / 2;
          const x = centerX + ringRadius * Math.cos(angle);
          const y = centerY + ringRadius * Math.sin(angle);
          ringPoints.push(`${x},${y}`);
        }
        
        return (
          <polygon
            key={`condition-${idx}`}
            points={ringPoints.join(' ')}
            fill="none"
            stroke={getConditionColor(condition.name)}
            strokeWidth={2}
            opacity={0.9}
            onMouseEnter={() => setHoveredCondition(condition)}
            onMouseLeave={() => setHoveredCondition(null)}
          />
        );
      })}
      
      {/* Selection indicator */}
      {isSelected && (
        <polygon
          points={getHexPoints(centerX, centerY, hexSize * 1.2)}
          fill="none"
          stroke="#3498db"
          strokeWidth={3}
          strokeDasharray="8 4"
          opacity={0.9}
        >
          <animate
            attributeName="stroke-dashoffset"
            from="0"
            to="24"
            dur="1s"
            repeatCount="indefinite"
          />
        </polygon>
      )}
      
      {/* Avatar */}
      <foreignObject
        x={centerX - hexSize * 0.6}
        y={centerY - hexSize * 0.6}
        width={hexSize * 1.2}
        height={hexSize * 1.2}
        style={{ pointerEvents: 'none' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
          <PixelAvatar
            pixels={token.avatar}
            size={hexSize * 1.2}
            borderColor={token.color}
            placeholderLabel={token.name?.[0]}
            background="transparent"
          />
        </div>
      </foreignObject>
      
      {/* HP text */}
      <text
        x={centerX}
        y={centerY + hexSize * 1.3}
        textAnchor="middle"
        fontSize={hexSize * 0.25}
        fontWeight="bold"
        fill={healthColor}
        style={{ textShadow: '0 0 3px rgba(0,0,0,0.8)' }}
      >
        {Math.round(hpData.current)}/{hpData.max}
      </text>
      
      {/* Condition tooltip */}
      {hoveredCondition && (
        <foreignObject
          x={centerX - 100}
          y={centerY - hexSize * 2}
          width={200}
          height={60}
          style={{ pointerEvents: 'none' }}
        >
          <div style={{
            background: 'rgba(0,0,0,0.95)',
            padding: '8px',
            borderRadius: '6px',
            color: '#fff',
            fontSize: '12px',
            border: `2px solid ${getConditionColor(hoveredCondition.name)}`
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
              {hoveredCondition.name}
            </div>
            <div style={{ fontSize: '11px', opacity: 0.9 }}>
              {hoveredCondition.description}
            </div>
          </div>
        </foreignObject>
      )}
    </g>
  );
};

// Helper function
const getConditionColor = (conditionName) => {
  const colors = {
    'Bleeding out': '#8b0000',
    'Blinded': '#2c3e50',
    'Dazed': '#f39c12',
    'Immobilised': '#7f8c8d',
    'Paralysed': '#9b59b6',
    'Prone': '#95a5a6',
    'Slowed': '#3498db',
    'Empowered': '#f1c40f',
    'Armor Surge': '#16a085',
    'Barrier Surge': '#8e44ad',
    'Harmonic Flow': '#e91e63'
  };
  return colors[conditionName] || '#e74c3c';
};

const getHexPoints = (cx, cy, radius) => {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    points.push(`${x},${y}`);
  }
  return points.join(' ');
};

export default HexCharacterToken;
```

## Summary

The CharacterToken component has been successfully integrated with **BattlemapCanvas** (square grid). For **BattlemapViewer** (hex grid), you can either:

1. **Create HexCharacterToken** - SVG-based version (recommended)
2. **Use HTML overlay** - Reuse existing CharacterToken with coordinate conversion

Both approaches will provide the same visual features:
- ✅ Hexagonal health bars
- ✅ Condition rings with colors
- ✅ Hover tooltips
- ✅ Character sheet integration
- ✅ Selection indicators
