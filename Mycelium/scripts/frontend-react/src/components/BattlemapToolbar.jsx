import React, { useState } from 'react';
import './BattlemapToolbar.css';

const BattlemapToolbar = ({
  selectedImage,
  imageOptions,
  rows,
  cols,
  scale,
  imageDimensions,
  cellSize,
  onImageSelect,
  onImageTextChange,
  onFileUpload,
  onRowsChange,
  onColsChange,
  onScaleChange
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className={`battlemap-toolbar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="toolbar-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3 className="toolbar-title">
          <span className="collapse-icon">{isCollapsed ? '▶' : '▼'}</span>
          Image & Grid Settings
        </h3>
        {isCollapsed && imageDimensions.width > 0 && (
          <div className="toolbar-preview">
            {selectedImage && <span className="preview-text">📷 {selectedImage}</span>}
            <span className="preview-text">{rows}×{cols} grid</span>
            <span className="preview-text">{scale.toFixed(1)}× scale</span>
          </div>
        )}
      </div>
      
      {!isCollapsed && (
        <div className="toolbar-content">
          <div className="toolbar-section">
            <div className="toolbar-group">
              <label className="toolbar-label">Base Image</label>
              <select
                value={selectedImage}
                onChange={(e) => onImageSelect(e.target.value)}
                className="toolbar-select"
              >
                <option value="">— None —</option>
                {imageOptions.map((img) => (
                  <option key={img} value={img}>{img}</option>
                ))}
              </select>
              <input
                type="text"
                value={selectedImage}
                placeholder="or enter filename..."
                onChange={(e) => onImageTextChange(e.target.value)}
                className="toolbar-input"
              />
              <label className="upload-label">
                <input
                  type="file"
                  accept="image/*"
                  onChange={onFileUpload}
                />
                <span className="upload-icon">📁</span>
                Choose file
              </label>
            </div>
          </div>

          <div className="toolbar-section">
            <div className="toolbar-group">
              <label className="toolbar-label">Grid Size</label>
              <div className="input-group">
                <input
                  type="number"
                  min="1"
                  max="200"
                  value={rows}
                  onChange={(e) => onRowsChange(e.target.value)}
                  className="size-input"
                  placeholder="rows"
                />
                <span className="toolbar-sep">×</span>
                <input
                  type="number"
                  min="1"
                  max="200"
                  value={cols}
                  onChange={(e) => onColsChange(e.target.value)}
                  className="size-input"
                  placeholder="cols"
                />
              </div>
            </div>
          </div>

          <div className="toolbar-section">
            <div className="toolbar-group">
              <label className="toolbar-label">Scale</label>
              <input
                type="range"
                min="0.1"
                max="5"
                step="0.1"
                value={scale}
                onChange={(e) => onScaleChange(parseFloat(e.target.value))}
                className="scale-slider"
              />
              <span className="scale-value">{scale.toFixed(1)}×</span>
            </div>
          </div>

          {imageDimensions.width > 0 && (
            <div className="toolbar-info">
              <span className="info-badge">
                📐 Image: {imageDimensions.width}×{imageDimensions.height}px
              </span>
              <span className="info-badge">
                🔲 Cell: {(cellSize.width * scale).toFixed(1)}×{(cellSize.height * scale).toFixed(1)}px
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BattlemapToolbar;

