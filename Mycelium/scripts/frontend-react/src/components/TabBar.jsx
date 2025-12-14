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
        {tabs.map((tab) => (
          <div
            key={tab.path}
            className={`tab ${activeTab?.path === tab.path ? 'active' : ''}`}
            onClick={() => onTabSelect(tab)}
            title={tab.path}
          >
            <span className="tab-icon">{getFileIcon(tab.name)}</span>
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
        ))}
      </div>
    </div>
  );
};

export default TabBar;
