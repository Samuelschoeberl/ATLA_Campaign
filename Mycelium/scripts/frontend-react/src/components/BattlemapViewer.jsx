import React, { useEffect, useMemo, useState, useRef } from 'react';
import './BattlemapViewer.css';
import { API_BASE_URL } from '../config/api';
import PixelAvatar from './PixelAvatar';
import TokenLibrary from './TokenLibrary';
import { normalizeAvatarMatrix } from '../utils/avatarUtils';

/**
 * HexBattlemapViewer - Hex-grid based battlemap with token placement and drawing tools
 * Supports:
 * - Custom grid size (rows/cols)
 * - Background image upload
 * - Character token placement with avatars
 * - Drawing tools (paint, eraser, sphere, cone, line)
 * - Measurement tool
 * - Token management and movement
 * - Animated effects (fire, ice, earth, air, poison, lightning, darkness, healing)
 * - Real-time synchronization
 */

// Improved hex patterns for AOE shapes
const AREA_PATTERNS = {
  sphere1: {
    name: 'Sphere (1 hex radius)',
    pattern: [
      { hexes: [{ row: 0, col: 0 }] }
    ]
  },
  sphere2: {
    name: 'Sphere (2 hex radius)',
    pattern: [
      { hexes: [
        { row: -1, col: -1 }, { row: -1, col: 0 },
        { row: 0, col: -1 }, { row: 0, col: 0 }, { row: 0, col: 1 },
        { row: 1, col: 0 }, { row: 1, col: 1 }
      ]}
    ]
  },
  sphere3: {
    name: 'Sphere (3 hex radius)',
    pattern: [
      { hexes: [
        { row: -2, col: -1 }, { row: -2, col: 0 },
        { row: -1, col: -2 }, { row: -1, col: -1 }, { row: -1, col: 0 }, { row: -1, col: 1 },
        { row: 0, col: -2 }, { row: 0, col: -1 }, { row: 0, col: 0 }, { row: 0, col: 1 }, { row: 0, col: 2 },
        { row: 1, col: -1 }, { row: 1, col: 0 }, { row: 1, col: 1 }, { row: 1, col: 2 },
        { row: 2, col: 0 }, { row: 2, col: 1 }
      ]}
    ]
  },
  cone: {
    name: 'Cone (3 hex)',
    pattern: [
      { hexes: [
        { row: 0, col: 0 },
        { row: 1, col: -1 }, { row: 1, col: 0 },
        { row: 2, col: -1 }, { row: 2, col: 0 }, { row: 2, col: 1 }
      ]}
    ]
  },
};

// Effect presets with enhanced animation patterns and visual styles
const EFFECT_PRESETS = {
  fire: {
    name: '🔥 Fire',
    colors: ['#ff6b1a', '#ffaa00', '#ff4444', '#ff8800', '#ff3300'],
    animation: 'flicker',
    glowColor: 'rgba(255, 100, 0, 0.6)',
    pattern: 'chaos',
    emoji: '🔥',
    gradient: 'radial-gradient(circle, #ffaa00 0%, #ff6b1a 50%, #ff3300 100%)'
  },
  ice: {
    name: '❄️ Ice',
    colors: ['#88ccff', '#ccffff', '#66bbee', '#aae6ff', '#5599dd'],
    animation: 'pulse',
    glowColor: 'rgba(136, 204, 255, 0.5)',
    pattern: 'crystallize',
    emoji: '❄️',
    gradient: 'linear-gradient(135deg, #ccffff 0%, #88ccff 50%, #5599dd 100%)'
  },
  poison: {
    name: '☠️ Poison',
    colors: ['#9d4edd', '#c77dff', '#7b2cbf', '#b185db', '#8b45c7'],
    animation: 'bubble',
    glowColor: 'rgba(157, 78, 221, 0.5)',
    pattern: 'toxic',
    emoji: '☠️',
    gradient: 'radial-gradient(circle, #c77dff 0%, #9d4edd 50%, #7b2cbf 100%)'
  },
  lightning: {
    name: '⚡ Lightning',
    colors: ['#ffeb3b', '#fff176', '#ffd54f', '#ffe082', '#ffdd33'],
    animation: 'spark',
    glowColor: 'rgba(255, 235, 59, 0.6)',
    pattern: 'electric',
    emoji: '⚡',
    gradient: 'linear-gradient(45deg, #ffe082 0%, #ffeb3b 50%, #ffdd33 100%)'
  },
  earth: {
    name: '🪨 Earth',
    colors: ['#8b6f47', '#a0826d', '#6f5436', '#9a7b5a', '#705442'],
    animation: 'static',
    glowColor: 'rgba(139, 111, 71, 0.5)',
    pattern: 'boulder',
    emoji: '🪨',
    gradient: 'linear-gradient(180deg, #a0826d 0%, #8b6f47 50%, #6f5436 100%)'
  },
  air: {
    name: '🌪️ Air',
    colors: ['#e6f3ff', '#d0e8ff', '#ffd9a8', '#ffe5c2', '#c0dcf0'],
    animation: 'swirl',
    glowColor: 'rgba(230, 243, 255, 0.4)',
    pattern: 'vortex',
    emoji: '🌪️',
    gradient: 'conic-gradient(from 45deg, #e6f3ff, #ffd9a8, #d0e8ff, #ffe5c2, #e6f3ff)'
  },
  darkness: {
    name: '🌑 Darkness',
    colors: ['#1a1a1a', '#2a2a2a', '#0a0a0a', '#151515', '#000000'],
    animation: 'wave',
    glowColor: 'rgba(0, 0, 0, 0.9)',
    pattern: 'shadow',
    emoji: '🌑',
    gradient: 'radial-gradient(circle, #2a2a2a 0%, #1a1a1a 50%, #000000 100%)'
  },
  healing: {
    name: '✨ Healing',
    colors: ['#ffdd88', '#ffffaa', '#ffee99', '#ffcc77', '#ffe68c'],
    animation: 'shimmer',
    glowColor: 'rgba(255, 230, 150, 0.6)',
    pattern: 'radiance',
    emoji: '✨',
    gradient: 'radial-gradient(circle, #ffffaa 0%, #ffee99 50%, #ffdd88 100%)'
  },
  water: {
    name: '💧 Water',
    colors: ['#4da6ff', '#66b3ff', '#3399ff', '#80c1ff', '#3d8fd9'],
    animation: 'flow',
    glowColor: 'rgba(77, 166, 255, 0.5)',
    pattern: 'ripple',
    emoji: '💧',
    gradient: 'linear-gradient(180deg, #80c1ff 0%, #4da6ff 50%, #3d8fd9 100%)'
  },
  blood: {
    name: '🩸 Blood',
    colors: ['#8b0000', '#a30000', '#700000', '#950000', '#600000'],
    animation: 'drip',
    glowColor: 'rgba(139, 0, 0, 0.6)',
    pattern: 'splatter',
    emoji: '🩸',
    gradient: 'radial-gradient(circle, #a30000 0%, #8b0000 50%, #600000 100%)'
  },
  none: {
    name: '⬡ Solid',
    colors: null,
    animation: 'none',
    glowColor: null,
    pattern: 'solid',
    emoji: '⬡',
    gradient: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)'
  }
};


const BattlemapViewer = ({ filePath, content, advancedMode = false }) => {
  // Coordinate conversion functions (odd-r offset <-> cube coordinates)
  const offsetToCube = (row, col) => {
    const q = col - (row - (row & 1)) / 2;
    const r = row;
    const s = -q - r;
    return { q, r, s };
  };
  
  const cubeToOffset = (q, r, s) => {
    const col = q + (r - (r & 1)) / 2;
    const row = r;
    return { row, col };
  };

  // Graph-based hex grid conversion functions
  // Converts the 2D array hexGrid to a graph where each node has neighbors
  // KEY OPTIMIZATION: Only stores filled/painted hexes (sparse representation)
  const gridToGraphData = (hexGrid, gridSize) => {
    const nodes = {};
    const directions = ['NW', 'NE', 'E', 'SE', 'SW', 'W']; // Six hex directions
    
    // Helper to get neighbors inline (flat-top hex, odd-r offset)
    const getNeighborsInline = (row, col) => {
      const isOddRow = row % 2 === 1;
      const offsets = isOddRow
        ? [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [0, -1]] // NW, NE, E, SE, SW, W for odd rows
        : [[-1, -1], [-1, 0], [0, 1], [1, 0], [1, -1], [0, -1]]; // NW, NE, E, SE, SW, W for even rows
      
      return offsets.map(([dr, dc]) => ({
        row: row + dr,
        col: col + dc
      }));
    };
    
    for (let row = 0; row < gridSize.rows; row++) {
      for (let col = 0; col < gridSize.cols; col++) {
        const cell = hexGrid[row]?.[col];
        
        // OPTIMIZATION: Skip empty/unfilled hexes to save space
        if (!cell || !cell.filled) continue;
        
        const nodeId = `${row},${col}`;
        
        // Get the 6 neighbors
        const neighbors = getNeighborsInline(row, col);
        const neighborMap = {};
        
        neighbors.forEach((neighbor, idx) => {
          const { row: nRow, col: nCol } = neighbor;
          // Only add neighbor if it's within bounds
          if (nRow >= 0 && nRow < gridSize.rows && nCol >= 0 && nCol < gridSize.cols) {
            neighborMap[directions[idx]] = `${nRow},${nCol}`;
          }
        });
        
        nodes[nodeId] = {
          id: nodeId,
          row,
          col,
          neighbors: neighborMap,
          data: {
            filled: cell.filled,
            color: cell.color,
            effect: cell.effect,
            animationOffset: cell.animationOffset,
            paintedAt: cell.paintedAt
          }
        };
      }
    }
    
    return nodes;
  };
  
  // Converts graph back to 2D array format
  const graphDataToGrid = (graphData, gridSize) => {
    const grid = initializeHexGrid(gridSize.rows, gridSize.cols);
    
    Object.values(graphData).forEach(node => {
      const { row, col, data } = node;
      if (grid[row] && grid[row][col]) {
        grid[row][col] = { ...data };
      }
    });
    
    return grid;
  };
  
  // Grid state
  const [gridSize, setGridSize] = useState({ rows: 10, cols: 10 });
  const [pendingGridSize, setPendingGridSize] = useState({ rows: 10, cols: 10 });
  const [hexGrid, setHexGrid] = useState([]);
  const [hexSize, setHexSize] = useState(40);
  
  // Background image state
  const [backgroundUrl, setBackgroundUrl] = useState('');
  const [imageOptions, setImageOptions] = useState([]);
  const [selectedImage, setSelectedImage] = useState('');
  const [imageDimensions, setImageDimensions] = useState({ width: 800, height: 800 }); // Actual image dimensions
  
  // Drawing tools state
  const [currentTool, setCurrentTool] = useState('paint'); // paint, eraser, measure, sphere, cone, line, token, aura, debug
  const [currentEffect, setCurrentEffect] = useState('none'); // Effect preset key
  const [brushColor, setBrushColor] = useState('#ff6b6b');
  const [isPainting, setIsPainting] = useState(false);
  const [paintMode, setPaintMode] = useState(false); // false = erase
  
  // Debug tool state
  const [selectedHexInfo, setSelectedHexInfo] = useState(null); // { row, col, neighbors, data }
  
  // Measurement tool state
  const [measureStart, setMeasureStart] = useState(null); // { row, col }
  const [measureEnd, setMeasureEnd] = useState(null); // { row, col }
  const [measureDistance, setMeasureDistance] = useState(null); // number
  const [showMeasurement, setShowMeasurement] = useState(false);
  
  // Line tool state
  const [lineStart, setLineStart] = useState(null); // { row, col }
  
  // Area effect tool state (sphere/cone)
  const [areaOrigin, setAreaOrigin] = useState(null); // { row, col }
  const [showAreaInput, setShowAreaInput] = useState(false);
  const [areaRange, setAreaRange] = useState('');
  const [areaDirection, setAreaDirection] = useState(null); // { row, col } for cone first direction hex
  const [areaDirection2, setAreaDirection2] = useState(null); // { row, col } for cone second direction hex
  const [showDirectionSelect, setShowDirectionSelect] = useState(false);
  const [auraTokenId, setAuraTokenId] = useState(null); // For aura tool
  const [auraOutlineColor, setAuraOutlineColor] = useState('#ff6b6b'); // Aura outline color
  const [auraMoveHexes, setAuraMoveHexes] = useState(false); // Whether aura should move underlying hexes
  
  // Animation state
  const [animationFrame, setAnimationFrame] = useState(0);
  const [shadeIntensity, setShadeIntensity] = useState(0.3); // 0-1, controls color variation
  const [opacityIntensity, setOpacityIntensity] = useState(0.3); // 0-1, controls opacity variation
  
  // Fade effect state
  const [fadeEnabled, setFadeEnabled] = useState(false);
  const [fadeSeconds, setFadeSeconds] = useState(3);
  
  // Token state
  const [tokens, setTokens] = useState([]); // { id, row, col, name, avatar, color, aura }
  const [selectedToken, setSelectedToken] = useState(null);
  const [draggedToken, setDraggedToken] = useState(null);
  
  // Character data for token creation
  const [availableCharacters, setAvailableCharacters] = useState([]);
  const [enemyTokens, setEnemyTokens] = useState([
    { name: 'Bandit', icon: '🗡️', color: '#c0392b' },
    { name: 'Guard', icon: '🛡️', color: '#7f8c8d' },
    { name: 'Fire Nation Soldier', icon: '🔥', color: '#e74c3c' },
    { name: 'Earth Kingdom Soldier', icon: '🪨', color: '#8b6f47' },
    { name: 'Water Tribe Warrior', icon: '💧', color: '#3498db' },
    { name: 'Spirit', icon: '👻', color: '#9b59b6' },
    { name: 'Beast', icon: '🐺', color: '#34495e' },
    { name: 'Elite', icon: '⚔️', color: '#e67e22' }
  ]);
  
  // Undo history state (stores last 5 states)
  const [history, setHistory] = useState([]);
  
  // UI state
  const [scale, setScale] = useState(1.0);
  const [showTokenPanel, setShowTokenPanel] = useState(false);
  const [showToolbar, setShowToolbar] = useState(true);
  const [showDrawingTools, setShowDrawingTools] = useState(true);
  
  // Watcher Mode state
  const [watcherMode, setWatcherMode] = useState(false);
  const [defaultCameraScale, setDefaultCameraScale] = useState(1.0);
  const [preWatcherScale, setPreWatcherScale] = useState(1.0); // Store scale before entering watcher mode
  const [watcherRotation, setWatcherRotation] = useState(0); // Rotation angle for watcher mode (0 or 90 degrees)
  const [watcherDefaultView, setWatcherDefaultView] = useState({ scale: 1.0, rotation: 0 }); // Store the calculated optimal view
  const [showCameraPanel, setShowCameraPanel] = useState(false); // Toggle for camera control panel
  
  // Sync state
  const [lastSyncTime, setLastSyncTime] = useState(Date.now());
  const [isSyncing, setIsSyncing] = useState(false);
  const saveTimeoutRef = useRef(null);
  const lastSavedStateRef = useRef(null);
  const isUpdatingFromSyncRef = useRef(false); // Track if updates are from sync
  const previousImageNameRef = useRef(null); // Track previous image name for comparison
  
  // Refs for current state values (used in sync to avoid stale closures)
  const gridSizeRef = useRef(gridSize);
  const hexGridRef = useRef(hexGrid);
  const tokensRef = useRef(tokens);
  const selectedImageRef = useRef(selectedImage);
  const hexSizeRef = useRef(hexSize);
  const lastSyncTimeRef = useRef(lastSyncTime);
  
  const canvasRef = useRef(null);
  const areaRangeInputRef = useRef(null);
  
  // Keep refs in sync with state
  useEffect(() => {
    gridSizeRef.current = gridSize;
    // Also sync pendingGridSize to match actual gridSize when it changes
    setPendingGridSize(gridSize);
  }, [gridSize]);
  
  useEffect(() => {
    hexGridRef.current = hexGrid;
  }, [hexGrid]);
  
  useEffect(() => {
    tokensRef.current = tokens;
  }, [tokens]);
  
  useEffect(() => {
    selectedImageRef.current = selectedImage;
  }, [selectedImage]);
  
  useEffect(() => {
    hexSizeRef.current = hexSize;
  }, [hexSize]);
  
  useEffect(() => {
    lastSyncTimeRef.current = lastSyncTime;
  }, [lastSyncTime]);

  // Auto-focus the area range input when it appears
  useEffect(() => {
    if (showAreaInput && areaRangeInputRef.current) {
      // Use setTimeout to ensure the DOM has fully rendered
      setTimeout(() => {
        if (areaRangeInputRef.current) {
          areaRangeInputRef.current.focus();
          areaRangeInputRef.current.select();
        }
      }, 0);
    }
  }, [showAreaInput]);

  // Reset debug tool when leaving advanced mode
  useEffect(() => {
    if (!advancedMode) {
      if (currentTool === 'debug') {
        setCurrentTool('paint');
      }
      setSelectedHexInfo(null);
    }
  }, [advancedMode, currentTool]);

  // Directory path for images
  const dirPath = useMemo(() => {
    if (!filePath || !filePath.includes('/')) return '';
    const parts = filePath.split('/');
    parts.pop();
    return parts.join('/');
  }, [filePath]);

  // Animation loop for effects
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationFrame(prev => (prev + 1) % 60); // 60 frame cycle
      
      // Handle fade effect
      if (fadeEnabled && fadeSeconds > 0) {
        const fadeMs = fadeSeconds * 1000;
        const now = Date.now();
        
        setHexGrid(prev => {
          let hasChanges = false;
          const updated = prev.map(row => 
            row.map(cell => {
              if (cell.filled && cell.paintedAt && (now - cell.paintedAt >= fadeMs)) {
                hasChanges = true;
                return {
                  ...cell,
                  filled: false,
                  paintedAt: null
                };
              }
              return cell;
            })
          );
          return hasChanges ? updated : prev;
        });
      }
    }, 100); // Update every 100ms
    
    return () => clearInterval(interval);
  }, [fadeEnabled, fadeSeconds]);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      if (!document.fullscreenElement && watcherMode) {
        // User exited fullscreen manually (e.g., with ESC key)
        setWatcherMode(false);
      }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, [watcherMode]);

  // Handle background image changes - save current and load new hex grid
  useEffect(() => {
    const handleImageChange = async () => {
      const currentImageName = selectedImage?.name;
      const prevImageName = previousImageNameRef.current;

      console.log('🔍 Image change detected:', { currentImageName, prevImageName });

      // Skip if no change
      if (currentImageName === prevImageName) {
        console.log('ℹ️ No image change, skipping');
        return;
      }

      // Save hex grid for previous image (if it exists and not initial load)
      if (prevImageName) {
        console.log('🔄 Background image changed, saving hex grid for:', prevImageName);
        await saveHexGridForImage(prevImageName);
      }

      // Load hex grid for new image (if it exists)
      if (currentImageName) {
        console.log('🔄 Loading hex grid for new image:', currentImageName);
        const loadedData = await loadHexGridForImage(currentImageName);

        if (loadedData) {
          // Apply loaded hex grid data
          isUpdatingFromSyncRef.current = true; // Prevent triggering auto-save

          if (loadedData.format === 'graph' && loadedData.hexGraph) {
            const newGrid = graphDataToGrid(loadedData.hexGraph, loadedData.gridSize);
            setHexGrid(newGrid);
            console.log('✅ Applied graph format hex grid');
          } else if (loadedData.hexGrid) {
            setHexGrid(loadedData.hexGrid);
            console.log('✅ Applied array format hex grid');
          }

          if (loadedData.gridSize) {
            setGridSize(loadedData.gridSize);
            console.log('✅ Applied grid size:', loadedData.gridSize);
          }
          if (loadedData.tokens) {
            setTokens(loadedData.tokens);
            console.log('✅ Applied tokens:', loadedData.tokens.length);
          }
          if (loadedData.hexSize) {
            setHexSize(loadedData.hexSize);
            console.log('✅ Applied hex size:', loadedData.hexSize);
          }

          console.log('✅ Hex grid data loaded and applied for:', currentImageName);
        } else {
          // No saved hex grid found, calculate optimal grid size based on image dimensions
          console.log('ℹ️ No saved hex grid for', currentImageName, ', calculating grid size from image dimensions');
          isUpdatingFromSyncRef.current = true;
          
          // Calculate grid size that covers image + 10 hex buffer on each side
          const optimalGridSize = calculateGridSizeForImage(
            imageDimensions.width, 
            imageDimensions.height, 
            hexSize
          );
          
          setGridSize(optimalGridSize);
          const freshGrid = initializeHexGrid(optimalGridSize.rows, optimalGridSize.cols);
          setHexGrid(freshGrid);
          setTokens([]);
          console.log('✅ Fresh grid initialized with size:', optimalGridSize);
        }
      } else if (!currentImageName && prevImageName) {
        // Image was removed (set to None)
        console.log('ℹ️ Background image removed, keeping current hex grid');
      }

      // Update the previous image reference
      previousImageNameRef.current = currentImageName;
    };

    handleImageChange();
  }, [selectedImage]);

  // Initialize hex grid with effect support
  const initializeHexGrid = (rows, cols) => {
    const grid = [];
    for (let r = 0; r < rows; r++) {
      const row = [];
      for (let c = 0; c < cols; c++) {
        row.push({ 
          filled: false, 
          color: '#3498db',
          effect: 'none',
          animationOffset: Math.random() * 10, // Random offset for variety
          paintedAt: null, // Timestamp when cell was painted (for fade effect)
          auraTokenId: null // ID of token this hex is an aura tile for
        });
      }
      grid.push(row);
    }
    return grid;
  };

  // Get hex grid filename for a specific background image
  const getHexGridFilename = (imageName) => {
    if (!imageName || !dirPath) {
      console.log('⚠️ getHexGridFilename: missing imageName or dirPath', { imageName, dirPath });
      return null;
    }
    // Remove extension from image name and add _hexgrid.json
    const baseName = imageName.replace(/\.[^/.]+$/, '');
    const fullPath = `${dirPath}/${baseName}_hexgrid.json`;
    console.log('📝 Hex grid path:', fullPath);
    return fullPath;
  };

  // Save hex grid data for current background image
  const saveHexGridForImage = async (imageName) => {
    if (!imageName) return;
    
    const hexGridPath = getHexGridFilename(imageName);
    if (!hexGridPath) return;

    const hexGridData = {
      format: 'graph',
      version: '2.0',
      gridSize,
      hexGraph: gridToGraphData(hexGrid, gridSize),
      tokens,
      hexSize,
      lastModified: Date.now()
    };

    console.log('💾 Saving hex grid for image:', imageName, 'to:', hexGridPath);

    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(hexGridPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: JSON.stringify(hexGridData, null, 2)
        })
      });

      if (response.ok) {
        console.log('✅ Hex grid saved successfully for:', imageName);
      } else {
        console.error('❌ Failed to save hex grid:', response.status);
      }
    } catch (err) {
      console.error('❌ Error saving hex grid:', err);
    }
  };

  // Calculate grid size that covers image dimensions plus 10 hex buffer on each side
  const calculateGridSizeForImage = (imageWidth, imageHeight, hexSize) => {
    const hexWidth = hexSize * Math.sqrt(3);
    const hexHeight = hexSize * 2;
    const vertSpacing = hexSize * 1.5;
    
    // Calculate how many hexes fit in the image dimensions
    const hexesInImageWidth = Math.ceil(imageWidth / hexWidth);
    const hexesInImageHeight = Math.ceil(imageHeight / vertSpacing);
    
    // Add 10 hexes buffer on each side (20 total per dimension)
    const cols = hexesInImageWidth + 20;
    const rows = hexesInImageHeight + 20;
    
    console.log(`📐 Calculated grid size for ${imageWidth}x${imageHeight}px image: ${rows}x${cols} (includes 10-hex buffer)`);
    
    return { rows: Math.min(rows, 150), cols: Math.min(cols, 150) };
  };

  // Load hex grid data for a specific background image
  const loadHexGridForImage = async (imageName) => {
    if (!imageName) return null;

    const hexGridPath = getHexGridFilename(imageName);
    if (!hexGridPath) return null;

    console.log('📂 Loading hex grid for image:', imageName, 'from:', hexGridPath);

    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(hexGridPath)}`);
      
      if (response.ok) {
        const contentType = response.headers.get('content-type');
        let data;

        if (contentType && contentType.includes('application/json')) {
          const jsonData = await response.json();
          if (jsonData.content) {
            data = JSON.parse(jsonData.content);
          } else {
            data = jsonData;
          }
        } else {
          const text = await response.text();
          if (text && text.trim() !== '') {
            data = JSON.parse(text);
          }
        }

        if (data) {
          console.log('✅ Hex grid loaded for:', imageName);
          return data;
        }
      } else if (response.status === 404) {
        console.log('ℹ️ No existing hex grid found for:', imageName);
      } else {
        console.error('❌ Failed to load hex grid:', response.status);
      }
    } catch (err) {
      console.error('❌ Error loading hex grid:', err);
    }

    return null;
  };

  // Save battlemap state to server (debounced)
  const saveBattlemapState = async (useGraphFormat = true) => {
    if (!filePath) {
      console.warn('BattlemapViewer: No filePath provided, cannot save');
      return;
    }
    
    const now = Date.now();
    
    // Build state in the chosen format
    let state;
    if (useGraphFormat) {
      // Graph-based format: much more efficient for large grids
      state = {
        format: 'graph',
        version: '2.0',
        gridSize,
        hexGraph: gridToGraphData(hexGrid, gridSize),
        tokens,
        backgroundImage: selectedImage,
        hexSize,
        lastModified: now
      };
    } else {
      // Legacy 2D array format: kept for compatibility
      state = {
        format: 'array',
        version: '1.0',
        gridSize,
        hexGrid,
        tokens,
        backgroundImage: selectedImage,
        hexSize,
        lastModified: now
      };
    }
    
    // Check if state actually changed
    const stateString = JSON.stringify(state, null, 2); // Pretty print for readability
    if (stateString === lastSavedStateRef.current) {
      console.log('BattlemapViewer: State unchanged, skipping save');
      return; // No changes, skip save
    }
    
    console.log('💾 BattlemapViewer: Saving to path:', filePath);
    console.log('BattlemapViewer: lastModified timestamp:', now);
    
    try {
      setIsSyncing(true);
      // Use the player_root endpoint (POST to save file content)
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: stateString
        })
      });
      
      if (response.ok) {
        lastSavedStateRef.current = stateString;
        setLastSyncTime(now); // Use same timestamp as state.lastModified
        console.log('✅ BattlemapViewer: Save successful, lastSyncTime updated to:', now);
      } else {
        const errorText = await response.text();
        console.error('❌ BattlemapViewer: Save failed with status:', response.status, errorText);
      }
    } catch (err) {
      console.error('❌ Failed to save battlemap:', err);
    } finally {
      setIsSyncing(false);
    }
  };
  
  // Debounced auto-save: saves 1 second after last change
  useEffect(() => {
    // Don't trigger auto-save if changes came from sync
    if (isUpdatingFromSyncRef.current) {
      console.log('BattlemapViewer: Skipping auto-save (changes from sync)');
      isUpdatingFromSyncRef.current = false;
      return;
    }
    
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    saveTimeoutRef.current = setTimeout(() => {
      console.log('BattlemapViewer: Triggering auto-save (local changes)');
      saveBattlemapState();
      // Also save hex grid for current image
      if (selectedImage?.name) {
        saveHexGridForImage(selectedImage.name);
      }
    }, 1000); // Wait 1 second after last change
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [hexGrid, tokens, selectedImage, hexSize, gridSize]);
  
  // Sync from server: poll for changes every 2 seconds
  useEffect(() => {
    if (!filePath) return;
    
    console.log('BattlemapViewer: Setting up sync for path:', filePath);
    console.log('BattlemapViewer: API_BASE_URL:', API_BASE_URL);
    
    // Track the last fetch request to prevent race conditions
    let latestFetchId = 0;
    
    const syncInterval = setInterval(async () => {
      const currentFetchId = ++latestFetchId;
      
      try {
        // Use the same endpoint as we use for saving (GET to read)
        const syncUrl = `${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`;
        console.log('🔄 BattlemapViewer: Polling for updates from:', syncUrl, '(fetch #' + currentFetchId + ')');
        
        const response = await fetch(syncUrl);
        
        // If this is not the latest fetch, ignore the result (race condition prevention)
        if (currentFetchId !== latestFetchId) {
          console.log('⚠️ Ignoring stale fetch response #' + currentFetchId + ' (latest is #' + latestFetchId + ')');
          return;
        }
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
          const contentType = response.headers.get('content-type');
          console.log('Content-Type:', contentType);
          
          let newState;
          
          // Check if response is already JSON or needs parsing
          if (contentType && contentType.includes('application/json')) {
            // Response might be wrapped: {content: "..."} or direct JSON
            const jsonResponse = await response.json();
            console.log('Got JSON response, keys:', Object.keys(jsonResponse));
            
            // Check if it's wrapped in {content: "..."}
            if (jsonResponse.content) {
              console.log('Content is wrapped, parsing inner content');
              newState = JSON.parse(jsonResponse.content);
            } else {
              // Direct JSON
              newState = jsonResponse;
            }
          } else {
            // Plain text, parse it
            const textContent = await response.text();
            console.log('Got text response, length:', textContent.length);
            console.log('First 100 chars:', textContent.substring(0, 100));
            
            if (!textContent || textContent.trim() === '') {
              console.log('⚠️ BattlemapViewer: File is empty, skipping sync');
              return;
            }
            
            newState = JSON.parse(textContent);
          }
          
          console.log('📥 Parsed state - lastModified:', newState.lastModified, '| Local:', lastSyncTimeRef.current);
          console.log('Parsed state format:', newState.format || 'legacy array');
          console.log('Parsed state - hexGrid rows:', newState.hexGrid?.length, '| tokens:', newState.tokens?.length);
          
          // Convert graph format to grid if needed
          if (newState.format === 'graph' && newState.hexGraph) {
            console.log('📊 Converting graph format to grid');
            newState.hexGrid = graphDataToGrid(newState.hexGraph, newState.gridSize);
          }
          
          // CRITICAL: Verify this fetch is still the latest before applying changes
          if (currentFetchId !== latestFetchId) {
            console.log('⚠️ State parsed but fetch is stale (#' + currentFetchId + ' vs #' + latestFetchId + '), discarding');
            return;
          }
          
          // Only update if remote state is newer and different
          // Use refs to get current values without creating dependency
          if (newState.lastModified && newState.lastModified > lastSyncTimeRef.current) {
            const currentStateString = JSON.stringify({
              gridSize: gridSizeRef.current,
              hexGrid: hexGridRef.current,
              tokens: tokensRef.current,
              backgroundImage: selectedImageRef.current,
              hexSize: hexSizeRef.current
            });
            const newStateString = JSON.stringify({
              gridSize: newState.gridSize,
              hexGrid: newState.hexGrid,
              tokens: newState.tokens,
              backgroundImage: newState.backgroundImage,
              hexSize: newState.hexSize
            });
            
            if (currentStateString !== newStateString) {
              // Remote changes detected, update local state
              console.log('✅ BattlemapViewer: Applying remote changes from', new Date(newState.lastModified).toISOString());
              
              isUpdatingFromSyncRef.current = true; // Mark that next updates are from sync
              
              if (newState.gridSize) setGridSize(newState.gridSize);
              if (newState.hexGrid) setHexGrid(newState.hexGrid);
              if (newState.tokens) setTokens(newState.tokens);
              if (newState.backgroundImage) setSelectedImage(newState.backgroundImage);
              if (newState.hexSize) setHexSize(newState.hexSize);
              setLastSyncTime(newState.lastModified);
            } else {
              console.log('ℹ️ Remote state is newer but identical, skipping update');
            }
          }
        } else {
          console.warn('❌ BattlemapViewer: Sync failed with status:', response.status);
        }
      } catch (err) {
        console.error('❌ Failed to sync battlemap:', err);
      }
    }, 2000); // Poll every 2 seconds
    
    return () => {
      console.log('BattlemapViewer: Clearing sync interval');
      clearInterval(syncInterval);
    };
  }, [filePath]); // Only depend on filePath

  // Load saved battlemap state
  useEffect(() => {
    console.log('BattlemapViewer: Loading initial state from content');
    console.log('BattlemapViewer: filePath =', filePath);
    console.log('BattlemapViewer: content length =', content?.length || 0);
    
    isUpdatingFromSyncRef.current = true; // Mark initial load as sync update
    
    try {
      // Handle empty content
      if (!content || content.trim() === '') {
        console.log('BattlemapViewer: Content is empty, initializing default state');
        const defaultGrid = initializeHexGrid(gridSize.rows, gridSize.cols);
        setHexGrid(defaultGrid);
        // Trigger save by updating a dummy state after grid is set
        // The debounced auto-save will pick this up
        return;
      }
      
      const data = JSON.parse(content);
      console.log('BattlemapViewer: Loaded state:', data);
      console.log('BattlemapViewer: Format:', data.format || 'legacy array');
      
      // Convert graph format to grid if needed
      if (data.format === 'graph' && data.hexGraph) {
        console.log('📊 Converting graph format to grid for display');
        data.hexGrid = graphDataToGrid(data.hexGraph, data.gridSize);
      }
      
      if (data.gridSize) {
        setGridSize(data.gridSize);
        setHexGrid(data.hexGrid || initializeHexGrid(data.gridSize.rows, data.gridSize.cols));
      } else {
        setHexGrid(initializeHexGrid(gridSize.rows, gridSize.cols));
      }
      if (data.tokens) setTokens(data.tokens);
      if (data.backgroundImage) setSelectedImage(data.backgroundImage);
      if (data.hexSize) setHexSize(data.hexSize);
      if (data.lastModified) setLastSyncTime(data.lastModified);
    } catch (err) {
      console.error('BattlemapViewer: Error parsing content, initializing default:', err);
      setHexGrid(initializeHexGrid(gridSize.rows, gridSize.cols));
    }
  }, [content]);

  // Load available images from directory and Battlemaps folder
  useEffect(() => {
    const fetchImages = async () => {
      try {
        const allFiles = [];
        
        // Fetch images from current directory if available
        if (dirPath) {
          try {
            const resp = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(dirPath)}`);
            if (resp.ok) {
              const data = await resp.json();
              const files = (data.entries || []).filter((e) => {
                const n = (e.name || '').toLowerCase();
                return n.match(/\.(png|jpe?g|webp)$/);
              });
              allFiles.push(...files.map((f) => ({ name: f.name, path: dirPath })));
            }
          } catch (err) {
            console.error('Error loading images from current directory:', err);
          }
        }
        
        // Always fetch images from Battlemaps folder
        try {
          const battlemapsPath = 'Maps/Battlemaps';
          const resp = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(battlemapsPath)}`);
          if (resp.ok) {
            const data = await resp.json();
            const files = (data.entries || []).filter((e) => {
              const n = (e.name || '').toLowerCase();
              return n.match(/\.(png|jpe?g|webp)$/);
            });
            allFiles.push(...files.map((f) => ({ name: `[Battlemaps] ${f.name}`, path: battlemapsPath })));
          }
        } catch (err) {
          console.error('Error loading images from Battlemaps:', err);
        }
        
        setImageOptions(allFiles);
      } catch (err) {
        console.error('Error loading images:', err);
      }
    };
    fetchImages();
  }, [dirPath]);

  // Load available characters for tokens with their avatars
  useEffect(() => {
    const fetchCharacters = async () => {
      try {
        // Get customizations which include character names, avatars, and colors
        const customResp = await fetch(`${API_BASE_URL}/api/characters/customizations`);
        if (!customResp.ok) {
          console.error('BattlemapViewer: Failed to fetch customizations:', customResp.status);
          return;
        }
        const customData = await customResp.json();
        console.log('BattlemapViewer: Customizations API response:', customData);
        
        const customizations = customData.customizations || customData || {};
        console.log('BattlemapViewer: Parsed customizations:', customizations);
        
        // Convert customizations object to array of characters
        const characters = Object.entries(customizations).map(([name, data]) => ({
          name: name,
          avatar: data.avatar || null,
          color: data.folderColor || '#3498db',
          type: 'player'
        }));
        
        console.log('BattlemapViewer: Loaded characters with avatars:', characters);
        setAvailableCharacters(characters);
      } catch (err) {
        console.error('Error loading characters:', err);
      }
    };
    fetchCharacters();
  }, []);

  // Update background URL
  useEffect(() => {
    if (selectedImage) {
      // selectedImage is now an object with { name, path } or just a string (legacy)
      let imagePath;
      if (typeof selectedImage === 'object' && selectedImage.path) {
        // Extract actual filename from display name if it has [Battlemaps] prefix
        const actualName = selectedImage.name.replace('[Battlemaps] ', '');
        imagePath = `${selectedImage.path}/${actualName}`;
      } else if (typeof selectedImage === 'string') {
        // Legacy format or direct string
        imagePath = dirPath ? `${dirPath}/${selectedImage}` : selectedImage;
      } else {
        imagePath = '';
      }
      
      if (imagePath) {
        setBackgroundUrl(`${API_BASE_URL}/player_root/${encodeURIComponent(imagePath)}`);
      } else {
        setBackgroundUrl('');
      }
    } else {
      setBackgroundUrl('');
    }
  }, [selectedImage, dirPath]);

  // Save current state to history (limit to 5 entries)
  const saveToHistory = () => {
    const currentState = {
      hexGrid: JSON.parse(JSON.stringify(hexGrid)), // Deep copy
      tokens: JSON.parse(JSON.stringify(tokens)),
      timestamp: Date.now()
    };
    
    setHistory(prev => {
      const newHistory = [currentState, ...prev];
      return newHistory.slice(0, 5); // Keep only last 5 states
    });
  };

  // Undo last action
  const handleUndo = () => {
    if (history.length === 0) return;
    
    const [lastState, ...remainingHistory] = history;
    setHexGrid(lastState.hexGrid);
    setTokens(lastState.tokens);
    setHistory(remainingHistory);
  };

  // Watcher Mode functions
  const calculateOptimalZoom = () => {
    // Calculate the grid dimensions
    const gridWidth = gridSize.cols * (hexSize * Math.sqrt(3)) + (hexSize * Math.sqrt(3));
    const gridHeight = gridSize.rows * (hexSize * 1.5) + hexSize;
    
    // Get viewport dimensions
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // Calculate grid aspect ratio
    const gridAspectRatio = gridWidth / gridHeight;
    const viewportAspectRatio = viewportWidth / viewportHeight;
    
    // Determine if rotating improves fit
    let shouldRotate = false;
    let optimalScale;
    
    // Calculate scale without rotation
    const scaleNoRotation = Math.min(
      (viewportWidth * 0.95) / gridWidth,
      (viewportHeight * 0.95) / gridHeight
    );
    
    // Calculate scale WITH 90° rotation (swap width/height)
    const scaleWithRotation = Math.min(
      (viewportWidth * 0.95) / gridHeight,  // viewport width fits grid height
      (viewportHeight * 0.95) / gridWidth   // viewport height fits grid width
    );
    
    // Choose rotation if it gives better coverage
    if (scaleWithRotation > scaleNoRotation) {
      shouldRotate = true;
      optimalScale = scaleWithRotation;
    } else {
      shouldRotate = false;
      optimalScale = scaleNoRotation;
    }
    
    // Cap at 2.0 to avoid excessive zoom
    optimalScale = Math.min(optimalScale, 2.0);
    
    return { scale: optimalScale, rotate: shouldRotate };
  };

  const toggleWatcherMode = () => {
    if (!watcherMode) {
      // Entering watcher mode - go fullscreen and optimize view
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen().then(() => {
          // Wait for fullscreen to take effect, then calculate optimal zoom
          setTimeout(() => {
            const { scale: optimalScale, rotate } = calculateOptimalZoom();
            setScale(optimalScale);
            setWatcherRotation(rotate ? 90 : 0);
            // Save the optimal view for reset button
            setWatcherDefaultView({ scale: optimalScale, rotation: rotate ? 90 : 0 });
          }, 100);
        }).catch(err => {
          console.error('Fullscreen failed:', err);
          // Still calculate zoom even if fullscreen fails
          const { scale: optimalScale, rotate } = calculateOptimalZoom();
          setScale(optimalScale);
          setWatcherRotation(rotate ? 90 : 0);
          setWatcherDefaultView({ scale: optimalScale, rotation: rotate ? 90 : 0 });
        });
      } else {
        // Fallback if fullscreen not supported
        const { scale: optimalScale, rotate } = calculateOptimalZoom();
        setScale(optimalScale);
        setWatcherRotation(rotate ? 90 : 0);
        setWatcherDefaultView({ scale: optimalScale, rotation: rotate ? 90 : 0 });
      }
      
      // Hide parent UI elements (search bar, tab bar, dice roller, file tree)
      const hideElements = () => {
        // Hide file explorer header (search + advanced button)
        const explorerHeaders = document.querySelectorAll('.file-explorer-header, [class*="header"]');
        explorerHeaders.forEach(el => {
          if (el.querySelector('input[type="text"]') || el.textContent.includes('Advanced')) {
            el.style.display = 'none';
            el.setAttribute('data-watcher-hidden', 'true');
          }
        });
        
        // Hide tab bar
        const tabBars = document.querySelectorAll('.tab-bar, [class*="tab"]');
        tabBars.forEach(el => {
          el.style.display = 'none';
          el.setAttribute('data-watcher-hidden', 'true');
        });
        
        // Hide dice roller at bottom
        const diceRollers = document.querySelectorAll('[class*="dice"], [style*="borderTop"]');
        diceRollers.forEach(el => {
          if (el.textContent.includes('Roll') || el.querySelector('button')) {
            el.style.display = 'none';
            el.setAttribute('data-watcher-hidden', 'true');
          }
        });

        // Hide collapsed file tree sidebar
        const sidebars = document.querySelectorAll(
          '[class*="sidebar"], [class*="activitybar"], [class*="sidebarPart"], ' +
          '[class*="composite"], [class*="split-view-view"], ' + 
          '.part.sidebar, .part.activitybar, ' +
          '[id*="workbench.parts.sidebar"]'
        );
        sidebars.forEach(el => {
          // Check if it's a sidebar element (usually has fixed width when collapsed)
          if (el.offsetWidth > 0 && el.offsetWidth < 100) {
            el.style.display = 'none';
            el.setAttribute('data-watcher-hidden', 'true');
          }
        });

        // Also try to hide any element that looks like a collapsed sidebar (thin vertical bar)
        document.querySelectorAll('*').forEach(el => {
          const computedStyle = window.getComputedStyle(el);
          if (computedStyle.position === 'fixed' || computedStyle.position === 'absolute') {
            const width = el.offsetWidth;
            const height = el.offsetHeight;
            // If it's a thin vertical element on the left side
            if (width > 0 && width < 100 && height > 500 && 
                el.getBoundingClientRect().left < 100 &&
                !el.closest('[data-watcher-hidden]')) {
              el.style.display = 'none';
              el.setAttribute('data-watcher-hidden', 'true');
            }
          }
        });
      };
      
      setTimeout(hideElements, 50);
      
      // Store current scale to restore later
      setPreWatcherScale(scale);
    } else {
      // Exiting watcher mode - exit fullscreen and restore previous scale
      if (document.exitFullscreen && document.fullscreenElement) {
        document.exitFullscreen().catch(err => {
          console.error('Exit fullscreen failed:', err);
        });
      }
      
      // Restore hidden UI elements
      const hiddenElements = document.querySelectorAll('[data-watcher-hidden="true"]');
      hiddenElements.forEach(el => {
        el.style.display = '';
        el.removeAttribute('data-watcher-hidden');
      });
      
      // Restore previous scale and rotation
      setScale(preWatcherScale);
      setWatcherRotation(0);
    }
    setWatcherMode(!watcherMode);
  };

  const resetWatcherView = () => {
    // Reset to the optimal calculated view
    setScale(watcherDefaultView.scale);
    setWatcherRotation(watcherDefaultView.rotation);
  };

  const rotateWatcherView = () => {
    // Rotate 90 degrees clockwise
    setWatcherRotation((prev) => (prev + 90) % 360);
  };

  const setCurrentAsDefaultPosition = () => {
    setDefaultCameraScale(scale);
    // Show a temporary notification
    const notification = document.createElement('div');
    notification.textContent = `Default zoom saved: ${Math.round(scale * 100)}%`;
    notification.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: linear-gradient(135deg, #27ae60, #229954);
      color: white;
      padding: 20px 40px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 18px;
      z-index: 10000;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      animation: fadeInOut 2s ease-in-out;
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 2000);
  };

  // Handle grid size change
  const handleGridSizeChange = (rows, cols) => {
    const r = Math.max(1, Math.min(150, rows));
    const c = Math.max(1, Math.min(150, cols));
    setGridSize({ rows: r, cols: c });
    
    // Preserve existing grid data
    const newGrid = initializeHexGrid(r, c);
    for (let i = 0; i < Math.min(r, hexGrid.length); i++) {
      for (let j = 0; j < Math.min(c, hexGrid[i]?.length || 0); j++) {
        if (hexGrid[i]?.[j]) {
          newGrid[i][j] = hexGrid[i][j];
        }
      }
    }
    setHexGrid(newGrid);
  };

  // Handle hex painting with effects
  const handleHexPaint = (row, col, erase = false) => {
    if (currentTool === 'token') return; // Don't paint in token mode
    
    setHexGrid(prev => {
      const updated = prev.map((r, rIdx) => 
        r.map((cell, cIdx) => {
          if (rIdx === row && cIdx === col) {
            if (erase) {
              // Completely reset the cell
              return { 
                filled: false, 
                color: '#3498db',
                effect: 'none',
                animationOffset: Math.random() * 10,
                paintedAt: null
              };
            } else {
              // Use effect colors if available, otherwise use brush color
              const effectPreset = EFFECT_PRESETS[currentEffect];
              const baseColor = effectPreset.colors ? effectPreset.colors[0] : brushColor;
              
              // Completely overwrite with new values
              return { 
                filled: true, 
                color: baseColor,
                effect: currentEffect,
                animationOffset: Math.random() * 10,
                paintedAt: fadeEnabled ? Date.now() : null
              };
            }
          }
          return cell;
        })
      );
      return updated;
    });
  };

  // Handle line drawing between two hexes
  const handleLineDraw = (startRow, startCol, endRow, endCol) => {
    saveToHistory();
    
    // Convert odd-r offset coordinates to cube coordinates
    const start = offsetToCube(startRow, startCol);
    const end = offsetToCube(endRow, endCol);
    
    // Calculate line using cube coordinate lerp
    const distance = Math.max(
      Math.abs(start.q - end.q),
      Math.abs(start.r - end.r),
      Math.abs(start.s - end.s)
    );
    
    const lineHexes = [];
    for (let i = 0; i <= distance; i++) {
      const t = distance === 0 ? 0 : i / distance;
      const q = Math.round(start.q * (1 - t) + end.q * t);
      const r = Math.round(start.r * (1 - t) + end.r * t);
      const s = Math.round(start.s * (1 - t) + end.s * t);
      
      // Convert back to offset coordinates
      const offset = cubeToOffset(q, r, s);
      lineHexes.push(offset);
    }
    
    // Paint all hexes in the line
    setHexGrid(prev => {
      const updated = prev.map(r => r.map(c => ({ ...c })));
      const effectPreset = EFFECT_PRESETS[currentEffect];
      const baseColor = effectPreset.colors ? effectPreset.colors[0] : brushColor;
      
      lineHexes.forEach(({ row, col }) => {
        if (row >= 0 && row < gridSize.rows && col >= 0 && col < gridSize.cols) {
          // Completely overwrite the cell
          updated[row][col] = {
            filled: true,
            color: baseColor,
            effect: currentEffect,
            animationOffset: Math.random() * 10,
            paintedAt: fadeEnabled ? Date.now() : null
          };
        }
      });
      
      return updated;
    });
  };

  // Handle area drawing with new pattern system
  const handleAreaDraw = (startRow, startCol) => {
    const pattern = AREA_PATTERNS[currentTool];
    if (!pattern || !pattern.pattern) return;
    
    setHexGrid(prev => {
      const updated = prev.map(r => r.map(c => ({ ...c })));
      const effectPreset = EFFECT_PRESETS[currentEffect];
      const baseColor = effectPreset.colors ? effectPreset.colors[0] : brushColor;
      
      // Apply pattern using coordinate offsets
      pattern.pattern[0].hexes.forEach(offset => {
        const targetRow = startRow + offset.row;
        const targetCol = startCol + offset.col;
        
        if (targetRow >= 0 && targetRow < gridSize.rows && 
            targetCol >= 0 && targetCol < gridSize.cols) {
          // Completely overwrite the cell
          updated[targetRow][targetCol] = { 
            filled: true, 
            color: baseColor,
            effect: currentEffect,
            animationOffset: Math.random() * 10,
            paintedAt: fadeEnabled ? Date.now() : null
          };
        }
      });
      
      return updated;
    });
  };

  // Handle hex click
  const handleHexClick = (row, col, erase = false) => {
    if (currentTool === 'debug') {
      // Debug tool: Show hex info
      handleDebugHex(row, col);
    } else if (currentTool === 'paint') {
      // Don't save to history here - it's saved on mouseDown
      handleHexPaint(row, col, erase);
    } else if (currentTool === 'eraser') {
      // Eraser always erases
      handleHexPaint(row, col, true);
    } else if (currentTool === 'measure') {
      // Measure distance between two hexes
      handleMeasure(row, col);
    } else if (currentTool === 'line') {
      // Draw a line between two hexes (similar to measure tool)
      if (!lineStart) {
        // First click: set start point
        setLineStart({ row, col });
      } else {
        // Second click: draw line
        handleLineDraw(lineStart.row, lineStart.col, row, col);
        setLineStart(null);
      }
    } else if (currentTool === 'aura') {
      // Aura tool: select token to attach aura to
      handleAuraToolClick(row, col);
    } else if (currentTool === 'sphere' || currentTool === 'cone') {
      // Handle sphere/cone with range input
      if (showDirectionSelect && currentTool === 'cone') {
        // Step 3 for cone: select direction
        handleConeDirection(row, col);
      } else if (!areaOrigin) {
        // Step 1: select origin (can be a hex with or without a token)
        handleAreaEffectStart(row, col);
      }
    } else if (currentTool === 'token') {
      // Check if clicking on existing token
      const tokenAtPos = tokens.find(t => t.row === row && t.col === col);
      if (tokenAtPos) {
        setSelectedToken(tokenAtPos.id);
      }
    }
  };

  // Handle token drag start
  const handleTokenDragStart = (tokenId) => {
    // Save state before moving token
    saveToHistory();
    
    // Start dragging immediately (no dialog)
    setDraggedToken(tokenId);
    setSelectedToken(tokenId);
  };

  // Handle aura tool click - attach aura to token at clicked hex
  const handleAuraToolClick = (row, col) => {
    // Find token at this hex
    const token = tokens.find(t => t.row === row && t.col === col);
    
    if (!token) {
      console.log('No token at this hex. Select a token to attach aura to.');
      return;
    }
    
    // Show area input for aura diameter
    setAreaOrigin({ row, col });
    setAuraTokenId(token.id);
    setAreaRange('');
    setShowAreaInput(true);
  };

  // Apply aura to token (from aura tool)
  const handleAuraToolApply = () => {
    if (!areaOrigin || !auraTokenId || !areaRange) return;
    
    const diameter = parseInt(areaRange);
    if (diameter <= 0) return;
    
    saveToHistory();
    
    const token = tokens.find(t => t.id === auraTokenId);
    if (!token) return;
    
    // Generate aura hexes
    const auraHexes = generateSpherePattern(token.row, token.col, diameter);
    
    // Store aura metadata on the token
    setTokens(prev => prev.map(t => 
      t.id === auraTokenId 
        ? { 
            ...t, 
            aura: {
              diameter,
              outlineColor: auraOutlineColor,
              moveHexes: auraMoveHexes
            }
          }
        : t
    ));
    
    // Mark all hexes in aura as aura tiles linked to this token (only if moveHexes is true)
    if (auraMoveHexes) {
      setHexGrid(prev => {
        const updated = prev.map(r => r.map(c => ({ ...c })));
        const effectPreset = EFFECT_PRESETS[currentEffect];
        const baseColor = effectPreset.colors ? effectPreset.colors[0] : brushColor;
        
        auraHexes.forEach(({ row, col }) => {
          if (updated[row] && updated[row][col]) {
            updated[row][col] = {
              ...updated[row][col],
              filled: true,
              color: baseColor,
              effect: currentEffect,
              auraTokenId: auraTokenId, // Link this hex to the token
              paintedAt: fadeEnabled ? Date.now() : null
            };
          }
        });
        
        return updated;
      });
    }
    
    // Reset
    resetAreaEffect();
    setAuraTokenId(null);
  };

  // Handle debug hex inspection
  const handleDebugHex = (row, col) => {
    const cell = hexGrid[row]?.[col];
    if (!cell) return;
    
    // Get neighbor information with directions
    const directions = ['NE', 'E', 'SE', 'SW', 'W', 'NW'];
    const isOddRow = row % 2 === 1;
    const offsets = isOddRow
      ? [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [0, -1]]
      : [[-1, -1], [-1, 0], [0, 1], [1, 0], [1, -1], [0, -1]];
    
    const neighborMap = {};
    offsets.forEach(([dr, dc], idx) => {
      const nRow = row + dr;
      const nCol = col + dc;
      if (nRow >= 0 && nRow < gridSize.rows && nCol >= 0 && nCol < gridSize.cols) {
        neighborMap[directions[idx]] = `${nRow},${nCol}`;
      } else {
        neighborMap[directions[idx]] = null; // Out of bounds
      }
    });
    
    setSelectedHexInfo({
      id: `${row},${col}`,
      row,
      col,
      neighbors: neighborMap,
      data: { ...cell }
    });
  };

  // Handle token drop
  const handleTokenDrop = (row, col) => {
    if (!draggedToken) return;
    
    // Find the token being moved
    const token = tokens.find(t => t.id === draggedToken);
    if (!token) return;
    
    const oldRow = token.row;
    const oldCol = token.col;
    const newRow = row;
    const newCol = col;
    
    // Only move aura hexes if the token has an aura with moveHexes enabled
    if (token.aura && token.aura.moveHexes) {
      // Find all hexes that are aura tiles for this token
      const auraHexes = [];
      for (let r = 0; r < gridSize.rows; r++) {
        for (let c = 0; c < gridSize.cols; c++) {
          const cell = hexGrid[r]?.[c];
          if (cell && cell.auraTokenId === draggedToken) {
            auraHexes.push({ row: r, col: c, data: { ...cell } });
          }
        }
      }
      
      if (auraHexes.length > 0) {
        // Calculate the diameter from the number of aura hexes
        // Use BFS to find the maximum distance from old token position
        let maxDistance = 0;
        const visited = new Set();
        const queue = [{ row: oldRow, col: oldCol, distance: 0 }];
        visited.add(`${oldRow},${oldCol}`);
        
        while (queue.length > 0) {
          const { row: r, col: c, distance } = queue.shift();
          
          // Check if this hex is part of the aura
          const cell = hexGrid[r]?.[c];
          if (cell && cell.auraTokenId === draggedToken) {
            maxDistance = Math.max(maxDistance, distance);
          }
          
          // Continue BFS if we haven't found all aura hexes yet
          if (visited.size < auraHexes.length + 10) { // +10 buffer for non-aura hexes
            const neighbors = getHexNeighbors(r, c);
            for (const neighbor of neighbors) {
              const key = `${neighbor.row},${neighbor.col}`;
              if (!visited.has(key)) {
                visited.add(key);
                queue.push({ row: neighbor.row, col: neighbor.col, distance: distance + 1 });
              }
            }
          }
        }
        
        const diameter = maxDistance * 2 + 1;
        
        // Get aura properties from first aura hex
        const firstAuraHex = auraHexes[0].data;
        const auraColor = firstAuraHex.color;
        const auraEffect = firstAuraHex.effect;
        const auraPaintedAt = firstAuraHex.paintedAt;
        
        // Clear old aura and regenerate from new position
        setHexGrid(prev => {
          const updated = prev.map(r => r.map(c => ({ ...c })));
          
          // Clear old aura hex positions
          auraHexes.forEach(({ row: r, col: c }) => {
            if (updated[r] && updated[r][c]) {
              updated[r][c] = {
                filled: false,
                color: '#3498db',
                effect: 'none',
                animationOffset: Math.random() * 10,
                paintedAt: null,
                auraTokenId: null
              };
            }
          });
          
          // Generate new aura pattern from new position
          const newAuraHexes = generateSpherePattern(newRow, newCol, diameter);
          
          // Paint new aura hex positions
          newAuraHexes.forEach(({ row: r, col: c }) => {
            if (updated[r] && updated[r][c]) {
              updated[r][c] = {
                ...updated[r][c],
                filled: true,
                color: auraColor,
                effect: auraEffect,
                auraTokenId: draggedToken,
                paintedAt: auraPaintedAt
              };
            }
          });
          
          return updated;
        });
      }
    }
    
    // Update token position
    setTokens(prev => prev.map(token => 
      token.id === draggedToken 
        ? { ...token, row, col }
        : token
    ));
    setDraggedToken(null);
  };

  // Add new token
  const handleAddToken = (character, targetRow = null, targetCol = null) => {
    // Save state before adding token
    saveToHistory();
    
    // Use provided position or default to center
    const row = targetRow !== null ? targetRow : Math.floor(gridSize.rows / 2);
    const col = targetCol !== null ? targetCol : Math.floor(gridSize.cols / 2);
    
    const newToken = {
      id: `token-${Date.now()}`,
      row,
      col,
      name: character.name,
      avatar: character.avatar,
      icon: character.icon, // For enemy tokens
      type: character.type || 'player', // Preserve type from drag data, default to player
      color: character.color || '#64c8ff'
    };
    setTokens(prev => [...prev, newToken]);
    setShowTokenPanel(false);
  };

  // Remove token
  const handleRemoveToken = (tokenId) => {
    // Save state before removing token
    saveToHistory();
    setTokens(prev => prev.filter(t => t.id !== tokenId));
    if (selectedToken === tokenId) setSelectedToken(null);
  };

  // Clear grid
  const handleClearGrid = () => {
    if (window.confirm('Clear all painted hexagons?')) {
      // Save state before clearing
      saveToHistory();
      setHexGrid(initializeHexGrid(gridSize.rows, gridSize.cols));
    }
  };

  // Calculate hex distance (using axial coordinates for flat-top hexes with odd-row offset)
  const calculateHexDistance = (row1, col1, row2, col2) => {
    // Convert odd-r offset coordinates to cube coordinates
    // Standard odd-r formula: q = col - (row + (row%2)) / 2
    const q1 = col1 - Math.floor((row1 + (row1 % 2)) / 2);
    const r1 = row1;
    const s1 = -q1 - r1;
    
    const q2 = col2 - Math.floor((row2 + (row2 % 2)) / 2);
    const r2 = row2;
    const s2 = -q2 - r2;
    
    // Manhattan distance in cube coordinates
    return (Math.abs(q1 - q2) + Math.abs(r1 - r2) + Math.abs(s1 - s2)) / 2;
  };

  // Generate sphere pattern dynamically based on diameter
  // Creates concentric rings around the center hex using proper odd-r offset conversion
  // Diameter 1 = only center tile, Diameter 2 = radius 1, Diameter 3 = radius 2, etc.
  const generateSpherePattern = (centerRow, centerCol, diameter) => {
    const hexes = [];
    const diameterNum = parseInt(diameter);
    
    // Convert diameter to radius using (diameter + 0.5) / 2 rounded up
    // diameter 1 -> radius 0 (just center)
    // diameter 2 -> radius 1
    // diameter 3 -> radius 2, etc.
    const radius = Math.ceil((diameterNum - 1) / 2);
    
    console.log(`🎯 generateSpherePattern: center=(${centerRow},${centerCol}) [${centerRow % 2 === 0 ? 'EVEN' : 'ODD'} row], diameter=${diameter}, radius=${radius}`);
    
    // Use BFS to find all hexes within radius using the neighbor system
    const visited = new Set();
    const queue = [{ row: centerRow, col: centerCol, distance: 0 }];
    visited.add(`${centerRow},${centerCol}`);
    
    while (queue.length > 0) {
      const { row, col, distance } = queue.shift();
      hexes.push({ row, col });
      
      if (distance <= 1) {
        console.log(`  Distance ${distance}: (${row},${col}) [${row % 2 === 0 ? 'even' : 'odd'}]`);
      }
      
      // If we haven't reached the radius limit, add neighbors
      if (distance < radius) {
        const neighbors = getHexNeighbors(row, col);
        for (const neighbor of neighbors) {
          const key = `${neighbor.row},${neighbor.col}`;
          if (!visited.has(key)) {
            visited.add(key);
            queue.push({ row: neighbor.row, col: neighbor.col, distance: distance + 1 });
          }
        }
      }
    }
    
    console.log(`Total hexes: ${hexes.length}`);
    return hexes;
  };

  // Get the 6 neighbors of a hex in odd-r offset coordinates (flat-top orientation)
  const getHexNeighbors = (row, col) => {
    const isOddRow = row % 2 === 1;
    
    // For flat-top hexes with odd-r offset:
    // Even rows: NW, NE, E, SE, SW, W
    // Odd rows: NW, NE, E, SE, SW, W (but with different column offsets)
    const neighbors = isOddRow ? [
      { row: row - 1, col: col },     // NW
      { row: row - 1, col: col + 1 }, // NE
      { row: row, col: col + 1 },     // E
      { row: row + 1, col: col + 1 }, // SE
      { row: row + 1, col: col },     // SW
      { row: row, col: col - 1 }      // W
    ] : [
      { row: row - 1, col: col - 1 }, // NW
      { row: row - 1, col: col },     // NE
      { row: row, col: col + 1 },     // E
      { row: row + 1, col: col },     // SE
      { row: row + 1, col: col - 1 }, // SW
      { row: row, col: col - 1 }      // W
    ];
    
    // Filter out neighbors that are outside the grid
    return neighbors.filter(n => 
      n.row >= 0 && n.row < gridSize.rows && 
      n.col >= 0 && n.col < gridSize.cols
    );
  };

  // Get neighbor in a specific direction
  const getNeighborInDirection = (row, col, direction) => {
    const directions = ['NE', 'E', 'SE', 'SW', 'W', 'NW'];
    const isOddRow = row % 2 === 1;
    const offsets = isOddRow
      ? [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [0, -1]]
      : [[-1, -1], [-1, 0], [0, 1], [1, 0], [1, -1], [0, -1]];
    
    const dirIndex = directions.indexOf(direction);
    if (dirIndex === -1) return null;
    
    const [dr, dc] = offsets[dirIndex];
    const newRow = row + dr;
    const newCol = col + dc;
    
    // Check bounds
    if (newRow < 0 || newRow >= gridSize.rows || newCol < 0 || newCol >= gridSize.cols) {
      return null;
    }
    
    return { row: newRow, col: newCol };
  };
  
  // Get the direction from one hex to an adjacent neighbor
  const getDirectionToNeighbor = (fromRow, fromCol, toRow, toCol) => {
    const directions = ['NE', 'E', 'SE', 'SW', 'W', 'NW'];
    const isOddRow = fromRow % 2 === 1;
    const offsets = isOddRow
      ? [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [0, -1]]
      : [[-1, -1], [-1, 0], [0, 1], [1, 0], [1, -1], [0, -1]];
    
    const deltaRow = toRow - fromRow;
    const deltaCol = toCol - fromCol;
    
    for (let i = 0; i < offsets.length; i++) {
      const [dr, dc] = offsets[i];
      if (dr === deltaRow && dc === deltaCol) {
        return directions[i];
      }
    }
    
    return null; // Not an adjacent neighbor
  };

  // Generate cone pattern based on selecting 2 adjacent hexes as first row
  // Fills ALL hexes between the two boundary lines to create a solid cone
  const generateConePattern = (originRow, originCol, dir1Row, dir1Col, dir2Row, dir2Col, range) => {
    const hexSet = new Set(); // Track unique hexes
    const rangeNum = parseInt(range);
    
    const addHex = (row, col) => {
      const key = `${row},${col}`;
      if (!hexSet.has(key) && row >= 0 && row < gridSize.rows && col >= 0 && col < gridSize.cols) {
        hexSet.add(key);
      }
    };
    
    // Get the directions from origin to each selected hex
    const direction1 = getDirectionToNeighbor(originRow, originCol, dir1Row, dir1Col);
    const direction2 = getDirectionToNeighbor(originRow, originCol, dir2Row, dir2Col);
    
    if (!direction1 || !direction2) {
      console.error('Selected hexes are not adjacent to origin!');
      return [];
    }
    
    // Build cone by extending both boundaries and filling between them at each layer
    for (let layer = 1; layer <= rangeNum; layer++) {
      // Track current boundary positions
      let currentBoundary1 = { row: originRow, col: originCol };
      let currentBoundary2 = { row: originRow, col: originCol };
      
      // Move to the current layer along each direction
      for (let step = 0; step < layer; step++) {
        const next1 = getNeighborInDirection(currentBoundary1.row, currentBoundary1.col, direction1);
        const next2 = getNeighborInDirection(currentBoundary2.row, currentBoundary2.col, direction2);
        
        if (next1) currentBoundary1 = next1;
        if (next2) currentBoundary2 = next2;
      }
      
      // Now flood fill between these two boundary points at this distance
      // Add all hexes that are at this distance from origin and between the two boundaries
      const targetDist = layer;
      
      for (let row = 0; row < gridSize.rows; row++) {
        for (let col = 0; col < gridSize.cols; col++) {
          const dist = calculateHexDistance(originRow, originCol, row, col);
          
          // Include hexes at exactly this distance from origin
          if (dist === targetDist) {
            // Check if this hex is "between" the two boundary hexes
            // by checking if it's reachable via a path through the cone
            const dist1 = calculateHexDistance(row, col, currentBoundary1.row, currentBoundary1.col);
            const dist2 = calculateHexDistance(row, col, currentBoundary2.row, currentBoundary2.col);
            
            // If the hex is close to either boundary or between them, include it
            // A hex is "in the cone" if it's within the angular spread
            const maxBoundaryDist = calculateHexDistance(currentBoundary1.row, currentBoundary1.col, 
                                                         currentBoundary2.row, currentBoundary2.col)-1;
            
            // Include if the sum of distances to both boundaries is not much larger than distance between boundaries
            if (dist1 + dist2 <= maxBoundaryDist + 2) {
              addHex(row, col);
            }
          }
        }
      }
    }
    
    // Convert set to array
    return Array.from(hexSet).map(key => {
      const [row, col] = key.split(',').map(Number);
      return { row, col };
    });
  };

  // Handle area effect tool (sphere/cone) - Step 1: Select origin
  const handleAreaEffectStart = (row, col) => {
    setAreaOrigin({ row, col });
    setAreaRange(''); // Clear the input field
    
    if (currentTool === 'sphere') {
      // For sphere, show range input immediately
      setShowAreaInput(true);
      setShowDirectionSelect(false);
    } else if (currentTool === 'cone') {
      // For cone, show direction selection first (select 2 adjacent hexes)
      setShowAreaInput(false);
      setShowDirectionSelect(true);
    }
  };

  // Handle range input submission
  const handleAreaRangeSubmit = () => {
    if (!areaRange || parseInt(areaRange) <= 0) return;
    
    if (currentTool === 'aura') {
      // Apply aura to token
      handleAuraToolApply();
    } else if (currentTool === 'sphere') {
      // Apply sphere immediately
      applySphereEffect(areaOrigin.row, areaOrigin.col, parseInt(areaRange));
      resetAreaEffect();
    } else if (currentTool === 'cone') {
      // Apply cone with both direction hexes and range
      applyConeEffect(areaOrigin.row, areaOrigin.col, areaDirection.row, areaDirection.col, 
                      areaDirection2.row, areaDirection2.col, parseInt(areaRange));
      resetAreaEffect();
    }
  };

  // Handle cone direction selection (2 adjacent hexes)
  const handleConeDirection = (row, col) => {
    if (!areaOrigin || (row === areaOrigin.row && col === areaOrigin.col)) return;
    
    // Check if selected hex is adjacent to origin
    const neighbors = getHexNeighbors(areaOrigin.row, areaOrigin.col);
    const isAdjacent = neighbors.some(n => n.row === row && n.col === col);
    
    if (!isAdjacent) {
      console.warn('Please select an adjacent hex');
      return;
    }
    
    if (!areaDirection) {
      // First hex selected
      setAreaDirection({ row, col });
    } else {
      // Second hex selected - verify it's adjacent to first
      const dist = calculateHexDistance(areaDirection.row, areaDirection.col, row, col);
      if (dist !== 1) {
        console.warn('Second hex must be adjacent to the first');
        return;
      }
      
      // Both hexes selected, now ask for range
      setAreaDirection2({ row, col });
      setAreaRange(''); // Clear the input field
      setShowDirectionSelect(false);
      setShowAreaInput(true);
    }
  };

  // Apply sphere effect to grid with whirlwind coordination
  const applySphereEffect = (centerRow, centerCol, range) => {
    saveToHistory();
    const hexes = generateSpherePattern(centerRow, centerCol, range);
    
    setHexGrid(prev => {
      const updated = prev.map(r => r.map(c => ({ ...c })));
      const effectPreset = EFFECT_PRESETS[currentEffect];
      const baseColor = effectPreset.colors ? effectPreset.colors[0] : brushColor;
      
      hexes.forEach(({ row, col }) => {
        // Calculate position relative to center for whirlwind effect
        const deltaRow = row - centerRow;
        const deltaCol = col - centerCol;
        
        // Calculate angle around the center (in radians)
        const angle = Math.atan2(deltaRow, deltaCol);
        
        // Calculate distance from center
        const distance = calculateHexDistance(centerRow, centerCol, row, col);
        
        // Create spiraling animation offset based on angle and distance
        // This will make the animation flow around the center in a whirlwind pattern
        const spiralOffset = (angle / (Math.PI * 2)) * 60 + distance * 5;
        
        // Completely overwrite the cell with coordinated whirlwind data
        updated[row][col] = {
          filled: true,
          color: baseColor,
          effect: currentEffect,
          animationOffset: spiralOffset, // Coordinated spiral offset
          paintedAt: fadeEnabled ? Date.now() : null,
          whirlwindCenter: { row: centerRow, col: centerCol }, // Store center for reference
          radialDistance: distance, // Store distance for intensity variation
          radialAngle: angle // Store angle for directional effects
        };
      });
      
      return updated;
    });
  };

  // Apply cone effect to grid
  const applyConeEffect = (originRow, originCol, dir1Row, dir1Col, dir2Row, dir2Col, range) => {
    saveToHistory();
    const hexes = generateConePattern(originRow, originCol, dir1Row, dir1Col, dir2Row, dir2Col, range);
    
    setHexGrid(prev => {
      const updated = prev.map(r => r.map(c => ({ ...c })));
      const effectPreset = EFFECT_PRESETS[currentEffect];
      const baseColor = effectPreset.colors ? effectPreset.colors[0] : brushColor;
      
      hexes.forEach(({ row, col }) => {
        // Calculate distance from origin for wave animation
        const distance = calculateHexDistance(originRow, originCol, row, col);
        // Create wave effect: each distance layer starts animation at different time
        // Negative offset means further hexes animate LATER (wave travels forward)
        // Higher multiplier = slower wave propagation
        const waveOffset = -distance * 4; // Negative for forward wave propagation
        
        // Completely overwrite the cell
        updated[row][col] = {
          filled: true,
          color: baseColor,
          effect: currentEffect,
          animationOffset: waveOffset, // Wave propagates from origin outward
          paintedAt: fadeEnabled ? Date.now() : null
        };
      });
      
      return updated;
    });
  };

  // Reset area effect state
  const resetAreaEffect = () => {
    setAreaOrigin(null);
    setShowAreaInput(false);
    setAreaRange('');
    setAreaDirection(null);
    setAreaDirection2(null);
    setShowDirectionSelect(false);
    setLineStart(null);
  };

  // Handle measurement tool
  const handleMeasure = (row, col) => {
    if (!measureStart) {
      // First click - set start point
      setMeasureStart({ row, col });
      setMeasureEnd(null);
      setMeasureDistance(null);
    } else {
      // Second click - calculate distance and show for 3 seconds
      setMeasureEnd({ row, col });
      const distance = calculateHexDistance(measureStart.row, measureStart.col, row, col);
      setMeasureDistance(distance);
      setShowMeasurement(true);
      
      // Hide measurement after 3 seconds and reset
      setTimeout(() => {
        setShowMeasurement(false);
        setMeasureStart(null);
        setMeasureEnd(null);
        setMeasureDistance(null);
      }, 3000);
    }
  };

  // Calculate hex coordinates
  const getHexCoordinates = (row, col) => {
    const hexWidth = hexSize * Math.sqrt(3);
    const vertSpacing = hexSize * 1.5;
    const horizSpacing = hexWidth;
    const tessellationOffset = (row % 2 === 1) ? (hexWidth / 2) : 0;
    
    const cx = col * horizSpacing + (hexWidth / 2) + tessellationOffset;
    const cy = row * vertSpacing + hexSize;
    
    return { cx, cy };
  };

  // Get hex vertices
  const getHexVertices = (cx, cy) => {
    const points = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i + Math.PI / 2;
      const x = cx + hexSize * Math.cos(angle);
      const y = cy + hexSize * Math.sin(angle);
      points.push(`${x},${y}`);
    }
    return points.join(' ');
  };

  // Get animated color and opacity for effects with whirlwind coordination
  const getAnimatedStyle = (cell) => {
    if (!cell.filled || cell.effect === 'none') {
      return { color: cell.color, opacity: 0.5 };
    }

    const effectPreset = EFFECT_PRESETS[cell.effect];
    if (!effectPreset || !effectPreset.colors) {
      return { color: cell.color, opacity: 0.5 };
    }

    // Apply logarithmic scaling to intensity values for more subtle changes
    const logOpacityIntensity = Math.log10(1 + 9 * opacityIntensity) * 0.3;
    const logShadeIntensity = Math.log10(1 + 9 * shadeIntensity) * 0.3;

    const frame = (animationFrame + cell.animationOffset) % 60;
    
    // Check if this cell is part of a whirlwind (has radial data)
    const hasWhirlwindData = cell.whirlwindCenter && typeof cell.radialAngle === 'number';
    
    switch (effectPreset.animation) {
      case 'flicker': {
        // Fire effect - if part of whirlwind, create expanding fire rings
        if (hasWhirlwindData) {
          // Create smooth outward-traveling ring of bright flames
          // Ring expands from center at a steady rate
          const ringSpeed = 0.15; // Slower, smoother wave propagation
          const ringWidth = 2.5; // Width of the bright flame ring
          
          // Distance from the flame wave (negative = behind wave, positive = ahead of wave)
          const wavePosition = (animationFrame * ringSpeed) % 15; // Ring cycles every ~100 frames
          const distanceFromWave = Math.abs(cell.radialDistance - wavePosition);
          
          // Calculate intensity - brightest at wave position, fades away from it
          const ringIntensity = Math.exp(-distanceFromWave / ringWidth); // Smooth gaussian-like falloff
          
          // Brightness peaks when ring passes through
          const brightness = 0.3 + ringIntensity * 0.7; // Range from dim (0.3) to bright (1.0)
          
          // Color shifts from yellow (hot core) to orange to red as ring passes
          const colorPhase = (1 - ringIntensity) * effectPreset.colors.length;
          const colorIndex = Math.min(
            effectPreset.colors.length - 1,
            Math.floor(colorPhase)
          );
          
          // Add subtle flicker for realism
          const flicker = Math.sin(animationFrame * 0.8 + cell.radialAngle * 5) * 0.1;
          const opacity = Math.max(0.2, Math.min(1.0, brightness + flicker));
          
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          // Standard flicker for non-whirlwind cells
          const colorIndex = Math.floor((frame / 5)) % effectPreset.colors.length;
          const opacityVariation = Math.sin(frame * 0.5) * logOpacityIntensity;
          const opacity = 0.5 + opacityVariation;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'pulse': {
        // Ice effect - crystallization spreading from center
        if (hasWhirlwindData) {
          const pulseWave = Math.sin(animationFrame * 0.2 - cell.radialDistance * 0.5);
          const opacity = 0.4 + pulseWave * 0.3;
          const colorIndex = Math.floor((animationFrame + cell.radialDistance * 5) / 15) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          const opacityVariation = Math.sin(frame * 0.2) * logOpacityIntensity;
          const opacity = 0.5 + opacityVariation;
          const colorIndex = Math.floor(frame / 20) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'bubble': {
        // Poison effect - toxic clouds swirling
        if (hasWhirlwindData) {
          const swirlPhase = animationFrame * 0.4 + cell.radialAngle * 10;
          const bubble = Math.sin(swirlPhase) * Math.sin(animationFrame * 0.3) * 0.25;
          const opacity = 0.5 + bubble;
          const colorIndex = Math.floor(swirlPhase / 12) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          const opacityVariation = Math.sin(frame * 0.3 + cell.animationOffset) * logOpacityIntensity;
          const opacity = 0.5 + opacityVariation;
          const colorIndex = (Math.floor(frame / 8) + Math.floor(cell.animationOffset)) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'spark': {
        // Lightning effect - crackling electricity spiraling outward
        if (hasWhirlwindData) {
          const electricWave = (animationFrame * 0.8 - cell.radialAngle * 15 + cell.radialDistance * 8) % 60;
          const flash = electricWave < 5 ? 0.9 : 0.4;
          const colorIndex = Math.floor(electricWave / 10) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity: flash };
        } else {
          const colorIndex = Math.floor(frame / 3) % effectPreset.colors.length;
          const baseOpacity = frame % 10 < 2 ? 0.8 : 0.5;
          const opacityVariation = Math.random() * logOpacityIntensity;
          const opacity = baseOpacity + opacityVariation;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'wave': {
        // Darkness effect - creeping shadow waves
        if (hasWhirlwindData) {
          const shadowWave = Math.sin(animationFrame * 0.2 - cell.radialDistance * 0.8);
          const opacity = 0.6 + shadowWave * 0.2;
          const colorIndex = Math.floor((animationFrame + cell.radialDistance * 10) / 20) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          const opacityVariation = Math.sin(frame * 0.15 + cell.animationOffset * 0.5) * logOpacityIntensity;
          const opacity = 0.6 + opacityVariation;
          const colorIndex = Math.floor(frame / 15) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'shimmer': {
        // Healing effect - radiant light pulsing from center
        if (hasWhirlwindData) {
          const radianceWave = Math.sin(animationFrame * 0.3 - cell.radialDistance * 0.6) * 0.3;
          const opacity = 0.5 + radianceWave;
          const colorIndex = Math.floor((animationFrame + cell.radialDistance * 8) / 12) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          const opacityVariation = Math.sin(frame * 0.25) * logOpacityIntensity;
          const opacity = 0.5 + opacityVariation;
          const colorIndex = Math.floor((frame + cell.animationOffset * 2) / 10) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'static': {
        // Earth effect - mostly static with slight variation
        const opacityVariation = Math.sin(frame * 0.1) * logOpacityIntensity * 0.3;
        const opacity = 0.6 + opacityVariation;
        return { color: effectPreset.colors[0], opacity };
      }
      
      case 'swirl': {
        // Air effect - true whirlwind with coordinated spiraling
        if (hasWhirlwindData) {
          // Create a rotating color wave that spirals around the center
          const spiralPhase = (animationFrame * 0.5 + (cell.radialAngle / (Math.PI * 2)) * 60 + cell.radialDistance * 3) % 60;
          const colorIndex = Math.floor(spiralPhase / 12) % effectPreset.colors.length;
          
          // Pulsing opacity that creates "gusts" in the whirlwind
          const gustWave = Math.sin(spiralPhase * 0.3) * 0.25;
          const opacity = 0.35 + gustWave;
          
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          // Standard swirl for non-whirlwind cells
          const opacityVariation = Math.sin(frame * 0.2) * logOpacityIntensity;
          const opacity = 0.4 + opacityVariation;
          const colorIndex = Math.floor((frame + cell.animationOffset * 3) / 15) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'flow': {
        // Water effect - flowing ripples from center
        if (hasWhirlwindData) {
          const rippleWave = Math.sin(animationFrame * 0.25 - cell.radialDistance * 0.7);
          const opacity = 0.45 + rippleWave * 0.25;
          const colorIndex = Math.floor((animationFrame + cell.radialDistance * 6) / 15) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        } else {
          const opacityVariation = Math.sin(frame * 0.2) * logOpacityIntensity;
          const opacity = 0.5 + opacityVariation;
          const colorIndex = Math.floor(frame / 15) % effectPreset.colors.length;
          return { color: effectPreset.colors[colorIndex], opacity };
        }
      }
      
      case 'drip': {
        // Blood effect - dripping and pooling from center
        if (hasWhirlwindData) {
          const dripPhase = (animationFrame * 0.3 + cell.radialDistance * 5) % 60;
          const drip = dripPhase < 10 ? Math.sin(dripPhase * 0.3) * 0.2 : 0;
          const opacity = 0.6 + drip;
          return { color: effectPreset.colors[0], opacity };
        } else {
          const opacityVariation = Math.sin(frame * 0.2) * logOpacityIntensity;
          const opacity = 0.6 + opacityVariation;
          return { color: effectPreset.colors[0], opacity };
        }
      }
      
      default:
        return { color: cell.color, opacity: 0.5 };
    }
  };

  // Calculate SVG dimensions
  const svgWidth = gridSize.cols * (hexSize * Math.sqrt(3)) + (hexSize * Math.sqrt(3));
  const svgHeight = gridSize.rows * (hexSize * 1.5) + hexSize;

  const STANDARD_COLORS = [
    '#ff6b6b', '#ffb347', '#ffd166', '#9b59b6', '#6c5ce7', '#3498db',
    '#5f81fd', '#2ecc71', '#1abc9c', '#16a085', '#e67e22', '#e74c3c'
  ];

  // Render custom effect graphics for a hex cell
  const renderEffectGraphics = (effect, cx, cy, rIdx, cIdx) => {
    if (!effect || effect === 'none') return null;

    const cellKey = `${rIdx}-${cIdx}`;
    const cellOffset = (rIdx * gridSize.cols + cIdx) * 17; // Unique offset per cell
    const frame = (animationFrame + cellOffset) % 60;

    switch (effect) {
      case 'fire':
        // Flames erupting from bottom edges
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {/* Base glow */}
            <circle cx={cx} cy={cy} r={hexSize * 0.8} fill="url(#fireGradient)" opacity="0.4" />
            
            {/* Flame particles from edges */}
            {[0, 1, 2, 3, 4, 5].map((edge) => {
              const angle = (Math.PI / 3) * edge + Math.PI / 2;
              const baseX = cx + hexSize * 0.85 * Math.cos(angle);
              const baseY = cy + hexSize * 0.85 * Math.sin(angle);
              const flameOffset = Math.sin((frame + edge * 10) * 0.2) * 5;
              const flameHeight = 8 + Math.sin((frame + edge * 15) * 0.15) * 4;
              
              return (
                <ellipse
                  key={`flame-${edge}`}
                  cx={baseX}
                  cy={baseY - flameHeight + flameOffset}
                  rx={3}
                  ry={flameHeight}
                  fill={['#ff4444', '#ff6b1a', '#ffaa00'][edge % 3]}
                  opacity={0.6 + Math.sin((frame + edge * 8) * 0.3) * 0.2}
                />
              );
            })}
          </g>
        );

      case 'ice':
        // Ice crystals and frost
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {/* Frozen base */}
            <polygon
              points={getHexVertices(cx, cy)}
              fill="url(#iceGradient)"
              opacity="0.5"
            />
            
            {/* Ice crystal shards */}
            {[0, 1, 2, 3, 4, 5].map((crystal) => {
              const angle = (Math.PI / 3) * crystal;
              const crystalX = cx + hexSize * 0.5 * Math.cos(angle);
              const crystalY = cy + hexSize * 0.5 * Math.sin(angle);
              const pulse = 0.7 + Math.sin((frame + crystal * 10) * 0.1) * 0.2;
              
              return (
                <g key={`crystal-${crystal}`} opacity={pulse}>
                  <line
                    x1={crystalX}
                    y1={crystalY}
                    x2={crystalX + 6 * Math.cos(angle)}
                    y2={crystalY + 6 * Math.sin(angle)}
                    stroke="#ccffff"
                    strokeWidth="2"
                    opacity="0.8"
                  />
                  <line
                    x1={crystalX}
                    y1={crystalY}
                    x2={crystalX + 4 * Math.cos(angle + 0.5)}
                    y2={crystalY + 4 * Math.sin(angle + 0.5)}
                    stroke="#88ccff"
                    strokeWidth="1.5"
                    opacity="0.6"
                  />
                  <line
                    x1={crystalX}
                    y1={crystalY}
                    x2={crystalX + 4 * Math.cos(angle - 0.5)}
                    y2={crystalY + 4 * Math.sin(angle - 0.5)}
                    stroke="#88ccff"
                    strokeWidth="1.5"
                    opacity="0.6"
                  />
                </g>
              );
            })}
          </g>
        );

      case 'earth':
        // Boulder/rock mound
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {/* Base earth texture */}
            <polygon
              points={getHexVertices(cx, cy)}
              fill="url(#earthPattern)"
              opacity="0.7"
            />
            
            {/* Central boulder */}
            <ellipse
              cx={cx}
              cy={cy + 2}
              rx={hexSize * 0.5}
              ry={hexSize * 0.4}
              fill="#6f5436"
              opacity="0.8"
            />
            <ellipse
              cx={cx - 3}
              cy={cy - 1}
              rx={hexSize * 0.4}
              ry={hexSize * 0.35}
              fill="#8b6f47"
              opacity="0.7"
            />
            <ellipse
              cx={cx + 4}
              cy={cy}
              rx={hexSize * 0.3}
              ry={hexSize * 0.25}
              fill="#9a7b5a"
              opacity="0.6"
            />
            
            {/* Rock cracks */}
            <path
              d={`M ${cx - 5} ${cy} Q ${cx} ${cy - 3} ${cx + 5} ${cy + 1}`}
              stroke="#4a3a2a"
              strokeWidth="1"
              fill="none"
              opacity="0.5"
            />
          </g>
        );

      case 'poison':
        // Bubbling poison
        const bubblePositions = [
          { x: -0.3, y: -0.2 },
          { x: 0.3, y: -0.3 },
          { x: -0.2, y: 0.2 },
          { x: 0.25, y: 0.3 },
          { x: 0, y: 0 }
        ];
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {bubblePositions.map((pos, idx) => {
              const bubblePhase = (frame + idx * 12) % 60;
              const bubbleScale = bubblePhase < 30 
                ? bubblePhase / 30 
                : 1 - (bubblePhase - 30) / 30;
              const bubbleY = cy + pos.y * hexSize - (bubblePhase * 0.2);
              
              return (
                <circle
                  key={`bubble-${idx}`}
                  cx={cx + pos.x * hexSize}
                  cy={bubbleY}
                  r={3 * bubbleScale}
                  fill="#88ff44"
                  opacity={0.6 * bubbleScale}
                />
              );
            })}
          </g>
        );

      case 'lightning':
        // Electric sparks
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {[0, 1, 2].map((bolt) => {
              const show = (frame + bolt * 20) % 60 < 10;
              if (!show) return null;
              
              const angle = (bolt * Math.PI * 2 / 3) + (frame * 0.1);
              const x1 = cx;
              const y1 = cy;
              const x2 = cx + Math.cos(angle) * hexSize * 0.7;
              const y2 = cy + Math.sin(angle) * hexSize * 0.7;
              const midX = (x1 + x2) / 2 + Math.random() * 8 - 4;
              const midY = (y1 + y2) / 2 + Math.random() * 8 - 4;
              
              return (
                <path
                  key={`bolt-${bolt}`}
                  d={`M ${x1} ${y1} L ${midX} ${midY} L ${x2} ${y2}`}
                  stroke="#ffffff"
                  strokeWidth="2"
                  fill="none"
                  opacity="0.9"
                  filter="drop-shadow(0 0 3px #aaffff)"
                />
              );
            })}
          </g>
        );

      case 'healing':
        // Sparkles and shimmer
        const sparkles = [
          { x: -0.4, y: -0.3 },
          { x: 0.4, y: -0.2 },
          { x: -0.3, y: 0.3 },
          { x: 0.3, y: 0.4 },
          { x: 0, y: -0.4 },
          { x: 0, y: 0.4 }
        ];
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {sparkles.map((pos, idx) => {
              const sparklePhase = (frame + idx * 10) % 60;
              const sparkleOpacity = sparklePhase < 30 
                ? sparklePhase / 30 
                : 1 - (sparklePhase - 30) / 30;
              
              return (
                <g key={`sparkle-${idx}`} opacity={sparkleOpacity}>
                  <line
                    x1={cx + pos.x * hexSize - 3}
                    y1={cy + pos.y * hexSize}
                    x2={cx + pos.x * hexSize + 3}
                    y2={cy + pos.y * hexSize}
                    stroke="#ffffaa"
                    strokeWidth="2"
                  />
                  <line
                    x1={cx + pos.x * hexSize}
                    y1={cy + pos.y * hexSize - 3}
                    x2={cx + pos.x * hexSize}
                    y2={cy + pos.y * hexSize + 3}
                    stroke="#ffdd88"
                    strokeWidth="2"
                  />
                </g>
              );
            })}
          </g>
        );

      case 'darkness':
        // Shadowy tendrils
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <circle cx={cx} cy={cy} r={hexSize * 0.9} fill="#0a0a0a" opacity="0.7" />
            {[0, 1, 2, 3, 4].map((tendril) => {
              const angle = (tendril * Math.PI * 2 / 5) + (frame * 0.05);
              const wave = Math.sin((frame + tendril * 12) * 0.15) * 5;
              const x = cx + Math.cos(angle) * (hexSize * 0.6 + wave);
              const y = cy + Math.sin(angle) * (hexSize * 0.6 + wave);
              
              return (
                <line
                  key={`tendril-${tendril}`}
                  x1={cx}
                  y1={cy}
                  x2={x}
                  y2={y}
                  stroke="#1a1a1a"
                  strokeWidth="3"
                  opacity="0.5"
                />
              );
            })}
          </g>
        );

      case 'air':
        // Swirling air currents with light blue and orange wisps
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {/* Circular air flow paths */}
            {[0, 1, 2].map((wisp) => {
              const baseAngle = (frame + wisp * 20 + cellOffset) * 0.1;
              const radius = hexSize * 0.6;
              const wispLength = 8;
              
              // Alternate between blue and orange
              const isBlue = (Math.floor((frame + wisp * 20) / 15)) % 2 === 0;
              const color = isBlue ? '#e6f3ff' : '#ffd9a8';
              
              // Create curved wisp
              const points = [];
              for (let i = 0; i < 4; i++) {
                const angle = baseAngle + (i * 0.3);
                const r = radius - (i * 3);
                points.push({
                  x: cx + Math.cos(angle) * r,
                  y: cy + Math.sin(angle) * r
                });
              }
              
              const pathD = `M ${points[0].x} ${points[0].y} ` +
                           `Q ${points[1].x} ${points[1].y} ${points[2].x} ${points[2].y} ` +
                           `T ${points[3].x} ${points[3].y}`;
              
              const opacity = 0.5 + Math.sin((frame + wisp * 15) * 0.2) * 0.3;
              
              return (
                <path
                  key={`wisp-${wisp}`}
                  d={pathD}
                  stroke={color}
                  strokeWidth="2"
                  fill="none"
                  opacity={opacity}
                  strokeLinecap="round"
                />
              );
            })}
            
            {/* Small swirl particles */}
            {[0, 1, 2, 3].map((particle) => {
              const angle = (frame + particle * 15 + cellOffset) * 0.15;
              const radius = hexSize * 0.4;
              const px = cx + Math.cos(angle) * radius;
              const py = cy + Math.sin(angle) * radius;
              const particlePhase = (frame + particle * 15) % 30;
              const particleOpacity = particlePhase < 15 ? particlePhase / 15 : 1 - (particlePhase - 15) / 15;
              
              const isOrange = particle % 2 === 0;
              const particleColor = isOrange ? '#ffcc99' : '#d4e9ff';
              
              return (
                <circle
                  key={`particle-${particle}`}
                  cx={px}
                  cy={py}
                  r="1.5"
                  fill={particleColor}
                  opacity={particleOpacity * 0.8}
                />
              );
            })}
          </g>
        );

      default:
        return null;
    }
  };

  return (
    <div className="battlemap-viewer" style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', gap: '10px', overflow: 'visible' }}>
      {/* Toolbar - Hidden in Watcher Mode */}
      {!watcherMode && (
      <div style={{
        background: '#2a2a2a',
        borderRadius: '8px',
        overflow: 'hidden',
        flexShrink: 0
      }}>
        {/* Toolbar Header */}
        <div
          onClick={() => setShowToolbar(!showToolbar)}
          style={{
            padding: '12px 16px',
            background: 'linear-gradient(135deg, #34495e, #2c3e50)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: showToolbar ? '1px solid #3e3e42' : 'none',
            transition: 'background 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'linear-gradient(135deg, #3d566e, #34495e)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'linear-gradient(135deg, #34495e, #2c3e50)';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>⚙️</span>
            <span style={{ fontWeight: '700', color: '#fff', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Toolbar
            </span>
          </div>
          <span style={{ fontSize: '20px', transform: showToolbar ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }}>
            ▼
          </span>
        </div>

        {/* Toolbar Content */}
        {showToolbar && (
      <div style={{
        padding: '15px',
        display: 'flex',
        gap: '20px',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        {/* Sync Indicator (Advanced Mode Only) */}
        {advancedMode && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            background: isSyncing ? '#3498db' : '#27ae60',
            borderRadius: '4px',
            fontSize: '12px',
            fontWeight: '600',
            color: '#fff'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#fff',
              animation: isSyncing ? 'pulse 1s infinite' : 'none'
            }} />
            {isSyncing ? 'Syncing...' : 'Synced'}
          </div>
        )}
        
        {/* Format Comparison Button (Advanced Mode Only) */}
        {advancedMode && (
        <button
          onClick={() => {
            // Calculate sizes for both formats
            const arrayFormat = {
              format: 'array',
              version: '1.0',
              gridSize,
              hexGrid,
              tokens,
              backgroundImage: selectedImage,
              hexSize,
              lastModified: Date.now()
            };
            
            const graphFormat = {
              format: 'graph',
              version: '2.0',
              gridSize,
              hexGraph: gridToGraphData(hexGrid, gridSize),
              tokens,
              backgroundImage: selectedImage,
              hexSize,
              lastModified: Date.now()
            };
            
            const arraySize = JSON.stringify(arrayFormat).length;
            const graphSize = JSON.stringify(graphFormat).length;
            const savings = ((1 - graphSize / arraySize) * 100).toFixed(1);
            
            alert(
              `📊 Format Comparison\n\n` +
              `Array Format: ${(arraySize / 1024).toFixed(1)} KB\n` +
              `Graph Format: ${(graphSize / 1024).toFixed(1)} KB\n\n` +
              `Space Savings: ${savings}%\n\n` +
              `Graph format uses neighbor connections instead of storing\n` +
              `every hex in a 2D array. Much more efficient for large grids!`
            );
          }}
          style={{
            padding: '8px 16px',
            background: '#9b59b6',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          � Compare Formats
        </button>
        )}
        
        {/* Manual Sync Check Button (Advanced Mode Only) */}
        {advancedMode && (
        <button
          onClick={async () => {
            console.log('🔍 Manual sync check triggered');
            console.log('Current filePath:', filePath);
            console.log('Current lastSyncTime:', lastSyncTime);
            console.log('Current lastSyncTimeRef:', lastSyncTimeRef.current);
            
            try {
              const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
              console.log('Fetch response status:', response.status);
              console.log('Content-Type:', response.headers.get('content-type'));
              
              if (response.ok) {
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                  const jsonData = await response.json();
                  console.log('Response is JSON, keys:', Object.keys(jsonData));
                  console.log('Full JSON response:', jsonData);
                  
                  if (jsonData.content) {
                    console.log('Has content property, parsing inner JSON');
                    const parsed = JSON.parse(jsonData.content);
                    console.log('Parsed inner content:', parsed);
                  }
                } else {
                  const content = await response.text();
                  console.log('Response is text, length:', content.length);
                  console.log('Full text content:', content);
                  
                  if (content && content.trim() !== '') {
                    const parsed = JSON.parse(content);
                    console.log('Parsed from text:', parsed);
                    console.log('lastModified:', parsed.lastModified);
                    console.log('hexGrid rows:', parsed.hexGrid?.length);
                    console.log('tokens count:', parsed.tokens?.length);
                  }
                }
              } else {
                console.error('Fetch failed with status:', response.status);
              }
            } catch (err) {
              console.error('Manual sync check error:', err);
            }
          }}
          style={{
            padding: '8px 16px',
            background: '#e67e22',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          🔍 Check Sync
        </button>
        )}
        
        {/* Undo Button */}
        <button
          onClick={handleUndo}
          disabled={history.length === 0}
          style={{
            padding: '8px 16px',
            background: history.length > 0 ? '#9b59b6' : '#555',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            cursor: history.length > 0 ? 'pointer' : 'not-allowed',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            opacity: history.length > 0 ? 1 : 0.5
          }}
          title={`Undo (${history.length} actions available)`}
        >
          ↶ Undo {history.length > 0 && `(${history.length})`}
        </button>

        {/* Watcher Mode Button */}
        <button
          onClick={toggleWatcherMode}
          style={{
            padding: '8px 16px',
            background: watcherMode 
              ? 'linear-gradient(135deg, #e74c3c, #c0392b)' 
              : 'linear-gradient(135deg, #27ae60, #229954)',
            border: watcherMode ? '2px solid #c0392b' : '2px solid #27ae60',
            borderRadius: '6px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '700',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: watcherMode 
              ? '0 0 15px rgba(231, 76, 60, 0.5)' 
              : '0 4px 8px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}
          title={watcherMode ? 'Exit Watcher Mode (ESC)' : 'Enter Watcher Mode (Fullscreen)'}
        >
          {watcherMode ? '🔴 Live' : '👁️ Watcher Mode'}
        </button>

        {/* Set Default Position Button */}
        <button
          onClick={setCurrentAsDefaultPosition}
          style={{
            padding: '8px 16px',
            background: 'linear-gradient(135deg, rgba(52, 152, 219, 0.8), rgba(41, 128, 185, 0.8))',
            border: '2px solid rgba(52, 152, 219, 0.6)',
            borderRadius: '6px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            transition: 'all 0.2s ease',
            fontSize: '13px'
          }}
          title="Save current camera position as default for Watcher Mode"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'linear-gradient(135deg, #3498db, #2980b9)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'linear-gradient(135deg, rgba(52, 152, 219, 0.8), rgba(41, 128, 185, 0.8))';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          📍 Set Default Position
        </button>

        {/* Token Library Toggle Button */}
        <button
          onClick={() => setShowTokenPanel(!showTokenPanel)}
          style={{
            padding: '8px 16px',
            background: showTokenPanel ? '#27ae60' : '#3498db',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: showTokenPanel ? '0 0 10px rgba(39, 174, 96, 0.5)' : 'none'
          }}
        >
          🎭 Token Library
        </button>
        
        {/* Debug Tool Button (Advanced Mode Only) */}
        {advancedMode && (
          <button
            onClick={() => setCurrentTool('debug')}
            style={{
              padding: '8px 16px',
              background: currentTool === 'debug' ? '#e74c3c' : '#c0392b',
              border: currentTool === 'debug' ? '2px solid #fff' : 'none',
              borderRadius: '4px',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🔍 Debug Hex
          </button>
        )}

        {/* Grid Size */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontWeight: '600' }}>Grid:</label>
          <input
            type="number"
            value={pendingGridSize.rows}
            onChange={(e) => setPendingGridSize({ ...pendingGridSize, rows: parseInt(e.target.value) || 1 })}
            min="1"
            max="150"
            style={{
              width: '60px',
              padding: '6px',
              borderRadius: '4px',
              border: '1px solid #3e3e42',
              background: '#1a1a1a',
              color: '#e0e0e0'
            }}
          />
          <span>×</span>
          <input
            type="number"
            value={pendingGridSize.cols}
            onChange={(e) => setPendingGridSize({ ...pendingGridSize, cols: parseInt(e.target.value) || 1 })}
            min="1"
            max="150"
            style={{
              width: '60px',
              padding: '6px',
              borderRadius: '4px',
              border: '1px solid #3e3e42',
              background: '#1a1a1a',
              color: '#e0e0e0'
            }}
          />
          <button
            onClick={() => handleGridSizeChange(pendingGridSize.rows, pendingGridSize.cols)}
            disabled={pendingGridSize.rows === gridSize.rows && pendingGridSize.cols === gridSize.cols}
            style={{
              padding: '6px 12px',
              background: (pendingGridSize.rows !== gridSize.rows || pendingGridSize.cols !== gridSize.cols) 
                ? '#27ae60' 
                : '#555',
              border: 'none',
              borderRadius: '4px',
              color: '#fff',
              cursor: (pendingGridSize.rows !== gridSize.rows || pendingGridSize.cols !== gridSize.cols) 
                ? 'pointer' 
                : 'not-allowed',
              fontWeight: '600',
              fontSize: '12px',
              opacity: (pendingGridSize.rows !== gridSize.rows || pendingGridSize.cols !== gridSize.cols) 
                ? 1 
                : 0.5,
              transition: 'all 0.2s ease'
            }}
            title="Apply grid size changes"
          >
            ✓ Apply
          </button>
        </div>

        {/* Hex Size */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontWeight: '600' }}>Hex Size:</label>
          <input
            type="range"
            value={hexSize}
            onChange={(e) => setHexSize(parseInt(e.target.value))}
            min="10"
            max="80"
            style={{ width: '120px' }}
          />
          <span style={{ minWidth: '40px' }}>{hexSize}px</span>
        </div>

        {/* Scale */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontWeight: '600' }}>Zoom:</label>
          <input
            type="range"
            value={scale}
            onChange={(e) => setScale(parseFloat(e.target.value))}
            min="0.25"
            max="3"
            step="0.1"
            style={{ width: '120px' }}
          />
          <span style={{ minWidth: '40px' }}>{Math.round(scale * 100)}%</span>
        </div>

        {/* Background Image */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flex: 1 }}>
          <label style={{ fontWeight: '600' }}>Background:</label>
          <select
            value={selectedImage ? JSON.stringify(selectedImage) : ''}
            onChange={(e) => {
              if (e.target.value) {
                setSelectedImage(JSON.parse(e.target.value));
              } else {
                setSelectedImage('');
              }
            }}
            style={{
              flex: 1,
              padding: '6px',
              borderRadius: '4px',
              border: '1px solid #3e3e42',
              background: '#1a1a1a',
              color: '#e0e0e0'
            }}
          >
            <option value="">None</option>
            {imageOptions.map((img, idx) => (
              <option key={idx} value={JSON.stringify(img)}>{img.name}</option>
            ))}
          </select>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                setBackgroundUrl(URL.createObjectURL(file));
              }
            }}
            style={{ display: 'none' }}
            id="bg-upload"
          />
          <label
            htmlFor="bg-upload"
            style={{
              padding: '6px 12px',
              background: '#3498db',
              borderRadius: '4px',
              cursor: 'pointer',
              whiteSpace: 'nowrap'
            }}
          >
            📁 Upload
          </label>
        </div>
      </div>
        )}
      </div>
      )}

      {/* Drawing Tools - Hidden in Watcher Mode */}
      {!watcherMode && (
      <div style={{
        background: '#2a2a2a',
        borderRadius: '8px',
        overflow: 'hidden',
        flexShrink: 0
      }}>
        {/* Drawing Tools Header */}
        <div
          onClick={() => setShowDrawingTools(!showDrawingTools)}
          style={{
            padding: '12px 16px',
            background: 'linear-gradient(135deg, #34495e, #2c3e50)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: showDrawingTools ? '1px solid #3e3e42' : 'none',
            transition: 'background 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'linear-gradient(135deg, #3d566e, #34495e)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'linear-gradient(135deg, #34495e, #2c3e50)';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>🎨</span>
            <span style={{ fontWeight: '700', color: '#fff', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Drawing Tools
            </span>
          </div>
          <span style={{ fontSize: '20px', transform: showDrawingTools ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }}>
            ▼
          </span>
        </div>

        {/* Drawing Tools Content */}
        {showDrawingTools && (
      <div style={{
        padding: '15px',
        display: 'flex',
        gap: '15px',
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        {/* Tool Selection - Horizontal Design */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          background: 'linear-gradient(135deg, rgba(52, 152, 219, 0.15), rgba(41, 128, 185, 0.15))',
          padding: '16px 20px',
          borderRadius: '10px',
          border: '2px solid rgba(52, 152, 219, 0.4)',
          boxShadow: '0 4px 12px rgba(52, 152, 219, 0.2)'
        }}>
          <label style={{
            fontWeight: '800',
            color: '#5dade2',
            fontSize: '13px',
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            marginBottom: '2px'
          }}>
            🛠️ Tools
          </label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {[
              { id: 'paint', icon: '🖌️', label: 'Paint' },
              { id: 'eraser', icon: '🧹', label: 'Eraser' },
              { id: 'measure', icon: '📏', label: 'Measure' },
              { id: 'sphere', icon: '⭕', label: 'Sphere (click hex or token)' },
              { id: 'cone', icon: '📐', label: 'Cone (click hex or token)' },
              { id: 'line', icon: '➖', label: 'Line' },
              { id: 'aura', icon: '✨', label: 'Aura (click token)' },
              { id: 'token', icon: '👤', label: 'Move tokens' }
            ].map(tool => (
              <button
                key={tool.id}
                onClick={() => {
                  setCurrentTool(tool.id);
                  // Reset area effect state when switching tools
                  resetAreaEffect();
                }}
                style={{
                  padding: '10px 16px',
                  background: currentTool === tool.id 
                    ? 'linear-gradient(135deg, #3498db, #2980b9)' 
                    : 'rgba(26, 26, 26, 0.8)',
                  border: currentTool === tool.id ? '2px solid #5dade2' : '2px solid #3e3e42',
                  borderRadius: '8px',
                  color: '#e0e0e0',
                  cursor: 'pointer',
                  fontWeight: currentTool === tool.id ? '700' : '500',
                  fontSize: '20px',
                  boxShadow: currentTool === tool.id 
                    ? '0 0 15px rgba(52, 152, 219, 0.5), 0 4px 8px rgba(0,0,0,0.3)' 
                    : '0 2px 4px rgba(0,0,0,0.2)',
                  transition: 'all 0.2s ease',
                  transform: currentTool === tool.id ? 'translateY(-2px)' : 'translateY(0)',
                  minWidth: '48px',
                  minHeight: '48px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title={tool.label}
                onMouseEnter={(e) => {
                  if (currentTool !== tool.id) {
                    e.currentTarget.style.background = 'rgba(52, 152, 219, 0.3)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentTool !== tool.id) {
                    e.currentTarget.style.background = 'rgba(26, 26, 26, 0.8)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }
                }}
              >
                {tool.icon}
              </button>
            ))}
          </div>
        </div>

        {/* Range Input for Sphere/Cone/Aura */}
        {showAreaInput && areaOrigin && (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') && (
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', background: '#1a1a1a', padding: '8px 12px', borderRadius: '6px', border: '2px solid #3498db' }}>
            <label style={{ fontWeight: '600' }}>
              {currentTool === 'sphere' ? 'Diameter (tiles):' : currentTool === 'aura' ? 'Aura Diameter (meters):' : 'Range (meters):'}
            </label>
            <input
              ref={areaRangeInputRef}
              type="number"
              min="1"
              max="20"
              value={areaRange}
              onChange={(e) => setAreaRange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAreaRangeSubmit();
                if (e.key === 'Escape') resetAreaEffect();
              }}
              onFocus={(e) => e.target.select()}
              autoFocus
              style={{
                width: '80px',
                padding: '6px',
                borderRadius: '4px',
                border: '1px solid #3e3e42',
                background: '#2a2a2a',
                color: '#e0e0e0',
                fontSize: '14px'
              }}
            />
            <button
              onClick={handleAreaRangeSubmit}
              style={{
                padding: '6px 12px',
                background: '#2ecc71',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              ✓ Confirm
            </button>
            <button
              onClick={resetAreaEffect}
              style={{
                padding: '6px 12px',
                background: '#e74c3c',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              ✗ Cancel
            </button>
          </div>
        )}

        {/* Direction Instruction for Cone */}
        {showDirectionSelect && currentTool === 'cone' && areaOrigin && (
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', background: '#9b59b6', padding: '8px 12px', borderRadius: '6px' }}>
            <span style={{ fontWeight: '600', color: '#fff' }}>
              {!areaDirection ? '📐 Click first adjacent hex (1/2)' : '📐 Click second adjacent hex (2/2)'}
            </span>
            <button
              onClick={resetAreaEffect}
              style={{
                padding: '6px 12px',
                background: '#e74c3c',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              ✗ Cancel
            </button>
          </div>
        )}

        {/* Aura Tool Settings */}
        {currentTool === 'aura' && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: 'linear-gradient(135deg, rgba(255, 107, 107, 0.15), rgba(231, 76, 60, 0.15))',
            padding: '16px 20px',
            borderRadius: '10px',
            border: '2px solid rgba(255, 107, 107, 0.4)',
            boxShadow: '0 4px 12px rgba(255, 107, 107, 0.2)'
          }}>
            <label style={{ 
              fontWeight: '800', 
              color: '#ff6b6b',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '1.5px'
            }}>
              ✨ Aura Settings
            </label>
            
            {/* Aura Outline Color Picker */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ fontWeight: '600', color: '#e0e0e0', fontSize: '13px', minWidth: '120px' }}>
                Outline Color:
              </label>
              <input
                type="color"
                value={auraOutlineColor}
                onChange={(e) => setAuraOutlineColor(e.target.value)}
                style={{
                  width: '60px',
                  height: '36px',
                  border: '2px solid #3e3e42',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  background: 'transparent'
                }}
              />
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '4px',
                background: auraOutlineColor,
                border: '2px solid #fff',
                boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
              }} />
            </div>
            
            {/* Move Hexes Checkbox */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ 
                fontWeight: '600', 
                color: '#e0e0e0', 
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer'
              }}>
                <input
                  type="checkbox"
                  checked={auraMoveHexes}
                  onChange={(e) => setAuraMoveHexes(e.target.checked)}
                  style={{
                    width: '20px',
                    height: '20px',
                    cursor: 'pointer',
                    accentColor: '#ff6b6b'
                  }}
                />
                Move underlying hexes with token
              </label>
            </div>
            
            {/* Aura Area Effect - only shown if moveHexes is enabled */}
            {auraMoveHexes && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                paddingTop: '10px',
                borderTop: '1px solid rgba(255, 107, 107, 0.3)'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <label style={{ 
                    fontWeight: '700', 
                    color: '#ff6b6b',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '1px'
                  }}>
                    🔮 Aura Area Effect
                  </label>
                  <span style={{
                    fontSize: '11px',
                    color: '#ff6b6b',
                    fontWeight: '600',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    background: 'rgba(255, 107, 107, 0.2)',
                    padding: '3px 10px',
                    borderRadius: '6px',
                    border: '1px solid rgba(255, 107, 107, 0.3)'
                  }}>
                    {EFFECT_PRESETS[currentEffect]?.name || 'None'}
                  </span>
                </div>
                
                <div style={{
                  display: 'flex',
                  gap: '6px',
                  flexWrap: 'wrap',
                  alignItems: 'center'
                }}>
                  {Object.entries(EFFECT_PRESETS).map(([key, preset]) => (
                    <button
                      key={key}
                      onClick={() => setCurrentEffect(key)}
                      style={{
                        padding: '0',
                        width: '44px',
                        height: '44px',
                        background: currentEffect === key ? preset.gradient : 'rgba(42, 42, 42, 0.8)',
                        border: currentEffect === key ? '3px solid #fff' : '2px solid #4e4e52',
                        borderRadius: '8px',
                        color: '#fff',
                        cursor: 'pointer',
                        fontSize: '22px',
                        boxShadow: currentEffect === key 
                          ? `0 0 15px ${preset.glowColor}, 0 4px 8px rgba(0,0,0,0.5)` 
                          : '0 2px 4px rgba(0,0,0,0.3)',
                        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                        transform: currentEffect === key ? 'scale(1.05)' : 'scale(1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                      title={preset.name}
                      onMouseEnter={(e) => {
                        if (currentEffect !== key) {
                          e.currentTarget.style.background = preset.gradient;
                          e.currentTarget.style.transform = 'scale(1.02)';
                          e.currentTarget.style.boxShadow = `0 0 10px ${preset.glowColor}, 0 3px 6px rgba(0,0,0,0.4)`;
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (currentEffect !== key) {
                          e.currentTarget.style.background = 'rgba(42, 42, 42, 0.8)';
                          e.currentTarget.style.transform = 'scale(1)';
                          e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
                        }
                      }}
                    >
                      {preset.emoji}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Enhanced Effect Presets - Horizontal Design */}
        {currentTool !== 'token' && currentTool !== 'aura' && currentTool !== 'eraser' && currentTool !== 'measure' && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            background: 'linear-gradient(135deg, rgba(155, 89, 182, 0.15), rgba(142, 68, 173, 0.15))',
            padding: '16px 20px',
            borderRadius: '10px',
            border: '2px solid rgba(155, 89, 182, 0.4)',
            boxShadow: '0 4px 12px rgba(155, 89, 182, 0.2)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <label style={{ 
                fontWeight: '800', 
                color: '#bb8fce',
                fontSize: '13px',
                textTransform: 'uppercase',
                letterSpacing: '1.5px'
              }}>
                🔮 Elements
              </label>
              <span style={{
                fontSize: '12px',
                color: '#bb8fce',
                fontWeight: '600',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                background: 'rgba(155, 89, 182, 0.2)',
                padding: '4px 12px',
                borderRadius: '6px',
                border: '1px solid rgba(155, 89, 182, 0.3)'
              }}>
                {EFFECT_PRESETS[currentEffect]?.name || 'None'}
              </span>
            </div>
            
            <div style={{
              display: 'flex',
              gap: '8px',
              flexWrap: 'wrap',
              alignItems: 'center'
            }}>
              {Object.entries(EFFECT_PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => setCurrentEffect(key)}
                  style={{
                    padding: '0',
                    width: '52px',
                    height: '52px',
                    background: currentEffect === key ? preset.gradient : 'rgba(42, 42, 42, 0.8)',
                    border: currentEffect === key ? '3px solid #fff' : '2px solid #4e4e52',
                    borderRadius: '10px',
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: '26px',
                    boxShadow: currentEffect === key 
                      ? `0 0 20px ${preset.glowColor}, 0 6px 12px rgba(0,0,0,0.5)` 
                      : '0 3px 6px rgba(0,0,0,0.3)',
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                    transform: currentEffect === key ? 'scale(1.1) translateY(-2px)' : 'scale(1)',
                    position: 'relative',
                    overflow: 'hidden',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title={preset.name}
                  onMouseEnter={(e) => {
                    if (currentEffect !== key) {
                      e.currentTarget.style.background = preset.gradient;
                      e.currentTarget.style.transform = 'scale(1.05) translateY(-1px)';
                      e.currentTarget.style.boxShadow = `0 0 15px ${preset.glowColor}, 0 4px 8px rgba(0,0,0,0.4)`;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (currentEffect !== key) {
                      e.currentTarget.style.background = 'rgba(42, 42, 42, 0.8)';
                      e.currentTarget.style.transform = 'scale(1)';
                      e.currentTarget.style.boxShadow = '0 3px 6px rgba(0,0,0,0.3)';
                    }
                  }}
                >
                  {preset.emoji}
                  {currentEffect === key && (
                    <div style={{
                      position: 'absolute',
                      top: '3px',
                      right: '3px',
                      width: '8px',
                      height: '8px',
                      background: '#fff',
                      borderRadius: '50%',
                      boxShadow: '0 0 8px #fff'
                    }} />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Enhanced Animation Intensity Controls (Advanced Mode Only) */}
        {advancedMode && currentTool !== 'token' && currentEffect !== 'none' && (
          <div style={{
            display: 'flex',
            gap: '15px',
            alignItems: 'center',
            flexWrap: 'wrap',
            background: 'linear-gradient(135deg, rgba(155, 89, 182, 0.1), rgba(52, 152, 219, 0.1))',
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid #3e3e42'
          }}>
            {/* Shade Intensity */}
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column',
              gap: '5px',
              minWidth: '140px'
            }}>
              <label style={{ 
                fontWeight: '600', 
                fontSize: '12px',
                color: '#fff',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Shade Flicker
              </label>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  type="range"
                  value={shadeIntensity}
                  onChange={(e) => setShadeIntensity(parseFloat(e.target.value))}
                  min="0"
                  max="1"
                  step="0.05"
                  style={{ 
                    flex: 1,
                    accentColor: '#9b59b6',
                    cursor: 'pointer'
                  }}
                />
                <span style={{ 
                  minWidth: '40px', 
                  fontSize: '13px',
                  fontWeight: '700',
                  color: '#ffeb3b',
                  textAlign: 'right'
                }}>
                  {Math.round(shadeIntensity * 100)}%
                </span>
              </div>
            </div>
            
            {/* Opacity Intensity */}
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column',
              gap: '5px',
              minWidth: '140px'
            }}>
              <label style={{ 
                fontWeight: '600', 
                fontSize: '12px',
                color: '#fff',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Opacity Flicker
              </label>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                  type="range"
                  value={opacityIntensity}
                  onChange={(e) => setOpacityIntensity(parseFloat(e.target.value))}
                  min="0"
                  max="1"
                  step="0.05"
                  style={{ 
                    flex: 1,
                    accentColor: '#3498db',
                    cursor: 'pointer'
                  }}
                />
                <span style={{ 
                  minWidth: '40px', 
                  fontSize: '13px',
                  fontWeight: '700',
                  color: '#ffeb3b',
                  textAlign: 'right'
                }}>
                  {Math.round(opacityIntensity * 100)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Fade Effect Controls - Always Visible */}
        {currentTool !== 'token' && currentEffect !== 'none' && (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column',
            gap: '8px',
            minWidth: '180px',
            background: 'rgba(231, 76, 60, 0.15)',
            padding: '12px',
            borderRadius: '8px',
            border: '2px solid rgba(231, 76, 60, 0.4)',
            boxShadow: '0 2px 8px rgba(231, 76, 60, 0.2)'
          }}>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px', 
              fontWeight: '700', 
              fontSize: '13px',
              color: '#fff',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={fadeEnabled}
                onChange={(e) => setFadeEnabled(e.target.checked)}
                style={{ 
                  cursor: 'pointer',
                  width: '18px',
                  height: '18px',
                  accentColor: '#e74c3c'
                }}
              />
              <span style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>⏱️ Auto Fade</span>
            </label>
            {fadeEnabled && (
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginLeft: '26px' }}>
                <input
                  type="number"
                  value={fadeSeconds}
                  onChange={(e) => setFadeSeconds(Math.max(1, parseInt(e.target.value) || 1))}
                  min="1"
                  max="60"
                  style={{
                    width: '65px',
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '2px solid #e74c3c',
                    background: '#2a2a2a',
                    color: '#fff',
                    fontSize: '14px',
                    fontWeight: '600'
                  }}
                />
                <span style={{ fontSize: '12px', color: '#ffeb3b', fontWeight: '600' }}>seconds</span>
              </div>
            )}
          </div>
        )}

        {/* Color Picker */}
        {currentTool !== 'token' && currentTool !== 'eraser' && currentTool !== 'measure' && currentEffect === 'none' && (
          <>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <label style={{ fontWeight: '600' }}>Color:</label>
              <input
                type="color"
                value={brushColor}
                onChange={(e) => setBrushColor(e.target.value)}
                style={{
                  width: '50px',
                  height: '35px',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              />
              <div style={{
                padding: '6px 12px',
                background: '#1a1a1a',
                borderRadius: '4px',
                fontFamily: 'monospace',
                fontSize: '14px'
              }}>
                {brushColor}
              </div>
            </div>

            {/* Color Palette */}
            <div style={{ display: 'flex', gap: '6px' }}>
              {STANDARD_COLORS.map(color => (
                <div
                  key={color}
                  onClick={() => setBrushColor(color)}
                  style={{
                    width: '28px',
                    height: '28px',
                    backgroundColor: color,
                    borderRadius: '4px',
                    cursor: 'pointer',
                    border: brushColor === color ? '3px solid #fff' : '1px solid #555',
                    transition: 'transform 0.1s'
                  }}
                  onMouseEnter={(e) => e.target.style.transform = 'scale(1.1)'}
                  onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
                />
              ))}
            </div>
          </>
        )}

        {/* Clear Grid Button - Always visible */}
        <button
          onClick={handleClearGrid}
          style={{
            padding: '8px 16px',
            background: '#e74c3c',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '600',
            boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
          }}
        >
          🗑️ Clear Grid
        </button>

        {/* Token Controls */}
        {currentTool === 'token' && selectedToken && (
          <>
            <button
              onClick={() => handleRemoveToken(selectedToken)}
              style={{
                padding: '8px 16px',
                background: '#e74c3c',
                border: 'none',
                borderRadius: '4px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              🗑️ Remove Selected Token
            </button>
            
            {/* Remove Aura Button - only show if token has an aura */}
            {tokens.find(t => t.id === selectedToken)?.aura && (
              <button
                onClick={() => {
                  saveToHistory();
                  
                  // Remove aura metadata from token
                  setTokens(prev => prev.map(t => 
                    t.id === selectedToken 
                      ? { ...t, aura: undefined }
                      : t
                  ));
                  
                  // Clear aura hexes if they exist
                  setHexGrid(prev => {
                    const updated = prev.map(r => r.map(c => ({ ...c })));
                    for (let r = 0; r < gridSize.rows; r++) {
                      for (let c = 0; c < gridSize.cols; c++) {
                        const cell = updated[r]?.[c];
                        if (cell && cell.auraTokenId === selectedToken) {
                          updated[r][c] = {
                            filled: false,
                            color: '#3498db',
                            effect: 'none',
                            animationOffset: Math.random() * 10,
                            paintedAt: null,
                            auraTokenId: null
                          };
                        }
                      }
                    }
                    return updated;
                  });
                }}
                style={{
                  padding: '8px 16px',
                  background: '#9b59b6',
                  border: 'none',
                  borderRadius: '4px',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                ✨ Remove Aura
              </button>
            )}
          </>
        )}
      </div>
        )}
      </div>
      )}
      
      {/* Canvas */}
      <div
        ref={canvasRef}
        style={{
          minHeight: watcherMode ? '100vh' : '600px',
          flexGrow: 1,
          background: '#1a1a1a',
          borderRadius: watcherMode ? '0' : '8px',
          overflow: 'auto', // Always allow scrolling for panning
          position: 'relative',
          padding: watcherMode ? '0' : '20px'
        }}
      >
        {/* Zoom and Rotation Wrapper - Applied to both layers equally */}
        <div
          style={{
            transform: watcherMode 
              ? `scale(${scale}) rotate(${watcherRotation}deg)` 
              : `scale(${scale})`,
            transformOrigin: 'center center',
            position: 'relative',
            width: `${svgWidth}px`,
            height: `${svgHeight}px`,
            margin: 'auto'
          }}
        >
          {/* Background Image Layer - Fixed size, doesn't scale with hexSize */}
          {backgroundUrl && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: `${imageDimensions.width}px`,
                height: `${imageDimensions.height}px`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
                zIndex: 0
              }}
            >
              <img
                src={backgroundUrl}
                alt="Battlemap background"
                onLoad={(e) => {
                  // Update container size to match actual image dimensions
                  setImageDimensions({
                    width: e.target.naturalWidth,
                    height: e.target.naturalHeight
                  });
                }}
                style={{
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                  opacity: 0.7
                }}
              />
            </div>
          )}

          {/* Hex Grid Layer - Scales with hexSize */}
          <div
            style={{
              width: `${svgWidth}px`,
              height: `${svgHeight}px`,
              position: 'relative',
              margin: '0',
              zIndex: 1
            }}
          >
          {/* Hex Grid SVG */}
          <svg
            width={svgWidth}
            height={svgHeight}
            style={{
              position: 'absolute',
              top: 0,
              left: 0
            }}
            onMouseUp={() => setIsPainting(false)}
            onMouseLeave={() => setIsPainting(false)}
          >
            {/* SVG Definitions for effect patterns */}
            <defs>
              {/* Fire gradient */}
              <radialGradient id="fireGradient">
                <stop offset="0%" stopColor="#ffaa00" stopOpacity="0.9" />
                <stop offset="50%" stopColor="#ff6b1a" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#ff4444" stopOpacity="0.5" />
              </radialGradient>
              
              {/* Ice gradient */}
              <linearGradient id="iceGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ccffff" stopOpacity="0.8" />
                <stop offset="50%" stopColor="#88ccff" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#66bbee" stopOpacity="0.7" />
              </linearGradient>
              
              {/* Earth texture pattern */}
              <pattern id="earthPattern" width="20" height="20" patternUnits="userSpaceOnUse">
                <rect width="20" height="20" fill="#8b6f47" />
                <circle cx="5" cy="5" r="2" fill="#6f5436" opacity="0.6" />
                <circle cx="15" cy="8" r="3" fill="#9a7b5a" opacity="0.5" />
                <circle cx="8" cy="15" r="2.5" fill="#6f5436" opacity="0.7" />
                <circle cx="18" cy="17" r="2" fill="#a0826d" opacity="0.6" />
              </pattern>
            </defs>

            {hexGrid.map((row, rIdx) =>
              row.map((cell, cIdx) => {
                const { cx, cy } = getHexCoordinates(rIdx, cIdx);
                const points = getHexVertices(cx, cy);
                const hasToken = tokens.some(t => t.row === rIdx && t.col === cIdx);
                
                // Get animated style if cell has effect
                const animStyle = cell.filled && cell.effect !== 'none' 
                  ? getAnimatedStyle(cell) 
                  : null;
                
                // Get glow effect for animated cells
                const effectPreset = cell.effect && EFFECT_PRESETS[cell.effect];
                const glowFilter = effectPreset && effectPreset.glowColor
                  ? `drop-shadow(0 0 4px ${effectPreset.glowColor})`
                  : undefined;

                // Check if this hex is on the outer edge of the grid
                const isOuterEdge = rIdx === 0 || rIdx === gridSize.rows - 1 || 
                                   cIdx === 0 || cIdx === gridSize.cols - 1;

                return (
                  <polygon
                    key={`hex-${rIdx}-${cIdx}`}
                    points={points}
                    fill={animStyle ? animStyle.color : (cell.filled ? cell.color : 'transparent')}
                    fillOpacity={animStyle ? animStyle.opacity : (cell.filled ? 0.5 : 0)}
                    stroke={hasToken ? '#64c8ff' : (isOuterEdge ? 'rgba(150, 150, 150, 0.6)' : 'rgba(150, 150, 150, 0.3)')}
                    strokeWidth={hasToken ? 3 : (isOuterEdge ? 2 : 1)}
                    style={{
                      cursor: currentTool === 'token' ? 'pointer' : 
                              (showDirectionSelect && currentTool === 'cone') ? 'pointer' :
                              'crosshair',
                      transition: animStyle ? 'none' : 'all 0.1s',
                      filter: glowFilter
                    }}
                    onMouseDown={(e) => {
                      if (currentTool === 'token') {
                        handleHexClick(rIdx, cIdx, false);
                      } else if (currentTool === 'measure' || currentTool === 'line' || 
                                 currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') {
                        // For click-based tools, just handle the click
                        handleHexClick(rIdx, cIdx, false);
                      } else {
                        // For paint/eraser tools, save to history when starting to paint/draw
                        if (!isPainting) {
                          saveToHistory();
                        }
                        setIsPainting(true);
                        setPaintMode(!e.altKey && e.button !== 2);
                        handleHexClick(rIdx, cIdx, e.altKey || e.button === 2);
                      }
                    }}
                    onMouseEnter={() => {
                      if (isPainting && currentTool === 'paint') {
                        handleHexPaint(rIdx, cIdx, !paintMode);
                      } else if (isPainting && currentTool === 'eraser') {
                        handleHexPaint(rIdx, cIdx, true);
                      }
                    }}
                    onMouseUp={() => {
                      if (draggedToken) {
                        handleTokenDrop(rIdx, cIdx);
                      }
                    }}
                    onDragOver={(e) => {
                      if (currentTool === 'token') {
                        e.preventDefault();
                        e.dataTransfer.dropEffect = 'copy';
                      }
                    }}
                    onDrop={(e) => {
                      if (currentTool === 'token') {
                        e.preventDefault();
                        try {
                          const charData = JSON.parse(e.dataTransfer.getData('character'));
                          if (charData && charData.name) {
                            handleAddToken(charData, rIdx, cIdx);
                          }
                        } catch (err) {
                          console.error('Error dropping token:', err);
                        }
                      }
                    }}
                    onContextMenu={(e) => e.preventDefault()}
                  />
                );
              })
            )}

            {/* Effect Graphics Layer */}
            {hexGrid.map((row, rIdx) =>
              row.map((cell, cIdx) => {
                if (!cell.filled || cell.effect === 'none') return null;
                const { cx, cy } = getHexCoordinates(rIdx, cIdx);
                return renderEffectGraphics(cell.effect, cx, cy, rIdx, cIdx);
              })
            )}

            {/* Token Auras - visualize hexes marked as aura tiles */}
            {tokens.map(token => {
              // Only render aura outline if token has aura metadata
              if (!token.aura) return null;
              
              // Find all hexes that are aura tiles for this token (if moveHexes is enabled)
              // OR calculate aura pattern based on diameter (if moveHexes is disabled)
              let auraHexes = [];
              
              if (token.aura.moveHexes) {
                // Find hexes marked with auraTokenId
                for (let r = 0; r < gridSize.rows; r++) {
                  for (let c = 0; c < gridSize.cols; c++) {
                    const cell = hexGrid[r]?.[c];
                    if (cell && cell.auraTokenId === token.id) {
                      auraHexes.push({ row: r, col: c });
                    }
                  }
                }
              } else {
                // Generate aura pattern on the fly based on token position and diameter
                auraHexes = generateSpherePattern(token.row, token.col, token.aura.diameter);
              }
              
              if (auraHexes.length === 0) return null;
              
              // Create a set for fast lookup
              const auraSet = new Set(auraHexes.map(h => `${h.row},${h.col}`));
              
              // Find outer edges by checking which hex edges don't have a neighbor in the aura
              const outerEdges = [];
              
              auraHexes.forEach(({ row, col }) => {
                const { cx, cy } = getHexCoordinates(row, col);
                const neighbors = getHexNeighbors(row, col);
                
                // Get all 6 vertices of this hex
                // Vertices go: 0=top, 1=top-right, 2=bottom-right, 3=bottom, 4=bottom-left, 5=top-left
                const hexVertices = [];
                for (let i = 0; i < 6; i++) {
                  const angle = (Math.PI / 3) * i + Math.PI / 2;
                  const x = cx + hexSize * Math.cos(angle);
                  const y = cy + hexSize * Math.sin(angle);
                  hexVertices.push({ x, y });
                }
                
                // Map between edge indices and neighbor indices
                // Neighbors are: [NW, NE, E, SE, SW, W]
                // Rotated 2 positions to the right from [3, 4, 5, 0, 1, 2]:
                // Edge 0-1 (top to top-right) → NE (neighbor[1])
                // Edge 1-2 (top-right to bottom-right) → E (neighbor[2])
                // Edge 2-3 (bottom-right to bottom) → SE (neighbor[3])
                // Edge 3-4 (bottom to bottom-left) → SW (neighbor[4])
                // Edge 4-5 (bottom-left to top-left) → W (neighbor[5])
                // Edge 5-0 (top-left to top) → NW (neighbor[0])
                const edgeToNeighborMap = [4, 5, 0, 1, 2, 3]; // Maps edge index to neighbor index (rotated 2 right)
                
                // Check each edge (between consecutive vertices)
                for (let i = 0; i < 6; i++) {
                  const neighborIdx = edgeToNeighborMap[i];
                  const neighbor = neighbors[neighborIdx];
                  const isNeighborInAura = neighbor && auraSet.has(`${neighbor.row},${neighbor.col}`);
                  
                  if (!isNeighborInAura) {
                    // This edge is on the outer boundary
                    const v1 = hexVertices[i];
                    const v2 = hexVertices[(i + 1) % 6];
                    outerEdges.push({ x1: v1.x, y1: v1.y, x2: v2.x, y2: v2.y });
                  }
                }
              });
              
              return (
                <g key={`aura-outline-${token.id}`}>
                  {outerEdges.map((edge, idx) => (
                    <line
                      key={`aura-edge-${idx}`}
                      x1={edge.x1}
                      y1={edge.y1}
                      x2={edge.x2}
                      y2={edge.y2}
                      stroke={token.aura.outlineColor || '#64c8ff'}
                      strokeWidth={3}
                      strokeOpacity={0.8}
                      strokeLinecap="round"
                      style={{ pointerEvents: 'none' }}
                    />
                  ))}
                </g>
              );
            })}

            {/* Tokens */}
            {tokens.map(token => {
              const { cx, cy } = getHexCoordinates(token.row, token.col);
              const isEnemy = token.type === 'enemy';
              const isPlayer = token.type === 'player';
              const points = getHexVertices(cx, cy);
              
              return (
                <g
                  key={token.id}
                  onMouseDown={(e) => {
                    // For sphere/cone/aura tools, let the click pass through to the hex
                    if (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') {
                      // Don't handle the token drag, let it bubble to hex
                      return;
                    }
                    // For other tools, handle token dragging normally
                    handleTokenDragStart(token.id);
                  }}
                  style={{ 
                    cursor: (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') ? 'crosshair' : 'move',
                    pointerEvents: (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') ? 'none' : 'auto'
                  }}
                >
                  {/* Token Background Hexagon with gradient */}
                  <defs>
                    <linearGradient id={`tokenGradient-${token.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor={token.color || '#888'} />
                      <stop offset="100%" stopColor={`${token.color || '#888'}dd`} />
                    </linearGradient>
                    
                    {/* Clipping path for hexagon */}
                    <clipPath id={`hex-clip-token-${token.id}`}>
                      <polygon points={points} />
                    </clipPath>
                  </defs>
                  
                  <polygon
                    points={points}
                    fill={`url(#tokenGradient-${token.id})`}
                    stroke={token.color || '#888'}
                    strokeWidth={3}
                    strokeDasharray={isEnemy ? '5,3' : 'none'}
                    style={{
                      filter: selectedToken === token.id 
                        ? 'drop-shadow(0 0 10px rgba(100, 200, 255, 0.8))'
                        : isEnemy 
                          ? 'drop-shadow(0 2px 6px rgba(231, 76, 60, 0.5))'
                          : 'drop-shadow(0 2px 4px rgba(39, 174, 96, 0.5))'
                    }}
                  />
                  
                  {/* Token Icon/Avatar with hex clipping */}
                  {token.avatar && isPlayer ? (
                    // Use foreignObject to embed PixelAvatar component in SVG with hex clipping
                    <g clipPath={`url(#hex-clip-token-${token.id})`}>
                      <foreignObject
                        x={cx - hexSize}
                        y={cy - hexSize}
                        width={hexSize * 2}
                        height={hexSize * 2}
                        style={{ pointerEvents: 'none' }}
                      >
                        <div style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center',
                          width: '100%',
                          height: '100%'
                        }}>
                          <PixelAvatar
                            pixels={normalizeAvatarMatrix(token.avatar)}
                            size={hexSize * 2}
                            borderColor="transparent"
                            background="transparent"
                            placeholderLabel={token.name}
                          />
                        </div>
                      </foreignObject>
                    </g>
                  ) : token.icon ? (
                    // Enemy token with icon emoji - centered in hex
                    <text
                      x={cx}
                      y={cy}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={hexSize * 1.2}
                      style={{ pointerEvents: 'none' }}
                    >
                      {token.icon}
                    </text>
                  ) : (
                    // Fallback: First 3 letters
                    <text
                      x={cx}
                      y={cy}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="#fff"
                      fontSize={hexSize * 0.6}
                      fontWeight="bold"
                      style={{ pointerEvents: 'none', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}
                    >
                      {token.name.slice(0, 3).toUpperCase()}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Measurement Line and Display */}
            {measureStart && (
              <>
                {/* Highlight start hex */}
                {(() => {
                  const { cx, cy } = getHexCoordinates(measureStart.row, measureStart.col);
                  const points = getHexVertices(cx, cy);
                  return (
                    <polygon
                      points={points}
                      fill="none"
                      stroke="#ffeb3b"
                      strokeWidth={3}
                      strokeDasharray="5,5"
                    />
                  );
                })()}
                
                {/* Line to current end point or mouse */}
                {measureEnd && (
                  <>
                    {/* Line connecting the hexes */}
                    {(() => {
                      const start = getHexCoordinates(measureStart.row, measureStart.col);
                      const end = getHexCoordinates(measureEnd.row, measureEnd.col);
                      return (
                        <line
                          x1={start.cx}
                          y1={start.cy}
                          x2={end.cx}
                          y2={end.cy}
                          stroke="#ffeb3b"
                          strokeWidth={3}
                          strokeDasharray="8,4"
                        />
                      );
                    })()}
                    
                    {/* Highlight end hex */}
                    {(() => {
                      const { cx, cy } = getHexCoordinates(measureEnd.row, measureEnd.col);
                      const points = getHexVertices(cx, cy);
                      return (
                        <polygon
                          points={points}
                          fill="none"
                          stroke="#ffeb3b"
                          strokeWidth={3}
                          strokeDasharray="5,5"
                        />
                      );
                    })()}
                  </>
                )}
              </>
            )}

            {/* Distance Display */}
            {showMeasurement && measureDistance !== null && measureStart && measureEnd && (
              <>
                {(() => {
                  const start = getHexCoordinates(measureStart.row, measureStart.col);
                  const end = getHexCoordinates(measureEnd.row, measureEnd.col);
                  const midX = (start.cx + end.cx) / 2;
                  const midY = (start.cy + end.cy) / 2;
                  
                  return (
                    <g>
                      {/* Background box */}
                      <rect
                        x={midX - 40}
                        y={midY - 25}
                        width={80}
                        height={50}
                        fill="#000"
                        opacity={0.8}
                        rx={8}
                      />
                      {/* Distance text */}
                      <text
                        x={midX}
                        y={midY}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#ffeb3b"
                        fontSize={hexSize * 0.6}
                        fontWeight="bold"
                      >
                        {measureDistance}
                      </text>
                      {/* Label */}
                      <text
                        x={midX}
                        y={midY + 12}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#fff"
                        fontSize={hexSize * 0.3}
                      >
                        {measureDistance === 1 ? 'meter' : 'meters'}
                      </text>
                    </g>
                  );
                })()}
              </>
            )}

            {/* Line Tool Start Point Highlight */}
            {lineStart && currentTool === 'line' && (
              <>
                {(() => {
                  const { cx, cy } = getHexCoordinates(lineStart.row, lineStart.col);
                  const points = getHexVertices(cx, cy);
                  return (
                    <polygon
                      points={points}
                      fill="rgba(52, 152, 219, 0.3)"
                      stroke="#3498db"
                      strokeWidth={3}
                      strokeDasharray="5,5"
                    />
                  );
                })()}
              </>
            )}

            {/* Area Effect Origin Highlight */}
            {areaOrigin && (currentTool === 'sphere' || currentTool === 'cone') && (
              <>
                {/* Highlight origin hex */}
                {(() => {
                  const { cx, cy } = getHexCoordinates(areaOrigin.row, areaOrigin.col);
                  const points = getHexVertices(cx, cy);
                  // Check if there's a token at origin
                  const tokenAtOrigin = tokens.find(t => t.row === areaOrigin.row && t.col === areaOrigin.col);
                  
                  return (
                    <>
                      <polygon
                        points={points}
                        fill="rgba(52, 152, 219, 0.3)"
                        stroke="#3498db"
                        strokeWidth={4}
                        strokeDasharray="5,5"
                      />
                      {/* Show special indicator if token is at origin */}
                      {tokenAtOrigin && (
                        <circle
                          cx={cx}
                          cy={cy}
                          r={hexSize * 0.4}
                          fill="none"
                          stroke="#3498db"
                          strokeWidth={3}
                          strokeDasharray="2,2"
                          style={{
                            pointerEvents: 'none'
                          }}
                        />
                      )}
                    </>
                  );
                })()}
                
                {/* Highlight adjacent hexes for cone direction selection */}
                {showDirectionSelect && currentTool === 'cone' && (() => {
                  const neighbors = getHexNeighbors(areaOrigin.row, areaOrigin.col);
                  return neighbors.map((neighbor, idx) => {
                    const { cx, cy } = getHexCoordinates(neighbor.row, neighbor.col);
                    const points = getHexVertices(cx, cy);
                    
                    // Check if this is the first selected direction
                    const isFirstDirection = areaDirection && 
                      neighbor.row === areaDirection.row && 
                      neighbor.col === areaDirection.col;
                    
                    return (
                      <polygon
                        key={`neighbor-${idx}`}
                        points={points}
                        fill={isFirstDirection ? "rgba(46, 204, 113, 0.5)" : "rgba(155, 89, 182, 0.3)"}
                        stroke={isFirstDirection ? "#2ecc71" : "#9b59b6"}
                        strokeWidth={isFirstDirection ? 4 : 3}
                        strokeDasharray="5,5"
                        style={{ 
                          pointerEvents: 'none'
                        }}
                      />
                    );
                  });
                })()}
              </>
            )}
          </svg>
        </div>
        </div>
      </div>

      {/* Token Library - Floating Panel */}
      {showTokenPanel && (
        <TokenLibrary
          availableCharacters={availableCharacters}
          enemyTokens={enemyTokens}
          onClose={() => setShowTokenPanel(false)}
        />
      )}
      
      {/* Debug Info Panel - Floating Panel */}
      {selectedHexInfo && advancedMode && (
        <div style={{
          position: 'fixed',
          top: '100px',
          right: '20px',
          background: '#1a1a1a',
          border: '2px solid #e74c3c',
          borderRadius: '8px',
          padding: '20px',
          maxWidth: '400px',
          zIndex: 1000,
          color: '#e0e0e0',
          boxShadow: '0 4px 20px rgba(231, 76, 60, 0.3)',
          fontFamily: 'monospace',
          fontSize: '12px'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '15px',
            paddingBottom: '10px',
            borderBottom: '1px solid #444'
          }}>
            <h3 style={{ margin: 0, color: '#e74c3c', fontSize: '16px' }}>🔍 Hex Debug Info</h3>
            <button
              onClick={() => setSelectedHexInfo(null)}
              style={{
                background: '#e74c3c',
                border: 'none',
                color: '#fff',
                cursor: 'pointer',
                borderRadius: '4px',
                padding: '4px 8px',
                fontWeight: '600'
              }}
            >
              ✕
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Basic Info */}
            <div style={{ background: '#2a2a2a', padding: '10px', borderRadius: '4px' }}>
              <div style={{ color: '#3498db', fontWeight: '600', marginBottom: '6px' }}>Node ID:</div>
              <div>{selectedHexInfo.id}</div>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ background: '#2a2a2a', padding: '10px', borderRadius: '4px' }}>
                <div style={{ color: '#3498db', fontWeight: '600', marginBottom: '6px' }}>Row:</div>
                <div>{selectedHexInfo.row}</div>
              </div>
              <div style={{ background: '#2a2a2a', padding: '10px', borderRadius: '4px' }}>
                <div style={{ color: '#3498db', fontWeight: '600', marginBottom: '6px' }}>Column:</div>
                <div>{selectedHexInfo.col}</div>
              </div>
            </div>
            
            {/* Neighbors */}
            <div style={{ background: '#2a2a2a', padding: '10px', borderRadius: '4px' }}>
              <div style={{ color: '#27ae60', fontWeight: '600', marginBottom: '8px' }}>Neighbors:</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px' }}>
                {Object.entries(selectedHexInfo.neighbors).map(([direction, neighborId]) => (
                  <div key={direction} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    padding: '4px 6px',
                    background: '#1a1a1a',
                    borderRadius: '3px',
                    border: neighborId ? '1px solid #27ae60' : '1px solid #555'
                  }}>
                    <span style={{ color: '#f39c12', fontWeight: '600' }}>{direction}:</span>
                    <span style={{ color: neighborId ? '#27ae60' : '#888' }}>
                      {neighborId || 'null'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Cell Data */}
            <div style={{ background: '#2a2a2a', padding: '10px', borderRadius: '4px' }}>
              <div style={{ color: '#9b59b6', fontWeight: '600', marginBottom: '8px' }}>Cell Data:</div>
              <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px' }}>
                  <span>Filled:</span>
                  <span style={{ color: selectedHexInfo.data.filled ? '#27ae60' : '#e74c3c' }}>
                    {selectedHexInfo.data.filled ? 'true' : 'false'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px' }}>
                  <span>Color:</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {selectedHexInfo.data.color}
                    <div style={{ 
                      width: '16px', 
                      height: '16px', 
                      background: selectedHexInfo.data.color,
                      border: '1px solid #fff',
                      borderRadius: '2px'
                    }}></div>
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px' }}>
                  <span>Effect:</span>
                  <span style={{ color: '#f39c12' }}>{selectedHexInfo.data.effect}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px' }}>
                  <span>Animation Offset:</span>
                  <span>{selectedHexInfo.data.animationOffset?.toFixed(2) || 'N/A'}</span>
                </div>
                {selectedHexInfo.data.paintedAt && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px' }}>
                    <span>Painted At:</span>
                    <span style={{ fontSize: '10px' }}>
                      {new Date(selectedHexInfo.data.paintedAt).toLocaleTimeString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Floating Controls for Watcher Mode */}
      {watcherMode && (
        <>
          {/* Camera Control Panel */}
          <div style={{
            position: 'fixed',
            top: '20px',
            left: '20px',
            background: 'linear-gradient(135deg, rgba(30, 30, 35, 0.95), rgba(20, 20, 25, 0.95))',
            border: '2px solid #3e3e42',
            borderRadius: '12px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
            zIndex: 10000,
            minWidth: '280px',
            maxWidth: '320px',
            overflow: 'hidden'
          }}>
            {/* Panel Header */}
            <div
              onClick={() => setShowCameraPanel(!showCameraPanel)}
              style={{
                padding: '12px 16px',
                background: 'linear-gradient(135deg, #34495e, #2c3e50)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: showCameraPanel ? '1px solid #3e3e42' : 'none',
                transition: 'background 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, #3d566e, #34495e)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'linear-gradient(135deg, #34495e, #2c3e50)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '18px' }}>📹</span>
                <span style={{ fontWeight: '700', color: '#fff', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Camera Controls
                </span>
              </div>
              <span style={{ fontSize: '20px', transform: showCameraPanel ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }}>
                ▼
              </span>
            </div>

            {/* Panel Content */}
            {showCameraPanel && (
              <div style={{
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
                color: '#e0e0e0'
              }}>
                {/* Current Position Info */}
                <div style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  padding: '10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontFamily: 'monospace'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: '#888' }}>Zoom:</span>
                    <span style={{ color: '#3498db', fontWeight: '700' }}>{Math.round(scale * 100)}%</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#888' }}>Rotation:</span>
                    <span style={{ color: '#9b59b6', fontWeight: '700' }}>{watcherRotation}°</span>
                  </div>
                </div>

                {/* Zoom Control */}
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '11px',
                    fontWeight: '700',
                    color: '#aaa',
                    marginBottom: '6px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    Zoom Level
                  </label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      type="range"
                      value={scale}
                      onChange={(e) => setScale(parseFloat(e.target.value))}
                      min="0.25"
                      max="3"
                      step="0.05"
                      style={{
                        flex: 1,
                        accentColor: '#3498db',
                        cursor: 'pointer'
                      }}
                    />
                    <span style={{ 
                      minWidth: '50px', 
                      fontSize: '13px',
                      fontWeight: '700',
                      color: '#3498db',
                      textAlign: 'right',
                      fontFamily: 'monospace'
                    }}>
                      {Math.round(scale * 100)}%
                    </span>
                  </div>
                </div>

                {/* Rotation Control */}
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '11px',
                    fontWeight: '700',
                    color: '#aaa',
                    marginBottom: '6px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    Rotation
                  </label>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      onClick={() => setWatcherRotation((prev) => (prev - 90 + 360) % 360)}
                      style={{
                        flex: 1,
                        padding: '8px',
                        background: 'rgba(155, 89, 182, 0.2)',
                        border: '1px solid #9b59b6',
                        borderRadius: '6px',
                        color: '#bb8fce',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: '600',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(155, 89, 182, 0.4)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(155, 89, 182, 0.2)';
                      }}
                    >
                      ↶ -90°
                    </button>
                    <button
                      onClick={() => setWatcherRotation((prev) => (prev + 90) % 360)}
                      style={{
                        flex: 1,
                        padding: '8px',
                        background: 'rgba(155, 89, 182, 0.2)',
                        border: '1px solid #9b59b6',
                        borderRadius: '6px',
                        color: '#bb8fce',
                        cursor: 'pointer',
                        fontSize: '12px',
                        fontWeight: '600',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(155, 89, 182, 0.4)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(155, 89, 182, 0.2)';
                      }}
                    >
                      ↷ +90°
                    </button>
                  </div>
                </div>

                {/* Reset Button */}
                <button
                  onClick={resetWatcherView}
                  style={{
                    padding: '10px',
                    background: 'linear-gradient(135deg, #27ae60, #229954)',
                    border: '2px solid #27ae60',
                    borderRadius: '8px',
                    color: '#fff',
                    cursor: 'pointer',
                    fontWeight: '700',
                    fontSize: '13px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 2px 8px rgba(39, 174, 96, 0.3)'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, #2ecc71, #27ae60)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(39, 174, 96, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, #27ae60, #229954)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(39, 174, 96, 0.3)';
                  }}
                >
                  🎯 Reset to Default View
                </button>

                {/* Exit Watcher Mode Button */}
                <button
                  onClick={toggleWatcherMode}
                  style={{
                    padding: '10px',
                    background: 'linear-gradient(135deg, #e74c3c, #c0392b)',
                    border: '2px solid #e74c3c',
                    borderRadius: '8px',
                    color: '#fff',
                    cursor: 'pointer',
                    fontWeight: '700',
                    fontSize: '13px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 2px 8px rgba(231, 76, 60, 0.3)'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, #ec7063, #e74c3c)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(231, 76, 60, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(231, 76, 60, 0.3)';
                  }}
                >
                  🔴 Exit Watcher Mode
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default BattlemapViewer;
