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
 * @param {Function} onLearn - Callback when learn/unlearn button is clicked
 * @param {boolean} isLearned - Whether the move is currently learned
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
  onLearn,
  isLearned = true,
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

  // Check if character meets the requirements to learn this move
  const canLearnMove = () => {
    if (move.level === undefined || move.level === null) return true;
    if (!characterData?.bendingLevels) return true;
    
    // Check if this is a teamup move with multiple elements
    const isTeamup = move.tags && move.tags.some(tag => tag.toLowerCase().includes('teamup'));
    
    if (isTeamup) {
      // Extract all element tags from the move
      const elementTags = ['air', 'water', 'earth', 'fire', 'spirit'];
      const moveElements = elementTags.filter(element => 
        move.tags.some(tag => tag.toLowerCase().includes(element))
      );
      
      // For teamup moves, character needs ANY of the elements at the required level
      if (moveElements.length > 0) {
        return moveElements.some(element => {
          const elementLevel = characterData.bendingLevels[element] || 0;
          return elementLevel >= move.level;
        });
      }
    }
    
    // For non-teamup moves, check the single element
    if (!move.element) return true;
    const elementLevel = characterData.bendingLevels[move.element.toLowerCase()] || 0;
    return elementLevel >= move.level;
  };

  const meetsRequirements = canLearnMove();
  const learnButtonDisabled = !meetsRequirements;

  // Generate display costs based on the move's element with current values
  const displayCosts = [];
  if (move.element) {
    const elementLower = move.element.toLowerCase();
    
    if (elementLower === 'water') {
      // Water moves show both waterbottle and environmental charges
      if (characterData && characterData.consumables) {
        const waterbottleConsumable = characterData.consumables.find(c => 
          c && c.name && c.name.toLowerCase().includes('waterbottle')
        );
        const environmentalConsumable = characterData.consumables.find(c => 
          c && c.name && c.name.toLowerCase().includes('environmental') && c.name.toLowerCase().includes('water')
        );
        if (waterbottleConsumable) {
          displayCosts.push({ 
            name: 'Waterbottle charges', 
            current: waterbottleConsumable.current || 0,
            max: waterbottleConsumable.max || 0
          });
        }
        if (environmentalConsumable) {
          displayCosts.push({ 
            name: 'Environmental water charges', 
            current: environmentalConsumable.current || 0,
            max: environmentalConsumable.max || 0
          });
        }
      }
    } else {
      // Other elements show their bending slots
      const elementName = move.element.charAt(0).toUpperCase() + move.element.slice(1);
      const slotName = `${elementName}bending slot`;
      let currentSlots = 0;
      let maxSlots = 0;
      
      if (characterData && characterData.consumables) {
        const slotConsumable = characterData.consumables.find(c => 
          c && c.name && c.name.toLowerCase().includes(elementLower) && 
          c.name.toLowerCase().includes('slot')
        );
        if (slotConsumable) {
          currentSlots = slotConsumable.current || 0;
          maxSlots = slotConsumable.max || 0;
        }
      }
      
      displayCosts.push({ name: slotName, current: currentSlots, max: maxSlots });
    }
  }

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
    
    // Don't toggle if user is selecting text
    const selection = window.getSelection();
    if (selection && selection.toString().length > 0) return;
    
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
              {displayCosts.length > 0 && (
                <span style={{ fontSize: '11px', opacity: 0.7 }} title={displayCosts.map(c => `${c.name}: ${c.current}/${c.max}`).join(', ')}>
                  💎
                </span>
              )}
            </div>
          </div>

          {/* Right side: Action buttons */}
          <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
            {onLearn && !move.isLevel1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (!learnButtonDisabled) {
                    onLearn(move);
                  }
                }}
                disabled={learnButtonDisabled}
                style={{
                  padding: '4px 6px',
                  fontSize: '12px',
                  backgroundColor: learnButtonDisabled
                    ? (lightMode ? '#e0e0e0' : '#2a2a2a')
                    : isLearned 
                      ? hexToRgba('#2ecc71', 0.3)
                      : 'transparent',
                  border: learnButtonDisabled
                    ? '1px solid #666'
                    : isLearned 
                      ? '1px solid #2ecc71' 
                      : '1px solid #999',
                  borderRadius: '4px',
                  cursor: learnButtonDisabled ? 'not-allowed' : 'pointer',
                  color: learnButtonDisabled
                    ? '#666'
                    : isLearned 
                      ? '#2ecc71' 
                      : (lightMode ? '#666' : '#999'),
                  transition: 'all 0.2s',
                  opacity: learnButtonDisabled ? 0.4 : 1
                }}
                onMouseEnter={(e) => {
                  if (!learnButtonDisabled) {
                    e.target.style.color = isLearned ? '#27ae60' : '#2ecc71';
                    e.target.style.backgroundColor = hexToRgba('#2ecc71', 0.2);
                    e.target.style.borderColor = '#2ecc71';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!learnButtonDisabled) {
                    e.target.style.color = isLearned ? '#2ecc71' : (lightMode ? '#666' : '#999');
                    e.target.style.backgroundColor = isLearned ? hexToRgba('#2ecc71', 0.3) : 'transparent';
                    e.target.style.borderColor = isLearned ? '#2ecc71' : '#999';
                  }
                }}
                title={
                  learnButtonDisabled 
                    ? `Requires ${move.element} level ${move.level}` 
                    : isLearned 
                      ? "Unlearn this move" 
                      : "Learn this move"
                }
              >
                {isLearned ? '✓' : '📖'}
              </button>
            )}
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
              {onLearn && !move.isLevel1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!learnButtonDisabled) {
                      onLearn(move);
                    }
                  }}
                  disabled={learnButtonDisabled}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: learnButtonDisabled
                      ? (lightMode ? '#e0e0e0' : '#2a2a2a')
                      : isLearned 
                        ? hexToRgba('#2ecc71', 0.3)
                        : (lightMode ? '#f0f0f0' : '#3e3e42'),
                    border: learnButtonDisabled
                      ? '1px solid #666'
                      : isLearned 
                        ? '1px solid #2ecc71' 
                        : '1px solid #999',
                    borderRadius: '4px',
                    cursor: learnButtonDisabled ? 'not-allowed' : 'pointer',
                    color: learnButtonDisabled
                      ? '#666'
                      : isLearned 
                        ? '#2ecc71' 
                        : (lightMode ? '#333' : '#e0e0e0'),
                    transition: 'all 0.2s',
                    opacity: learnButtonDisabled ? 0.4 : 1
                  }}
                  onMouseEnter={(e) => {
                    if (!learnButtonDisabled) {
                      e.target.style.backgroundColor = hexToRgba('#2ecc71', 0.2);
                      e.target.style.color = isLearned ? '#27ae60' : '#2ecc71';
                      e.target.style.borderColor = '#2ecc71';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!learnButtonDisabled) {
                      e.target.style.backgroundColor = isLearned 
                        ? hexToRgba('#2ecc71', 0.3)
                        : (lightMode ? '#f0f0f0' : '#3e3e42');
                      e.target.style.color = isLearned 
                        ? '#2ecc71' 
                        : (lightMode ? '#333' : '#e0e0e0');
                      e.target.style.borderColor = isLearned ? '#2ecc71' : '#999';
                    }
                  }}
                  title={
                    learnButtonDisabled 
                      ? `Requires ${move.element} level ${move.level}` 
                      : isLearned 
                        ? "Unlearn this move" 
                        : "Learn this move"
                  }
                >
                  {isLearned ? '✓ Learned' : '📖 Learn'}
                </button>
              )}
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
          {displayCosts.length > 0 && (
            <div style={{
              fontSize: '11px',
              opacity: 0.7,
              marginBottom: '8px',
              color: lightMode ? '#666' : '#999'
            }}>
              {displayCosts.map(c => `${c.name}: ${c.current}/${c.max}`).join('; ')}
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
