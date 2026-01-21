import React from 'react';

/**
 * TokenContextMenu - Context menu for token operations
 */
const TokenContextMenu = ({
  contextMenu,
  setContextMenu,
  setTokens,
  setTokenToMove,
  handleToggleTokenHp,
  handleEditDataClick,
  handleRemoveToken,
  handleOpenCharacterSheet,
  handleOpenNpcCharacterSheet
}) => {
  if (!contextMenu) return null;
  
  return (
    <div
      style={{
        position: 'fixed',
        top: contextMenu.y,
        left: contextMenu.x,
        background: '#2c3e50',
        border: '2px solid #34495e',
        borderRadius: '8px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        zIndex: 10000,
        minWidth: '200px',
        padding: '8px 0'
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div style={{ padding: '8px 16px', borderBottom: '1px solid #34495e', color: '#ecf0f1', fontWeight: 'bold', fontSize: '14px' }}>
        {contextMenu.token.name}
      </div>
      
      {/* Toggle HP Bar */}
      <button
        onClick={() => handleToggleTokenHp(contextMenu.tokenId)}
        style={{
          width: '100%',
          padding: '10px 16px',
          background: 'transparent',
          border: 'none',
          color: '#ecf0f1',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        <span style={{ width: '20px' }}>{contextMenu.token.showHp !== false ? '✓' : ''}</span>
        Show HP Bar
      </button>
      
      {/* Toggle Conditions */}
      <button
        onClick={() => {
          setTokens(prev => prev.map(t => 
            t.id === contextMenu.tokenId
              ? { ...t, showConditions: t.showConditions === false ? true : false }
              : t
          ));
          setContextMenu(null);
        }}
        style={{
          width: '100%',
          padding: '10px 16px',
          background: 'transparent',
          border: 'none',
          color: '#ecf0f1',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        <span style={{ width: '20px' }}>{contextMenu.token.showConditions !== false ? '✓' : ''}</span>
        Show Conditions
      </button>
      
      {/* Toggle Defensive Stats */}
      <button
        onClick={() => {
          setTokens(prev => prev.map(t => 
            t.id === contextMenu.tokenId
              ? { ...t, showDefensiveStats: t.showDefensiveStats === false ? true : false }
              : t
          ));
          setContextMenu(null);
        }}
        style={{
          width: '100%',
          padding: '10px 16px',
          background: 'transparent',
          border: 'none',
          color: '#ecf0f1',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        <span style={{ width: '20px' }}>{contextMenu.token.showDefensiveStats !== false ? '✓' : ''}</span>
        Show Defensive Stats
      </button>
      
      {/* Move Token */}
      <button
        onClick={() => {
          setTokenToMove(contextMenu.tokenId);
          setContextMenu(null);
        }}
        style={{
          width: '100%',
          padding: '10px 16px',
          background: 'transparent',
          border: 'none',
          color: '#ecf0f1',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        🔄 Move Token
      </button>
      
      {/* Edit Token */}
      <button
        onClick={() => {
          handleEditDataClick(contextMenu.token.row, contextMenu.token.col);
          setContextMenu(null);
        }}
        style={{
          width: '100%',
          padding: '10px 16px',
          background: 'transparent',
          border: 'none',
          color: '#ecf0f1',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        ✏️ Edit Token
      </button>
      
      {/* Open Character Sheet (player tokens) */}
      {contextMenu.token.type === 'player' && contextMenu.token.name && handleOpenCharacterSheet && (
        <button
          onClick={() => {
            handleOpenCharacterSheet(contextMenu.token.name);
            setContextMenu(null);
          }}
          style={{
            width: '100%',
            padding: '10px 16px',
            background: 'transparent',
            border: 'none',
            color: '#ecf0f1',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'background 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          📄 Open Character Sheet
        </button>
      )}

      {/* Generate/Show NPC/Enemy Sheet */}
      {contextMenu.token.type !== 'player' && handleOpenNpcCharacterSheet && (
        <button
          onClick={() => {
            handleOpenNpcCharacterSheet(contextMenu.token);
            setContextMenu(null);
          }}
          style={{
            width: '100%',
            padding: '10px 16px',
            background: 'transparent',
            border: 'none',
            color: '#ecf0f1',
            cursor: 'pointer',
            textAlign: 'left',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'background 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          📄 Generate/Show NPC Sheet
        </button>
      )}
      
      {/* Remove Token */}
      <button
        onClick={() => handleRemoveToken(contextMenu.tokenId)}
        style={{
          width: '100%',
          padding: '10px 16px',
          background: 'transparent',
          border: 'none',
          borderTop: '1px solid #34495e',
          color: '#e74c3c',
          cursor: 'pointer',
          textAlign: 'left',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          transition: 'background 0.2s',
          marginTop: '4px'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = '#34495e'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
      >
        🗑️ Remove Token
      </button>
    </div>
  );
};

export default TokenContextMenu;
