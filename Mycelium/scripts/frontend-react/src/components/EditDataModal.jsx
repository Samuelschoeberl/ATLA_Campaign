import React, { useState, useEffect } from 'react';
import './EditDataModal.css';

/**
 * EditDataModal - Modal for editing token or hex cell data
 * Allows quick editing of HP, conditions, and other parameters
 */
const EditDataModal = ({ 
  isOpen, 
  onClose, 
  target, 
  onSave,
  availableConditions = [],
  onOpenCharacterSheet
}) => {
  const [formData, setFormData] = useState({});
  const [activeConditions, setActiveConditions] = useState([]);
  const [conditionsCollapsed, setConditionsCollapsed] = useState(true);
  
  useEffect(() => {
    if (target) {
      if (target.type === 'token') {
        setFormData({
          name: target.data.name || '',
          currentHp: target.data.currentHp || target.data.hp || 100,
          maxHp: target.data.maxHp || 100,
          color: target.data.color || '#888888',
          type: target.data.type || 'player',
          width: target.data.width || 1,
          height: target.data.height || 1,
          auraDiameter: target.data.aura?.diameter || 0,
          auraColor: target.data.aura?.outlineColor || '#64c8ff',
          auraMoveHexes: target.data.aura?.moveHexes || false,
          evasion: target.data.defensive?.Evasion || 0,
          barrier: target.data.defensive?.Barrier || 0,
          generalArmor: target.data.defensive?.['General Armor'] || 0,
          physicalArmor: target.data.defensive?.['Physical Armor'] || 0,
          fireArmor: target.data.defensive?.['Fire Armor'] || 0,
          iceArmor: target.data.defensive?.['Ice Armor'] || 0,
          spiritArmor: target.data.defensive?.['Spirit Armor'] || 0,
          showHp: target.data.showHp !== false,
          showConditions: target.data.showConditions !== false,
          showDefensiveStats: target.data.showDefensiveStats !== false,
          customBackgroundPng: target.data.customBackgroundPng || null
        });
        setActiveConditions(target.data.conditions || []);
      } else if (target.type === 'hex') {
        setFormData({
          color: target.data.color || [0, 0, 0, 0],
          effect: target.data.effect || null
        });
      }
    }
  }, [target]);
  
  if (!isOpen || !target) return null;
  
  const handleFieldChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // No client normalization - server handles all profile stripping via PIL
  const normalizePngDataUrl = (dataUrl) => {
    return Promise.resolve(dataUrl);
  };
  
  const handleColorChange = (e) => {
    const hex = e.target.value;
    handleFieldChange('color', hex);
  };
  
  const toggleCondition = (conditionName) => {
    setActiveConditions(prev => {
      const exists = prev.find(c => c.name === conditionName);
      if (exists) {
        return prev.filter(c => c.name !== conditionName);
      } else {
        return [...prev, { name: conditionName, active: true, description: '' }];
      }
    });
  };
  
  const handleSave = () => {
    const updatedData = {
      ...target.data,
      ...formData
    };
    
    if (target.type === 'token') {
      updatedData.conditions = activeConditions;
      
      // Remove flat aura properties (they should only be in nested aura object)
      delete updatedData.auraDiameter;
      delete updatedData.auraColor;
      
      // Handle aura data - moveHexes defaults to false (aura shows as outline only)
      if (formData.auraDiameter && formData.auraDiameter > 0) {
        updatedData.aura = {
          diameter: formData.auraDiameter,
          outlineColor: formData.auraColor || '#64c8ff',
          moveHexes: false
        };
      } else {
        updatedData.aura = null;
      }
      
      // Handle defensive stats
      updatedData.defensive = {
        'Evasion': parseFloat(formData.evasion) || 0,
        'Barrier': parseFloat(formData.barrier) || 0,
        'General Armor': parseFloat(formData.generalArmor) || 0,
        'Physical Armor': parseFloat(formData.physicalArmor) || 0,
        'Fire Armor': parseFloat(formData.fireArmor) || 0,
        'Ice Armor': parseFloat(formData.iceArmor) || 0,
        'Spirit Armor': parseFloat(formData.spiritArmor) || 0
      };
      
      // Remove flat defensive properties
      delete updatedData.evasion;
      delete updatedData.barrier;
      delete updatedData.generalArmor;
      delete updatedData.physicalArmor;
      delete updatedData.fireArmor;
      delete updatedData.iceArmor;
      delete updatedData.spiritArmor;
      
      // Save display toggles
      updatedData.showHp = formData.showHp;
      updatedData.showConditions = formData.showConditions;
      updatedData.showDefensiveStats = formData.showDefensiveStats;
    }
    
    onSave({
      type: target.type,
      row: target.row,
      col: target.col,
      data: updatedData,
      tokenId: target.data.id
    });
    
    onClose();
  };

  const handleGoToCharacterSheet = async () => {
    const name = (formData.name || '').trim();
    if (!name || !onOpenCharacterSheet) return;
    await onOpenCharacterSheet(name);
  };
  
  const CONDITION_LIST = [
    'Bleeding out',
    'Blinded',
    'Dazed',
    'Immobilised',
    'Paralysed',
    'Prone',
    'Slowed',
    'Empowered',
    'Armor Surge',
    'Barrier Surge',
    'Harmonic Flow',
    'Exhausted'
  ];
  
  return (
    <div className="edit-data-modal-overlay" onClick={onClose}>
      <div className="edit-data-modal" onClick={e => e.stopPropagation()}>
        <div className="edit-data-header">
          <h2>
            {target.type === 'token' ? '🎭 Edit Token' : '⬢ Edit Hex Cell'}
          </h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="edit-data-content">
          {target.type === 'token' ? (
            <>
              {/* Token Name */}
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={e => handleFieldChange('name', e.target.value)}
                  placeholder="Token name"
                />
              </div>
              
              {/* HP Fields */}
              <div className="form-row">
                <div className="form-group">
                  <label>Current HP</label>
                  <input
                    type="number"
                    className="hex-input"
                    value={formData.currentHp || 0}
                    onChange={e => handleFieldChange('currentHp', parseFloat(e.target.value) || 0)}
                    min="0"
                  />
                </div>
                
                <div className="form-group">
                  <label>Max HP</label>
                  <input
                    type="number"
                    className="hex-input"
                    value={formData.maxHp || 0}
                    onChange={e => handleFieldChange('maxHp', parseFloat(e.target.value) || 0)}
                    min="1"
                  />
                </div>
              </div>
              
              {/* HP Bar */}
              <div className="hp-bar-preview">
                <div className="hp-bar-label">HP: {formData.currentHp}/{formData.maxHp}</div>
                <div className="hp-bar-container">
                  <div 
                    className="hp-bar-fill"
                    style={{ 
                      width: `${Math.min(100, (formData.currentHp / formData.maxHp) * 100)}%`,
                      backgroundColor: getHealthColor((formData.currentHp / formData.maxHp) * 100)
                    }}
                  />
                </div>
              </div>
              
              {/* Color Picker */}
              <div className="form-group">
                <label>Token Color</label>
                <div className="color-input-group">
                  <input
                    type="color"
                    value={formData.color === 'rgba(0,0,0,0)' ? '#888888' : (formData.color || '#888888')}
                    onChange={handleColorChange}
                    disabled={formData.color === 'rgba(0,0,0,0)'}
                  />
                  <input
                    type="text"
                    value={formData.color || '#888888'}
                    onChange={handleColorChange}
                    placeholder="#888888"
                  />
                  <button
                    type="button"
                    onClick={() => handleFieldChange('color', formData.color === 'rgba(0,0,0,0)' ? '#888888' : 'rgba(0,0,0,0)')}
                    style={{
                      padding: '8px 12px',
                      background: formData.color === 'rgba(0,0,0,0)' ? '#2ecc71' : '#34495e',
                      border: '1px solid #555',
                      borderRadius: '4px',
                      color: '#ecf0f1',
                      cursor: 'pointer',
                      fontSize: '12px',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {formData.color === 'rgba(0,0,0,0)' ? '✓ Transparent' : 'Transparent'}
                  </button>
                </div>
              </div>
              
              {/* Type */}
              <div className="form-group">
                <label>Type</label>
                <select
                  value={formData.type || 'player'}
                  onChange={e => handleFieldChange('type', e.target.value)}
                >
                  <option value="player">Player</option>
                  <option value="enemy">Enemy</option>
                  <option value="npc">NPC</option>
                </select>
              </div>
              
              {/* Size */}
              <div className="form-row">
                <div className="form-group">
                  <label>Width (hexes)</label>
                  <input
                    type="number"
                    className="hex-input"
                    value={formData.width || 1}
                    onChange={e => handleFieldChange('width', parseInt(e.target.value) || 1)}
                    min="1"
                    max="10"
                  />
                </div>
                
                <div className="form-group">
                  <label>Height (hexes)</label>
                  <input
                    type="number"
                    className="hex-input"
                    value={formData.height || 1}
                    onChange={e => handleFieldChange('height', parseInt(e.target.value) || 1)}
                    min="1"
                    max="10"
                  />
                </div>
              </div>
              
              {/* Aura Settings */}
              <div className="form-group">
                <label>Aura Settings</label>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label style={{ fontSize: '12px' }}>Diameter (hexes)</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.auraDiameter || 0}
                      onChange={e => handleFieldChange('auraDiameter', parseInt(e.target.value) || 0)}
                      min="0"
                      max="20"
                      placeholder="0 = no aura"
                    />
                  </div>
                  
                  <div className="form-group" style={{ flex: 1 }}>
                    <label style={{ fontSize: '12px' }}>Aura Color</label>
                    <input
                      type="color"
                      value={formData.auraColor || '#64c8ff'}
                      onChange={e => handleFieldChange('auraColor', e.target.value)}
                      disabled={!formData.auraDiameter || formData.auraDiameter === 0}
                    />
                  </div>
                </div>
              </div>
              
              {/* Display Toggles */}
              <div className="form-group">
                <label>Display Options</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.showHp !== false}
                      onChange={e => handleFieldChange('showHp', e.target.checked)}
                      style={{ cursor: 'pointer' }}
                    />
                    Show HP Bar & Marker
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.showConditions !== false}
                      onChange={e => handleFieldChange('showConditions', e.target.checked)}
                      style={{ cursor: 'pointer' }}
                    />
                    Show Condition Markers
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={formData.showDefensiveStats !== false}
                      onChange={e => handleFieldChange('showDefensiveStats', e.target.checked)}
                      style={{ cursor: 'pointer' }}
                    />
                    Show Defensive Stat Markers
                  </label>
                </div>
              </div>
              
              {/* Background PNG Upload */}
              <div className="form-group">
                <label>Custom Background PNG</label>
                <input
                  type="file"
                  accept=".png,image/png"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      const reader = new FileReader();
                      reader.onload = async (event) => {
                        // Upload raw data URL - server will strip profile and save to file
                        // We'll use a temporary marker that server will replace with file path
                        const dataUrl = event.target.result;
                        handleFieldChange('customBackgroundPng', dataUrl);
                        // Mark that this needs to be saved (for UI feedback)
                        console.log('PNG uploaded, ready to save:', file.name);
                      };
                      reader.readAsDataURL(file);
                    }
                  }}
                  style={{
                    width: '100%',
                    padding: '8px',
                    background: '#34495e',
                    border: '1px solid #4a5f7f',
                    borderRadius: '4px',
                    color: '#ecf0f1',
                    cursor: 'pointer'
                  }}
                />
                {formData.customBackgroundPng && (
                  <div style={{ marginTop: '8px' }}>
                    <button
                      onClick={() => handleFieldChange('customBackgroundPng', null)}
                      style={{
                        padding: '6px 12px',
                        background: '#e74c3c',
                        border: 'none',
                        borderRadius: '4px',
                        color: '#fff',
                        cursor: 'pointer',
                        fontSize: '12px'
                      }}
                    >
                      Clear Custom Background
                    </button>
                  </div>
                )}
              </div>
              
              {/* Defensive Stats */}
              <div className="form-group">
                <label>Defensive Stats</label>
                <div className="form-row">
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>Evasion</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.evasion || 0}
                      onChange={e => handleFieldChange('evasion', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>Barrier</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.barrier || 0}
                      onChange={e => handleFieldChange('barrier', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>General Armor</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.generalArmor || 0}
                      onChange={e => handleFieldChange('generalArmor', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>Physical Armor</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.physicalArmor || 0}
                      onChange={e => handleFieldChange('physicalArmor', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>Fire Armor</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.fireArmor || 0}
                      onChange={e => handleFieldChange('fireArmor', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>Ice Armor</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.iceArmor || 0}
                      onChange={e => handleFieldChange('iceArmor', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ fontSize: '12px' }}>Spirit Armor</label>
                    <input
                      type="number"
                      className="hex-input"
                      value={formData.spiritArmor || 0}
                      onChange={e => handleFieldChange('spiritArmor', parseFloat(e.target.value) || 0)}
                      min="0"
                      step="0.5"
                      style={{ width: '80px' }}
                    />
                  </div>
                </div>
              </div>
              
              {/* Conditions */}
              <div className="form-group">
                <label 
                  onClick={() => setConditionsCollapsed(!conditionsCollapsed)}
                  style={{ 
                    cursor: 'pointer', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    userSelect: 'none'
                  }}
                >
                  <span>Conditions</span>
                  <span style={{ fontSize: '14px', opacity: 0.7 }}>
                    {conditionsCollapsed ? '▼' : '▲'}
                  </span>
                </label>
                
                {/* Active conditions badges - always visible */}
                <div style={{ marginBottom: conditionsCollapsed ? '0' : '12px', display: 'flex', gap: '6px', flexWrap: 'wrap', minHeight: '24px' }}>
                  {activeConditions.length === 0 ? (
                    <span style={{ opacity: 0.5, fontSize: '12px' }}>No active conditions</span>
                  ) : (
                    activeConditions.map((cond) => {
                      const condName = cond.name || cond;
                      const bgColor = getConditionColor(condName);
                      
                      return (
                        <span
                          key={`active-${condName}`}
                          style={{
                            padding: '3px 8px',
                            borderRadius: '4px',
                            backgroundColor: bgColor,
                            color: '#fff',
                            fontSize: '11px',
                            fontWeight: 600,
                            boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                          }}
                        >
                          {condName}
                        </span>
                      );
                    })
                  )}
                </div>
                
                {/* Condition cards grid - only show when not collapsed */}
                {!conditionsCollapsed && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                    gap: '8px',
                    marginTop: '12px'
                  }}>
                  {CONDITION_LIST.map(condition => {
                    const isActive = activeConditions.some(c => (c.name || c) === condition);
                    const borderColor = isActive ? getConditionColor(condition) : 'rgba(255, 255, 255, 0.2)';
                    const backgroundColor = isActive ? `${getConditionColor(condition)}14` : 'rgba(255, 255, 255, 0.05)';
                    
                    return (
                      <div
                        key={`cond-${condition}`}
                        style={{
                          borderColor: borderColor,
                          backgroundColor: backgroundColor,
                          border: `1px solid ${borderColor}`,
                          borderRadius: '6px',
                          padding: '8px',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease'
                        }}
                        onClick={() => toggleCondition(condition)}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: '13px',
                            marginBottom: '4px',
                            fontWeight: 600
                          }}
                        >
                          <span>{condition}</span>
                          <input
                            type="checkbox"
                            checked={isActive}
                            onChange={() => {}}
                            style={{ width: '14px', height: '14px', cursor: 'pointer' }}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </div>
                        <p
                          style={{
                            marginTop: '2px',
                            fontSize: '11px',
                            opacity: 0.7,
                            whiteSpace: 'pre-line',
                            lineHeight: '1.3'
                          }}
                        >
                          {getConditionDescription(condition)}
                        </p>
                      </div>
                    );
                  })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              {/* Hex Cell Data */}
              <div className="form-group">
                <label>Hex Position</label>
                <div className="hex-position">
                  Row: {target.row + 1}, Col: {target.col + 1}
                </div>
              </div>
              
              <div className="form-group">
                <label>Cell Color</label>
                <div className="color-preview" style={{
                  backgroundColor: Array.isArray(formData.color) 
                    ? `rgba(${formData.color[0]}, ${formData.color[1]}, ${formData.color[2]}, ${formData.color[3] / 255})`
                    : formData.color
                }}>
                  {Array.isArray(formData.color) && formData.color[3] === 0 ? 'Transparent' : 'Painted'}
                </div>
              </div>
              
              {formData.effect && (
                <div className="form-group">
                  <label>Effect</label>
                  <div className="effect-info">
                    {formData.effect.type || 'Custom Effect'}
                  </div>
                </div>
              )}
              
              <div className="info-box">
                <p>💡 Hex cell editing is limited. Use paint tools to modify cell colors and effects.</p>
              </div>
            </>
          )}
        </div>
        
        <div className="edit-data-footer">
          <button className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
          {target.type === 'token' && (formData.type || target.data.type) === 'player' && (
            <button
              className="btn-secondary"
              onClick={handleGoToCharacterSheet}
              disabled={!(formData.name || '').trim()}
              title="Open character sheet in a new tab"
            >
              📄 Go to Character Sheet
            </button>
          )}
          <button className="btn-save" onClick={handleSave}>
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

// Helper functions
const getHealthColor = (percentage) => {
  if (percentage > 66) return '#2ecc71';
  if (percentage > 33) return '#f39c12';
  if (percentage > 0) return '#e74c3c';
  return '#95a5a6';
};

const getConditionColor = (conditionName) => {
  const colors = {
    'Bleeding out': '#d7263d',
    'Blinded': '#2c3e50',
    'Dazed': '#f39c12',
    'Immobilised': '#7f8c8d',
    'Paralysed': '#9b59b6',
    'Prone': '#95a5a6',
    'Slowed': '#3498db',
    'Empowered': '#4ec9b0',
    'Quickened': '#4ec9b0',
    'Armor Surge': '#4ec9b0',
    'Barrier Surge': '#4ec9b0',
    'Harmonic Flow': '#4ec9b0',
    'Exhausted': '#c9944eff'
  };
  return colors[conditionName] || '#95a5a6';
};

const getConditionDescription = (conditionName) => {
  const descriptions = {
    'Bleeding out': 'Movement capped at 1m.\nMax 1 bending slot per move.\nNo bonus actions.\nDeath saves each turn:\n- 3 success = stable for 3 rounds\n- 3 fails = dead',
    'Blinded': 'Cannot see. Attacks against you have advantage.',
    'Dazed': 'Disadvantage on attack rolls and ability checks.',
    'Immobilised': 'Cannot move from current position.',
    'Paralysed': 'Incapacitated and cannot move or speak.',
    'Prone': 'Disadvantage on attacks. Melee attacks against you have advantage.',
    'Slowed': 'Movement speed reduced by half.',
    'Empowered': 'Enhanced abilities and damage output.',
    'Quickened': 'Increased movement and action economy.',
    'Armor Surge': 'Temporary boost to armor class.',
    'Barrier Surge': 'Protective barrier absorbs damage.',
    'Harmonic Flow': 'Enhanced chi flow for bending.',
    'Exhausted': 'Physical and mental fatigue penalties.'
  };
  return descriptions[conditionName] || 'Toggle to track this condition.';
};

export default EditDataModal;
