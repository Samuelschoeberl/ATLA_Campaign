import React from 'react';

/**
 * TokenDetailsPopup - Displays detailed information about a token including full-size avatar
 */
const TokenDetailsPopup = ({ token, onClose }) => {
  if (!token) return null;
  
  return (
    <div 
      className="token-details-overlay"
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000,
        cursor: 'pointer',
        animation: 'fadeIn 0.2s ease-out'
      }}
    >
      <div 
        className="token-details-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          backgroundColor: '#2c3e50',
          borderRadius: '12px',
          padding: '24px',
          maxWidth: '600px',
          maxHeight: '90vh',
          overflow: 'auto',
          cursor: 'default',
          animation: 'popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
          border: '2px solid #34495e'
        }}
      >
        <button 
          className="token-details-close"
          onClick={onClose}
          aria-label="Close"
          style={{
            position: 'absolute',
            top: '-12px',
            right: '-12px',
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: '#e74c3c',
            color: 'white',
            border: '2px solid white',
            fontSize: '24px',
            lineHeight: '28px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
            zIndex: 1
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#c0392b';
            e.currentTarget.style.transform = 'scale(1.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#e74c3c';
            e.currentTarget.style.transform = 'scale(1)';
          }}
        >
          ×
        </button>
        
        {/* Header with avatar */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: '16px',
          marginBottom: '20px'
        }}>
          {(token.avatarPng || token.icon) && (
            <div style={{
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
              border: `3px solid ${token.color || '#888'}`,
              backgroundColor: '#1a1a1a'
            }}>
              <img 
                src={token.avatarPng || token.icon} 
                alt={`${token.name} avatar`}
                style={{
                  display: 'block',
                  maxWidth: '300px',
                  maxHeight: '300px',
                  width: 'auto',
                  height: 'auto',
                  imageRendering: 'pixelated'
                }}
              />
            </div>
          )}
          
          <h2 style={{ 
            margin: 0, 
            color: '#ecf0f1',
            fontSize: '24px',
            textAlign: 'center'
          }}>
            {token.name}
          </h2>
        </div>
        
        {/* Token Information Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '16px',
          marginBottom: '16px'
        }}>
          {/* Type */}
          <div style={{
            backgroundColor: '#34495e',
            padding: '12px',
            borderRadius: '8px'
          }}>
            <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Type</div>
            <div style={{ color: '#ecf0f1', fontSize: '16px', fontWeight: 'bold', textTransform: 'capitalize' }}>
              {token.type === 'player' ? '🎭 Player' : token.type === 'enemy' ? '⚔️ Enemy' : '🤖 NPC'}
            </div>
          </div>
          
          {/* Position */}
          <div style={{
            backgroundColor: '#34495e',
            padding: '12px',
            borderRadius: '8px'
          }}>
            <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Position</div>
            <div style={{ color: '#ecf0f1', fontSize: '16px', fontWeight: 'bold' }}>
              ({token.row}, {token.col})
            </div>
          </div>
          
          {/* Size */}
          <div style={{
            backgroundColor: '#34495e',
            padding: '12px',
            borderRadius: '8px'
          }}>
            <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Size</div>
            <div style={{ color: '#ecf0f1', fontSize: '16px', fontWeight: 'bold' }}>
              {token.width || 1} × {token.height || 1} hexes
            </div>
          </div>
          
          {/* HP */}
          {token.hp !== undefined && (
            <div style={{
              backgroundColor: '#34495e',
              padding: '12px',
              borderRadius: '8px'
            }}>
              <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '4px' }}>Health Points</div>
              <div style={{ color: '#ecf0f1', fontSize: '16px', fontWeight: 'bold' }}>
                {token.hp.current || 0} / {token.hp.max || 0}
              </div>
            </div>
          )}
        </div>
        
        {/* Defensive Stats */}
        {(token.ac !== undefined || token.barrier !== undefined || token.defense !== undefined) && (
          <div style={{
            backgroundColor: '#34495e',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '16px'
          }}>
            <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '8px' }}>Defensive Stats</div>
            <div style={{ 
              display: 'flex', 
              gap: '12px',
              flexWrap: 'wrap'
            }}>
              {token.ac !== undefined && (
                <div style={{ color: '#ecf0f1' }}>
                  <span style={{ color: '#95a5a6' }}>AC:</span> <strong>{token.ac}</strong>
                </div>
              )}
              {token.barrier !== undefined && (
                <div style={{ color: '#ecf0f1' }}>
                  <span style={{ color: '#95a5a6' }}>Barrier:</span> <strong>{token.barrier}</strong>
                </div>
              )}
              {token.defense !== undefined && (
                <div style={{ color: '#ecf0f1' }}>
                  <span style={{ color: '#95a5a6' }}>Defense:</span> <strong>{token.defense}</strong>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Conditions */}
        {token.conditions && token.conditions.length > 0 && (
          <div style={{
            backgroundColor: '#34495e',
            padding: '12px',
            borderRadius: '8px',
            marginBottom: '16px'
          }}>
            <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '8px' }}>Active Conditions</div>
            <div style={{ 
              display: 'flex', 
              gap: '8px',
              flexWrap: 'wrap'
            }}>
              {token.conditions.map((condition, idx) => (
                <div 
                  key={idx}
                  style={{
                    backgroundColor: '#2c3e50',
                    padding: '6px 12px',
                    borderRadius: '12px',
                    color: '#ecf0f1',
                    fontSize: '13px',
                    border: '1px solid #7f8c8d'
                  }}
                >
                  {condition}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Aura */}
        {token.aura && (
          <div style={{
            backgroundColor: '#34495e',
            padding: '12px',
            borderRadius: '8px'
          }}>
            <div style={{ color: '#95a5a6', fontSize: '12px', marginBottom: '8px' }}>Aura</div>
            <div style={{ color: '#ecf0f1' }}>
              <div>
                <span style={{ color: '#95a5a6' }}>Range:</span> <strong>{token.aura.range}</strong> hexes
              </div>
              <div>
                <span style={{ color: '#95a5a6' }}>Effect:</span> <strong style={{ textTransform: 'capitalize' }}>{token.aura.effect}</strong>
              </div>
              {token.aura.outlineColor && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                  <span style={{ color: '#95a5a6' }}>Color:</span>
                  <div style={{
                    width: '24px',
                    height: '24px',
                    backgroundColor: token.aura.outlineColor,
                    borderRadius: '4px',
                    border: '1px solid #7f8c8d'
                  }} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TokenDetailsPopup;
