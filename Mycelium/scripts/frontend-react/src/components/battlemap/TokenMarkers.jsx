import React from 'react';
import { CONDITION_COLORS } from '../../constants/effectPresets';

/**
 * TokenMarkers - Renders HP, condition, and defensive stat markers for tokens
 */
const TokenMarkers = ({
  token,
  tokenSizeMultiplier,
  hexSize,
  getHexCoordinates,
  conditionDescriptions,
  setMarkerPopup
}) => {
  const { row, col, width: tokenWidth, height: tokenHeight } = token;
  const conditions = token.conditions || [];
  const defensive = token.defensive || {};
  
  // Calculate center hex position for multi-tile tokens
  const centerRow = row + Math.floor(tokenHeight / 2);
  const centerCol = col + Math.floor(tokenWidth / 2);
  const { cx, cy } = getHexCoordinates(centerRow, centerCol);
  
  // Check if features should be shown
  const shouldShowHp = token.showHp !== false && token.currentHp !== undefined && token.maxHp > 0;
  const shouldShowConditions = token.showConditions !== false && conditions.length > 0;
  
  // Defensive stats configuration
  const defensiveStats = [
    { key: 'Evasion', color: '#3498db', label: 'Evasion' },
    { key: 'Barrier', color: '#9b59b6', label: 'Barrier' },
    { key: 'General Armor', color: '#95a5a6', label: 'General Armor' },
    { key: 'Physical Armor', color: '#7f8c8d', label: 'Physical Armor' },
    { key: 'Fire Armor', color: '#e74c3c', label: 'Fire Armor' },
    { key: 'Ice Armor', color: '#5dade2', label: 'Ice Armor' },
    { key: 'Spirit Armor', color: '#af7ac5', label: 'Spirit Armor' }
  ];
  
  const activeDefensiveStats = defensiveStats.filter(stat => {
    const value = defensive[stat.key];
    return value && parseFloat(value) > 0;
  });
  
  const shouldShowDefensiveStats = token.showDefensiveStats !== false && activeDefensiveStats.length > 0;
  
  // Helper to get health bar color
  const getHealthBarColor = (hpPercentage) => {
    if (hpPercentage > 50) return '#27ae60';
    if (hpPercentage > 25) return '#f39c12';
    return '#e74c3c';
  };
  
  const currentHp = token.currentHp || 0;
  const maxHp = token.maxHp || 100;
  const hpPercentage = maxHp > 0 ? (currentHp / maxHp) * 100 : 0;
  const healthBarColor = getHealthBarColor(hpPercentage);
  
  return (
    <>
      {/* HP Marker at top of token */}
      {shouldShowHp && (
        <g key={`hp-marker-${token.id}`}>
          {/* Outer glow circle */}
          <circle
            cx={cx}
            cy={cy - hexSize * tokenSizeMultiplier - 15}
            r={12}
            fill={healthBarColor}
            opacity="0.3"
            style={{ pointerEvents: 'none' }}
          />
          {/* Main HP circle */}
          <circle
            cx={cx}
            cy={cy - hexSize * tokenSizeMultiplier - 15}
            r={10}
            fill={healthBarColor}
            stroke="#1a1a1a"
            strokeWidth="2"
            opacity="0.95"
            style={{ cursor: 'pointer', pointerEvents: 'all' }}
            onClick={(e) => {
              e.stopPropagation();
              const svgRect = e.currentTarget.ownerSVGElement.getBoundingClientRect();
              setMarkerPopup({
                type: 'hp',
                tokenId: token.id,
                data: { currentHp, maxHp },
                x: e.clientX - svgRect.left,
                y: e.clientY - svgRect.top
              });
            }}
          >
            <title>{`HP: ${Math.round(currentHp)}/${maxHp}`}</title>
          </circle>
          {/* HP value text */}
          <text
            x={cx}
            y={cy - hexSize * tokenSizeMultiplier - 15}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize="11"
            fontWeight="bold"
            fill="#fff"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {Math.round(currentHp)}
          </text>
        </g>
      )}
      
      {/* Condition markers - right side of token */}
      {shouldShowConditions && conditions.map((condition, idx) => {
        const conditionName = condition.name || condition;
        const color = CONDITION_COLORS[conditionName] || '#e74c3c';
        const description = conditionDescriptions[conditionName] || '';
        const tooltipText = description ? `${conditionName}\n\n${description}` : conditionName;
        
        const markerStartX = cx + hexSize * tokenSizeMultiplier + 15;
        const markerY = cy - (conditions.length * 10) / 2;
        const markerSize = 16;
        const markerSpacing = 20;
        const markerX = markerStartX;
        const markerYPos = markerY + (idx * markerSpacing);
        
        return (
          <g key={`condition-marker-${token.id}-${idx}`}>
            {/* Outer glow circle */}
            <circle
              cx={markerX}
              cy={markerYPos}
              r={markerSize / 2 + 2}
              fill={color}
              opacity="0.3"
              style={{ pointerEvents: 'none' }}
            />
            {/* Main condition circle */}
            <circle
              cx={markerX}
              cy={markerYPos}
              r={markerSize / 2}
              fill={color}
              stroke="#1a1a1a"
              strokeWidth="2"
              opacity="0.95"
              style={{ cursor: 'pointer', pointerEvents: 'all' }}
              onClick={(e) => {
                e.stopPropagation();
                const svgRect = e.currentTarget.ownerSVGElement.getBoundingClientRect();
                setMarkerPopup({
                  type: 'condition',
                  tokenId: token.id,
                  data: conditionName,
                  x: e.clientX - svgRect.left,
                  y: e.clientY - svgRect.top
                });
              }}
            >
              <title>{tooltipText}</title>
            </circle>
            {/* Condition initial letter */}
            <text
              x={markerX}
              y={markerYPos}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize="11"
              fontWeight="bold"
              fill="#fff"
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >
              {conditionName.charAt(0).toUpperCase()}
            </text>
          </g>
        );
      })}
      
      {/* Defensive stat markers - left side of token */}
      {shouldShowDefensiveStats && activeDefensiveStats.map((stat, idx) => {
        const value = defensive[stat.key];
        const intValue = Math.floor(parseFloat(value));
        const tooltipText = `${stat.label}: ${value}`;
        
        const markerStartX = cx - hexSize * tokenSizeMultiplier - 15;
        const markerY = cy - (activeDefensiveStats.length * 10) / 2;
        const markerSize = 16;
        const markerSpacing = 20;
        const markerX = markerStartX;
        const markerYPos = markerY + (idx * markerSpacing);
        
        return (
          <g key={`defensive-${token.id}-${stat.key}`}>
            {/* Outer glow circle */}
            <circle
              cx={markerX}
              cy={markerYPos}
              r={markerSize / 2 + 2}
              fill={stat.color}
              opacity="0.3"
              style={{ pointerEvents: 'none' }}
            />
            {/* Main defensive stat circle */}
            <circle
              cx={markerX}
              cy={markerYPos}
              r={markerSize / 2}
              fill={stat.color}
              stroke="#1a1a1a"
              strokeWidth="2"
              opacity="0.95"
              style={{ cursor: 'pointer', pointerEvents: 'all' }}
              onClick={(e) => {
                e.stopPropagation();
                const svgRect = e.currentTarget.ownerSVGElement.getBoundingClientRect();
                setMarkerPopup({
                  type: 'defensive',
                  tokenId: token.id,
                  data: { key: stat.key, label: stat.label, value: value },
                  x: e.clientX - svgRect.left,
                  y: e.clientY - svgRect.top
                });
              }}
            >
              <title>{tooltipText}</title>
            </circle>
            {/* Value text */}
            <text
              x={markerX}
              y={markerYPos}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize="10"
              fontWeight="bold"
              fill="#fff"
              style={{ pointerEvents: 'none', userSelect: 'none' }}
            >
              {intValue}
            </text>
          </g>
        );
      })}
    </>
  );
};

export default TokenMarkers;
