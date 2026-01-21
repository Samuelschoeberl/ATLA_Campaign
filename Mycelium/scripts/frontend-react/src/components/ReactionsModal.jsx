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
 * ReactionsModal - Modal displaying Reactions and Danger Sense Reactions
 * 
 * @param {boolean} isOpen - Whether the modal is open
 * @param {Function} onClose - Callback to close the modal
 * @param {Object} movesByType - Object containing categorized moves
 * @param {Array} bendingSlotConsumables - Array of bending slot consumables
 * @param {Array} waterChargeConsumables - Array of water charge consumables
 * @param {Set} expandedMoves - Set of expanded move paths
 * @param {Function} onToggleExpand - Callback to toggle move expansion
 * @param {Function} onPinMove - Callback to pin a move
 * @param {Array} pinnedMoves - Array of currently pinned moves
 * @param {boolean} movesLoading - Whether moves are loading
 * @param {string} movesError - Error message if moves failed to load
 * @param {boolean} lightMode - Whether light mode is active
 * @param {boolean} showAllMoves - Whether to show all moves or only learned ones
 * @param {Function} onToggleShowAll - Callback to toggle show all moves
 */
const ReactionsModal = ({
  isOpen,
  onClose,
  movesByType,
  bendingSlotConsumables,
  waterChargeConsumables,
  expandedMoves,
  onToggleExpand,
  onPinMove,
  pinnedMoves = [],
  onLearnMove,
  movesLoading,
  movesError,
  lightMode = false,
  characterData = null,
  showLearnableMoves = false,
  onToggleShowLearnable,
  showAllMoves = false,
  onToggleShowAll,
  totalLearnedMovesCount = 0,
  maxLearnedMoves = null
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Reactions & Danger Sense</h3>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: '#888', marginRight: '4px' }}>
              Learned: {totalLearnedMovesCount}{maxLearnedMoves !== null ? ` / ${maxLearnedMoves}` : ''}
            </span>
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
            <button className="ghost-button" onClick={onClose}>Close</button>
          </div>
        </div>
        
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
          </>
        )}
      </div>
    </div>
  );
};

export default ReactionsModal;
