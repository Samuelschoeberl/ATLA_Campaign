import React, { useState } from 'react';
import './PaintControls.css';

const STANDARD_COLORS = [
  '#ff6b6b', '#ffb347', '#ffd166', '#9b59b6', '#6c5ce7', '#3498db',
  '#5f81fd', '#2ecc71', '#1abc9c', '#16a085', '#e67e22', '#e74c3c',
  '#c0392b', '#f1c40f', '#f39c12', '#95a5a6', '#7f8c8d', '#ecf0f1',
  '#2d3436'
];

const PaintControls = ({
  brushColor,
  brushAlpha,
  recentColors,
  onColorChange,
  onAlphaChange,
  onClearGrid
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className={`paint-controls ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="controls-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="controls-title">
          <span className="collapse-icon">{isCollapsed ? '▶' : '▼'}</span>
          Paint Controls
        </h3>
        {isCollapsed && (
          <div className="controls-preview">
            <div className="preview-color" style={{ backgroundColor: brushColor }} />
            <span className="preview-text">{Math.round(brushAlpha * 100)}% opacity</span>
          </div>
        )}
      </div>

      {!isCollapsed && (
        <div className="controls-content">
          <div className="control-section">
            <div className="control-group">
              <label className="control-label">Brush Color</label>
              <div className="color-picker-wrapper">
                <input
                  type="color"
                  value={brushColor}
                  onChange={(e) => onColorChange(e.target.value)}
                  className="color-picker"
                />
                <span className="color-value">{brushColor.toUpperCase()}</span>
              </div>
            </div>

            <div className="control-group">
              <label className="control-label">
                Opacity <span className="opacity-value">{Math.round(brushAlpha * 100)}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={brushAlpha}
                onChange={(e) => onAlphaChange(parseFloat(e.target.value))}
                className="opacity-slider"
              />
            </div>
          </div>

          <div className="control-section">
            <div className="palette-section">
              <div className="palette-header">
                <span className="palette-title">🎨 Color Palette</span>
              </div>
              <div className="palette-grid">
                {STANDARD_COLORS.map((color) => (
                  <button
                    key={color}
                    className={`palette-swatch ${color === brushColor ? 'active' : ''}`}
                    style={{ backgroundColor: color }}
                    onClick={() => onColorChange(color)}
                    title={color.toUpperCase()}
                  />
                ))}
              </div>
            </div>

            {recentColors.length > 0 && (
              <div className="palette-section">
                <div className="palette-header">
                  <span className="palette-title">🕐 Recent Colors</span>
                </div>
                <div className="palette-grid recent-grid">
                  {recentColors.map((color, idx) => (
                    <button
                      key={`recent-${color}-${idx}`}
                      className={`palette-swatch ${color === brushColor ? 'active' : ''}`}
                      style={{ backgroundColor: color }}
                      onClick={() => onColorChange(color)}
                      title={color.toUpperCase()}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="control-section">
            <button className="clear-button" onClick={onClearGrid}>
              🗑️ Clear Grid
            </button>
            <div className="paint-hint">
              💡 <strong>Tip:</strong> Click to paint • Alt+Click or Right-click to erase • Drag to paint multiple cells
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaintControls;
