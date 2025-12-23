import React from 'react';
import { hexToRgba } from '../utils/colorUtils';
import './StressLevel.css';

const StressLevel = ({ currentLevel, maxLevel = 10, fireLevel = 0, lightMode = false, onLevelChange, onMaxLevelChange }) => {
  // Parse current level if it's a string
  const parsedLevel = typeof currentLevel === 'string' 
    ? parseInt(currentLevel) || 0 
    : currentLevel || 0;
  
  const parsedMaxLevel = typeof maxLevel === 'string'
    ? parseInt(maxLevel) || 10
    : maxLevel || 10;
  
  // Calculate effects based on stress level
  const calculateEffects = (level) => {
    return {
      attackPenalty: -level,
      dcPenalty: -level,
      damageBonus: 2 * level,
      iceArmorBonus: level
    };
  };

  const effects = calculateEffects(parsedLevel);
  
  // Fire color for the stress level indicator
  const fireColor = '#ffb3b3';
  const activeColor = '#d7263d'; // Brighter red for active stress
  const inactiveColor = lightMode ? '#f0f0f0' : '#3a3a3a';

  // Handle checkbox change
  const handleCheckboxChange = (index, isChecked) => {
    if (!onLevelChange) return;
    
    // If checking a box, set level to at least index + 1
    // If unchecking, set level to at most index
    const newLevel = isChecked 
      ? Math.max(index + 1, parsedLevel)
      : Math.min(index, parsedLevel);
    
    onLevelChange(newLevel);
  };

  // Handle max level change
  const handleMaxLevelChange = (newMax) => {
    if (!onMaxLevelChange) return;
    const max = Math.max(1, Math.min(20, parseInt(newMax) || 10));
    onMaxLevelChange(max);
    // Adjust current level if it exceeds new max
    if (parsedLevel > max && onLevelChange) {
      onLevelChange(max);
    }
  };

  return (
    <div className="stress-level-container">
      <div className="stress-level-header">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          marginBottom: '12px'
        }}>
          <div className="stress-level-value" style={{
            fontSize: '24px',
            fontWeight: 'bold',
            color: activeColor,
            textAlign: 'center',
            textShadow: parsedLevel > 0 ? '0 0 8px rgba(215, 38, 61, 0.5)' : 'none'
          }}>
            {parsedLevel}
          </div>
          <span style={{ opacity: 0.5, fontSize: '18px' }}>/</span>
          <input
            type="number"
            min="1"
            max="20"
            value={parsedMaxLevel}
            onChange={(e) => handleMaxLevelChange(e.target.value)}
            style={{
              width: '50px',
              padding: '4px 8px',
              fontSize: '18px',
              fontWeight: 'bold',
              border: `1px solid ${hexToRgba(fireColor, 0.5)}`,
              borderRadius: '4px',
              backgroundColor: lightMode ? '#fff' : '#2a2a2a',
              color: lightMode ? '#333' : '#ddd',
              textAlign: 'center',
              cursor: 'pointer'
            }}
            title="Maximum stress level (1-20)"
          />
        </div>
      </div>

      {/* Visual stress meter with checkboxes */}
      <div className="stress-meter" style={{
        marginBottom: '16px',
        padding: '12px',
        backgroundColor: lightMode ? 'rgba(0,0,0,0.03)' : 'rgba(255,255,255,0.03)',
        borderRadius: '8px',
        border: `1px solid ${hexToRgba(fireColor, 0.3)}`
      }}>
        <div className="checkbox-grid" style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(40px, 1fr))',
          gap: '8px',
          maxWidth: '100%'
        }}>
          {Array.from({ length: parsedMaxLevel }, (_, i) => (
            <label key={i} className="checkbox-label" style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
              userSelect: 'none'
            }}>
              <input
                type="checkbox"
                checked={i < parsedLevel}
                onChange={(e) => handleCheckboxChange(i, e.target.checked)}
                className="resource-checkbox"
                style={{ display: 'none' }}
              />
              <span 
                className="checkbox-mark" 
                style={{
                  width: '36px',
                  height: '36px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: '6px',
                  border: `2px solid ${i < parsedLevel ? activeColor : hexToRgba(fireColor, 0.4)}`,
                  backgroundColor: i < parsedLevel ? activeColor : inactiveColor,
                  transition: 'all 0.2s ease',
                  boxShadow: i < parsedLevel ? '0 0 8px rgba(215, 38, 61, 0.4)' : 'none',
                  position: 'relative',
                  overflow: 'hidden',
                  fontSize: '16px'
                }}
              >
                {i < parsedLevel && (
                  <>
                    <span style={{ position: 'relative', zIndex: 1 }}>🔥</span>
                    <div style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: 'linear-gradient(180deg, rgba(255,255,255,0.2) 0%, transparent 100%)',
                      zIndex: 0
                    }} />
                  </>
                )}
              </span>
              <span style={{
                fontSize: '10px',
                fontWeight: '600',
                opacity: 0.6,
                color: i < parsedLevel ? activeColor : 'inherit'
              }}>
                {i + 1}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Effects breakdown */}
      <div className="stress-effects" style={{
        backgroundColor: lightMode ? 'rgba(255, 179, 179, 0.1)' : 'rgba(255, 179, 179, 0.05)',
        borderRadius: '8px',
        padding: '12px',
        border: `1px solid ${hexToRgba(fireColor, 0.3)}`
      }}>
        <h4 style={{ 
          margin: '0 0 8px 0',
          fontSize: '13px',
          fontWeight: '600',
          color: fireColor,
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          Current Effects
        </h4>
        
        <div className="effect-grid" style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
          fontSize: '12px'
        }}>
          <div className="effect-item" style={{
            padding: '6px 8px',
            backgroundColor: lightMode ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)',
            borderRadius: '4px',
            borderLeft: `3px solid ${effects.attackPenalty < 0 ? '#e74c3c' : '#95a5a6'}`
          }}>
            <div style={{ opacity: 0.7, fontSize: '10px', marginBottom: '2px' }}>Fire Attack Roll</div>
            <div style={{ 
              fontWeight: 'bold',
              color: effects.attackPenalty < 0 ? '#e74c3c' : '#95a5a6'
            }}>
              {effects.attackPenalty === 0 ? '±0' : effects.attackPenalty}
            </div>
          </div>

          <div className="effect-item" style={{
            padding: '6px 8px',
            backgroundColor: lightMode ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)',
            borderRadius: '4px',
            borderLeft: `3px solid ${effects.dcPenalty < 0 ? '#e74c3c' : '#95a5a6'}`
          }}>
            <div style={{ opacity: 0.7, fontSize: '10px', marginBottom: '2px' }}>Firebending DC</div>
            <div style={{ 
              fontWeight: 'bold',
              color: effects.dcPenalty < 0 ? '#e74c3c' : '#95a5a6'
            }}>
              {effects.dcPenalty === 0 ? '±0' : effects.dcPenalty}
            </div>
          </div>

          <div className="effect-item" style={{
            padding: '6px 8px',
            backgroundColor: lightMode ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)',
            borderRadius: '4px',
            borderLeft: `3px solid ${effects.damageBonus > 0 ? '#27ae60' : '#95a5a6'}`
          }}>
            <div style={{ opacity: 0.7, fontSize: '10px', marginBottom: '2px' }}>Fire Damage</div>
            <div style={{ 
              fontWeight: 'bold',
              color: effects.damageBonus > 0 ? '#27ae60' : '#95a5a6'
            }}>
              {effects.damageBonus === 0 ? '±0' : `+${effects.damageBonus}`}
            </div>
          </div>

          <div className="effect-item" style={{
            padding: '6px 8px',
            backgroundColor: lightMode ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)',
            borderRadius: '4px',
            borderLeft: `3px solid ${effects.iceArmorBonus > 0 ? '#3498db' : '#95a5a6'}`
          }}>
            <div style={{ opacity: 0.7, fontSize: '10px', marginBottom: '2px' }}>Ice Armor</div>
            <div style={{ 
              fontWeight: 'bold',
              color: effects.iceArmorBonus > 0 ? '#3498db' : '#95a5a6'
            }}>
              {effects.iceArmorBonus === 0 ? '±0' : `+${effects.iceArmorBonus}`}
            </div>
          </div>
        </div>

        {/* Mechanics reminder */}
        <div style={{
          marginTop: '12px',
          padding: '8px',
          backgroundColor: lightMode ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)',
          borderRadius: '4px',
          fontSize: '11px',
          lineHeight: '1.4',
          opacity: 0.8
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '4px', color: fireColor }}>📋 Mechanics</div>
          <div><strong>Gain 1:</strong> Taking damage or using firebending slot on damaging move</div>
          <div><strong>Lose 1:</strong> Each turn end or certain moves</div>
        </div>
      </div>
    </div>
  );
};

export default StressLevel;
