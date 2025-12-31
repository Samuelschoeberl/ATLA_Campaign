import React, { useState } from 'react';
import BendingMove from './BendingMove';
import ShapeshiftingForm from './ShapeshiftingForm';
import { hexToRgba } from '../utils/colorUtils';

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

const ACTION_COLORS = {
  'Action': '#3498db',
  'Bonus Action': '#9b59b6',
  'Reaction': '#e67e22',
  'Danger Sense Reaction': '#e74c3c'
};

/**
 * BendingMoveWrapper - A wrapper component for displaying bending moves
 * Shows a collapsed card with core traits and can expand to show full details
 * 
 * @param {Object} move - The move data object
 * @param {boolean} isExpanded - Whether the move is currently expanded
 * @param {Function} onToggleExpand - Callback when expand/collapse is clicked
 * @param {Function} onPin - Callback when pin button is clicked
 * @param {boolean} isPinned - Whether the move is currently pinned
 * @param {Function} onUse - Optional callback when use button is clicked
 * @param {boolean} showUseButton - Whether to show the "Use" button
 * @param {boolean} lightMode - Whether light mode is active
 */
const BendingMoveWrapper = ({ 
  move, 
  isExpanded, 
  onToggleExpand, 
  onPin,
  isPinned = false,
  onUse,
  showUseButton = false,
  lightMode = false,
  characterData = null
}) => {
  if (!move) {
    return null;
  }

  const isShapeshifting = move.tags && move.tags.some(tag => 
    tag.toLowerCase().startsWith('shapeshifting')
  );

  const elementColor = move.element ? ELEMENT_COLORS[move.element.toLowerCase()] || '#3498db' : '#3498db';
  const actionColor = move.actionType ? ACTION_COLORS[move.actionType] || '#3498db' : '#3498db';

  // Extract cost information from move slots
  const costs = move.slots && move.slots.length > 0 
    ? move.slots.map(slotStr => {
        const match = slotStr.match(/(.+?)\s*(?:\((\d+)\))?$/);
        if (match) {
          const slotName = match[1].trim();
          const amount = match[2] ? parseInt(match[2]) : 1;
          return { name: slotName, amount };
        }
        return null;
      }).filter(Boolean)
    : [];

  // Extract teamup info
  const teamupInfo = move.tags && move.tags.some(tag => tag.toLowerCase().startsWith('teamup'))
    ? move.tags
        .map(tag => {
          const match = tag.match(/^(action|bonus_action|reaction|danger_sense_reaction)\s*\((\w+)(?:bender)?\)/i);
          if (match) {
            const actionType = match[1].replace(/_/g, ' ');
            const element = match[2];
            return { actionType, element };
          }
          return null;
        })
        .filter(Boolean)
    : null;

  const handleCardClick = (e) => {
    // Don't toggle if clicking on buttons
    if (e.target.closest('button')) return;
    onToggleExpand(move.path);
  };

  return (
    <div 
      style={{ 
        border: `2px solid ${elementColor}`,
        borderRadius: '20px',
        padding: '8px 14px',
        backgroundColor: lightMode ? hexToRgba(elementColor, 0.1) : hexToRgba(elementColor, 0.15),
        transition: 'all 0.2s ease',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        justifyContent: 'space-between',
        minHeight: isExpanded ? 'auto' : '40px',
        flexWrap: 'wrap',
        gridColumn: isExpanded ? '1 / -1' : 'auto'
      }}
      onClick={handleCardClick}
    >
      {/* Collapsed Pill View */}
      {!isExpanded && (
        <>
          {/* Left side: Name and badges */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            flex: 1,
            minWidth: '0'
          }}>
            <span style={{
              fontWeight: '600',
              fontSize: '13px',
              color: lightMode ? '#333' : '#e8e8e8',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {move.name}
            </span>
            
            {/* Compact badges */}
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center', flexShrink: 0 }}>
              {/* Level badge - just the number */}
              {move.level !== undefined && move.level !== null && (
                <span style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  color: elementColor,
                  opacity: 0.8
                }}>
                  L{move.level}
                </span>
              )}
              
              {/* Teamup icon */}
              {teamupInfo && (
                <span style={{ fontSize: '14px' }} title="Teamup move">🤝</span>
              )}
              
              {/* Shapeshifting icon */}
              {isShapeshifting && (
                <span style={{ fontSize: '14px' }} title="Shapeshifting">🦎</span>
              )}
              
              {/* Cost indicator - just show if it has cost */}
              {costs.length > 0 && (
                <span style={{ fontSize: '11px', opacity: 0.7 }} title={costs.map(c => `${c.amount}×${c.name}`).join(', ')}>
                  💎
                </span>
              )}
            </div>
          </div>

          {/* Right side: Action buttons */}
          <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
            {onPin && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onPin(move);
                }}
                style={{
                  padding: '4px 6px',
                  fontSize: '12px',
                  backgroundColor: isPinned 
                    ? hexToRgba(elementColor, 0.3)
                    : 'transparent',
                  border: isPinned 
                    ? `1px solid ${elementColor}` 
                    : 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: isPinned 
                    ? elementColor 
                    : (lightMode ? '#666' : '#999'),
                  transition: 'all 0.2s',
                  transform: isPinned ? 'rotate(45deg)' : 'none'
                }}
                onMouseEnter={(e) => {
                  e.target.style.color = elementColor;
                  e.target.style.backgroundColor = hexToRgba(elementColor, 0.2);
                }}
                onMouseLeave={(e) => {
                  e.target.style.color = isPinned ? elementColor : (lightMode ? '#666' : '#999');
                  e.target.style.backgroundColor = isPinned ? hexToRgba(elementColor, 0.3) : 'transparent';
                }}
                title={isPinned ? "Already pinned" : "Pin this move"}
              >
                📌
              </button>
            )}
            {showUseButton && onUse && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onUse(move);
                }}
                style={{
                  padding: '4px 10px',
                  fontSize: '11px',
                  fontWeight: '600',
                  backgroundColor: '#2ecc71',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#27ae60'}
                onMouseLeave={(e) => e.target.style.backgroundColor = '#2ecc71'}
                title="Use this move"
              >
                Use
              </button>
            )}
          </div>
        </>
      )}

      {/* Expanded View - Full details */}
      {isExpanded && (
        <div style={{ width: '100%' }}>
          {/* Header with close indicator */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '12px',
            paddingBottom: '8px',
            borderBottom: `1px solid ${hexToRgba(elementColor, 0.3)}`
          }}>
            <h4 style={{ 
              margin: 0,
              fontSize: '16px',
              fontWeight: '600',
              color: elementColor
            }}>
              {move.name}
            </h4>
            <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
              {onPin && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onPin(move);
                  }}
                  style={{
                    padding: '4px 6px',
                    fontSize: '12px',
                    backgroundColor: isPinned 
                      ? hexToRgba(elementColor, 0.3)
                      : (lightMode ? '#f0f0f0' : '#3e3e42'),
                    border: isPinned 
                      ? `1px solid ${elementColor}` 
                      : 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    color: isPinned 
                      ? elementColor 
                      : (lightMode ? '#333' : '#e0e0e0'),
                    transition: 'all 0.2s',
                    transform: isPinned ? 'rotate(45deg)' : 'none'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = hexToRgba(elementColor, 0.2);
                    e.target.style.color = elementColor;
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = isPinned 
                      ? hexToRgba(elementColor, 0.3)
                      : (lightMode ? '#f0f0f0' : '#3e3e42');
                    e.target.style.color = isPinned 
                      ? elementColor 
                      : (lightMode ? '#333' : '#e0e0e0');
                  }}
                  title={isPinned ? "Already pinned" : "Pin this move"}
                >
                  📌
                </button>
              )}
              {showUseButton && onUse && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onUse(move);
                  }}
                  style={{
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: '600',
                    backgroundColor: '#2ecc71',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '12px',
                    cursor: 'pointer'
                  }}
                  title="Use this move"
                >
                  Use
                </button>
              )}
              <span style={{ 
                fontSize: '12px', 
                opacity: 0.6,
                marginLeft: '8px',
                cursor: 'pointer'
              }}>
                ▲ Click to collapse
              </span>
            </div>
          </div>

          {/* Badges row */}
          <div style={{
            display: 'flex',
            gap: '8px',
            flexWrap: 'wrap',
            fontSize: '11px',
            marginBottom: '12px'
          }}>
            {/* Element Badge */}
            {move.element && (
              <span style={{
                padding: '3px 8px',
                borderRadius: '12px',
                backgroundColor: hexToRgba(elementColor, 0.2),
                color: elementColor,
                fontWeight: '600',
                textTransform: 'capitalize'
              }}>
                {move.element}
              </span>
            )}

            {/* Level Badge */}
            {move.level !== undefined && move.level !== null && (
              <span style={{
                padding: '3px 8px',
                borderRadius: '12px',
                backgroundColor: lightMode ? '#f0f0f0' : '#3e3e42',
                color: lightMode ? '#333' : '#e0e0e0',
                fontWeight: '600'
              }}>
                Level {move.level}
              </span>
            )}

            {/* Action Type Badge */}
            {move.actionType && (
              <span style={{
                padding: '3px 8px',
                borderRadius: '12px',
                backgroundColor: hexToRgba(actionColor, 0.2),
                color: actionColor,
                fontWeight: '600'
              }}>
                {move.actionType}
              </span>
            )}

            {/* Teamup Badge */}
            {teamupInfo && (
              <span style={{
                padding: '3px 8px',
                borderRadius: '12px',
                backgroundColor: 'rgba(155, 89, 182, 0.2)',
                color: '#9b59b6',
                fontWeight: '600'
              }}>
                🤝 Teamup
              </span>
            )}
          </div>

          {/* Cost Info */}
          {costs.length > 0 && (
            <div style={{
              fontSize: '12px',
              opacity: 0.8,
              fontStyle: 'italic',
              marginBottom: '12px',
              color: lightMode ? '#666' : '#aaa'
            }}>
              💎 Cost: {costs.map(c => `${c.amount} × ${c.name}`).join(', ')}
            </div>
          )}

          {/* Full move details */}
          <div style={{
            marginTop: '12px',
            paddingTop: '12px',
            borderTop: `1px solid ${lightMode ? '#e0e0e0' : '#3e3e42'}`
          }}>
            {isShapeshifting ? (
              <ShapeshiftingForm 
                file={{ path: move.path, name: move.name }}
                lightMode={lightMode}
              />
            ) : (
              <BendingMove 
                file={{ path: move.path, name: move.name }}
                lightMode={lightMode}
                characterData={characterData}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default BendingMoveWrapper;
