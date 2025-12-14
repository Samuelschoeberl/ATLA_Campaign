import React, { useState, useEffect } from 'react';
import FileTree from './FileTree';
import FileViewer from './FileViewer';
import SearchBar from './SearchBar';
import TabBar from './TabBar';
import './FileExplorer.css';

const FileExplorer = ({ lightMode, onToggleTheme }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [openTabs, setOpenTabs] = useState([]);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [fileRefreshKey, setFileRefreshKey] = useState(0);

  // Automatically open Quicklinks.md on initial load
  useEffect(() => {
    const loadQuicklinks = async () => {
      try {
        // Construct the file object for Quicklinks.md
        const quicklinksFile = {
          name: 'Quicklinks.md',
          path: 'Quicklinks.md',
          type: 'file'
        };
        setSelectedFile(quicklinksFile);
        setOpenTabs([quicklinksFile]);
      } catch (error) {
        console.error('Failed to load Quicklinks.md:', error);
      }
    };

    loadQuicklinks();
  }, []); // Empty dependency array means this runs once on mount

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    
    // Add file to tabs if not already open
    const isAlreadyOpen = openTabs.some(tab => tab.path === file.path);
    if (!isAlreadyOpen) {
      setOpenTabs([...openTabs, file]);
    }
  };

  const handleTabSelect = (tab) => {
    setSelectedFile(tab);
  };

  const handleTabClose = (tabToClose) => {
    const newTabs = openTabs.filter(tab => tab.path !== tabToClose.path);
    setOpenTabs(newTabs);
    
    // If we're closing the active tab, select another one
    if (selectedFile?.path === tabToClose.path) {
      if (newTabs.length > 0) {
        // Select the tab to the right, or the last tab if closing the rightmost
        const closedIndex = openTabs.findIndex(tab => tab.path === tabToClose.path);
        const newActiveIndex = closedIndex < newTabs.length ? closedIndex : newTabs.length - 1;
        setSelectedFile(newTabs[newActiveIndex]);
      } else {
        setSelectedFile(null);
      }
    }
  };

  const handleFileUpdate = (filePath) => {
    // Increment the refresh key to force FileViewer to reload
    setFileRefreshKey(prev => prev + 1);
  };

  return (
    <div className={`file-explorer ${lightMode ? 'light-mode' : ''}`}>
      <div className="file-explorer-sidebar">
        <FileTree 
          onFileSelect={handleFileSelect}
          lightMode={lightMode}
          advancedMode={advancedMode}
          onFileUpdate={handleFileUpdate}
        />
      </div>
      <div className="file-explorer-main">
        <div className="file-explorer-header">
          <SearchBar onFileSelect={handleFileSelect} lightMode={lightMode} />
          <button 
            className="advanced-toggle"
            onClick={() => setAdvancedMode(!advancedMode)}
            title={advancedMode ? "Disable Advanced Options" : "Enable Advanced Options"}
            style={{
              padding: '8px 16px',
              marginRight: '8px',
              background: advancedMode ? '#007acc' : (lightMode ? '#ddd' : '#3c3c3c'),
              color: advancedMode ? '#fff' : (lightMode ? '#333' : '#ccc'),
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: advancedMode ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            ⚙️ Advanced
          </button>
          <button 
            className="theme-toggle"
            onClick={onToggleTheme}
            title={lightMode ? "Switch to Dark Mode" : "Switch to Light Mode"}
          >
            {lightMode ? '🌙' : '☀️'}
          </button>
        </div>
        <TabBar 
          tabs={openTabs}
          activeTab={selectedFile}
          onTabSelect={handleTabSelect}
          onTabClose={handleTabClose}
          lightMode={lightMode}
        />
        <div className="file-explorer-content">
          <FileViewer 
            key={fileRefreshKey} 
            file={selectedFile} 
            lightMode={lightMode} 
            onFileSelect={handleFileSelect} 
          />
        </div>
      </div>
    </div>
  );
};

export default FileExplorer;
