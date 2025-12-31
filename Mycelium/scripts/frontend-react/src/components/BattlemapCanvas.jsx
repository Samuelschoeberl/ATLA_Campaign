import React, { useRef } from 'react';
import { pixelToCssRgba } from '../utils/avatarUtils';
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
  onCanvasMount
}) => {
  const canvasRef = useRef(null);

  // Calculate scaled dimensions
  const scaledCellWidth = cellSize.width * scale;
  const scaledCellHeight = cellSize.height * scale;
  const totalWidth = cols * scaledCellWidth;
  const totalHeight = rows * scaledCellHeight;

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
              }}
              onMouseEnter={() => {
                if (isPainting) {
                  onPaintCell(rowIdx, colIdx, eraseMode);
                }
              }}
              onContextMenu={(e) => e.preventDefault()}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default BattlemapCanvas;
