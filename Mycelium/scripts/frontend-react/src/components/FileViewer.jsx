import React, { useState, useEffect } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import CharacterSheet from './CharacterSheet';
import BendingMove from './BendingMove';
import './FileViewer.css';

const FileViewer = ({ file, lightMode = false, onFileSelect }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [imageCache, setImageCache] = useState({});
  const [renderedHtml, setRenderedHtml] = useState('');
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkModalData, setLinkModalData] = useState({ searchTerm: '', matches: [] });

  // Determine file type
  const isMarkdown = file?.name.endsWith('.md');
  const isImage = file ? /\.(jpg|jpeg|png|gif|svg|webp)$/i.test(file.name) : false;
  const isHtml = file ? /\.(html|htm)$/i.test(file.name) : false;
  const isCharacterSheet = file ? file.name.toLowerCase().includes('character sheet') : false;
  const isBendingMove = file ? 
    (file.path && file.path.includes('Bending Rules -') && 
     !file.name.toLowerCase().includes('utility') &&
     !file.name.toLowerCase().includes('mechanics') &&
     !file.name.toLowerCase().includes('progression') &&
     !file.name.toLowerCase().includes('rules') &&
     !file.name.toLowerCase().includes('slot') &&
     isMarkdown) : false;

  useEffect(() => {
    if (file) {
      loadFileContent();
    } else {
      // Clear content when no file is selected
      setContent('');
      setRenderedHtml('');
    }
  }, [file]);

  // Use effect to render markdown when content changes
  useEffect(() => {
    const renderMarkdown = async () => {
      if (!content) {
        // Clear rendered HTML if content is empty
        setRenderedHtml('');
        return;
      }
      
      // Process Obsidian-style links
      const processedContent = await processObsidianLinks(content);
      
      // Configure marked options
      marked.setOptions({
        breaks: true,
        gfm: true,
      });
      
      // Parse markdown to HTML
      const rawHtml = marked.parse(processedContent);
      
      // Sanitize HTML
      return DOMPurify.sanitize(rawHtml);
    };

    if (isMarkdown) {
      renderMarkdown().then(html => {
        if (html !== undefined) {
          setRenderedHtml(html);
        }
      });
    }
  }, [content, isMarkdown]);

  // Function to resolve image paths by trying multiple locations
  const resolveImagePath = async (imageName) => {
    // Check cache first
    if (imageCache[imageName]) {
      return imageCache[imageName];
    }

    // Get the directory of the current file
    const fileDir = file.path.substring(0, file.path.lastIndexOf('/'));
    
    // Build possible paths
    const possiblePaths = [];

    // If the file is in "Shapeshifting Forms", look in "Shapeshifting Pics" at the Spirit level
    if (fileDir.includes('Spiritbending Moves/Shapeshifting Forms')) {
      // Go up to Spirit level and look in Shapeshifting Pics
      const spiritPath = fileDir.split('Spiritbending Moves')[0];
      possiblePaths.push(`${spiritPath}Shapeshifting Pics/${imageName}`);
    }

    // Add common relative paths
    possiblePaths.push(
      `${fileDir}/${imageName}`,
      `${fileDir}/../${imageName}`,
      `${fileDir}/../../${imageName}`,
      `${fileDir}/../../Shapeshifting Pics/${imageName}`,
      // Known image directories
      `Rules/Bending Rules/Spirit/Shapeshifting Pics/${imageName}`,
      `NPCs/${imageName}`,
      `visuals/${imageName}`,
      imageName // Fallback: just the filename
    );

    // Try each path until one works
    for (const path of possiblePaths) {
      try {
        const testUrl = `http://localhost:9002/player_root/${encodeURIComponent(path)}`;
        console.log(`Trying image path: ${path}`);
        const response = await fetch(testUrl, { method: 'HEAD' });
        if (response.ok) {
          console.log(`✓ Found image at: ${path}`);
          setImageCache(prev => ({ ...prev, [imageName]: testUrl }));
          return testUrl;
        }
      } catch (err) {
        // Continue trying other paths
      }
    }
    
    // Fallback: return the first attempt (even if it might 404)
    console.warn(`Could not resolve image: ${imageName}, using fallback: ${possiblePaths[0]}`);
    const fallbackUrl = `http://localhost:9002/player_root/${encodeURIComponent(possiblePaths[0])}`;
    return fallbackUrl;
  };

  // Process Obsidian-style links in markdown
  const processObsidianLinks = async (markdownText) => {
    // Replace Obsidian image embeds: ![[image.ext]]
    const imageEmbedRegex = /!\[\[([^\]]+?\.(png|jpg|jpeg|gif|svg|webp))\]\]/gi;
    
    let processedText = markdownText;
    const matches = [...markdownText.matchAll(imageEmbedRegex)];
    
    for (const match of matches) {
      const [fullMatch, imageName] = match;
      const imagePath = await resolveImagePath(imageName);
      // Replace with standard markdown image syntax
      processedText = processedText.replace(fullMatch, `![${imageName}](${imagePath})`);
    }

    // Replace Obsidian wiki links: [[link]] or [[link|display text]]
    // Convert to clickable links with a special data attribute
    processedText = processedText.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (match, linkTarget, displayText) => {
      const display = displayText || linkTarget;
      // Use a special format that we can identify after markdown rendering
      return `<a href="#" class="obsidian-link" data-file-name="${linkTarget.trim()}">${display.trim()}</a>`;
    });
    
    return processedText;
  };

  const loadFileContent = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setContent(''); // Clear content immediately when loading starts
    setRenderedHtml(''); // Clear rendered HTML immediately

    try {
      // Use the player_root endpoint - it returns JSON with {content, hash} for text files
      const response = await fetch(`http://localhost:9002/player_root/${encodeURIComponent(file.path)}`);
      if (response.ok) {
        const contentType = response.headers.get('content-type');
        
        // If it's JSON, extract the content field
        if (contentType && contentType.includes('application/json')) {
          const data = await response.json();
          setContent(data.content || '');
        } else {
          // For images and other files, just get the text
          const text = await response.text();
          setContent(text);
        }
      } else {
        setError('Failed to load file');
      }
    } catch (err) {
      setError('Error loading file: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Function to search for a file or folder by name
  const searchFileByName = async (fileName) => {
    try {
      // First, try to find it as a folder path
      const tryFolder = async (folderPath) => {
        try {
          const folderResponse = await fetch(
            `http://localhost:9002/player_root/${encodeURIComponent(folderPath)}`
          );
          
          if (folderResponse.ok) {
            const contentType = folderResponse.headers.get('content-type');
            
            // If it's JSON, it's a folder listing
            if (contentType && contentType.includes('application/json')) {
              const folderData = await folderResponse.json();
              
              // Check if it's a folder structure (can be files, entries, or an array)
              if (folderData.files || folderData.entries || Array.isArray(folderData)) {
                const items = folderData.files || folderData.entries || folderData;
                
                if (Array.isArray(items) && items.length > 0) {
                  // Sort files alphabetically and get the first one
                  // Filter out folders - check for isFolder, isDirectory, type === 'directory', or type === 'dir'
                  const sortedFiles = items
                    .filter(item => {
                      const isFolder = item.isFolder || item.isDirectory || item.type === 'directory' || item.type === 'dir';
                      return !isFolder && item.name;
                    })
                    .sort((a, b) => a.name.localeCompare(b.name));
                  
                  if (sortedFiles.length > 0) {
                    const firstFile = sortedFiles[0];
                    const firstFilePath = `${folderPath}/${firstFile.name}`;
                    onFileSelect({
                      name: firstFile.name,
                      path: firstFilePath
                    });
                    return true;
                  }
                }
              }
            }
          }
        } catch (err) {
          return false;
        }
        return false;
      };

      // Try common folder patterns for the name
      const folderPatterns = [
        fileName, // Direct folder name
        `PCs/${fileName}`, // PCs folder
        `NPCs/${fileName}`, // NPCs folder
        `Lotus/${fileName}`, // Lotus subfolder
        `NPCs/Lotus/${fileName}`, // Lotus in NPCs
      ];

      for (const pattern of folderPatterns) {
        if (await tryFolder(pattern)) {
          return;
        }
      }

      // If not found as folder, search for files and folders
      const response = await fetch(
        `http://localhost:9002/player_root/search?q=${encodeURIComponent(fileName)}`
      );
      
      if (response.ok) {
        const data = await response.json();
        const results = data.results || [];
        
        if (results.length > 0) {
          // First, check if any result has a folder with exact name match in path
          // Look for paths that contain /fileName/ or end with /fileName
          for (const result of results) {
            const pathSegments = result.path.replace(/^Player Root\//, '').split('/');
            
            // Check if any segment matches exactly (case-insensitive)
            for (let i = 0; i < pathSegments.length - 1; i++) { // -1 to exclude the file itself
              if (pathSegments[i].toLowerCase() === fileName.toLowerCase()) {
                // Build the folder path up to and including the matching segment
                const folderPath = pathSegments.slice(0, i + 1).join('/');
                
                // Try to open this folder
                if (await tryFolder(folderPath)) {
                  return;
                }
              }
            }
          }
          
          // Second, check for exact file name matches
          const exactMatch = results.find(r => {
            const resultName = r.path.split('/').pop();
            const baseName = resultName.replace(/\.[^/.]+$/, ''); // Remove extension
            return resultName.toLowerCase() === fileName.toLowerCase() || 
                   resultName.toLowerCase() === `${fileName}.md`.toLowerCase() ||
                   baseName.toLowerCase() === fileName.toLowerCase();
          });
          
          if (exactMatch) {
            const cleanPath = exactMatch.path.replace(/^Player Root\//, '');
            onFileSelect({
              name: exactMatch.path.split('/').pop(),
              path: cleanPath
            });
            return;
          }
          
          // No exact match found - show modal with nearest matches
          const nearestMatches = results.slice(0, 10).map(r => ({
            name: r.path.split('/').pop(),
            path: r.path.replace(/^Player Root\//, ''),
            fullPath: r.path
          }));
          
          setLinkModalData({
            searchTerm: fileName,
            matches: nearestMatches
          });
          setShowLinkModal(true);
          return;
        }
      }
      
      // No results at all
      setLinkModalData({
        searchTerm: fileName,
        matches: []
      });
      setShowLinkModal(true);
    } catch (err) {
      console.error('Error searching for file:', err);
    }
  };

  // Handle clicks on Obsidian-style links
  useEffect(() => {
    if (!renderedHtml || !onFileSelect) return;

    const handleLinkClick = (e) => {
      const target = e.target;
      if (target.classList.contains('obsidian-link')) {
        e.preventDefault();
        const fileName = target.getAttribute('data-file-name');
        if (fileName) {
          searchFileByName(fileName);
        }
      }
    };

    // Attach click handler to the document
    document.addEventListener('click', handleLinkClick);
    
    return () => {
      document.removeEventListener('click', handleLinkClick);
    };
  }, [renderedHtml, onFileSelect]);

  if (!file) {
    return (
      <div className="file-viewer-empty">
        <p>Select a file to view its contents</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="file-viewer-loading">
        <p>Loading file...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="file-viewer-error">
        <p>{error}</p>
      </div>
    );
  }

  // Render character sheet component if it's a character sheet file
  if (isCharacterSheet) {
    return <CharacterSheet file={file} lightMode={lightMode} />;
  }

  // Render bending move component if it's a bending move file
  if (isBendingMove) {
    return <BendingMove file={file} lightMode={lightMode} />;
  }

  return (
    <>
      <div className={`file-viewer ${lightMode ? 'light-mode' : ''}`}>
        <div className="file-viewer-header">
          <h2>{file.name}</h2>
          <span className="file-path">{file.path}</span>
        </div>
        <div className="file-viewer-content">
          {isImage ? (
            <img src={`http://localhost:9002/player_root/${encodeURIComponent(file.path)}`} alt={file.name} />
          ) : isHtml ? (
            <iframe 
              src={`http://localhost:9002/player_root/${encodeURIComponent(file.path)}`}
              title={file.name}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                minHeight: '600px'
              }}
            />
          ) : isMarkdown ? (
            <div 
              className="markdown-content" 
              dangerouslySetInnerHTML={{ __html: renderedHtml }}
            />
          ) : (
            <pre className="text-content">{content}</pre>
          )}
        </div>
      </div>

      {/* Link not found modal */}
      {showLinkModal && (
        <div className="link-modal-overlay" onClick={() => setShowLinkModal(false)}>
          <div className={`link-modal ${lightMode ? 'light-mode' : ''}`} onClick={(e) => e.stopPropagation()}>
            <div className="link-modal-header">
              <h3>No Exact Match Found</h3>
              <button className="link-modal-close" onClick={() => setShowLinkModal(false)}>×</button>
            </div>
            <div className="link-modal-content">
              <p>Could not find an exact match for: <strong>{linkModalData.searchTerm}</strong></p>
              {linkModalData.matches.length > 0 ? (
                <>
                  <p className="link-modal-subtitle">Nearest matches:</p>
                  <ul className="link-modal-matches">
                    {linkModalData.matches.map((match, index) => (
                      <li key={index} onClick={() => {
                        onFileSelect({
                          name: match.name,
                          path: match.path
                        });
                        setShowLinkModal(false);
                      }}>
                        <span className="match-name">{match.name}</span>
                        <span className="match-path">{match.fullPath}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="no-matches">No files found matching this search.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default FileViewer;
