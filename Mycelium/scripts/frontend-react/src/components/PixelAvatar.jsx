import React from 'react';
import './PixelAvatar.css';

const PixelAvatar = ({
  avatarPng,  // PNG data URL
  size = 28,
  borderColor = 'rgba(255, 255, 255, 0.2)',
  background = 'transparent',
  placeholderLabel = '',
  className = ''
}) => {
  return (
    <div
      className={`pixel-avatar ${className}`}
      style={{
        width: size,
        height: size,
        borderColor,
        background: avatarPng ? 'transparent' : background,
        filter: 'none',            // prevent inherited filters
        mixBlendMode: 'normal',    // avoid blending with underlying SVG
        isolation: 'isolate'       // ensure no color inversion through blending
      }}
    >
      {avatarPng ? (
        <img
          src={avatarPng}
          alt="Avatar"
          style={{
            width: '100%',
            height: '100%',
            imageRendering: 'pixelated',
            filter: 'none',
            mixBlendMode: 'normal'
          }}
        />
      ) : (
        placeholderLabel && (
          <div className="pixel-avatar-placeholder">
            {placeholderLabel.slice(0, 2).toUpperCase()}
          </div>
        )
      )}
    </div>
  );
};

export default PixelAvatar;
