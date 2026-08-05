import React, { useMemo, useId } from 'react';
import PixelAvatar from './PixelAvatar';

/**
 * HexGridSVG - Renders hexagon tiling by filling hexagons based on pattern
 * Shows bender position and effect area with proper spacing
 * 
 * @param {Array} pattern - Array of {count, offset} objects defining the grid pattern
 * @param {string} color - Hex color code
 * @param {number} opacity - Opacity value (0-1)
 * @param {boolean} lightMode - Whether light mode is active
 * @param {number} range - Range multiplier (e.g., 5 for "5 * firebending_slot meters")
 * @param {Object} characterData - Character data for pixel avatar
 * @param {string} patternType - Type of pattern (e.g., 'cone', 'sphere', 'line')
 */
const HexGridSVG = ({ 
  pattern, 
  color = '#3498db', 
  opacity = 0.35, 
  lightMode = false,
  range = 0,
  characterData = null,
  patternType = null
}) => {
  if (!pattern || pattern.length === 0) return null;

  const hexSize = 20; // Distance from center to vertex
  const clipPathId = useId(); // Generate unique ID for this component instance

  const { benderHex, effectHexagons, pathHexagons, bounds } = useMemo(() => {
    const hexList = [];
    
    // Calculate hexagon dimensions for flat-top hexagons
    const hexWidth = hexSize * Math.sqrt(3);
    const hexHeight = hexSize * 2;
    
    // Proper spacing for tessellation
    const horizSpacing = hexWidth;
    const vertSpacing = hexSize * 1.5;

    // First, generate effect hexagons at position (0, 0) centered
    pattern.forEach((row, rowIdx) => {
      const cy = rowIdx * vertSpacing;
      
      // For proper tessellation: every odd row is offset by half width
      const tessellationOffset = (rowIdx % 2 === 1) ? (hexWidth / 2) : 0;
      
      // Pattern offset is for centering the pattern, not tessellation
      const patternOffset = row.offset * (hexWidth / 2);
      
      for (let i = 0; i < row.count; i++) {
        const cx = (i - (row.count - 1) / 2) * horizSpacing + patternOffset + tessellationOffset;
        
        const vertices = [];
        for (let v = 0; v < 6; v++) {
          const angle = (Math.PI / 3) * v + Math.PI / 2;
          const x = cx + hexSize * Math.cos(angle);
          const y = cy + hexSize * Math.sin(angle);
          vertices.push({ x, y });
        }
        
        hexList.push({
          cx,
          cy,
          vertices,
          key: `hex-${rowIdx}-${i}`
        });
      }
    });

    // Find the CENTER of the effect area (both horizontal and vertical)
    const effectCenterX = (Math.min(...hexList.map(h => h.cx)) + Math.max(...hexList.map(h => h.cx))) / 2;
    const effectCenterY = (Math.min(...hexList.map(h => h.cy)) + Math.max(...hexList.map(h => h.cy))) / 2;
    
    // Bender position logic:
    // For CONE: bender is AT the origin (first hex of the pattern, row 0)
    // For other effects: bender is to the LEFT with range-based spacing
    let benderX, benderY;
    
    if (patternType === 'cone') {
      // For cones, bender is at the first hex (row 0, which should be centered in hexList)
      // Find the hex at row 0 (cy = 0)
      const originHex = hexList.find(h => h.cy === 0);
      if (originHex) {
        benderX = originHex.cx;
        benderY = originHex.cy;
      } else {
        // Fallback to first hex if row 0 not found
        benderX = hexList[0].cx;
        benderY = hexList[0].cy;
      }
    } else {
      // For non-cone effects: to the LEFT of the effect CENTER with range hex-lengths in between
      // range * horizSpacing gives us the distance in terms of hex widths
      benderX = effectCenterX - (range * horizSpacing);
      benderY = effectCenterY; // Same vertical center as effect
    }
    
    // Create bender hexagon
    const benderVertices = [];
    for (let v = 0; v < 6; v++) {
      const angle = (Math.PI / 3) * v + Math.PI / 2;
      const x = benderX + hexSize * Math.cos(angle);
      const y = benderY + hexSize * Math.sin(angle);
      benderVertices.push({ x, y });
    }
    
    const benderHex = {
      cx: benderX,
      cy: benderY,
      vertices: benderVertices,
      key: 'bender'
    };

    // Create path hexagons from bender to effect (if range > 1)
    // Path hexagons go BETWEEN bender and effect, not including either
    // Skip for cones (cone emanates directly from caster)
    const pathHexes = [];
    if (range > 1 && patternType !== 'cone') {
      for (let i = 1; i < range; i++) {
        const pathX = benderX + (i * horizSpacing);
        const pathVertices = [];
        for (let v = 0; v < 6; v++) {
          const angle = (Math.PI / 3) * v + Math.PI / 2;
          const x = pathX + hexSize * Math.cos(angle);
          const y = benderY + hexSize * Math.sin(angle);
          pathVertices.push({ x, y });
        }
        pathHexes.push({
          cx: pathX,
          cy: benderY,
          vertices: pathVertices,
          key: `path-${i}`
        });
      }
    }

    // Calculate bounds including bender and path
    const allX = [
      ...hexList.flatMap(h => h.vertices.map(v => v.x)),
      ...benderVertices.map(v => v.x),
      ...pathHexes.flatMap(h => h.vertices.map(v => v.x))
    ];
    const allY = [
      ...hexList.flatMap(h => h.vertices.map(v => v.y)),
      ...benderVertices.map(v => v.y),
      ...pathHexes.flatMap(h => h.vertices.map(v => v.y))
    ];
    const minX = Math.min(...allX);
    const maxX = Math.max(...allX);
    const minY = Math.min(...allY);
    const maxY = Math.max(...allY);
    
    const padding = 15;
    const bounds = {
      minX: minX - padding,
      maxX: maxX + padding,
      minY: minY - padding,
      maxY: maxY + padding,
      width: maxX - minX + 2 * padding,
      height: maxY - minY + 2 * padding
    };

    return { 
      benderHex, 
      effectHexagons: hexList, 
      pathHexagons: pathHexes,
      bounds 
    };
  }, [pattern, hexSize, range]);

  const fillColor = color;
  const strokeColor = color;
  const fillOpacity = opacity;
  const strokeOpacity = Math.min(opacity + 0.4, 1);

  return (
    <div style={{ 
      width: '100%', 
      display: 'flex', 
      justifyContent: 'center',
      padding: '10px 0',
      position: 'relative'
    }}>
      <svg
        width={bounds.width}
        height={bounds.height}
        viewBox={`${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}`}
        style={{ 
          maxWidth: '100%',
          height: 'auto'
        }}
      >
        {/* Draw path hexagons (range indicators) */}
        {pathHexagons.map((hex) => {
          const pathData = hex.vertices
            .map((v, i) => `${i === 0 ? 'M' : 'L'} ${v.x} ${v.y}`)
            .join(' ') + ' Z';
          
          return (
            <path
              key={hex.key}
              d={pathData}
              fill="none"
              stroke={strokeColor}
              strokeOpacity={strokeOpacity * 0.3}
              strokeWidth="1"
              strokeDasharray="4 2"
            />
          );
        })}
        
        {/* Draw effect hexagons */}
        {effectHexagons.map((hex) => {
          const pathData = hex.vertices
            .map((v, i) => `${i === 0 ? 'M' : 'L'} ${v.x} ${v.y}`)
            .join(' ') + ' Z';
          
          return (
            <path
              key={hex.key}
              d={pathData}
              fill={fillColor}
              fillOpacity={fillOpacity}
              stroke={strokeColor}
              strokeOpacity={strokeOpacity}
              strokeWidth="2"
              style={{
                transition: 'all 0.2s ease',
                filter: lightMode 
                  ? 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))' 
                  : 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))'
              }}
            />
          );
        })}
        
        {/* Draw bender hexagon */}
        <path
          d={benderHex.vertices
            .map((v, i) => `${i === 0 ? 'M' : 'L'} ${v.x} ${v.y}`)
            .join(' ') + ' Z'}
          fill="rgba(100, 200, 255, 0.15)"
          stroke="rgba(100, 200, 255, 0.9)"
          strokeOpacity={1}
          strokeWidth="3"
          style={{
            filter: lightMode 
              ? 'drop-shadow(0 2px 4px rgba(100, 200, 255, 0.3))' 
              : 'drop-shadow(0 2px 6px rgba(100, 200, 255, 0.4))'
          }}
        />
        
        {/* Clipping path for hexagon - create a tight fit */}
        <defs>
          <clipPath id={clipPathId}>
            <path d={benderHex.vertices
              .map((v, i) => `${i === 0 ? 'M' : 'L'} ${v.x} ${v.y}`)
              .join(' ') + ' Z'} />
          </clipPath>
        </defs>
        
        {/* Embed pixel avatar in bender hexagon with clipping */}
        {characterData?.pixels && (
          <g clipPath={`url(#${clipPathId})`}>
            <foreignObject
              x={benderHex.cx - hexSize}
              y={benderHex.cy - hexSize}
              width={hexSize * 2}
              height={hexSize * 2}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%',
                height: '100%',
                overflow: 'hidden'
              }}>
                <PixelAvatar
                  avatarPng={characterData.avatarPng}
                  size={hexSize * 2}
                  borderColor="transparent"
                  background="transparent"
                />
              </div>
            </foreignObject>
          </g>
        )}
      </svg>
    </div>
  );
};

export default HexGridSVG;
