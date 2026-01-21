import React, { useState } from 'react';

/**
 * MarkerPopup - Popup for editing conditions and defensive stats
 */
const MarkerPopup = ({ markerPopup, setMarkerPopup, setTokens, onSyncTokenSheet }) => {
  if (!markerPopup) return null;
  
  const [editValue, setEditValue] = useState(
    markerPopup.type === 'defensive' ? markerPopup.data.value : 0
  );
  const [currentHp, setCurrentHp] = useState(
    markerPopup.type === 'hp' ? markerPopup.data.currentHp : 0
  );
  const [maxHp, setMaxHp] = useState(
    markerPopup.type === 'hp' ? markerPopup.data.maxHp : 0
  );
  
  const handleRemoveCondition = () => {
    let nextConditions = [];
    setTokens(prev => prev.map(t => {
      if (t.id === markerPopup.tokenId) {
        nextConditions = (t.conditions || []).filter(c => (c.name || c) !== markerPopup.data);
        return { ...t, conditions: nextConditions };
      }
      return t;
    }));
    if (onSyncTokenSheet) {
      onSyncTokenSheet(markerPopup.tokenId, { conditions: nextConditions });
    }
    setMarkerPopup(null);
  };
  
  const handleSaveDefensiveStat = () => {
    let nextDefensive = null;
    setTokens(prev => prev.map(t => {
      if (t.id === markerPopup.tokenId) {
        nextDefensive = { ...(t.defensive || {}) };
        nextDefensive[markerPopup.data.key] = editValue;
        return { ...t, defensive: nextDefensive };
      }
      return t;
    }));
    if (onSyncTokenSheet && nextDefensive) {
      onSyncTokenSheet(markerPopup.tokenId, { defensive: nextDefensive });
    }
    setMarkerPopup(null);
  };
  
  const handleSaveHp = () => {
    setTokens(prev => prev.map(t => 
      t.id === markerPopup.tokenId
        ? { ...t, currentHp, maxHp }
        : t
    ));
    if (onSyncTokenSheet) {
      onSyncTokenSheet(markerPopup.tokenId, { currentHp, maxHp });
    }
    setMarkerPopup(null);
  };
  
  return (
    <div
      style={{
        position: 'fixed',
        left: `${markerPopup.x}px`,
        top: `${markerPopup.y}px`,
        background: '#2c3e50',
        border: '1px solid #34495e',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        padding: '12px',
        zIndex: 15000,
        minWidth: '200px'
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {markerPopup.type === 'condition' ? (
        <>
          <div style={{ color: '#ecf0f1', fontWeight: 'bold', marginBottom: '12px', fontSize: '14px' }}>
            {markerPopup.data}
          </div>
          <button
            onClick={handleRemoveCondition}
            style={{
              width: '100%',
              padding: '8px 12px',
              background: '#e74c3c',
              border: 'none',
              borderRadius: '4px',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 'bold'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#c0392b'}
            onMouseLeave={(e) => e.currentTarget.style.background = '#e74c3c'}
          >
            Remove Condition
          </button>
        </>
      ) : markerPopup.type === 'hp' ? (
        <>
          <div style={{ color: '#ecf0f1', fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>
            HP
          </div>
          <div style={{ marginBottom: '8px' }}>
            <label style={{ color: '#ecf0f1', fontSize: '12px', display: 'block', marginBottom: '4px' }}>Current HP</label>
            <input
              type="number"
              value={currentHp}
              onChange={(e) => setCurrentHp(parseFloat(e.target.value) || 0)}
              min="0"
              style={{
                width: '100%',
                padding: '8px',
                background: '#34495e',
                border: '1px solid #4a5f7f',
                borderRadius: '4px',
                color: '#ecf0f1',
                fontSize: '14px'
              }}
            />
          </div>
          <div style={{ marginBottom: '8px' }}>
            <label style={{ color: '#ecf0f1', fontSize: '12px', display: 'block', marginBottom: '4px' }}>Max HP</label>
            <input
              type="number"
              value={maxHp}
              onChange={(e) => setMaxHp(parseFloat(e.target.value) || 0)}
              min="1"
              style={{
                width: '100%',
                padding: '8px',
                background: '#34495e',
                border: '1px solid #4a5f7f',
                borderRadius: '4px',
                color: '#ecf0f1',
                fontSize: '14px'
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleSaveHp}
              style={{
                flex: 1,
                padding: '8px 12px',
                background: '#27ae60',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 'bold'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#229954'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#27ae60'}
            >
              Save
            </button>
            <button
              onClick={() => setMarkerPopup(null)}
              style={{
                flex: 1,
                padding: '8px 12px',
                background: '#95a5a6',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 'bold'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#7f8c8d'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#95a5a6'}
            >
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <div style={{ color: '#ecf0f1', fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>
            {markerPopup.data.label}
          </div>
          <input
            type="number"
            value={editValue}
            onChange={(e) => setEditValue(parseFloat(e.target.value) || 0)}
            step="0.5"
            min="0"
            style={{
              width: '100%',
              padding: '8px',
              background: '#34495e',
              border: '1px solid #4a5f7f',
              borderRadius: '4px',
              color: '#ecf0f1',
              fontSize: '14px',
              marginBottom: '8px'
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleSaveDefensiveStat}
              style={{
                flex: 1,
                padding: '8px 12px',
                background: '#27ae60',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 'bold'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#229954'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#27ae60'}
            >
              Save
            </button>
            <button
              onClick={() => setMarkerPopup(null)}
              style={{
                flex: 1,
                padding: '8px 12px',
                background: '#95a5a6',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 'bold'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#7f8c8d'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#95a5a6'}
            >
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default MarkerPopup;
