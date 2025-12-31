import React from 'react';
import './TabBar.css';

const TabBar = ({ tabs, activeTab, onTabSelect, onTabClose, lightMode }) => {
  const getFileIcon = (filename) => {
    if (filename.match(/\.(html|htm)$/i)) return '<>';
    if (filename.endsWith('.md')) return '⬇';
    return '�';
  };

  const truncateFilename = (name, maxLength = 20) => {
    if (name.length <= maxLength) return name;
    const extension = name.split('.').pop();
    const nameWithoutExt = name.substring(0, name.lastIndexOf('.'));
    const truncated = nameWithoutExt.substring(0, maxLength - extension.length - 4) + '...';
    return `${truncated}.${extension}`;
  };

  return (
    <div className={`tab-bar ${lightMode ? 'light-mode' : ''}`}>
      <div className="tabs-container">
        {tabs.map((tab) => {
          const isActive = activeTab?.path === tab.path;
          return (
            <div
              key={tab.path}
              className={`tab ${isActive ? 'active' : ''}`}
              onClick={() => onTabSelect(tab)}
              title={tab.path}
            >
              <span className="tab-icon" style={{ 
                filter: isActive ? 'brightness(1.3)' : 'none',
                transform: isActive ? 'scale(1.1)' : 'scale(1)',
                transition: 'all 0.2s'
              }}>
                {getFileIcon(tab.name)}
              </span>
              <span className="tab-name">{truncateFilename(tab.name)}</span>
              <button
                className="tab-close"
                onClick={(e) => {
                  e.stopPropagation();
                  onTabClose(tab);
                }}
                title="Close tab"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TabBar;
