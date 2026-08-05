import React, { useState, useEffect, useRef, useCallback } from 'react';
import FileTree from './FileTree';
import FileViewer from './FileViewer';
import SearchBar from './SearchBar';
import TabBar from './TabBar';
import './FileExplorer.css';

const FileExplorer = ({ lightMode, onToggleTheme, gmMode, onToggleGmMode }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [openTabs, setOpenTabs] = useState([]);
  const [advancedMode, setAdvancedMode] = useState(false);
  const [fileRefreshKey, setFileRefreshKey] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isTreeCollapsed, setIsTreeCollapsed] = useState(true);
  const fileTreeRef = useRef(null);

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
    
    // Expand folders in the file tree to show the selected file
    if (fileTreeRef.current && file.path) {
      fileTreeRef.current.expandToFile(file.path);
    }
    
    // Add file to tabs if not already open
    const isAlreadyOpen = openTabs.some(tab => tab.path === file.path);
    if (!isAlreadyOpen) {
      setOpenTabs([...openTabs, file]);
    }
  };

  const handleTabSelect = (tab) => {
    setSelectedFile(tab);
  };

  const handleTabClose = useCallback((tabToClose) => {
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
  }, [openTabs, selectedFile]);

  // Keyboard shortcut: Alt/Option + W to close current tab
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Check for Alt/Option + W (case insensitive)
      if ((e.altKey || e.metaKey) && (e.key === 'w' || e.key === 'W')) {
        e.preventDefault(); // Prevent default browser behavior
        
        // Close the currently selected tab
        if (selectedFile) {
          handleTabClose(selectedFile);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    
    // Cleanup event listener on unmount
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedFile, handleTabClose]); // Re-bind when selectedFile or handleTabClose change

  const handleFileUpdate = (filePath) => {
    // Increment the refresh key to force FileViewer to reload
    setFileRefreshKey(prev => prev + 1);
  };

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      // Enter fullscreen
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen();
      } else if (elem.webkitRequestFullscreen) { // Safari
        elem.webkitRequestFullscreen();
      } else if (elem.msRequestFullscreen) { // IE11
        elem.msRequestFullscreen();
      }
      setIsFullscreen(true);
    } else {
      // Exit fullscreen
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) { // Safari
        document.webkitExitFullscreen();
      } else if (document.msExitFullscreen) { // IE11
        document.msExitFullscreen();
      }
      setIsFullscreen(false);
    }
  };

  // Listen for fullscreen changes (e.g., pressing ESC)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.msFullscreenElement
      );
      setIsFullscreen(isCurrentlyFullscreen);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('msfullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('msfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Check if the selected file is the initiative tracker
  const isInitiativeTracker = selectedFile?.name === 'Initiative Tracker.md';

  return (
    <div className={`file-explorer ${lightMode ? 'light-mode' : ''}`}>
      <div className="file-explorer-sidebar" style={{ width: isTreeCollapsed ? 0 : undefined, borderRight: isTreeCollapsed ? 'none' : undefined, overflow: 'hidden' }}>
        <FileTree
          ref={fileTreeRef}
          onFileSelect={handleFileSelect}
          lightMode={lightMode}
          advancedMode={advancedMode}
          onFileUpdate={handleFileUpdate}
          selectedFile={selectedFile}
          isCollapsed={false}
          onToggleCollapse={() => setIsTreeCollapsed(true)}
        />
      </div>
      <div className="file-explorer-main">
        <div className="file-explorer-header">
          {isTreeCollapsed && (
            <button
              onClick={() => setIsTreeCollapsed(false)}
              title="Show File Tree"
              style={{
                background: 'transparent',
                border: 'none',
                color: lightMode ? '#333' : '#ccc',
                fontSize: '16px',
                cursor: 'pointer',
                padding: '4px 8px',
                marginRight: 'auto',
              }}
            >
              ▶
            </button>
          )}
          <SearchBar onFileSelect={handleFileSelect} lightMode={lightMode} />
          {advancedMode && (
            <button 
              onClick={onToggleGmMode}
              title={gmMode ? "Switch to Player Mode" : "Switch to GM Mode"}
              style={{
                padding: '8px 16px',
                marginRight: '8px',
                background: gmMode 
                  ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
                  : (lightMode ? '#ddd' : '#3c3c3c'),
                color: gmMode ? '#fff' : (lightMode ? '#333' : '#ccc'),
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: gmMode ? 'bold' : 'normal',
                transition: 'all 0.2s',
                boxShadow: gmMode ? '0 2px 8px rgba(102, 126, 234, 0.4)' : 'none'
              }}
            >
              {gmMode ? '🎲 Player' : '🎯 GM'}
            </button>
          )}
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
          {advancedMode && (
            <button 
              className="fullscreen-toggle"
              onClick={toggleFullscreen}
              title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
              style={{
                padding: '8px 16px',
                marginRight: '8px',
                background: isFullscreen ? '#007acc' : (lightMode ? '#ddd' : '#3c3c3c'),
                color: isFullscreen ? '#fff' : (lightMode ? '#333' : '#ccc'),
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: isFullscreen ? 'bold' : 'normal',
                transition: 'all 0.2s'
              }}
            >
              {isFullscreen ? '⊗ Exit Fullscreen' : '⛶ Fullscreen'}
            </button>
          )}
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
            advancedMode={advancedMode}
          />
        </div>
      </div>
    </div>
  );
};

export default FileExplorer;
