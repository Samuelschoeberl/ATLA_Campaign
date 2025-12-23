import React, { useState, useEffect } from 'react';
import './Quicklinks.css';
import { API_BASE_URL } from '../config/api';
import { hexToRgba, getLighterColor } from '../utils/colorUtils';

const Quicklinks = ({ lightMode = false, onFileSelect }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fileColors, setFileColors] = useState({});

  useEffect(() => {
    loadQuicklinks();
    loadFileColors();
  }, []);

  const loadQuicklinks = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/player_root/Quicklinks.md`);
      if (response.ok) {
        const data = await response.json();
        setContent(data.content || '');
        setError(null);
      } else {
        setError('Failed to load Quicklinks');
      }
    } catch (err) {
      setError('Error loading Quicklinks: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadFileColors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/file-colors`);
      if (response.ok) {
        const data = await response.json();
        setFileColors(data.colors || {});
      }
    } catch (error) {
      console.error('Error loading file colors:', error);
    }
  };

  const parseQuicklinks = () => {
    if (!content) return { topLinks: [], characters: [] };

    const lines = content.trim().split('\n');
    const topLinks = [];
    const characters = [];
    let inTable = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Skip empty lines
      if (!line) continue;

      // Check for wikilinks at the top
      const wikilinkMatch = line.match(/\[\[([^\]]+)\]\]/);
      if (wikilinkMatch && !inTable) {
        topLinks.push(wikilinkMatch[1]);
        continue;
      }

      // Check if we're entering a table
      if (line.startsWith('|') && !inTable) {
        // Skip the header row
        if (line.toLowerCase().includes('characters')) {
          inTable = true;
          i++; // Skip separator line
          continue;
        }
      }

      // Parse character links in the table
      if (inTable && line.startsWith('|')) {
        const wikilinkInTable = line.match(/\[\[([^\]]+)\]\]/);
        if (wikilinkInTable) {
          characters.push(wikilinkInTable[1]);
        }
      }
    }

    return { topLinks, characters };
  };

  const handleLinkClick = async (linkName) => {
    console.log('Quicklinks: Clicking link:', linkName);
    try {
      // Search for the file
      const searchResponse = await fetch(
        `${API_BASE_URL}/player_root/search?q=${encodeURIComponent(linkName)}`
      );
      
      if (searchResponse.ok) {
        const searchData = await searchResponse.json();
        const results = searchData.results || [];
        console.log('Quicklinks: Search results:', results);
        
        // Look for exact filename match (case-insensitive)
        const fileNameLower = linkName.toLowerCase();
        // Replace underscores with spaces for comparison
        const fileNameWithSpaces = linkName.replace(/_/g, ' ').toLowerCase();
        
        // First, try exact match
        let exactMatch = results.find(result => {
          const pathParts = result.path.split('/');
          const resultFileName = pathParts[pathParts.length - 1];
          const resultFileNameLower = resultFileName.toLowerCase();
          
          // Check for exact match or exact match with .md extension
          return resultFileNameLower === fileNameLower || 
                 resultFileNameLower === `${fileNameLower}.md` ||
                 resultFileNameLower === fileNameWithSpaces ||
                 resultFileNameLower === `${fileNameWithSpaces}.md`;
        });
        
        // If no exact match, try to find character sheet files
        if (!exactMatch) {
          exactMatch = results.find(result => {
            const pathParts = result.path.split('/');
            const resultFileName = pathParts[pathParts.length - 1];
            const resultFileNameLower = resultFileName.toLowerCase();
            
            // Check for "[CharacterName] character sheet.md" or "[CharacterName] Character Sheet.md"
            return resultFileNameLower === `${fileNameLower} character sheet.md` ||
                   resultFileNameLower === `${fileNameWithSpaces} character sheet.md` ||
                   resultFileNameLower === `${fileNameLower}_character_sheet.md`;
          });
        }
        
        if (exactMatch) {
          console.log('Quicklinks: Found match:', exactMatch);
          // Extract the relative path (remove "Player Root/" prefix)
          const relativePath = exactMatch.path.replace(/^Player Root\//, '');
          const fileName = relativePath.split('/').pop();
          
          console.log('Quicklinks: Opening file:', { name: fileName, path: relativePath });
          onFileSelect({
            name: fileName,
            path: relativePath
          });
        } else {
          console.warn(`No exact match found for: ${linkName}`);
          alert(`Could not find file for: ${linkName}`);
        }
      }
    } catch (err) {
      console.error('Error navigating to link:', err);
      alert(`Error navigating to: ${linkName}`);
    }
  };

  if (loading) {
    return (
      <div className={`quicklinks-container ${lightMode ? 'light-mode' : ''}`}>
        <div className="quicklinks-loading">Loading Quicklinks...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`quicklinks-container ${lightMode ? 'light-mode' : ''}`}>
        <div className="quicklinks-error">{error}</div>
      </div>
    );
  }

  const { topLinks, characters } = parseQuicklinks();

  return (
    <div className={`quicklinks-container ${lightMode ? 'light-mode' : ''}`}>
      <div className="quicklinks-header">
        <h1>Quicklinks</h1>
      </div>

      {topLinks.length > 0 && (
        <div className="quicklinks-section">
          <h2>Quick Access</h2>
          <div className="quicklinks-grid">
            {topLinks.map((link, index) => (
              <button
                key={index}
                className="quicklink-button primary"
                onClick={() => handleLinkClick(link)}
              >
                <span className="quicklink-icon">🔗</span>
                <span className="quicklink-text">{link}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {characters.length > 0 && (
        <div className="quicklinks-section">
          <h2>Characters</h2>
          <div className="quicklinks-grid">
            {characters.map((character, index) => {
              // Get the character folder color (format: PCs/CharacterName/)
              const folderPath = `PCs/${character}/`;
              const characterColor = fileColors[folderPath] || '#3498db'; // default blue if not found
              const isUncolored = characterColor === '#e6e6e6';
              
              // Use the character color for background
              const backgroundColor = isUncolored 
                ? 'rgba(52, 152, 219, 0.2)' 
                : hexToRgba(characterColor, 0.35);
              const borderColor = isUncolored 
                ? 'rgba(52, 152, 219, 0.5)' 
                : `${characterColor}80`; // 50% opacity
              const hoverBackground = isUncolored
                ? 'rgba(52, 152, 219, 0.4)'
                : hexToRgba(getLighterColor(characterColor), 0.5);
              const hoverBorder = isUncolored
                ? 'rgba(52, 152, 219, 0.8)'
                : characterColor;
              
              return (
                <button
                  key={index}
                  className="quicklink-button character"
                  onClick={() => handleLinkClick(character)}
                  style={{
                    background: backgroundColor,
                    borderColor: borderColor,
                    '--hover-bg': hoverBackground,
                    '--hover-border': hoverBorder,
                    '--character-color': characterColor,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = hoverBackground;
                    e.currentTarget.style.borderColor = hoverBorder;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = backgroundColor;
                    e.currentTarget.style.borderColor = borderColor;
                  }}
                >
                  <span className="quicklink-icon">👤</span>
                  <span className="quicklink-text">{character}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default Quicklinks;
