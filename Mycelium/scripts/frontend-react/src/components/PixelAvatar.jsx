import React, { useMemo } from 'react';
import {
  AVATAR_SIZE,
  avatarHasPixels,
  normalizeAvatarMatrix,
  pixelToCssRgba
} from '../utils/avatarUtils';
import './PixelAvatar.css';

const PixelAvatar = ({
  pixels,
  size = 28,
  borderColor = 'rgba(255, 255, 255, 0.2)',
  background = 'rgba(0, 0, 0, 0.15)',
  placeholderLabel = '',
  className = ''
}) => {
  const normalized = useMemo(() => normalizeAvatarMatrix(pixels), [pixels]);
  const hasPixels = useMemo(() => avatarHasPixels(pixels), [pixels]);
  const cellSize = size / AVATAR_SIZE;

  return (
    <div
      className={`pixel-avatar ${className}`}
      style={{
        width: size,
        height: size,
        borderColor,
        background
      }}
    >
      <div
        className="pixel-avatar-grid"
        style={{
          gridTemplateColumns: `repeat(${AVATAR_SIZE}, ${cellSize}px)`,
          gridTemplateRows: `repeat(${AVATAR_SIZE}, ${cellSize}px)`
        }}
      >
        {normalized.map((row, rIdx) =>
          row.map((pixel, cIdx) => (
            <div
              key={`${rIdx}-${cIdx}`}
              className="pixel-avatar-cell"
              style={{ backgroundColor: pixelToCssRgba(pixel) }}
            />
          ))
        )}
      </div>
      {!hasPixels && placeholderLabel && (
        <div className="pixel-avatar-placeholder">
          {placeholderLabel.slice(0, 2).toUpperCase()}
        </div>
      )}
    </div>
  );
};

export default PixelAvatar;
