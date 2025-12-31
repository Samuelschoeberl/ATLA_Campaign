import React from 'react';
import ActionPanel from './ActionPanel';

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

/**
 * PlanTurnModal - Modal for planning turns with Actions and Bonus Actions
 * Includes resource tracking and used moves log
 * 
 * @param {boolean} isOpen - Whether the modal is open
 * @param {Function} onClose - Callback to close the modal
 * @param {Object} movesByType - Object containing categorized moves
 * @param {Array} bendingSlotConsumables - Array of bending slot consumables
 * @param {Array} waterChargeConsumables - Array of water charge consumables
 * @param {Array} usedMoves - Array of moves used this turn
 * @param {Function} onClearUsedMoves - Callback to clear used moves log
 * @param {Set} expandedMoves - Set of expanded move paths
 * @param {Function} onToggleExpand - Callback to toggle move expansion
 * @param {Function} onPinMove - Callback to pin a move
 * @param {Array} pinnedMoves - Array of currently pinned moves
 * @param {Function} onUseMove - Callback when a move is used
 * @param {boolean} movesLoading - Whether moves are loading
 * @param {string} movesError - Error message if moves failed to load
 * @param {boolean} lightMode - Whether light mode is active
 * @param {boolean} isBleedingOut - Whether character is bleeding out (disables bonus actions)
 */
const PlanTurnModal = ({
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
  onUseMove,
  movesLoading,
  movesError,
  lightMode = false,
  characterData = null,
  isBleedingOut = false
}) => {
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Plan Turn</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
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
            <ActionPanel
              title="Actions"
              moves={movesByType.action || []}
              expandedMoves={expandedMoves}
              onToggleExpand={onToggleExpand}
              onPinMove={onPinMove}
              pinnedMoves={pinnedMoves}
              onUseMove={onUseMove}
              showUseButton={true}
              lightMode={lightMode}
              characterData={characterData}
            />
            {!isBleedingOut && (
              <ActionPanel
                title="Bonus Actions"
                moves={movesByType.bonus || []}
                expandedMoves={expandedMoves}
                onToggleExpand={onToggleExpand}
                onPinMove={onPinMove}
                pinnedMoves={pinnedMoves}
                onUseMove={onUseMove}
                showUseButton={true}
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

export default PlanTurnModal;
