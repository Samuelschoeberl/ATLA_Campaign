import React, { useState } from 'react';
import ActionPanel from './ActionPanel';

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
 * MyMovesModal - Combined modal displaying all move types with toggles
 */
const MyMovesModal = ({
  isOpen,
  onClose,
  movesByType,
  bendingSlotConsumables,
  waterChargeConsumables,
  usedMoves,
  onClearUsedMoves,
  expandedMoves,
  onToggleExpand,
  onPinMove,
  pinnedMoves = [],
  onLearnMove,
  onUseMove,
  movesLoading,
  movesError,
  lightMode = false,
  characterData = null,
  isBleedingOut = false,
  showLearnableMoves = false,
  onToggleShowLearnable,
  showAllMoves = false,
  onToggleShowAll,
  totalLearnedMovesCount = 0,
  maxLearnedMoves = null
}) => {
  const [visibleTypes, setVisibleTypes] = useState({
    action: true,
    bonus: true,
    reaction: true,
    danger: true
  });

  if (!isOpen) return null;

  const getElementFromName = (name) => {
    const nameLower = name.toLowerCase();
    if (nameLower.includes('fire')) return 'fire';
    if (nameLower.includes('water')) return 'water';
    if (nameLower.includes('earth')) return 'earth';
    if (nameLower.includes('air')) return 'air';
    if (nameLower.includes('spirit')) return 'spirit';
    return null;
  };

  const getMoveColors = (move) => {
    const elementColor = move.element ? ELEMENT_COLORS[move.element.toLowerCase()] || '#3498db' : '#3498db';
    return { elementColor };
  };

  const toggleType = (type) => {
    setVisibleTypes(prev => ({
      ...prev,
      [type]: !prev[type]
    }));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>My Moves</h3>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '13px', color: '#888', marginRight: '4px' }}>
              Learned: {totalLearnedMovesCount}{maxLearnedMoves !== null ? ` / ${maxLearnedMoves}` : ''}
            </span>
            
            {/* Mode Selector */}
            <div style={{
              display: 'flex',
              backgroundColor: lightMode ? '#e0e0e0' : '#2a2a2a',
              borderRadius: '6px',
              padding: '2px',
              gap: '2px'
            }}>
              <button
                onClick={() => {
                  onToggleShowLearnable && onToggleShowLearnable(false);
                  onToggleShowAll && onToggleShowAll(false);
                }}
                style={{
                  padding: '4px 12px',
                  fontSize: '12px',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: !showLearnableMoves && !showAllMoves ? (lightMode ? '#fff' : '#3e3e42') : 'transparent',
                  color: !showLearnableMoves && !showAllMoves ? (lightMode ? '#000' : '#fff') : (lightMode ? '#666' : '#888'),
                  fontWeight: !showLearnableMoves && !showAllMoves ? '600' : '400'
                }}
              >
                My Moves
              </button>
              <button
                onClick={() => {
                  onToggleShowLearnable && onToggleShowLearnable(true);
                  onToggleShowAll && onToggleShowAll(false);
                }}
                style={{
                  padding: '4px 12px',
                  fontSize: '12px',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: showLearnableMoves ? (lightMode ? '#fff' : '#3e3e42') : 'transparent',
                  color: showLearnableMoves ? (lightMode ? '#000' : '#fff') : (lightMode ? '#666' : '#888'),
                  fontWeight: showLearnableMoves ? '600' : '400'
                }}
              >
                Learnable
              </button>
              <button
                onClick={() => {
                  onToggleShowLearnable && onToggleShowLearnable(false);
                  onToggleShowAll && onToggleShowAll(true);
                }}
                style={{
                  padding: '4px 12px',
                  fontSize: '12px',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: showAllMoves ? (lightMode ? '#fff' : '#3e3e42') : 'transparent',
                  color: showAllMoves ? (lightMode ? '#000' : '#fff') : (lightMode ? '#666' : '#888'),
                  fontWeight: showAllMoves ? '600' : '400'
                }}
              >
                All Moves
              </button>
            </div>

            {/* Move Type Toggles */}
            <div style={{
              display: 'flex',
              gap: '8px',
              padding: '4px 8px',
              backgroundColor: lightMode ? '#f5f5f5' : '#1e1e1e',
              borderRadius: '6px'
            }}>
              {[
                { key: 'action', label: 'Actions', color: ACTION_COLORS['Action'] },
                { key: 'bonus', label: 'Bonus', color: ACTION_COLORS['Bonus Action'] },
                { key: 'reaction', label: 'Reactions', color: ACTION_COLORS['Reaction'] },
                { key: 'danger', label: 'Danger Sense', color: ACTION_COLORS['Danger Sense Reaction'] }
              ].map(({ key, label, color }) => (
                <label
                  key={key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: visibleTypes[key] ? '600' : '400',
                    color: visibleTypes[key] ? color : (lightMode ? '#999' : '#666'),
                    transition: 'all 0.2s',
                    userSelect: 'none'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={visibleTypes[key]}
                    onChange={() => toggleType(key)}
                    style={{
                      width: '16px',
                      height: '16px',
                      cursor: 'pointer',
                      accentColor: color
                    }}
                  />
                  {label}
                </label>
              ))}
            </div>

            {usedMoves.length > 0 && (
              <button 
                className="ghost-button" 
                onClick={onClearUsedMoves}
                style={{
                  backgroundColor: '#e74c3c',
                  color: '#fff',
                  border: 'none'
                }}
              >
                Clear Log
              </button>
            )}
            <button className="ghost-button" onClick={onClose}>Close</button>
          </div>
        </div>
        
        {/* Used Moves Log */}
        {usedMoves.length > 0 && (
          <div style={{
            marginBottom: '16px',
            padding: '12px',
            backgroundColor: lightMode ? '#e8f5e9' : 'rgba(46, 204, 113, 0.1)',
            borderRadius: '8px',
            border: `2px solid ${lightMode ? '#4caf50' : '#2ecc71'}`
          }}>
            <h4 style={{ 
              margin: '0 0 10px 0', 
              color: lightMode ? '#2e7d32' : '#2ecc71',
              fontSize: '14px',
              fontWeight: '600'
            }}>
              📋 Used This Turn
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {usedMoves.map((used, idx) => (
                <div 
                  key={idx}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: lightMode ? '#fff' : 'rgba(0, 0, 0, 0.2)',
                    borderRadius: '6px',
                    fontSize: '13px',
                    borderLeft: `3px solid ${getMoveColors(used.move).elementColor}`
                  }}
                >
                  <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                    {used.move.name}
                  </div>
                  {used.costs.length > 0 && (
                    <div style={{ 
                      fontSize: '12px', 
                      opacity: 0.8,
                      fontStyle: 'italic'
                    }}>
                      Consumed: {used.costs.map(c => `${c.consumed || c.amount} × ${c.name}`).join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Bending Slots Summary */}
        <div className="slot-summary-row">
          {bendingSlotConsumables.length === 0 ? (
            <span className="muted-text">No bending slot counters found.</span>
          ) : (
            bendingSlotConsumables.map(slot => {
              const slotElement = getElementFromName(slot.name);
              const color = slotElement ? ELEMENT_COLORS[slotElement] : '#3498db';
              return (
                <div key={slot.name} className="slot-summary-card" style={{ borderColor: color }}>
                  <span className="meta-label">{slot.name}</span>
                  <span className="meta-value">{slot.current} / {slot.max}</span>
                </div>
              );
            })
          )}
        </div>

        {/* Water Charges Summary */}
        {waterChargeConsumables.length > 0 && (
          <div className="slot-summary-row" style={{ marginTop: '12px' }}>
            {waterChargeConsumables.map(charge => {
              return (
                <div key={charge.name} className="slot-summary-card" style={{ borderColor: ELEMENT_COLORS.water }}>
                  <span className="meta-label">{charge.name}</span>
                  <span className="meta-value">{charge.current} / {charge.max}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Loading/Error States */}
        {movesLoading ? (
          <p className="muted-text">Loading moves...</p>
        ) : movesError ? (
          <p className="error-text">{movesError}</p>
        ) : (
          <>
            {isBleedingOut && (
              <div
                style={{
                  marginBottom: '16px',
                  padding: '12px',
                  borderRadius: '8px',
                  background: lightMode ? '#ffe1e1' : 'rgba(122, 11, 11, 0.6)',
                  border: lightMode ? '2px solid #d7263d' : '2px solid #f25f5c',
                  color: lightMode ? '#7a0b0b' : '#ffdede',
                  fontWeight: 600,
                  fontSize: '14px',
                  textAlign: 'center'
                }}
              >
                ⚠️ Bleeding out: No bonus actions available
              </div>
            )}
            
            {/* Actions */}
            {visibleTypes.action && (
              <ActionPanel
                title="Actions"
                moves={movesByType.action || []}
                expandedMoves={expandedMoves}
                onToggleExpand={onToggleExpand}
                onPinMove={onPinMove}
                pinnedMoves={pinnedMoves}
                onLearnMove={onLearnMove}
                onUseMove={onUseMove}
                showUseButton={true}
                lightMode={lightMode}
                characterData={characterData}
              />
            )}
            
            {/* Bonus Actions */}
            {visibleTypes.bonus && !isBleedingOut && (
              <ActionPanel
                title="Bonus Actions"
                moves={movesByType.bonus || []}
                expandedMoves={expandedMoves}
                onToggleExpand={onToggleExpand}
                onPinMove={onPinMove}
                pinnedMoves={pinnedMoves}
                onLearnMove={onLearnMove}
                onUseMove={onUseMove}
                showUseButton={true}
                lightMode={lightMode}
                characterData={characterData}
              />
            )}
            
            {/* Reactions */}
            {visibleTypes.reaction && (
              <ActionPanel
                title="Reactions"
                moves={movesByType.reaction || []}
                expandedMoves={expandedMoves}
                onToggleExpand={onToggleExpand}
                onPinMove={onPinMove}
                pinnedMoves={pinnedMoves}
                onLearnMove={onLearnMove}
                lightMode={lightMode}
                characterData={characterData}
              />
            )}
            
            {/* Danger Sense Reactions */}
            {visibleTypes.danger && (
              <ActionPanel
                title="Danger Sense Reactions"
                moves={movesByType.danger || []}
                expandedMoves={expandedMoves}
                onToggleExpand={onToggleExpand}
                onPinMove={onPinMove}
                pinnedMoves={pinnedMoves}
                onLearnMove={onLearnMove}
                lightMode={lightMode}
                characterData={characterData}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default MyMovesModal;
