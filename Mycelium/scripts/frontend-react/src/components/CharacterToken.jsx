import React, { useState, useMemo, useEffect, useRef } from 'react';
import PixelAvatar from './PixelAvatar';
import { pixelToCssRgba } from '../utils/avatarUtils';
import { animateTokenSelection, animateHPChange, animateTokenSpawn } from '../utils/battlemapAnimations';
import './CharacterToken.css';

/**
 * CharacterToken - Renders a character token with hexagonal health bar and condition rings
 * 
 * @param {Object} token - Token data including position, character info, HP, conditions
 * @param {number} size - Token size in pixels
 * @param {boolean} isSelected - Whether token is currently selected
 * @param {function} onClick - Click handler
 * @param {Object} characterSheet - Parsed character sheet data
 */
const CharacterToken = ({
  token,
  size = 60,
  isSelected = false,
  onClick,
  characterSheet = null
}) => {
  const [hoveredCondition, setHoveredCondition] = useState(null);
  const tokenRef = useRef(null);
  const prevHpRef = useRef(null);
  const hasSpawnedRef = useRef(false);
  
  // Extract HP data from character sheet or token
  const hpData = useMemo(() => {
    if (characterSheet?.vitals) {
      const currentHp = parseFloat(characterSheet.vitals.current_hp) || 0;
      const maxHp = parseFloat(characterSheet.vitals.max_hp) || 100;
      return { current: currentHp, max: maxHp, percentage: (currentHp / maxHp) * 100 };
    }
    // Fallback to token data
    const current = token.currentHp || token.hp || 100;
    const max = token.maxHp || 100;
    return { current, max, percentage: (current / max) * 100 };
  }, [characterSheet, token]);

  // Extract conditions from character sheet or token
  const conditions = useMemo(() => {
    if (characterSheet?.conditions && Array.isArray(characterSheet.conditions)) {
      return characterSheet.conditions.filter(c => c.active);
    }
    return token.conditions || [];
  }, [characterSheet, token]);
  
  // Animate selection changes
  useEffect(() => {
    if (tokenRef.current) {
      animateTokenSelection(tokenRef.current, isSelected);
    }
  }, [isSelected]);

  // Soft spawn when the token first mounts
  useEffect(() => {
    if (!tokenRef.current || hasSpawnedRef.current) return;
    animateTokenSpawn(tokenRef.current, 450);
    hasSpawnedRef.current = true;
  }, []);
  
  // Animate HP changes
  useEffect(() => {
    if (prevHpRef.current !== null && prevHpRef.current !== hpData.percentage) {
      const hpBarPath = tokenRef.current?.querySelector('.hp-bar-path');
      if (hpBarPath) {
        animateHPChange(hpBarPath, prevHpRef.current, hpData.percentage);
      }
    }
    prevHpRef.current = hpData.percentage;
  }, [hpData.percentage]);

  // Generate hexagon path for health bar
  const generateHexPath = (centerX, centerY, radius) => {
    const points = [];
    const segments = 6;
    
    // Create hexagon vertices (flat-top orientation)
    for (let i = 0; i < segments; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 2; // Start from top
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      points.push({ x, y });
    }
    
    return points;
  };

  // Generate arc path from points for health bar
  const generateArcPath = (centerX, centerY, radius, percentage) => {
    const points = generateHexPath(centerX, centerY, radius);
    
    if (percentage <= 0) return '';
    if (percentage >= 100) {
      // Full hexagon
      return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ') + ' Z';
    }
    
    // Calculate how many segments to fill
    const totalSegments = 6;
    const fillSegments = (percentage / 100) * totalSegments;
    const fullSegments = Math.floor(fillSegments);
    const partialSegment = fillSegments - fullSegments;
    
    let path = `M ${centerX},${centerY}`;
    
    // Add full segments
    for (let i = 0; i <= fullSegments; i++) {
      const point = points[i % totalSegments];
      path += ` L ${point.x},${point.y}`;
    }
    
    // Add partial segment if needed
    if (partialSegment > 0 && fullSegments < totalSegments) {
      const startPoint = points[fullSegments % totalSegments];
      const endPoint = points[(fullSegments + 1) % totalSegments];
      const partialX = startPoint.x + (endPoint.x - startPoint.x) * partialSegment;
      const partialY = startPoint.y + (endPoint.y - startPoint.y) * partialSegment;
      path += ` L ${partialX},${partialY}`;
    }
    
    path += ' Z';
    return path;
  };

  // Generate hexagon outline
  const hexagonOutline = useMemo(() => {
    const centerX = size / 2;
    const centerY = size / 2;
    const radius = (size / 2) * 0.95;
    const points = generateHexPath(centerX, centerY, radius);
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ') + ' Z';
  }, [size]);

  // Generate health bar path
  const healthBarPath = useMemo(() => {
    const centerX = size / 2;
    const centerY = size / 2;
    const radius = (size / 2) * 0.9;
    return generateArcPath(centerX, centerY, radius, hpData.percentage);
  }, [size, hpData.percentage]);

  // Generate health bar ring (hollow hexagon)
  const healthBarRing = useMemo(() => {
    const centerX = size / 2;
    const centerY = size / 2;
    const outerRadius = (size / 2) * 0.95;
    const innerRadius = (size / 2) * 0.85;
    
    const outerPoints = generateHexPath(centerX, centerY, outerRadius);
    const innerPoints = generateHexPath(centerX, centerY, innerRadius).reverse();
    
    const outerPath = outerPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ') + ' Z';
    const innerPath = innerPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ') + ' Z';
    
    return `${outerPath} ${innerPath}`;
  }, [size]);

  // Health bar color based on HP percentage
  const healthBarColor = useMemo(() => {
    const pct = hpData.percentage;
    if (pct > 66) return '#2ecc71'; // Green
    if (pct > 33) return '#f39c12'; // Orange
    if (pct > 0) return '#e74c3c'; // Red
    return '#95a5a6'; // Gray (dead)
  }, [hpData.percentage]);

  // Condition colors mapping
  const CONDITION_COLORS = {
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

  // Generate condition rings
  const conditionRings = useMemo(() => {
    if (conditions.length === 0) return [];
    
    const rings = [];
    const centerX = size / 2;
    const centerY = size / 2;
    const startRadius = (size / 2) * 1.08; // Just outside health bar
    const ringSpacing = 4;
    
    conditions.forEach((condition, index) => {
      const radius = startRadius + (index * ringSpacing);
      const points = generateHexPath(centerX, centerY, radius);
      const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ') + ' Z';
      const color = CONDITION_COLORS[condition.name] || '#e74c3c';
      
      rings.push({
        path,
        color,
        condition,
        index
      });
    });
    
    return rings;
  }, [conditions, size]);

  return (
    <div 
      ref={tokenRef}
      className={`character-token ${isSelected ? 'selected' : ''}`}
      style={{ 
        width: `${size}px`, 
        height: `${size}px`,
        position: 'relative',
        cursor: 'pointer',
        transition: 'transform 0.2s ease-out'
      }}
      onClick={onClick}
    >
      {/* SVG overlay for health bar and condition rings */}
      <svg
        className="token-overlay"
        width={size * 1.5}
        height={size * 1.5}
        viewBox={`0 0 ${size} ${size}`}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          zIndex: 2,
          overflow: 'visible'
        }}
      >
        {/* Health bar ring background (gray hexagon outline) */}
        <path
          d={healthBarRing}
          fill="#2c3e50"
          fillRule="evenodd"
          opacity="0.5"
        />
        
        {/* Health bar fill (colored arc) */}
        <path
          className="hp-bar-path"
          d={healthBarPath}
          fill={healthBarColor}
          opacity="0.9"
          style={{ transition: 'fill 0.3s ease-out' }}
        />
        
        {/* Condition rings */}
        {conditionRings.map((ring, idx) => (
          <g key={`condition-${idx}`}>
            <path
              d={ring.path}
              fill="none"
              stroke={ring.color}
              strokeWidth="3"
              opacity="0.9"
              onMouseEnter={() => setHoveredCondition(ring.condition)}
              onMouseLeave={() => setHoveredCondition(null)}
              style={{ pointerEvents: 'stroke' }}
            />
          </g>
        ))}
        
        {/* Selection indicator */}
        {isSelected && (
          <path
            d={hexagonOutline}
            fill="none"
            stroke="#3498db"
            strokeWidth="4"
            strokeDasharray="8 4"
            opacity="0.9"
          >
            <animate
              attributeName="stroke-dashoffset"
              from="0"
              to="24"
              dur="1s"
              repeatCount="indefinite"
            />
          </path>
        )}
      </svg>
      
      {/* Character avatar in center */}
      <div 
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: `${size * 0.7}px`,
          height: `${size * 0.7}px`,
          zIndex: 1
        }}
      >
        <PixelAvatar
          avatarPng={token.avatarPng}
          size={size * 0.7}
          borderColor={token.color || '#888888'}
          placeholderLabel={token.name?.[0] || 'C'}
          background="rgba(0, 0, 0, 0.15)"
        />
      </div>
      
      {/* HP text overlay */}
      <div 
        className="hp-text"
        style={{
          position: 'absolute',
          bottom: '-20px',
          left: '50%',
          transform: 'translateX(-50%)',
          fontSize: '11px',
          fontWeight: 'bold',
          color: healthBarColor,
          textShadow: '0 0 3px rgba(0,0,0,0.8)',
          whiteSpace: 'nowrap',
          zIndex: 3,
          pointerEvents: 'none'
        }}
      >
        {Math.round(hpData.current)}/{hpData.max}
      </div>
      
      {/* Condition tooltip */}
      {hoveredCondition && (
        <div 
          className="condition-tooltip"
          style={{
            position: 'absolute',
            top: '-60px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(0, 0, 0, 0.95)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#fff',
            whiteSpace: 'normal',
            zIndex: 1000,
            border: `2px solid ${CONDITION_COLORS[hoveredCondition.name] || '#e74c3c'}`,
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            pointerEvents: 'none',
            maxWidth: '250px'
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: '4px', color: CONDITION_COLORS[hoveredCondition.name] }}>
            {hoveredCondition.name}
          </div>
          <div style={{ fontSize: '11px', opacity: 0.9 }}>
            {hoveredCondition.description || 'Condition active'}
          </div>
        </div>
      )}
    </div>
  );
};

export default CharacterToken;
