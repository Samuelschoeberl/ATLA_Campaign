import React from 'react';
import { hexToRgba } from '../utils/colorUtils';

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

const ACTION_TYPE_ABBREV = {
  'Action': 'A',
  'Bonus Action': 'BA',
  'Reaction': 'R',
  'Danger Sense Reaction': 'DS'
};

/**
 * PinnedMoveSlimBar - A compact vertical representation of a pinned move
 * Shows a colored circle with action type abbreviation
 * 
 * @param {Object} move - The move data object
 * @param {Function} onClick - Callback when the circle is clicked
 * @param {boolean} lightMode - Whether light mode is active
 */
const PinnedMoveSlimBar = ({ move, onClick, lightMode = false }) => {
  if (!move) {
    return null;
  }

  const elementColor = move.element 
    ? ELEMENT_COLORS[move.element.toLowerCase()] || '#3498db' 
    : '#3498db';
  
  const actionTypeAbbrev = move.actionType 
    ? ACTION_TYPE_ABBREV[move.actionType] || 'A'
    : 'A';

  return (
    <div
      onClick={onClick}
      style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        border: `2px solid ${elementColor}`,
        backgroundColor: lightMode 
          ? hexToRgba(elementColor, 0.15) 
          : hexToRgba(elementColor, 0.2),
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        flexShrink: 0
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = lightMode 
          ? hexToRgba(elementColor, 0.25)
          : hexToRgba(elementColor, 0.35);
        e.currentTarget.style.transform = 'scale(1.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = lightMode 
          ? hexToRgba(elementColor, 0.15)
          : hexToRgba(elementColor, 0.2);
        e.currentTarget.style.transform = 'scale(1)';
      }}
      title={`${move.name} (${move.actionType})`}
    >
      <span
        style={{
          fontSize: actionTypeAbbrev.length > 1 ? '10px' : '14px',
          fontWeight: '700',
          color: elementColor,
          textAlign: 'center',
          lineHeight: 1
        }}
      >
        {actionTypeAbbrev}
      </span>
    </div>
  );
};

export default PinnedMoveSlimBar;
