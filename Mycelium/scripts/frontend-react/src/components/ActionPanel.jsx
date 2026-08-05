import React from 'react';
import BendingMoveWrapper from './BendingMoveWrapper';

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

/**
 * ActionPanel - Displays a group of moves (Actions, Bonus Actions, Reactions, etc.)
 * 
 * @param {string} title - The title of the action group
 * @param {Array} moves - Array of move objects to display
 * @param {Set} expandedMoves - Set of expanded move paths
 * @param {Function} onToggleExpand - Callback to toggle move expansion
 * @param {Function} onPinMove - Callback to pin a move
 * @param {Array} pinnedMoves - Array of currently pinned moves
 * @param {Function} onLearnMove - Callback to learn/unlearn a move
 * @param {Function} onUseMove - Optional callback when a move is used
 * @param {boolean} showUseButton - Whether to show "Use" buttons
 * @param {boolean} lightMode - Whether light mode is active
 */
const ActionPanel = ({
  title,
  moves,
  expandedMoves,
  onToggleExpand,
  onPinMove,
  pinnedMoves = [],
  onLearnMove,
  onUseMove,
  showUseButton = false,
  lightMode = false,
  characterData = null
}) => {
  // Safely handle moves array
  if (!moves || !Array.isArray(moves)) {
    return (
      <div className="move-group">
        <div className="move-group-header">
          <span>{title}</span>
          <span className="move-count">0</span>
        </div>
        <p className="muted-text">No moves found.</p>
      </div>
    );
  }

  // Sort moves by element first, then by level
  const sortedMoves = [...moves].sort((a, b) => {
    // Define element order
    const elementOrder = { fire: 0, water: 1, earth: 2, air: 3, spirit: 4 };
    
    // Get element values, treating null/undefined as coming last
    const elementA = a.element ? elementOrder[a.element.toLowerCase()] : 999;
    const elementB = b.element ? elementOrder[b.element.toLowerCase()] : 999;
    
    // Sort by element first
    if (elementA !== elementB) {
      return elementA - elementB;
    }
    
    // If same element, sort by level
    const levelA = a.level ?? 999;
    const levelB = b.level ?? 999;
    if (levelA !== levelB) {
      return levelA - levelB;
    }
    
    // If same element and level, sort by name
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="move-group">
      <div className="move-group-header">
        <span>{title}</span>
        <span className="move-count">{sortedMoves.length}</span>
      </div>
      
      {sortedMoves.length === 0 ? (
        <p className="muted-text">No moves found.</p>
      ) : (
        <div 
          className="move-card-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '10px'
          }}
        >
          {sortedMoves.map((move, index) => {
            if (!move.path) {
              console.warn(`[ActionPanel] ${title}: Move ${index} without path:`, move);
              return null;
            }

            return (
              <BendingMoveWrapper
                key={move.path}
                move={move}
                isExpanded={expandedMoves.has(move.path)}
                onToggleExpand={onToggleExpand}
                onPin={onPinMove}
                isPinned={pinnedMoves.some(pm => pm.path === move.path)}
                onLearn={onLearnMove}
                isLearned={move.isLearned}
                onUse={showUseButton && onUseMove ? onUseMove : undefined}
                showUseButton={showUseButton}
                lightMode={lightMode}
                characterData={characterData}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ActionPanel;
