import React from 'react';
import PixelAvatar from './PixelAvatar';
import { normalizeAvatarMatrix } from '../utils/avatarUtils';

/**
 * TokenLibrary - Draggable token library for battlemap
 * Displays player characters and enemy/NPC tokens that can be dragged onto the map
 */
const TokenLibrary = ({ 
  availableCharacters = [], 
  enemyTokens = [],
  onClose 
}) => {
  return (
    <div style={{
      position: 'fixed',
      right: '20px',
      top: '80px',
      width: '320px',
      maxHeight: 'calc(100vh - 100px)',
      background: '#2a2a2a',
      padding: '15px',
      borderRadius: '8px',
      overflowY: 'auto',
      border: '2px solid #3498db',
      boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
      zIndex: 1000
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '12px'
      }}>
        <h4 style={{ margin: 0, color: '#3498db', fontSize: '18px' }}>
          🎭 Token Library
        </h4>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#e74c3c',
            fontSize: '24px',
            cursor: 'pointer',
            padding: '0',
            width: '30px',
            height: '30px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
            transition: 'background 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(231, 76, 60, 0.2)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          ×
        </button>
      </div>
      
      <p style={{ fontSize: '13px', color: '#888', margin: '0 0 15px 0' }}>
        Drag and drop tokens onto the hex grid
      </p>
      
      {/* Player Characters Section */}
      <div style={{ marginBottom: '20px' }}>
        <h5 style={{ 
          margin: '0 0 10px 0', 
          color: '#27ae60', 
          borderBottom: '2px solid #27ae60',
          paddingBottom: '5px',
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          👥 Player Characters
        </h5>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 1fr))', 
          gap: '10px' 
        }}>
          {availableCharacters.map(char => (
            <div
              key={char.name}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('character', JSON.stringify({
                  ...char,
                  type: 'player'
                }));
                e.dataTransfer.effectAllowed = 'copy';
              }}
              style={{
                padding: '8px',
                background: '#1a1a1a',
                border: '2px solid #27ae60',
                borderRadius: '6px',
                color: '#e0e0e0',
                cursor: 'grab',
                textAlign: 'center',
                transition: 'all 0.2s',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#2ecc71';
                e.currentTarget.style.transform = 'scale(1.05)';
                e.currentTarget.style.boxShadow = '0 0 10px rgba(46, 204, 113, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#27ae60';
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              {char.avatar ? (
                <PixelAvatar
                  pixels={normalizeAvatarMatrix(char.avatar)}
                  size={45}
                  borderColor={char.color || '#27ae60'}
                  background="rgba(0,0,0,0.3)"
                  placeholderLabel={char.name}
                />
              ) : (
                <div style={{
                  width: '45px',
                  height: '45px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px'
                }}>
                  👤
                </div>
              )}
              <span style={{ 
                fontSize: '11px', 
                fontWeight: '600',
                wordBreak: 'break-word',
                lineHeight: '1.2'
              }}>
                {char.name}
              </span>
            </div>
          ))}
          {availableCharacters.length === 0 && (
            <p style={{ 
              color: '#888', 
              margin: 0, 
              gridColumn: '1 / -1', 
              fontSize: '12px',
              textAlign: 'center',
              padding: '20px 10px'
            }}>
              No player characters available
            </p>
          )}
        </div>
      </div>
      
      {/* Enemy Tokens Section */}
      <div>
        <h5 style={{ 
          margin: '0 0 10px 0', 
          color: '#e74c3c', 
          borderBottom: '2px solid #e74c3c',
          paddingBottom: '5px',
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          ⚔️ Enemy / NPC Tokens
        </h5>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 1fr))', 
          gap: '10px' 
        }}>
          {enemyTokens.map(enemy => (
            <div
              key={enemy.name}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('character', JSON.stringify({
                  name: enemy.name,
                  color: enemy.color,
                  icon: enemy.icon,
                  type: 'enemy'
                }));
                e.dataTransfer.effectAllowed = 'copy';
              }}
              style={{
                padding: '8px',
                background: '#1a1a1a',
                border: '2px solid #e74c3c',
                borderRadius: '6px',
                color: '#e0e0e0',
                cursor: 'grab',
                textAlign: 'center',
                transition: 'all 0.2s',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#c0392b';
                e.currentTarget.style.transform = 'scale(1.05)';
                e.currentTarget.style.boxShadow = '0 0 10px rgba(231, 76, 60, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e74c3c';
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={{
                width: '45px',
                height: '45px',
                borderRadius: '50%',
                background: `linear-gradient(135deg, ${enemy.color}, ${enemy.color}dd)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
                border: `2px solid ${enemy.color}`
              }}>
                {enemy.icon}
              </div>
              <span style={{ 
                fontSize: '11px', 
                fontWeight: '600',
                wordBreak: 'break-word',
                lineHeight: '1.2'
              }}>
                {enemy.name}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TokenLibrary;
