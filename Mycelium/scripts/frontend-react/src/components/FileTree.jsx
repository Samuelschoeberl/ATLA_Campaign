import React, { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import './FileTree.css';
import { getLighterColor, hexToRgba } from '../utils/colorUtils';
import { API_BASE_URL } from '../config/api';

const FileTree = forwardRef(({ onFileSelect, onNavigate, currentPath, lightMode = false, advancedMode = false, onFileUpdate, selectedFile = null }, ref) => {
  const [rootItems, setRootItems] = useState([]);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [folderContents, setFolderContents] = useState({});
  const [loading, setLoading] = useState(false);
  const [fileColors, setFileColors] = useState({});
  const [generatingGraphs, setGeneratingGraphs] = useState(new Set());
  const [deletingFiles, setDeletingFiles] = useState(new Set());
  const [creatingFileIn, setCreatingFileIn] = useState(null);
  const [editingFile, setEditingFile] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [savingFile, setSavingFile] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    loadRootDirectory();
    loadFileColors();
  }, []);

  const loadFileColors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/file-colors`);
      if (response.ok) {
        const data = await response.json();
        const baseColors = data.colors || {};
        const overrides = data.custom_folder_colors || {};

        // Apply custom folder color overrides to the folder itself and all descendants
        const derivedColors = { ...baseColors };
        Object.entries(overrides).forEach(([characterName, color]) => {
          const prefix = `PCs/${characterName}/`;
          Object.keys(baseColors).forEach((key) => {
            if (key === prefix || key.startsWith(prefix)) {
              derivedColors[key] = color;
            }
          });
        });

        setFileColors(derivedColors);
      }
    } catch (error) {
      console.error('Error loading file colors:', error);
    }
  };

  const loadRootDirectory = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/player_root`);
      
      if (response.ok) {
        const data = await response.json();
        setRootItems(data.entries || []);
      }
    } catch (error) {
      console.error('Error loading root directory:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFolderContents = async (folderPath) => {
    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(folderPath)}`);
      
      if (response.ok) {
        const data = await response.json();
        setFolderContents(prev => ({
          ...prev,
          [folderPath]: data.entries || []
        }));
      }
    } catch (error) {
      console.error('Error loading folder contents:', error);
    }
  };

  const toggleFolder = async (folderPath) => {
    const newExpandedFolders = new Set(expandedFolders);
    
    if (newExpandedFolders.has(folderPath)) {
      // Collapse the folder
      newExpandedFolders.delete(folderPath);
    } else {
      // Expand the folder
      newExpandedFolders.add(folderPath);
      // Load contents if not already loaded
      if (!folderContents[folderPath]) {
        await loadFolderContents(folderPath);
      }
    }
    
    setExpandedFolders(newExpandedFolders);
  };

  // Expose method to expand folders for a given file path
  const expandToFile = async (filePath) => {
    // Split the path into parts
    const pathParts = filePath.split('/');
    
    // Remove the file name (last part) to get folder parts
    const folderParts = pathParts.slice(0, -1);
    
    // Build and expand each folder in the path
    const newExpandedFolders = new Set(expandedFolders);
    let currentPath = '';
    
    for (const part of folderParts) {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      
      // Add to expanded set
      newExpandedFolders.add(currentPath);
      
      // Load contents if not already loaded
      if (!folderContents[currentPath]) {
        await loadFolderContents(currentPath);
      }
    }
    
    setExpandedFolders(newExpandedFolders);
  };

  // Expose the expandToFile method to parent components via ref
  useImperativeHandle(ref, () => ({
    expandToFile
  }));

  const handleItemClick = (item, parentPath = '') => {
    const itemPath = parentPath ? `${parentPath}/${item.name}` : item.name;
    const isDirectory = item.type === 'dir' || item.type === 'directory';
    
    if (isDirectory) {
      toggleFolder(itemPath);
    } else {
      onFileSelect({
        name: item.name,
        path: itemPath,
        type: item.type
      });
    }
  };

  const handleGenerateGraphs = async (folderPath, event) => {
    event.stopPropagation(); // Prevent folder toggle when clicking the button
    
    const newGenerating = new Set(generatingGraphs);
    newGenerating.add(folderPath);
    setGeneratingGraphs(newGenerating);

    try {
      // Convert folderPath to the format expected by the backend
      // Backend expects paths relative to Player Root or prefixed with "Player Root/"
      const backendPath = `Player Root/${folderPath}`;
      
      const response = await fetch(`${API_BASE_URL}/api/generate-graphs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ folder: backendPath }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Graphs generated:', data);
        
        // Show more detailed success message
        const fileCount = data.generated ? data.generated.length : 0;
        alert(`✅ Graphs generated successfully for ${folderPath}!\n\n${fileCount} file(s) created.\n\nCheck the folder for the output HTML files.`);
      } else {
        const error = await response.json();
        console.error('Error generating graphs:', error);
        alert(`❌ Failed to generate graphs: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error generating graphs:', error);
      alert(`❌ Failed to generate graphs: ${error.message}`);
    } finally {
      const newGenerating = new Set(generatingGraphs);
      newGenerating.delete(folderPath);
      setGeneratingGraphs(newGenerating);
    }
  };

  const handleDeleteFile = async (filePath, event) => {
    event.stopPropagation(); // Prevent file selection when clicking the button
    
    // Get the file name from the path
    const fileName = filePath.split('/').pop();
    
    // Confirm deletion
    if (!confirm(`Are you sure you want to move "${fileName}" to the deleted folder?`)) {
      return;
    }
    
    const newDeleting = new Set(deletingFiles);
    newDeleting.add(filePath);
    setDeletingFiles(newDeleting);

    try {
      // Construct source and destination paths
      const sourcePath = `Player Root/${filePath}`;
      const destPath = `Player Root/deleted/deleted_${fileName}`;
      
      const response = await fetch(`${API_BASE_URL}/player_root/move`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          src: sourcePath,
          dst: destPath 
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('File moved to deleted:', data);
        
        // Show success message
        alert(`✅ "${fileName}" moved to deleted folder successfully!`);
        
        // Refresh the file tree by reloading the affected folder
        const parentPath = filePath.split('/').slice(0, -1).join('/');
        if (parentPath) {
          await loadFolderContents(parentPath);
        } else {
          await loadRootDirectory();
        }
      } else {
        const error = await response.json();
        console.error('Error deleting file:', error);
        alert(`❌ Failed to delete file: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      alert(`❌ Failed to delete file: ${error.message}`);
    } finally {
      const newDeleting = new Set(deletingFiles);
      newDeleting.delete(filePath);
      setDeletingFiles(newDeleting);
    }
  };

  const handleCreateFile = async (folderPath, event) => {
    event.stopPropagation(); // Prevent folder toggle when clicking the button
    
    // Prompt for filename
    const fileName = prompt('Enter the name for the new file (must end with .md):');
    
    if (!fileName) {
      return; // User cancelled
    }
    
    // Validate filename
    if (!fileName.endsWith('.md')) {
      alert('❌ Filename must end with .md');
      return;
    }
    
    if (fileName.includes('/') || fileName.includes('\\') || fileName.includes('..')) {
      alert('❌ Invalid filename. Cannot contain /, \\, or ..');
      return;
    }
    
    setCreatingFileIn(folderPath);

    try {
      // Construct folder path for the backend
      const backendPath = `Player Root/${folderPath}`;
      
      const response = await fetch(`${API_BASE_URL}/api/create-md-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          folderPath: backendPath,
          filename: fileName 
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('File created:', data);
        
        // Show success message
        alert(`✅ File "${fileName}" created successfully!`);
        
        // Refresh the folder contents to show the new file
        await loadFolderContents(folderPath);
        
        // Ensure the folder is expanded to show the new file
        const newExpandedFolders = new Set(expandedFolders);
        newExpandedFolders.add(folderPath);
        setExpandedFolders(newExpandedFolders);
      } else {
        const error = await response.json();
        console.error('Error creating file:', error);
        alert(`❌ Failed to create file: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error creating file:', error);
      alert(`❌ Failed to create file: ${error.message}`);
    } finally {
      setCreatingFileIn(null);
    }
  };

  const handleEditFile = async (filePath, event) => {
    event.stopPropagation(); // Prevent file selection when clicking the button
    
    try {
      // Fetch the file content
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
      
      if (response.ok) {
        const data = await response.json();
        setEditContent(data.content || '');
        setEditingFile(filePath);
      } else {
        const error = await response.json();
        console.error('Error loading file:', error);
        alert(`❌ Failed to load file: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error loading file:', error);
      alert(`❌ Failed to load file: ${error.message}`);
    }
  };

  const handleSaveFile = async () => {
    if (!editingFile) return;
    
    setSavingFile(true);
    
    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(editingFile)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: editContent }),
      });

      if (response.ok) {
        alert(`✅ File saved successfully!`);
        
        // Notify parent component that file was updated
        if (onFileUpdate) {
          onFileUpdate(editingFile);
        }
        
        setEditingFile(null);
        setEditContent('');
      } else {
        const error = await response.json();
        console.error('Error saving file:', error);
        alert(`❌ Failed to save file: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving file:', error);
      alert(`❌ Failed to save file: ${error.message}`);
    } finally {
      setSavingFile(false);
    }
  };

  const handleCloseEditor = () => {
    if (editContent !== '' && !confirm('You have unsaved changes. Are you sure you want to close?')) {
      return;
    }
    setEditingFile(null);
    setEditContent('');
  };

  const renderItem = (item, parentPath = '', depth = 0) => {
    const itemPath = parentPath ? `${parentPath}/${item.name}` : item.name;
    const isExpanded = expandedFolders.has(itemPath);
    const isFolder = item.type === 'dir' || item.type === 'directory';
    const children = isFolder ? folderContents[itemPath] : null;
    
    // Check if this is the currently selected file
    const isSelected = !isFolder && selectedFile && selectedFile.path === itemPath;
    
    // Get color from the file colors map
    // For folders, look up with trailing slash
    const colorKey = isFolder ? `${itemPath}/` : itemPath;
    const itemColor = fileColors[colorKey] || '#e6e6e6'; // default to light grey
    const isUncolored = itemColor === '#e6e6e6';
    
    // Adjust background color for selected file
    const backgroundColor = isSelected 
      ? (lightMode ? 'rgba(52, 152, 219, 0.4)' : 'rgba(52, 152, 219, 0.3)')
      : (isUncolored ? 'transparent' : hexToRgba(itemColor, 0.35));
    const hoverColor = isSelected
      ? (lightMode ? 'rgba(52, 152, 219, 0.6)' : 'rgba(52, 152, 219, 0.5)')
      : (isUncolored ? 'rgba(255, 255, 255, 0.1)' : hexToRgba(getLighterColor(itemColor), 0.5));

    return (
      <div key={itemPath} className="file-tree-item">
        <div 
          className={`file-tree-item-content ${isFolder ? 'folder' : 'file'} ${isSelected ? 'selected' : ''}`}
          onClick={() => handleItemClick(item, parentPath)}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer', 
            padding: '4px 8px',
            paddingLeft: `${8 + depth * 16}px`,
            background: backgroundColor,
            color: '#fff',
            fontSize: '14px',
            transition: 'background 0.2s',
            borderLeft: isSelected 
              ? '3px solid #3498db' 
              : (isUncolored ? 'none' : `3px solid ${itemColor}`),
            fontWeight: isSelected ? '600' : (isFolder ? '500' : '400'),
            boxShadow: isSelected ? 'inset 0 0 8px rgba(52, 152, 219, 0.3)' : 'none'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = hoverColor;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = backgroundColor;
          }}
        >
          {isFolder && (
            <span className="folder-arrow" style={{ 
              marginRight: '4px',
              fontSize: '10px',
              transition: 'transform 0.2s',
              transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              display: 'inline-block',
              color: getLighterColor(itemColor)
            }}>
              ▶
            </span>
          )}
          <span className="file-tree-icon" style={{ 
            marginRight: '8px',
            fontSize: '16px',
            fontWeight: item.name.endsWith('.md') ? 'bold' : 'normal',
            color: item.name.match(/\.(html|htm)$/i) ? '#ff8c00' : 
                   item.name.endsWith('.md') ? '#569cd6' : 'inherit'
          }}>
            {isFolder ? (isExpanded ? '📂' : '📁') : 
             item.name.match(/\.(html|htm)$/i) ? '<>' : 
             item.name.endsWith('.md') ? '⬇' : '📄'}
          </span>
          <span className="file-tree-name" style={{ 
            fontSize: '13px',
            fontWeight: isFolder ? '500' : '400',
            flex: 1
          }}>
            {item.name}
          </span>
          {advancedMode && isFolder && (
            <button
              onClick={(e) => handleGenerateGraphs(itemPath, e)}
              disabled={generatingGraphs.has(itemPath)}
              title="Create/Update Graphs for this folder"
              style={{
                padding: '2px 8px',
                marginLeft: '8px',
                background: generatingGraphs.has(itemPath) ? '#555' : '#007acc',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                cursor: generatingGraphs.has(itemPath) ? 'wait' : 'pointer',
                fontSize: '11px',
                fontWeight: 'bold',
                opacity: generatingGraphs.has(itemPath) ? 0.6 : 1,
                transition: 'opacity 0.2s'
              }}
            >
              {generatingGraphs.has(itemPath) ? '⏳' : '📊'}
            </button>
          )}
          {advancedMode && isFolder && (
            <button
              onClick={(e) => handleCreateFile(itemPath, e)}
              disabled={creatingFileIn === itemPath}
              title="Create new file in this folder"
              style={{
                padding: '2px 8px',
                marginLeft: '8px',
                background: creatingFileIn === itemPath ? '#555' : '#4caf50',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                cursor: creatingFileIn === itemPath ? 'wait' : 'pointer',
                fontSize: '11px',
                fontWeight: 'bold',
                opacity: creatingFileIn === itemPath ? 0.6 : 1,
                transition: 'opacity 0.2s'
              }}
            >
              {creatingFileIn === itemPath ? '⏳' : '➕'}
            </button>
          )}
          {!isFolder && item.name.endsWith('.md') && (
            <button
              onClick={(e) => handleEditFile(itemPath, e)}
              title="Edit this file"
              style={{
                padding: '2px 8px',
                marginLeft: '8px',
                background: '#ff9800',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 'bold',
                transition: 'opacity 0.2s'
              }}
            >
              ✏️
            </button>
          )}
          {advancedMode && !isFolder && (
            <button
              onClick={(e) => handleDeleteFile(itemPath, e)}
              disabled={deletingFiles.has(itemPath)}
              title="Move file to deleted folder"
              style={{
                padding: '2px 8px',
                marginLeft: '8px',
                background: deletingFiles.has(itemPath) ? '#555' : '#d32f2f',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                cursor: deletingFiles.has(itemPath) ? 'wait' : 'pointer',
                fontSize: '11px',
                fontWeight: 'bold',
                opacity: deletingFiles.has(itemPath) ? 0.6 : 1,
                transition: 'opacity 0.2s'
              }}
            >
              {deletingFiles.has(itemPath) ? '⏳' : '🗑️'}
            </button>
          )}
        </div>
        
        {isFolder && isExpanded && children && (
          <div className="file-tree-children">
            {children.map(child => renderItem(child, itemPath, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`file-tree ${isCollapsed ? 'collapsed' : ''} ${lightMode ? 'light-mode' : ''}`} style={{ 
      background: lightMode ? '#f5f5f5' : '#252526', 
      color: lightMode ? '#333' : '#ccc', 
      height: '100%',
      width: isCollapsed ? '50px' : '300px',
      minWidth: isCollapsed ? '50px' : '250px',
      maxWidth: isCollapsed ? '50px' : '500px',
      display: 'flex',
      flexDirection: 'column',
      transition: 'all 0.3s ease'
    }}>
      <div className="file-tree-header" style={{
        padding: '16px',
        background: lightMode ? '#e8e8e8' : '#2d2d30',
        borderBottom: lightMode ? '1px solid #ccc' : '1px solid #444',
        fontSize: '16px',
        fontWeight: 'bold',
        color: '#fff',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        cursor: 'pointer'
      }}
      onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <h3 style={{ margin: 0, fontSize: '16px' }}>Files</h3>
        <button 
          className="collapse-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsCollapsed(!isCollapsed);
          }}
          aria-label={isCollapsed ? "Expand" : "Collapse"}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#fff',
            fontSize: '16px',
            cursor: 'pointer',
            padding: '4px 8px'
          }}
        >
          {isCollapsed ? '▶' : '◀'}
        </button>
      </div>
      {!isCollapsed && (
        <div className="file-tree-content" style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px 0'
        }}>
          {loading ? (
            <div className="loading" style={{ padding: '16px', color: '#888' }}>Loading...</div>
          ) : rootItems.length === 0 ? (
            <div className="loading" style={{ padding: '16px', color: '#888' }}>No items found</div>
          ) : (
            <div className="file-tree-items">
              {rootItems.map(item => renderItem(item, '', 0))}
            </div>
          )}
        </div>
      )}
      
      {/* File Editor Modal */}
      {editingFile && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000,
          }}
          onClick={handleCloseEditor}
        >
          <div
            style={{
              background: lightMode ? '#fff' : '#1e1e1e',
              borderRadius: '8px',
              padding: '24px',
              width: '80%',
              maxWidth: '800px',
              height: '80%',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}>
              <h3 style={{
                margin: 0,
                color: lightMode ? '#333' : '#fff',
                fontSize: '18px',
              }}>
                Edit: {editingFile.split('/').pop()}
              </h3>
              <button
                onClick={handleCloseEditor}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: lightMode ? '#333' : '#fff',
                  fontSize: '24px',
                  cursor: 'pointer',
                  padding: '0 8px',
                }}
              >
                ✖
              </button>
            </div>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              style={{
                flex: 1,
                background: lightMode ? '#f5f5f5' : '#252526',
                color: lightMode ? '#333' : '#ccc',
                border: `1px solid ${lightMode ? '#ccc' : '#444'}`,
                borderRadius: '4px',
                padding: '12px',
                fontSize: '14px',
                fontFamily: 'monospace',
                resize: 'none',
                marginBottom: '16px',
              }}
            />
            <div style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '12px',
            }}>
              <button
                onClick={handleCloseEditor}
                style={{
                  padding: '10px 20px',
                  background: lightMode ? '#ddd' : '#3c3c3c',
                  color: lightMode ? '#333' : '#ccc',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveFile}
                disabled={savingFile}
                style={{
                  padding: '10px 20px',
                  background: savingFile ? '#555' : '#007acc',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: savingFile ? 'wait' : 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold',
                }}
              >
                {savingFile ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

export default FileTree;
