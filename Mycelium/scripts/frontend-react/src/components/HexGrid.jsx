import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import * as THREE from 'three';

/**
 * Creates a regular hexagon shape for Three.js
 */
const createHexagonShape = (radius) => {
  const shape = new THREE.Shape();
  
  // Create hexagon with flat top/bottom (pointy sides)
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i + Math.PI / 6; // Rotate 30 degrees for flat top
    const x = radius * Math.cos(angle);
    const y = radius * Math.sin(angle);
    
    if (i === 0) {
      shape.moveTo(x, y);
    } else {
      shape.lineTo(x, y);
    }
  }
  
  shape.closePath();
  return shape;
};

/**
 * Single hexagon tile component
 */
const HexTile = ({ position, color, opacity }) => {
  const hexShape = useMemo(() => createHexagonShape(0.5), []);
  const geometry = useMemo(() => new THREE.ShapeGeometry(hexShape), [hexShape]);
  const edgesGeo = useMemo(() => new THREE.EdgesGeometry(geometry), [geometry]);
  
  return (
    <group position={position}>
      <mesh geometry={geometry}>
        <meshBasicMaterial 
          color={color} 
          transparent 
          opacity={opacity}
          side={THREE.DoubleSide}
        />
      </mesh>
      <lineSegments geometry={edgesGeo}>
        <lineBasicMaterial color={color} opacity={Math.min(opacity + 0.2, 1)} transparent />
      </lineSegments>
    </group>
  );
};

/**
 * HexGrid component - renders a grid of hexagons using Three.js
 * 
 * @param {Array} pattern - Array of {count, offset} objects defining the grid pattern
 * @param {string} color - Hex color code
 * @param {number} opacity - Opacity value (0-1)
 * @param {boolean} lightMode - Whether light mode is active
 */
const HexGrid = ({ pattern, color = '#3498db', opacity = 0.35, lightMode = false }) => {
  const hexPositions = useMemo(() => {
    if (!pattern || pattern.length === 0) return [];
    
    const positions = [];
    const hexWidth = Math.sqrt(3) / 2; // Width of hexagon with radius 0.5
    const hexHeight = 0.75; // Vertical spacing between rows
    
    // Calculate total height to center the grid
    const totalHeight = (pattern.length - 1) * hexHeight;
    
    pattern.forEach((row, rowIdx) => {
      const yPos = totalHeight / 2 - rowIdx * hexHeight;
      const xOffset = row.offset * hexWidth;
      
      for (let i = 0; i < row.count; i++) {
        const xPos = -((row.count - 1) * hexWidth) / 2 + i * hexWidth + xOffset;
        positions.push([xPos, yPos, 0]);
      }
    });
    
    return positions;
  }, [pattern]);

  if (!pattern || pattern.length === 0) return null;

  // Calculate bounds for camera
  const bounds = useMemo(() => {
    if (hexPositions.length === 0) return { width: 2, height: 2 };
    
    const xValues = hexPositions.map(p => p[0]);
    const yValues = hexPositions.map(p => p[1]);
    
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    
    const width = (maxX - minX) + 2;
    const height = (maxY - minY) + 2;
    
    return { width, height };
  }, [hexPositions]);

  const canvasHeight = Math.max(80, bounds.height * 40);

  return (
    <div style={{ 
      width: '100%', 
      height: `${canvasHeight}px`,
      backgroundColor: lightMode ? 'transparent' : 'transparent',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      <Canvas
        orthographic
        camera={{ zoom: 40, position: [0, 0, 10], near: 0.1, far: 1000 }}
      >
        <ambientLight intensity={0.8} />
        {hexPositions.map((pos, idx) => (
          <HexTile
            key={idx}
            position={pos}
            color={color}
            opacity={opacity}
          />
        ))}
      </Canvas>
    </div>
  );
};

export default HexGrid;
