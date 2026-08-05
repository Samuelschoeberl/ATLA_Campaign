import React, { useRef, useState, useEffect } from 'react';
import { pixelToCssRgba } from '../utils/avatarUtils';
import CharacterToken from './CharacterToken';
import { fetchCharacterSheet, loadConditionDescriptions } from '../utils/characterSheetParser';
import { API_BASE_URL } from '../config/api';
import { animateCellPaint, animateCellErase, animateRipple, animateTokenMove, animateTokenSpawn } from '../utils/battlemapAnimations';
import './BattlemapCanvas.css';

const BattlemapCanvas = ({
  backgroundUrl,
  imageDimensions,
  tiles,
  rows,
  cols,
  cellSize,
  scale,
  isPainting,
  eraseMode,
  onStartPaint,
  onPaintCell,
  onCanvasMount,
  tokens = [], // Array of character tokens on the map
  selectedTokenId = null,
  onTokenSelect = null
}) => {
  const canvasRef = useRef(null);
  const [characterSheets, setCharacterSheets] = useState({});
  const [conditionDescriptions, setConditionDescriptions] = useState({});
  const tokenRefs = useRef(new Map());
  const prevPositionsRef = useRef(new Map());

  // Calculate scaled dimensions
  const scaledCellWidth = cellSize.width * scale;
  const scaledCellHeight = cellSize.height * scale;
  const totalWidth = cols * scaledCellWidth;
  const totalHeight = rows * scaledCellHeight;

  // Load condition descriptions on mount
  useEffect(() => {
    loadConditionDescriptions(API_BASE_URL).then(descriptions => {
      setConditionDescriptions(descriptions);
    });
  }, []);

  // Load character sheets for tokens
  useEffect(() => {
    const loadSheets = async () => {
      const sheets = {};
      for (const token of tokens) {
        if (token.name && !characterSheets[token.name]) {
          const sheet = await fetchCharacterSheet(token.name, API_BASE_URL);
          if (sheet) {
            sheets[token.name] = sheet;
          }
        }
      }
      if (Object.keys(sheets).length > 0) {
        setCharacterSheets(prev => ({ ...prev, ...sheets }));
      }
    };
    
    if (tokens.length > 0) {
      loadSheets();
    }
  }, [tokens]);

  // Calculate token position on grid
  const getTokenPosition = (token) => {
    const x = token.col * scaledCellWidth;
    const y = token.row * scaledCellHeight;
    return { x, y };
  };

  // Smoothly animate token spawn and movement
  useEffect(() => {
    const seenIds = new Set();

    tokens.forEach((token) => {
      const el = tokenRefs.current.get(token.id);
      if (!el) return;

      const pos = getTokenPosition(token);
      const left = pos.x + scaledCellWidth / 2;
      const top = pos.y + scaledCellHeight / 2;
      const previous = prevPositionsRef.current.get(token.id);

      if (!previous) {
        animateTokenSpawn(el, 420);
      } else if (previous.left !== left || previous.top !== top) {
        animateTokenMove(el, { x: previous.left, y: previous.top }, { x: left, y: top });
      }

      prevPositionsRef.current.set(token.id, { left, top });
      seenIds.add(token.id);
    });

    // Cleanup positions for tokens that were removed
    Array.from(prevPositionsRef.current.keys()).forEach((id) => {
      if (!seenIds.has(id)) {
        prevPositionsRef.current.delete(id);
        tokenRefs.current.delete(id);
      }
    });
  }, [tokens, scaledCellWidth, scaledCellHeight]);

  return (
    <div className="battlemap-canvas" ref={(el) => {
      canvasRef.current = el;
      if (onCanvasMount) onCanvasMount(el);
    }}>
      {backgroundUrl && (
        <img
          src={backgroundUrl}
          alt="Battle map"
          className="battlemap-background"
          style={{
            width: `${totalWidth}px`,
            height: `${totalHeight}px`,
          }}
        />
      )}
      <div 
        className="battlemap-grid"
        style={{
          width: `${totalWidth}px`,
          height: `${totalHeight}px`,
          gridTemplateColumns: `repeat(${cols}, ${scaledCellWidth}px)`,
          gridTemplateRows: `repeat(${rows}, ${scaledCellHeight}px)`,
        }}
      >
        {tiles.map((row, rowIdx) =>
          row.map((cell, colIdx) => (
            <div
              key={`cell-${rowIdx}-${colIdx}`}
              className="grid-cell"
              style={{ backgroundColor: pixelToCssRgba(cell) }}
              title={`R${rowIdx + 1} C${colIdx + 1}`}
              onMouseDown={(e) => {
                e.preventDefault();
                const erase = e.altKey || e.button === 2;
                onStartPaint(erase);
                onPaintCell(rowIdx, colIdx, erase);
                
                // Add ripple effect on click
                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                animateRipple(e.currentTarget, x, y, erase ? 'rgba(255, 255, 255, 0.3)' : 'rgba(100, 149, 237, 0.4)');
              }}
              onMouseEnter={(e) => {
                if (isPainting) {
                  const cell = e.currentTarget;
                  const currentColor = pixelToCssRgba(tiles[rowIdx][colIdx]);
                  const newColor = eraseMode ? 'rgba(0, 0, 0, 0)' : currentColor;
                  
                  // Animate cell change
                  if (eraseMode) {
                    animateCellErase(cell);
                  } else {
                    animateCellPaint(cell, newColor);
                  }
                  
                  onPaintCell(rowIdx, colIdx, eraseMode);
                }
              }}
              onContextMenu={(e) => e.preventDefault()}
            />
          ))
        )}
      </div>

      {/* Character Tokens Layer */}
      {tokens.map((token) => {
        const position = getTokenPosition(token);
        const characterSheet = characterSheets[token.name];
        
        // Merge condition descriptions into character sheet conditions
        const enrichedSheet = characterSheet ? {
          ...characterSheet,
          conditions: characterSheet.conditions?.map(c => ({
            ...c,
            description: conditionDescriptions[c.name] || c.description
          }))
        } : null;

        return (
          <div
            key={token.id}
            ref={(el) => {
              if (el) {
                tokenRefs.current.set(token.id, el);
              } else {
                tokenRefs.current.delete(token.id);
              }
            }}
            style={{
              position: 'absolute',
              left: `${position.x + scaledCellWidth / 2}px`,
              top: `${position.y + scaledCellHeight / 2}px`,
              transform: 'translate(-50%, -50%)',
              zIndex: selectedTokenId === token.id ? 20 : 15,
              pointerEvents: 'auto',
              cursor: 'pointer'
            }}
            onClick={(e) => {
              e.stopPropagation();
              if (onTokenSelect) {
                onTokenSelect(token.id);
              }
            }}
          >
            <CharacterToken
              token={token}
              size={Math.min(scaledCellWidth, scaledCellHeight) * 0.9}
              isSelected={token.id === selectedTokenId}
              onClick={(e) => {
                e.stopPropagation();
                if (onTokenSelect) {
                  onTokenSelect(token.id);
                }
              }}
              characterSheet={enrichedSheet}
            />
          </div>
        );
      })}
    </div>
  );
};

export default BattlemapCanvas;
