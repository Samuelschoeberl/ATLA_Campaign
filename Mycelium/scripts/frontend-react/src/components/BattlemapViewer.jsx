import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import './BattlemapViewer.css';
import { API_BASE_URL } from '../config/api';
import PixelAvatar from './PixelAvatar';
import EditDataModal from './EditDataModal';
import TokenMarkers from './battlemap/TokenMarkers';
import MarkerPopup from './battlemap/MarkerPopup';
import TokenContextMenu from './battlemap/TokenContextMenu';
import TokenDetailsPopup from './battlemap/TokenDetailsPopup';
import { 
  loadConditionDescriptions, 
  fetchCharacterSheet, 
  updateCharacterSheet,
  parseSheetVitalsAndConditions,
  buildBasicCharacterSheet,
  loadNpcState,
  saveNpcState
} from '../utils/characterSheetParser';
import { animateToolSelection, animateEffectSelection, animateEffectHover, animateSectionReveal, animateToolHover, animateTokenMoveSvg } from '../utils/battlemapAnimations';
import { EFFECT_PRESETS, STANDARD_COLORS, CONDITION_COLORS } from '../constants/effectPresets';
import { AREA_PATTERNS } from '../constants/areaPatterns';
import {
  offsetToCube,
  cubeToOffset,
  calculateHexDistance,
  getHexNeighbors,
  getNeighborInDirection,
  getDirectionToNeighbor,
  getHexCoordinates,
  getHexVertices,
  generateSpherePattern,
  generateConePattern,
  getTokenCells,
  gridToGraphData,
  initializeHexGrid,
  graphDataToGrid,
  calculateGridSizeForImage,
  generateHexPathPoints,
  generateArcPath,
  getHealthBarColor
} from '../utils/hexUtils';
import {
  getHexGridFilename,
  saveHexGridForImage,
  loadHexGridForImage,
  saveBattlemapState as saveBattlemapStateUtil,
  syncFromServer
} from '../utils/syncUtils';
import {
  subscribe as subscribeToVaultPath,
  patchBattlemapToken,
} from '../data/vaultResource';

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


const BattlemapViewer = ({ filePath, content, advancedMode = false, onFileSelect, initialWatcherMode = false, syncIntervalMs = 8000 }) => {
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
  const [currentTool, setCurrentTool] = useState('select'); // select (default), paint, eraser, measure, sphere, cone, line, token, aura, debug, edit
  const [currentEffect, setCurrentEffect] = useState('fire'); // Effect preset key
  const [brushColor, setBrushColor] = useState('#ff6b6b');
  const [isPainting, setIsPainting] = useState(false);
  const [paintMode, setPaintMode] = useState(false); // false = erase
  
  // Edit Data tool state
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null); // { type: 'token' | 'hex', data: {...}, row, col }
  
  // Condition descriptions state
  const [conditionDescriptions, setConditionDescriptions] = useState({});
  
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
  
  // Stable mount timestamp used for image cache-busting (avoids new URL on every render)
  const mountTimestamp = useRef(Date.now());

  // Animation state
  const [animationFrame, setAnimationFrame] = useState(0);
  const [shadeIntensity, setShadeIntensity] = useState(0.3); // 0-1, controls color variation
  const [opacityIntensity, setOpacityIntensity] = useState(0.3); // 0-1, controls opacity variation
  
  // Fade effect state
  const [fadeEnabled, setFadeEnabled] = useState(false);
  const [fadeSeconds, setFadeSeconds] = useState(3);
  
  // Token state
  const [tokens, setTokens] = useState([]); // { id, row, col, name, avatar, color, aura, width, height, showHp }
  const [selectedToken, setSelectedToken] = useState(null);
  const [draggedToken, setDraggedToken] = useState(null);
  const [dragPreview, setDragPreview] = useState(null); // { row, col }
  const [tokenToMove, setTokenToMove] = useState(null); // Token ID to move on next hex click
  const tokenRefs = useRef(new Map());
  const prevTokenCentersRef = useRef(new Map());
  
  // Camera panning state (for select/neutral mode)
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [scrollStart, setScrollStart] = useState({ x: 0, y: 0 });
  
  // Context menu state
  const [contextMenu, setContextMenu] = useState(null); // { x, y, tokenId }
  
  // Marker popup state
  const [markerPopup, setMarkerPopup] = useState(null); // { type: 'condition'|'defensive', tokenId, data, x, y }
  
  // Token details popup state
  const [detailsPopupToken, setDetailsPopupToken] = useState(null); // Token object to display details for
  
  // Token placement tool state
  const [tokenToPlace, setTokenToPlace] = useState(null); // { name, avatar, color, icon, type, width, height }
  const [tokenPlacementSize, setTokenPlacementSize] = useState({ width: 1, height: 1 });
  
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
  const [navOpen, setNavOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('toolbar');
  const [sectionVisibility, setSectionVisibility] = useState({
    toolbar: false,
    drawing: false,
    tokens: false,
    camera: false,
    effects: false
  });
  const [drawingToolsCollapsed, setDrawingToolsCollapsed] = useState(false); // Collapse UI but keep tool active

  // Cache for normalized PNG data URLs (avoid repeat canvas work)
  const normalizedImageCacheRef = useRef(new Map());
  const [normalizedSrcMap, setNormalizedSrcMap] = useState(new Map());

  // Re-encode PNGs client-side to strip any remaining color profile for SVG rendering
  const normalizeDataUrl = async (dataUrl) => {
    if (!dataUrl || !dataUrl.startsWith('data:image')) return dataUrl;
    if (normalizedImageCacheRef.current.has(dataUrl)) {
      return normalizedImageCacheRef.current.get(dataUrl);
    }
    try {
      const normalized = await new Promise(async (resolve, reject) => {
        try {
          // Prefer createImageBitmap path to avoid premultiplied alpha/gamma surprises
          if (window.createImageBitmap) {
            const blob = await (await fetch(dataUrl)).blob();
            const bitmap = await createImageBitmap(blob, {
              colorSpaceConversion: 'none',
              premultiplyAlpha: 'none'
            });
            const canvas = document.createElement('canvas');
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            const ctx = canvas.getContext('2d', { alpha: true, colorSpace: 'srgb' });
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(bitmap, 0, 0);
            resolve(canvas.toDataURL('image/png'));
            return;
          }
        } catch (e) {
          console.warn('normalizeDataUrl createImageBitmap failed, falling back', e);
        }

        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext('2d', { alpha: true, colorSpace: 'srgb' });
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0);
          resolve(canvas.toDataURL('image/png'));
        };
        img.onerror = reject;
        img.src = dataUrl;
      });
      normalizedImageCacheRef.current.set(dataUrl, normalized);
      return normalized;
    } catch (err) {
      console.warn('normalizeDataUrl failed, using original', err);
      return dataUrl;
    }
  };

  // Ensure all token images are normalized once loaded
  useEffect(() => {
    // Skip normalization - just use raw images
  }, [tokens]);

  const NAV_SECTIONS = [
    { id: 'toolbar', label: 'Tools', icon: '⚙️', color: '#3498db' },
    { id: 'drawing', label: 'Draw', icon: '🎨', color: '#9b59b6' },
    { id: 'tokens', label: 'Tokens', icon: '🎭', color: '#e67e22', onNavigate: () => setCurrentTool('place-token') },
    { id: 'camera', label: 'View', icon: '📹', color: '#27ae60' },
    { id: 'effects', label: 'FX', icon: '✨', color: '#e74c3c', onNavigate: () => setCurrentTool('aura') }
  ];

  const currentToolLabel = (() => {
    switch (currentTool) {
      case 'paint': return 'Paint';
      case 'eraser': return 'Eraser';
      case 'measure': return 'Measure';
      case 'sphere': return 'Sphere';
      case 'cone': return 'Cone';
      case 'line': return 'Line';
      case 'token': return 'Token Select';
      case 'place-token': return 'Place Token';
      case 'aura': return 'Aura';
      case 'debug': return 'Debug';
      default: return 'None';
    }
  })();
  
  // Watcher Mode state
  const [watcherMode, setWatcherMode] = useState(initialWatcherMode);
  const [defaultCameraScale, setDefaultCameraScale] = useState(1.0);
  const [preWatcherScale, setPreWatcherScale] = useState(1.0); // Store scale before entering watcher mode
  const [watcherRotation, setWatcherRotation] = useState(0); // Rotation angle for watcher mode (0 or 90 degrees)
  const [watcherDefaultView, setWatcherDefaultView] = useState({ scale: 1.0, rotation: 0 }); // Store the calculated optimal view
  const [preWatcherTool, setPreWatcherTool] = useState('select'); // Remember tool before watcher mode
  const [showCameraPanel, setShowCameraPanel] = useState(false); // Toggle for camera control panel
  
  // Advanced Mode Fullscreen state
  const [advancedFullscreen, setAdvancedFullscreen] = useState(false);
  
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
  const toolbarContentRef = useRef(null);
  const drawingToolsContentRef = useRef(null);
  const pendingPaintsRef = useRef(new Map());
  const paintRafRef = useRef(null);
  
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
        setCurrentTool('select');
      }
      setSelectedHexInfo(null);
    }
  }, [advancedMode, currentTool]);

  // Load condition descriptions on mount
  useEffect(() => {
    const loadConditions = async () => {
      try {
        const descriptions = await loadConditionDescriptions(API_BASE_URL);
        setConditionDescriptions(descriptions);
        console.log('Loaded condition descriptions:', Object.keys(descriptions));
      } catch (error) {
        console.error('Error loading condition descriptions:', error);
      }
    };
    loadConditions();
  }, []);

  // (Collapsible animations removed; sections remain always visible for smoother nav)

  const scrollToSection = (sectionId) => {
    const target = document.querySelector(`[data-section-id="${sectionId}"]`);
    if (!target) return;
    const headerOffset = 76;
    const y = target.getBoundingClientRect().top + window.scrollY - headerOffset;
    window.scrollTo({ top: y, behavior: 'smooth' });
    setActiveSection(sectionId);
  };

  // Track visible section for nav highlighting
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const id = entry.target.getAttribute('data-section-id');
          if (id) setActiveSection(id);
        }
      });
    }, { threshold: 0.4 });

    const nodes = document.querySelectorAll('[data-section-id]');
    nodes.forEach(node => observer.observe(node));
    return () => observer.disconnect();
  }, [sectionVisibility]);

  // Keep active section aligned with visible sections
  useEffect(() => {
    const visibleIds = NAV_SECTIONS.filter(s => sectionVisibility[s.id]).map(s => s.id);
    if (!visibleIds.includes(activeSection) && visibleIds.length > 0) {
      setActiveSection(visibleIds[0]);
    }
  }, [sectionVisibility, activeSection]);

  // Gently reveal sections when they become visible
  useEffect(() => {
    Object.entries(sectionVisibility).forEach(([id, isVisible]) => {
      if (!isVisible) return;
      const node = document.querySelector(`[data-section-id="${id}"]`);
      if (node) {
        try { animateSectionReveal(node); } catch (e) { /* animejs compat */ }
      }
    });
  }, [sectionVisibility]);

  // Animate token motion inside the SVG layer
  useEffect(() => {
    const computeCenter = (token) => {
      const width = token.width || 1;
      const height = token.height || 1;
      const first = getHexCoordinates(token.row, token.col);
      const last = getHexCoordinates(token.row + height - 1, token.col + width - 1);
      return {
        x: (first.cx + last.cx) / 2,
        y: (first.cy + last.cy) / 2
      };
    };

    const seen = new Set();
    tokens.forEach((token) => {
      const el = tokenRefs.current.get(token.id);
      if (!el) return;
      const center = computeCenter(token);
      const prev = prevTokenCentersRef.current.get(token.id);
      if (prev && (prev.x !== center.x || prev.y !== center.y)) {
        animateTokenMoveSvg(el, prev, center);
      }
      prevTokenCentersRef.current.set(token.id, center);
      seen.add(token.id);
    });

    // cleanup removed tokens
    Array.from(prevTokenCentersRef.current.keys()).forEach((id) => {
      if (!seen.has(id)) {
        prevTokenCentersRef.current.delete(id);
        tokenRefs.current.delete(id);
      }
    });
  }, [tokens, hexSize]);

  // Directory path for images
  const dirPath = useMemo(() => {
    if (!filePath || !filePath.includes('/')) return '';
    const parts = filePath.split('/');
    parts.pop();
    return parts.join('/');
  }, [filePath]);

  // Animation loop for effects - optimized with CSS animations
  useEffect(() => {
    if (!fadeEnabled || fadeSeconds <= 0) return;
    
    let animationId;
    let lastFadeCheck = Date.now();
    const fadeCheckInterval = 1000; // Check fade every 1 second
    
    const checkFade = () => {
      const now = Date.now();
      
      // Only check fade effect periodically to reduce computation
      if (now - lastFadeCheck >= fadeCheckInterval) {
        lastFadeCheck = now;
        const fadeMs = fadeSeconds * 1000;
        
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
      
      animationId = requestAnimationFrame(checkFade);
    };
    
    animationId = requestAnimationFrame(checkFade);
    
    return () => cancelAnimationFrame(animationId);
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

  // Pinch-to-zoom on trackpad (two-finger zoom)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleWheel = (e) => {
      // Check if this is a pinch gesture (ctrlKey is set for pinch on most browsers)
      if (e.ctrlKey) {
        e.preventDefault();
        
        // deltaY is negative when pinching out (zooming in), positive when pinching in (zooming out)
        const delta = -e.deltaY;
        const zoomIntensity = 0.002; // Adjust sensitivity
        const newScale = Math.max(0.1, Math.min(5, scale + delta * zoomIntensity));
        
        setScale(newScale);
      }
    };

    // Use passive: false to allow preventDefault
    canvas.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', handleWheel);
  }, [scale]);

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
        await saveHexGridForImage(prevImageName, dirPath, gridSize, hexGrid, tokens, hexSize);
      }

      // Load hex grid for new image (if it exists)
      if (currentImageName) {
        console.log('🔄 Loading hex grid for new image:', currentImageName);
        const loadedData = await loadHexGridForImage(currentImageName, dirPath);

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
  const initializeHexGrid = useCallback((rows, cols) => {
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
  }, []);

  // Get all cells occupied by a token based on its position and size
  // For a 2x2 token at position (5,9), it occupies: (5,9), (5,10), (6,9), (6,10)
  const getTokenCells = useCallback((row, col, width, height) => {
    const cells = [];
    for (let h = 0; h < height; h++) {
      for (let w = 0; w < width; w++) {
        // In odd-r offset coordinates, moving right increases col
        // Moving down increases row
        cells.push({ row: row + h, col: col + w });
      }
    }
    return cells;
  }, []);

  // Pre-computed Set of "row-col" keys for all token-occupied cells.
  // Avoids O(tokens × cells) scan inside the hex render loop — O(1) lookup instead.
  const tokenOccupiedCells = useMemo(() => {
    const occupied = new Set();
    tokens.forEach(t => {
      getTokenCells(t.row, t.col, t.width || 1, t.height || 1).forEach(c => {
        occupied.add(`${c.row}-${c.col}`);
      });
    });
    return occupied;
  }, [tokens, getTokenCells]);

  const waterCellCount = useMemo(() =>
    hexGrid.reduce((count, row) =>
      count + row.filter(cell => cell.filled && cell.effect === 'water').length, 0
    ), [hexGrid]);

  // Use getHexGridFilename from syncUtils

  // Use saveHexGridForImage from syncUtils with current state

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

  // Use loadHexGridForImage from syncUtils

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
        lastSyncTimeRef.current = now; // CRITICAL: Update ref immediately to prevent race condition
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
    // Never auto-save in dedicated watcher mode (read-only tab)
    if (initialWatcherMode) return;
    // Don't trigger auto-save if changes came from sync
    if (isUpdatingFromSyncRef.current) {
      console.log('BattlemapViewer: Skipping auto-save (changes from sync)');
      return; // Don't clear the flag yet - let all state updates finish
    }
    
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    saveTimeoutRef.current = setTimeout(async () => {
      console.log('💾 Auto-save firing (local changes)');
      saveTimeoutRef.current = null;
      saveBattlemapState();
      // Also save hex grid for current image
      if (selectedImage?.name) {
        await saveHexGridForImage(selectedImage.name, dirPath, gridSize, hexGrid, tokens, hexSize);
      }
    }, 3000);
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = null;
      }
    };
  }, [hexGrid, tokens, selectedImage, hexSize, gridSize]);
  
  // Clear the sync flag after all state updates have been processed
  useEffect(() => {
    if (isUpdatingFromSyncRef.current) {
      // Set a short timeout to ensure all state updates from sync are processed
      const timer = setTimeout(() => {
        isUpdatingFromSyncRef.current = false;
        console.log('BattlemapViewer: Sync flag cleared after state updates');
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [hexGrid, tokens, selectedImage, hexSize, gridSize]);
  
  // Sync from server: used to poll on a timer (8s normally, 1.5s in watcher/
  // spectator mode) and compare a client-generated `lastModified` timestamp
  // to decide whether a remote update was "newer" -- vulnerable to clock
  // skew between different players'/the GM's machines. Now driven by the
  // shared SSE stream (vaultResource): the backend publishes a
  // `file_changed` event for this exact path whenever anyone's save lands
  // (including our own -- see the self-echo check below), so there's no
  // polling interval and no client-timestamp ordering at all.
  useEffect(() => {
    if (!filePath) return;

    const applyRemoteState = (rawContent) => {
      if (!rawContent || !rawContent.trim()) return;

      // Self-echo: this SSE event is just confirming our own most recent
      // save landed, not a genuine remote change -- skip reapplying it.
      if (rawContent === lastSavedStateRef.current) return;

      let newState;
      try {
        newState = JSON.parse(rawContent);
      } catch (e) {
        console.error('❌ Battlemap sync: failed to parse remote content', e);
        return;
      }

      if (newState.format === 'graph' && newState.hexGraph) {
        newState.hexGrid = graphDataToGrid(newState.hexGraph, newState.gridSize);
      }

      // Still avoid clobbering an in-flight local edit that hasn't saved yet.
      if (!initialWatcherMode && saveTimeoutRef.current) {
        return;
      }

      isUpdatingFromSyncRef.current = true;

      if (newState.gridSize) setGridSize(newState.gridSize);
      if (newState.hexGrid) setHexGrid(newState.hexGrid);
      if (newState.tokens) setTokens(newState.tokens);
      if (newState.backgroundImage) setSelectedImage(newState.backgroundImage);
      if (newState.hexSize) setHexSize(newState.hexSize);
      const now = newState.lastModified || Date.now();
      setLastSyncTime(now);
      lastSyncTimeRef.current = now;
    };

    const unsubscribe = subscribeToVaultPath(filePath, ({ content }) => applyRemoteState(content));
    return unsubscribe;
  }, [filePath]);

  // Periodic token stats refresh - refresh HP, conditions, and defensive stats every 15 seconds
  useEffect(() => {
    const abortController = new AbortController();

    const refreshTokens = async () => {
      const currentTokens = tokensRef.current;
      const tokensWithSheets = currentTokens.filter(t =>
        t.characterSheetPath || (t.type === 'player' && t.name)
      );
      if (tokensWithSheets.length === 0) return;

      try {
        const updatedTokens = await Promise.all(
          currentTokens.map(async (token) => {
            const sheetPath = token.characterSheetPath ||
              (token.type === 'player' && token.name
                ? `PCs/${token.name}/${token.name} character sheet.md`
                : null);
            if (!sheetPath) return token;

            try {
              const endpoint = token.characterSheetEndpoint || 'player_root';
              const encodedPath = sheetPath.split('/').map(s => encodeURIComponent(s)).join('/');
              const resp = await fetch(`${API_BASE_URL}/${endpoint}/${encodedPath}`, {
                cache: 'no-store',
                signal: abortController.signal
              });
              if (!resp.ok || abortController.signal.aborted) return token;

              const data = await resp.json();
              const content = data.content || '';

              let npcState = null;
              if (token.isTempCharacterSheet) {
                npcState = await loadNpcState(sheetPath, API_BASE_URL);
              }

              const parsed = parseSheetVitalsAndConditions(content, npcState);
              if (!parsed) return token;

              const newCurrentHp = parsed.currentHp ?? token.currentHp;
              const newMaxHp = parsed.maxHp ?? token.maxHp;
              let newConditions = parsed.conditions?.length ? parsed.conditions : (token.conditions || []);

              // Auto-add "Bleeding out" if HP is 0 or below
              const isBleedingOut = newMaxHp > 0 && newCurrentHp <= 0;
              if (isBleedingOut && !newConditions.includes('Bleeding out')) {
                newConditions = [...newConditions, 'Bleeding out'];
              } else if (!isBleedingOut) {
                newConditions = newConditions.filter(c => c !== 'Bleeding out');
              }

              return {
                ...token,
                currentHp: newCurrentHp,
                maxHp: newMaxHp,
                conditions: newConditions,
                defensive: Object.keys(parsed.defensive || {}).length ? parsed.defensive : token.defensive
              };
            } catch (err) {
              if (err.name !== 'AbortError') {
                console.warn(`⚠️ Could not refresh data for ${token.name}:`, err);
              }
            }

            return token;
          })
        );

        if (!abortController.signal.aborted && JSON.stringify(updatedTokens) !== JSON.stringify(tokensRef.current)) {
          setTokens(updatedTokens);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Error refreshing tokens:', err);
        }
      }
    };

    // Initial refresh after delay
    const initialTimeout = setTimeout(refreshTokens, 3000);

    // Set up periodic refresh
    const refreshInterval = setInterval(refreshTokens, 15000); // Every 15 seconds

    return () => {
      abortController.abort();
      clearInterval(refreshInterval);
      clearTimeout(initialTimeout);
    };
  }, []);

  // Cancel pending paint RAF on unmount
  useEffect(() => {
    return () => {
      if (paintRafRef.current) cancelAnimationFrame(paintRafRef.current);
    };
  }, []);

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
      
      // Check if content is valid JSON before parsing
      const trimmedContent = content.trim();
      if (!trimmedContent.startsWith('{') && !trimmedContent.startsWith('[')) {
        console.warn('BattlemapViewer: Content is not JSON format (appears to be Markdown or other format), initializing default state.');
        console.warn('BattlemapViewer: Content preview:', trimmedContent.substring(0, 100));
        console.info('💡 Tip: Select a battlemap.json file instead of a markdown file to load a saved battlemap.');
        const defaultGrid = initializeHexGrid(gridSize.rows, gridSize.cols);
        setHexGrid(defaultGrid);
        return;
      }
      
      let data;
      try {
        data = JSON.parse(trimmedContent);
      } catch (parseError) {
        // Treat non-JSON (e.g., markdown files with [[links]]) as empty battlemap instead of erroring
        console.warn('BattlemapViewer: JSON parse failed, falling back to default battlemap. Error:', parseError.message);
        console.warn('BattlemapViewer: Content preview (first 200 chars):', trimmedContent.substring(0, 200));
        const previewTail = trimmedContent.substring(Math.max(trimmedContent.length - 200, 0));
        console.warn('BattlemapViewer: Content preview (last 200 chars):', previewTail);
        if (trimmedContent.startsWith('[[')) {
          console.info('💡 Tip: This looks like a markdown file with wiki links. Open a battlemap JSON file instead.');
        }
        setHexGrid(initializeHexGrid(gridSize.rows, gridSize.cols));
        return;
      }
      
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
    const abortController = new AbortController();
    
    const fetchImages = async () => {
      try {
        const allFiles = [];
        const fetchPromises = [];
        
        // Fetch images from current directory if available
        if (dirPath) {
          fetchPromises.push(
            fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(dirPath)}`, { signal: abortController.signal })
              .then(resp => resp.ok ? resp.json() : null)
              .then(data => {
                if (data?.entries) {
                  const files = data.entries.filter(e => e.name?.toLowerCase().match(/\.(png|jpe?g|webp)$/));
                  return files.map(f => ({ name: f.name, path: dirPath }));
                }
                return [];
              })
              .catch(err => {
                if (err.name !== 'AbortError') {
                  console.error('Error loading images from current directory:', err);
                }
                return [];
              })
          );
        }
        
        // Fetch images from Battlemaps folder
        const battlemapsPath = 'Maps/Battlemaps';
        fetchPromises.push(
          fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(battlemapsPath)}`, { signal: abortController.signal })
            .then(resp => resp.ok ? resp.json() : null)
            .then(data => {
              if (data?.entries) {
                const files = data.entries.filter(e => e.name?.toLowerCase().match(/\.(png|jpe?g|webp)$/));
                return files.map(f => ({ name: `[Battlemaps] ${f.name}`, path: battlemapsPath }));
              }
              return [];
            })
            .catch(err => {
              if (err.name !== 'AbortError') {
                console.error('Error loading images from Battlemaps:', err);
              }
              return [];
            })
        );
        
        const results = await Promise.all(fetchPromises);
        results.forEach(files => allFiles.push(...files));
        
        if (!abortController.signal.aborted) {
          setImageOptions(allFiles);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Error loading images:', err);
        }
      }
    };
    
    fetchImages();
    
    return () => abortController.abort();
  }, [dirPath]);

  // Load available characters for tokens with their avatars
  useEffect(() => {
    const abortController = new AbortController();
    
    const fetchCharacters = async () => {
      try {
        // Get customizations
        const customResp = await fetch(`${API_BASE_URL}/api/characters/customizations`, { signal: abortController.signal });
        if (!customResp.ok) {
          console.error('BattlemapViewer: Failed to fetch customizations:', customResp.status);
          return;
        }
        const customData = await customResp.json();
        const customizations = customData.customizations || customData || {};
        
        // Scan PCs folder in parallel
        try {
          const pcsResp = await fetch(`${API_BASE_URL}/player_root/PCs`, { signal: abortController.signal });
          if (pcsResp.ok) {
            const pcsData = await pcsResp.json();
            const pcsFolders = pcsData.children || pcsData.folders || (Array.isArray(pcsData) ? pcsData : []);
            
            pcsFolders.forEach(child => {
              const childName = child.name || child;
              const isFolder = child.type === 'folder' || child.type === 'directory' || typeof child === 'string';
              
              if (isFolder && childName && !customizations[childName]) {
                customizations[childName] = {
                  name: childName,
                  folderColor: null,
                  avatarPng: null
                };
              }
            });
          }
        } catch (err) {
          if (err.name !== 'AbortError') {
            console.warn('BattlemapViewer: Could not scan PCs folder:', err);
          }
        }
        
        // Batch load avatar images
        const avatarPromises = Object.entries(customizations).map(async ([name, data]) => {
          if (!data.avatarPng) return [name, null];
          
          if (data.avatarPng.startsWith('data:image')) {
            return [name, data.avatarPng];
          }
          
          try {
            const fetchUrl = `${API_BASE_URL}/player_root/${encodeURIComponent(data.avatarPng)}?cb=${Date.now()}`;
            const imgResponse = await fetch(fetchUrl, { signal: abortController.signal });
            if (imgResponse.ok) {
              const blob = await imgResponse.blob();
              const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
              });
              return [name, dataUrl];
            }
          } catch (err) {
            if (err.name !== 'AbortError') {
              console.error(`Error loading avatar for ${name}:`, err);
            }
          }
          return [name, null];
        });
        
        const avatarResults = await Promise.all(avatarPromises);
        const avatarImages = Object.fromEntries(avatarResults.filter(([_, url]) => url));
        
        if (abortController.signal.aborted) return;
        
        // Convert to character array
        const characters = Object.entries(customizations).map(([name, data]) => ({
          name,
          avatarPng: avatarImages[name] || null,
          avatarPngNormalized: avatarImages[name] || null,
          color: data.folderColor || 'rgba(0,0,0,0)',
          type: 'player'
        }));
        
        setAvailableCharacters(characters);
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Error loading characters:', err);
        }
      }
    };
    
    fetchCharacters();
    
    return () => abortController.abort();
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
        setBackgroundUrl(`${API_BASE_URL}/player_root/${encodeURIComponent(imagePath)}?cb=${Date.now()}`);
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
      // Remember current tool and switch to neutral select for watcher mode
      setPreWatcherTool(currentTool);
      setCurrentTool('select');
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
      setCurrentTool(preWatcherTool || 'select');
    }
    setWatcherMode(!watcherMode);
  };

  const toggleAdvancedFullscreen = () => {
    if (!advancedFullscreen) {
      // Entering advanced fullscreen - hide external UI elements
      const hideElements = () => {
        // Hide file explorer header (search + advanced button)
        const explorerHeaders = document.querySelectorAll('.file-explorer-header, [class*="header"]');
        explorerHeaders.forEach(el => {
          if (el.querySelector('input[type="text"]') || el.textContent.includes('Advanced')) {
            el.style.display = 'none';
            el.setAttribute('data-advanced-fullscreen-hidden', 'true');
          }
        });
        
        // Hide tab bar
        const tabBars = document.querySelectorAll('.tab-bar, [class*="tab"]');
        tabBars.forEach(el => {
          el.style.display = 'none';
          el.setAttribute('data-advanced-fullscreen-hidden', 'true');
        });
        
        // Hide dice roller at bottom
        const diceRollers = document.querySelectorAll('[class*="dice"], [style*="borderTop"]');
        diceRollers.forEach(el => {
          if (el.textContent.includes('Roll') || el.querySelector('button')) {
            el.style.display = 'none';
            el.setAttribute('data-advanced-fullscreen-hidden', 'true');
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
            el.setAttribute('data-advanced-fullscreen-hidden', 'true');
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
                !el.closest('[data-advanced-fullscreen-hidden]')) {
              el.style.display = 'none';
              el.setAttribute('data-advanced-fullscreen-hidden', 'true');
            }
          }
        });
      };
      
      setTimeout(hideElements, 50);
    } else {
      // Exiting advanced fullscreen - restore hidden UI elements
      const hiddenElements = document.querySelectorAll('[data-advanced-fullscreen-hidden="true"]');
      hiddenElements.forEach(el => {
        el.style.display = '';
        el.removeAttribute('data-advanced-fullscreen-hidden');
      });
    }
    
    setAdvancedFullscreen(!advancedFullscreen);
  };

  const resetWatcherView = () => {
    // Reset to the optimal calculated view
    setScale(watcherDefaultView.scale);
    setWatcherRotation(watcherDefaultView.rotation);

    // Also recenter the scroll viewport on the grid
    requestAnimationFrame(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const padding = watcherMode ? 1000 : 20;
      const contentWidth = svgWidth + padding * 2;
      const contentHeight = svgHeight + padding * 2;
      const targetLeft = padding + svgWidth / 2 - canvas.clientWidth / 2;
      const targetTop = padding + svgHeight / 2 - canvas.clientHeight / 2;
      canvas.scrollLeft = Math.max(0, Math.min(contentWidth - canvas.clientWidth, targetLeft));
      canvas.scrollTop = Math.max(0, Math.min(contentHeight - canvas.clientHeight, targetTop));
    });
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

  // Edge panning removed - map is panned by click-and-drag only

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
      // Only clone the affected row — avoids allocating 22,500 objects per brush stroke
      return prev.map((r, rIdx) => {
        if (rIdx !== row) return r;
        return r.map((cell, cIdx) => {
          if (cIdx !== col) return cell;
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
            const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;

            // Completely overwrite with new values
            return {
              filled: true,
              color: baseColor,
              effect: currentEffect,
              animationOffset: Math.random() * 10,
              paintedAt: fadeEnabled ? Date.now() : null
            };
          }
        });
      });
    });
  };

  // Flush all pending paint operations into a single setHexGrid call (called via RAF)
  const flushPendingPaints = useCallback(() => {
    paintRafRef.current = null;
    const pending = pendingPaintsRef.current;
    if (pending.size === 0) return;
    pendingPaintsRef.current = new Map();

    setHexGrid(prev => {
      let next = null;
      for (const [, { row, col, erase, effect, color, animated }] of pending) {
        if (!next) next = [...prev]; // lazy-clone outer array once
        if (next[row] === prev[row]) next[row] = [...prev[row]]; // clone row on first touch
        next[row][col] = erase
          ? { filled: false, color: '#3498db', effect: 'none', animationOffset: Math.random() * 10, paintedAt: null }
          : { filled: true, color, effect, animationOffset: Math.random() * 10, paintedAt: animated ? Date.now() : null };
      }
      return next || prev;
    });
  }, []);

  // Queue a paint for the next animation frame instead of triggering a render per cell
  const queueHexPaint = useCallback((row, col, erase = false) => {
    if (currentTool === 'token') return;
    const effectPreset = EFFECT_PRESETS[currentEffect];
    const color = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;
    pendingPaintsRef.current.set(`${row}-${col}`, { row, col, erase, effect: currentEffect, color, animated: fadeEnabled });
    if (!paintRafRef.current) {
      paintRafRef.current = requestAnimationFrame(flushPendingPaints);
    }
  }, [currentTool, currentEffect, brushColor, fadeEnabled, flushPendingPaints]);

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
      const effectPreset = EFFECT_PRESETS[currentEffect];
      const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;

      // Build a Set of affected row indices so we only clone those rows
      const affectedRows = new Set();
      lineHexes.forEach(({ row, col }) => {
        if (row >= 0 && row < gridSize.rows && col >= 0 && col < gridSize.cols) {
          affectedRows.add(row);
        }
      });

      // Build a map of row → Set<col> for O(1) lookup inside the map
      const cellMap = new Map();
      lineHexes.forEach(({ row, col }) => {
        if (row >= 0 && row < gridSize.rows && col >= 0 && col < gridSize.cols) {
          if (!cellMap.has(row)) cellMap.set(row, new Set());
          cellMap.get(row).add(col);
        }
      });

      return prev.map((r, rIdx) => {
        if (!affectedRows.has(rIdx)) return r;
        const cols = cellMap.get(rIdx);
        return r.map((cell, cIdx) => {
          if (!cols.has(cIdx)) return cell;
          return {
            filled: true,
            color: baseColor,
            effect: currentEffect,
            animationOffset: Math.random() * 10,
            paintedAt: fadeEnabled ? Date.now() : null
          };
        });
      });
    });
  };

  // Handle area drawing with new pattern system
  const handleAreaDraw = (startRow, startCol) => {
    const pattern = AREA_PATTERNS[currentTool];
    if (!pattern || !pattern.pattern) return;
    
    setHexGrid(prev => {
      const effectPreset = EFFECT_PRESETS[currentEffect];
      const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;

      // Build a map of affected row → Set<col> so we only clone those rows
      const cellMap = new Map();
      pattern.pattern[0].hexes.forEach(offset => {
        const targetRow = startRow + offset.row;
        const targetCol = startCol + offset.col;
        if (targetRow >= 0 && targetRow < gridSize.rows &&
            targetCol >= 0 && targetCol < gridSize.cols) {
          if (!cellMap.has(targetRow)) cellMap.set(targetRow, new Set());
          cellMap.get(targetRow).add(targetCol);
        }
      });

      return prev.map((r, rIdx) => {
        if (!cellMap.has(rIdx)) return r;
        const cols = cellMap.get(rIdx);
        return r.map((cell, cIdx) => {
          if (!cols.has(cIdx)) return cell;
          return {
            filled: true,
            color: baseColor,
            effect: currentEffect,
            animationOffset: Math.random() * 10,
            paintedAt: fadeEnabled ? Date.now() : null
          };
        });
      });
    });
  };

  // Handle Edit Data tool click - opens modal to edit token or hex
  const handleEditDataClick = async (row, col) => {
    // Check if there's a token at this position
    const tokenAtPos = tokens.find(t => {
      const cells = getTokenCells(t.row, t.col, t.width || 1, t.height || 1);
      return cells.some(c => c.row === row && c.col === col);
    });
    
    if (tokenAtPos) {
      let tokenData = tokenAtPos;
      if (tokenAtPos.characterSheetPath) {
        const parsed = await parseCharacterSheetForToken(
          tokenAtPos.characterSheetPath,
          tokenAtPos.characterSheetEndpoint || 'player_root',
          tokenAtPos.isTempCharacterSheet || false
        );
        if (parsed) {
          tokenData = {
            ...tokenAtPos,
            currentHp: parsed.currentHp ?? tokenAtPos.currentHp,
            maxHp: parsed.maxHp ?? tokenAtPos.maxHp,
            conditions: parsed.conditions?.length ? parsed.conditions : tokenAtPos.conditions,
            defensive: Object.keys(parsed.defensive || {}).length ? parsed.defensive : tokenAtPos.defensive
          };
        }
      }
      // Edit token data
      setEditTarget({
        type: 'token',
        data: tokenData,
        row,
        col
      });
    } else {
      // Edit hex cell data
      const hexData = hexGrid[row]?.[col] || { filled: false, color: [0, 0, 0, 0] };
      setEditTarget({
        type: 'hex',
        data: hexData,
        row,
        col
      });
    }
    
    setEditModalOpen(true);
  };

  // Handle save from Edit Data modal
  const handleEditDataSave = async (editData) => {
    saveToHistory();
    
    if (editData.type === 'token') {
      // Find the old token to check if aura changed
      const oldToken = tokens.find(t => t.id === editData.tokenId);
      const newAura = editData.data.aura;
      const oldAura = oldToken?.aura;
      
      // Update token - ensure conditions are properly merged
      setTokens(prev => prev.map(t => {
        if (t.id === editData.tokenId) {
          return {
            ...t,
            ...editData.data,
            conditions: editData.data.conditions || [],
            defensive: editData.data.defensive || t.defensive || {}
          };
        }
        return t;
      }));
      
      // Sync HP/conditions/defensive back to the token's character sheet (PC or temp NPC)
      const updates = {};
      
      // Include HP updates if changed
      if (editData.data.currentHp !== undefined) {
        updates.currentHp = editData.data.currentHp;
      }
      if (editData.data.maxHp !== undefined) {
        updates.maxHp = editData.data.maxHp;
      }
      
      // Include conditions if present
      if (editData.data.conditions) {
        updates.conditions = editData.data.conditions;
      }
      
      // Include defensive stats if present
      if (editData.data.defensive) {
        updates.defensive = editData.data.defensive;
      }
      
      const targetName = editData.data.name || oldToken?.name;
      const targetSheetPath = editData.data.characterSheetPath || oldToken?.characterSheetPath;
      const targetEndpoint = editData.data.characterSheetEndpoint || oldToken?.characterSheetEndpoint || 'player_root';
      
      // Only attempt sync if we have updates and a target
      if (Object.keys(updates).length > 0 && (targetName || targetSheetPath)) {
        // Don't await - run in background to not block UI
        updateCharacterSheet(targetName, updates, API_BASE_URL, {
          sheetPath: targetSheetPath,
          endpoint: targetEndpoint
        }).catch(err => {
          console.warn('Failed to sync character sheet:', err);
        });
      }
      
      // Handle aura hex changes
      if (oldAura?.moveHexes || newAura?.moveHexes) {
        setHexGrid(prev => {
          const updated = prev.map(r => r.map(c => ({ ...c })));
          
          // Clear old aura hexes if they existed
          if (oldAura?.moveHexes) {
            updated.forEach(row => {
              row.forEach(cell => {
                if (cell.auraTokenId === editData.tokenId) {
                  cell.filled = false;
                  cell.color = [0, 0, 0, 0];
                  cell.effect = null;
                  delete cell.auraTokenId;
                  delete cell.paintedAt;
                }
              });
            });
          }
          
          // Add new aura hexes if aura exists and moveHexes is true
          if (newAura && newAura.moveHexes && newAura.diameter > 0) {
            const tokenWidth = editData.width || 1;
            const tokenHeight = editData.height || 1;
            const auraHexes = generateTokenAuraPattern(editData.row, editData.col, tokenWidth, tokenHeight, newAura.diameter);
            const effectPreset = EFFECT_PRESETS[currentEffect];
            const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;
            
            auraHexes.forEach(({ row, col }) => {
              if (updated[row] && updated[row][col]) {
                updated[row][col] = {
                  ...updated[row][col],
                  filled: true,
                  color: baseColor,
                  effect: currentEffect,
                  auraTokenId: editData.tokenId,
                  paintedAt: fadeEnabled ? Date.now() : null
                };
              }
            });
          }
          
          return updated;
        });
      }
    } else if (editData.type === 'hex') {
      // Update hex cell
      setHexGrid(prev => {
        const updated = prev.map(r => r.map(c => ({ ...c })));
        if (updated[editData.row] && updated[editData.row][editData.col]) {
          updated[editData.row][editData.col] = editData.data;
        }
        return updated;
      });
    }
  };

  // Handle hex click
  const handleHexClick = (row, col, erase = false) => {
    // Check if we're in move token mode
    if (tokenToMove) {
      handleTokenDrop(row, col);
      setTokenToMove(null);
      return;
    }
    
    if (currentTool === 'edit') {
      // Edit Data tool: Open modal to edit token or hex data
      handleEditDataClick(row, col);
    } else if (currentTool === 'debug') {
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
    } else if (currentTool === 'place-token') {
      // Place token tool: place selected token at clicked position
      if (tokenToPlace) {
        handleAddToken(tokenToPlace, row, col);
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
      // Check if clicking on existing token (check all cells occupied by each token)
      const tokenAtPos = tokens.find(t => {
        const cells = getTokenCells(t.row, t.col, t.width || 1, t.height || 1);
        return cells.some(c => c.row === row && c.col === col);
      });
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
    setDragPreview(null);
  };

  // Handle aura tool click - attach aura to token at clicked hex
  const handleAuraToolClick = (row, col) => {
    // Find token at this hex (check all cells occupied by each token)
    const token = tokens.find(t => {
      const cells = getTokenCells(t.row, t.col, t.width || 1, t.height || 1);
      return cells.some(c => c.row === row && c.col === col);
    });
    
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
    
    // Generate aura hexes using multi-tile token logic
    const tokenWidth = token.width || 1;
    const tokenHeight = token.height || 1;
    const auraHexes = generateTokenAuraPattern(token.row, token.col, tokenWidth, tokenHeight, diameter);
    
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
        const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;
        
        auraHexes.forEach(({ row, col }) => {
          if (updated[row] && updated[row][col]) {
            // Calculate distance from token center for pulsing animation
            const distance = calculateHexDistance(token.row, token.col, row, col);
            const pulseOffset = distance * 8;
            
            updated[row][col] = {
              ...updated[row][col],
              filled: true,
              color: baseColor,
              effect: currentEffect,
              animationOffset: pulseOffset, // Distance-based pulse offset for animated effects
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
    const movingTokenId = draggedToken || tokenToMove;
    if (!movingTokenId) return;
    
    // Find the token being moved
    const token = tokens.find(t => t.id === movingTokenId);
    if (!token) return;
    
    const oldRow = token.row;
    const oldCol = token.col;
    const newRow = row;
    const newCol = col;
    const width = token.width || 1;
    const height = token.height || 1;
    
    // Check if the token would fit within grid bounds
    if (newRow + height > gridSize.rows || newCol + width > gridSize.cols) {
      console.warn('Token movement out of bounds');
      setDraggedToken(null);
      return;
    }
    
    // Get cells that the token would occupy at new position
    const newTokenCells = getTokenCells(newRow, newCol, width, height);
    
    // Check for collision with other tokens (excluding itself)
    const hasCollision = tokens.some(existingToken => {
      if (existingToken.id === draggedToken) return false; // Skip self
      
      const existingCells = getTokenCells(
        existingToken.row, 
        existingToken.col, 
        existingToken.width || 1, 
        existingToken.height || 1
      );
      // Check if any cell overlaps
      return newTokenCells.some(newCell => 
        existingCells.some(existingCell => 
          existingCell.row === newCell.row && existingCell.col === newCell.col
        )
      );
    });
    
    if (hasCollision) {
      console.warn('Token movement would overlap with existing token');
      setDraggedToken(null);
      setDragPreview(null);
      return;
    }
    
    // Only move aura hexes if the token has an aura with moveHexes enabled
    if (token.aura && token.aura.moveHexes) {
      // Find all hexes that are aura tiles for this token
      const auraHexes = [];
      for (let r = 0; r < gridSize.rows; r++) {
        for (let c = 0; c < gridSize.cols; c++) {
          const cell = hexGrid[r]?.[c];
          if (cell && cell.auraTokenId === movingTokenId) {
            auraHexes.push({ row: r, col: c, data: { ...cell } });
          }
        }
      }
      
          setDragPreview(null);
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
          if (cell && cell.auraTokenId === movingTokenId) {
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
          const tokenWidth = tokenRef.width || 1;
          const tokenHeight = tokenRef.height || 1;
          const newAuraHexes = generateTokenAuraPattern(newRow, newCol, tokenWidth, tokenHeight, diameter);
          
          // Paint new aura hex positions - but only on empty hexes or hexes that were part of the old aura
          newAuraHexes.forEach(({ row: r, col: c }) => {
            if (updated[r] && updated[r][c]) {
              // Only paint if the hex is NOT filled, or if it was part of the old aura we just cleared
              const wasOldAura = auraHexes.some(old => old.row === r && old.col === c);
              if (!updated[r][c].filled || wasOldAura) {
                // Calculate distance from new token center for pulsing animation
                const distance = calculateHexDistance(newRow, newCol, r, c);
                const pulseOffset = distance * 8;
                
                updated[r][c] = {
                  ...updated[r][c],
                  filled: true,
                  color: auraColor,
                  effect: auraEffect,
                  animationOffset: pulseOffset, // Distance-based pulse offset
                  auraTokenId: movingTokenId,
                  paintedAt: auraPaintedAt
                };
              }
            }
          });
          
          return updated;
        });
      }
    }
    
    // Update token position
    setTokens(prev => prev.map(token =>
      token.id === movingTokenId
        ? { ...token, row, col }
        : token
    ));
    setDraggedToken(null);
    setTokenToMove(null);

    // Immediate DB-backed patch for just this token's position -- the
    // actual per-turn hot path. Previously a token move waited on the
    // 3-second debounced full-document save (the entire hexGrid + tokens
    // array + background), so a GM and a player moving different tokens
    // within that window could have one move silently reverted when the
    // other's save landed. This doesn't wait for the debounce, and the
    // battlemap file itself still gets the full-document save afterward as
    // the durable mirror.
    if (filePath) {
      patchBattlemapToken(filePath, movingTokenId, { position: { row, col } }).catch((e) =>
        console.error('Immediate token-position patch failed (debounced full save will still catch up):', e)
      );
    }
  };

  const slugifyName = (name) => {
    const safe = (name || 'token').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return safe || 'token';
  };

  const encodeRelativePath = (relativePath) => relativePath.split('/').map(segment => encodeURIComponent(segment)).join('/');

  const fetchCharacterSheetContentByPath = async (relativePath, endpoint = 'player_root') => {
    if (!relativePath) return null;
    const url = `${API_BASE_URL}/${endpoint}/${encodeRelativePath(relativePath)}`;
    try {
      const resp = await fetch(url, { cache: 'no-store' });
      if (!resp.ok) return null;
      const data = await resp.json();
      return data.content || '';
    } catch (err) {
      console.warn('Failed to fetch character sheet content for', relativePath, err);
      return null;
    }
  };

  const saveCharacterSheetContentByPath = async (relativePath, markdown, endpoint = 'player_root') => {
    const url = `${API_BASE_URL}/${endpoint}/${encodeRelativePath(relativePath)}`;
    await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: markdown })
    });
  };

  const ensureCharacterSheetForToken = useCallback(async ({ tokenId, name, type, defaults = {} }) => {
    const safeName = name || 'Token';
    const isPlayer = (type || 'player') === 'player';
    const path = isPlayer
      ? `PCs/${safeName}/${safeName} character sheet.md`
      : `NPCs/temp_token_${tokenId}_${slugifyName(safeName)}_character_sheet.md`;
    const endpoint = 'player_root';

    let content = await fetchCharacterSheetContentByPath(path, endpoint);
    if (!content) {
      const markdown = buildBasicCharacterSheet({
        name: safeName,
        currentHp: defaults.currentHp ?? 100,
        maxHp: defaults.maxHp ?? 100,
        conditions: defaults.conditions || [],
        defensive: defaults.defensive || {},
        type: type || 'npc'
      });
      try {
        await saveCharacterSheetContentByPath(path, markdown, endpoint);
        content = markdown;
      } catch (err) {
        console.warn('Failed to create character sheet for token', safeName, err);
      }
    }

    return { path, endpoint, isTemp: !isPlayer, content };
  }, []);

  const parseCharacterSheetForToken = useCallback(async (relativePath, endpoint = 'player_root', isTemp = false) => {
    if (!relativePath) return null;
    const content = await fetchCharacterSheetContentByPath(relativePath, endpoint);
    if (!content) return null;
    
    // For temp NPC sheets, try to load state JSON
    let npcState = null;
    if (isTemp) {
      npcState = await loadNpcState(relativePath, API_BASE_URL);
    }
    
    return { ...parseSheetVitalsAndConditions(content, npcState), content };
  }, []);

  const resetCharacterSheetForToken = useCallback(async (token) => {
    if (!token?.characterSheetPath || !token.isTempCharacterSheet) return;
    try {
      const markdown = buildBasicCharacterSheet({
        name: token.name || 'Token',
        currentHp: 0,
        maxHp: 0,
        conditions: [],
        defensive: token.defensive || {},
        type: token.type || 'npc'
      });
      await saveCharacterSheetContentByPath(
        token.characterSheetPath,
        markdown,
        token.characterSheetEndpoint || 'player_root'
      );
    } catch (err) {
      console.warn('Failed to reset temp character sheet for token', token?.name, err);
    }
  }, []);

  // Add new token
  const handleAddToken = async (character, targetRow = null, targetCol = null) => {
    // Save state before adding token
    saveToHistory();
    
    // Use provided position or default to center
    const row = targetRow !== null ? targetRow : Math.floor(gridSize.rows / 2);
    const col = targetCol !== null ? targetCol : Math.floor(gridSize.cols / 2);
    const width = character.width || 1;
    const height = character.height || 1;
    const tokenId = `token-${Date.now()}`;
    
    // Check if the token would fit within grid bounds
    if (row + height > gridSize.rows || col + width > gridSize.cols) {
      console.warn('Token placement out of bounds');
      return;
    }
    
    // Get cells that the new token would occupy
    const newTokenCells = getTokenCells(row, col, width, height);
    
    // Check for collision with existing tokens
    const hasCollision = tokens.some(existingToken => {
      const existingCells = getTokenCells(
        existingToken.row, 
        existingToken.col, 
        existingToken.width || 1, 
        existingToken.height || 1
      );
      // Check if any cell overlaps
      return newTokenCells.some(newCell => 
        existingCells.some(existingCell => 
          existingCell.row === newCell.row && existingCell.col === newCell.col
        )
      );
    });
    
    if (hasCollision) {
      console.warn('Token placement would overlap with existing token');
      return;
    }
    
    // Fetch character data from character sheet if this is a player character
    let characterData = null;
    if (character.type === 'player' && character.name) {
      try {
        console.log(`📋 Fetching character sheet data for ${character.name}...`);
        characterData = await fetchCharacterSheet(character.name, API_BASE_URL);
        console.log(`✅ Character data loaded for ${character.name}:`, characterData);
        if (characterData?.vitals) {
          console.log(`  Vitals:`, {
            current_hp: characterData.vitals.current_hp,
            max_hp: characterData.vitals.max_hp
          });
        }
      } catch (err) {
        console.warn(`⚠️ Could not load character sheet for ${character.name}:`, err);
      }
    }
    
    const parsedCurrentHp = characterData?.vitals?.current_hp ? parseFloat(characterData.vitals.current_hp) : undefined;
    const parsedMaxHp = characterData?.vitals?.max_hp ? parseFloat(characterData.vitals.max_hp) : undefined;

    // Ensure a character sheet exists for every token (players use their sheet, NPC/enemy get temp sheet)
    const sheetInfo = await ensureCharacterSheetForToken({
      tokenId,
      name: character.name,
      type: character.type || 'player',
      defaults: {
        currentHp: parsedCurrentHp ?? character.currentHp ?? 100,
        maxHp: parsedMaxHp ?? character.maxHp ?? 100,
        conditions: characterData?.conditions || [],
        defensive: characterData?.defensive || {}
      }
    });

    // Parse HP/conditions directly from the sheet for consistency
    const parsedSheet = await parseCharacterSheetForToken(sheetInfo.path, sheetInfo.endpoint, sheetInfo.isTemp);
    const sheetCurrentHp = parsedSheet?.currentHp;
    const sheetMaxHp = parsedSheet?.maxHp;
    const sheetConditions = parsedSheet?.conditions || [];
    const sheetDefensive = parsedSheet?.defensive || {};

    const newToken = {
      id: tokenId,
      row,
      col,
      name: character.name,
      avatarPng: character.avatarPng,
      icon: character.icon, // For enemy tokens
      type: character.type || 'player', // Preserve type from drag data, default to player
      color: character.color || 'rgba(0,0,0,0)',  // Default to transparent (rgba)
      width,
      height,
      currentHp: sheetCurrentHp ?? parsedCurrentHp,
      maxHp: sheetMaxHp ?? parsedMaxHp,
      conditions: sheetConditions.length ? sheetConditions : (characterData?.conditions || []),
      defensive: Object.keys(sheetDefensive).length ? sheetDefensive : (characterData?.defensive || {}),
      characterSheetPath: sheetInfo.path,
      characterSheetEndpoint: sheetInfo.endpoint,
      isTempCharacterSheet: sheetInfo.isTemp
    };
    
    console.log(`🎭 Adding token with HP data:`, {
      name: newToken.name,
      currentHp: newToken.currentHp,
      maxHp: newToken.maxHp,
      hasCharacterData: !!characterData,
      hasSheet: !!sheetInfo.path
    });
    setTokens(prev => [...prev, newToken]);
  };

  // Remove token
  const handleRemoveToken = (tokenId) => {
    // Save state before removing token
    saveToHistory();
    const tokenToDelete = tokens.find(t => t.id === tokenId);
    if (tokenToDelete) {
      resetCharacterSheetForToken(tokenToDelete);
    }
    setTokens(prev => prev.filter(t => t.id !== tokenId));
    if (selectedToken === tokenId) setSelectedToken(null);
    setContextMenu(null);
    setMarkerPopup(null);
  };
  
  // Toggle token HP visibility
  const handleToggleTokenHp = (tokenId) => {
    setTokens(prev => prev.map(token => 
      token.id === tokenId 
        ? { ...token, showHp: token.showHp === false ? true : false }
        : token
    ));
    setContextMenu(null);
    setMarkerPopup(null);
  };
  
  // Show token details popup
  const handleShowTokenDetails = (token) => {
    setDetailsPopupToken(token);
  };

  const openCharacterSheetByPath = useCallback(async (relativePath, endpoint = 'player_root', allowInApp = true) => {
    if (!relativePath) return false;

    if (allowInApp && onFileSelect) {
      const fileName = relativePath.split('/').pop();
      onFileSelect({ name: fileName, path: relativePath });
      return true;
    }

    try {
      const url = `${API_BASE_URL}/${endpoint}/${encodeURIComponent(relativePath)}`;
      const res = await fetch(url, { method: 'HEAD' });
      if (res.ok) {
        window.open(url, '_blank');
        return true;
      }
    } catch (err) {
      console.warn('Character sheet probe failed for', relativePath, err);
    }
    return false;
  }, [onFileSelect]);

  const handleOpenCharacterSheet = useCallback(async (tokenName) => {
    const name = (tokenName || '').trim();
    if (!name) return false;

    try {
      const searchResp = await fetch(`${API_BASE_URL}/player_root/search?q=${encodeURIComponent(name)}`);
      if (searchResp.ok) {
        const searchData = await searchResp.json();
        const results = searchData.results || [];
        const fileNameLower = name.toLowerCase();
        const fileNameWithSpaces = name.replace(/_/g, ' ').toLowerCase();

        let exactMatch = results.find(result => {
          const parts = result.path.split('/');
          const resultFile = parts[parts.length - 1].toLowerCase();
          return resultFile === fileNameLower ||
                 resultFile === `${fileNameLower}.md` ||
                 resultFile === fileNameWithSpaces ||
                 resultFile === `${fileNameWithSpaces}.md`;
        });

        if (!exactMatch) {
          exactMatch = results.find(result => {
            const parts = result.path.split('/');
            const resultFile = parts[parts.length - 1].toLowerCase();
            return resultFile === `${fileNameLower} character sheet.md` ||
                   resultFile === `${fileNameWithSpaces} character sheet.md` ||
                   resultFile === `${fileNameLower}_character_sheet.md`;
          });
        }

        if (exactMatch) {
          const relativePath = exactMatch.path.replace(/^Player Root\//, '');
          if (await openCharacterSheetByPath(relativePath, 'player_root')) return true;
        }
      }
    } catch (err) {
      console.warn('Character sheet search failed:', err);
    }

    const candidatePlayerPaths = [
      `PCs/${name}/${name} character sheet.md`,
      `PCs/${name}/${name} Character Sheet.md`,
      `PCs/${name}/${name}_character_sheet.md`,
      `${name} character sheet.md`,
      `${name}_character_sheet.md`
    ];

    for (const path of candidatePlayerPaths) {
      if (await openCharacterSheetByPath(path, 'player_root')) return true;
    }

    const dmPaths = [
      `Dms Root/NPCs/${name}/${name} character sheet.md`,
      `Dms Root/NPCs/${name}/${name}_character_sheet.md`
    ];

    for (const path of dmPaths) {
      // DM paths are outside player_root; open directly
      if (await openCharacterSheetByPath(path, 'file', false)) return true;
    }

    alert(`Could not find character sheet for ${name}`);
    return false;
  }, [openCharacterSheetByPath]);

  const syncTokenSheetUpdates = useCallback(async (tokenId, updates) => {
    if (!tokenId || !updates || !Object.keys(updates).length) return;
    const token = tokensRef.current.find(t => t.id === tokenId);
    if (!token) return;

    // Immediate DB-backed patch for HP/conditions -- same rationale as the
    // token-position patch in handleTokenDrop: this is the actual per-turn
    // hot path (HP ticks during combat), previously only protected by the
    // 3-second debounced full-document save.
    if (filePath && ('currentHp' in updates || 'maxHp' in updates || 'conditions' in updates)) {
      const changes = {};
      if ('currentHp' in updates) changes.hp = updates.currentHp;
      if ('maxHp' in updates) changes.maxHp = updates.maxHp;
      if ('conditions' in updates) changes.conditions = updates.conditions;
      patchBattlemapToken(filePath, tokenId, changes).catch((e) =>
        console.error('Immediate token HP/conditions patch failed (debounced full save will still catch up):', e)
      );
    }

    const targetName = token.name;
    const targetSheetPath = token.characterSheetPath || (token.type === 'player' && token.name
      ? `PCs/${token.name}/${token.name} character sheet.md`
      : null);
    const targetEndpoint = token.characterSheetEndpoint || 'player_root';

    if (!targetName && !targetSheetPath) return;

    // For temp NPC sheets, save state JSON
    if (token.isTempCharacterSheet && targetSheetPath) {
      try {
        // Build state object from current token and updates
        const currentState = {
          currentHp: updates.currentHp !== undefined ? updates.currentHp : token.currentHp,
          maxHp: updates.maxHp !== undefined ? updates.maxHp : token.maxHp,
          slots: updates.slots || token.slots || {},
          waterCharges: updates.waterCharges || token.waterCharges || {},
          conditions: updates.conditions || (token.conditions ? Object.keys(token.conditions).filter(k => token.conditions[k]) : []),
          lastUpdated: new Date().toISOString()
        };
        
        await saveNpcState(targetSheetPath, currentState, API_BASE_URL);
      } catch (err) {
        console.warn('Failed to save NPC state JSON', err);
      }
    }

    // Also update the markdown sheet
    updateCharacterSheet(targetName, updates, API_BASE_URL, {
      sheetPath: targetSheetPath,
      endpoint: targetEndpoint
    }).catch(err => {
      console.warn('Failed to sync token updates to sheet', tokenId, err);
    });
  }, []);

  const handleOpenNpcCharacterSheet = useCallback(async (token) => {
    if (!token) return false;

    let sheetPath = token.characterSheetPath;
    let sheetEndpoint = token.characterSheetEndpoint || 'player_root';

    // If no sheet is recorded (legacy tokens), generate one and persist metadata
    if (!sheetPath) {
      try {
        const sheetInfo = await ensureCharacterSheetForToken({
          tokenId: token.id || `token-${Date.now()}`,
          name: token.name || 'Token',
          type: token.type || 'npc',
          defaults: {
            currentHp: token.currentHp ?? 100,
            maxHp: token.maxHp ?? 100,
            conditions: token.conditions || [],
            defensive: token.defensive || {}
          }
        });
        sheetPath = sheetInfo.path;
        sheetEndpoint = sheetInfo.endpoint;
        setTokens(prev => prev.map(t =>
          t.id === token.id
            ? {
                ...t,
                characterSheetPath: sheetPath,
                characterSheetEndpoint: sheetEndpoint,
                isTempCharacterSheet: sheetInfo.isTemp
              }
            : t
        ));
      } catch (err) {
        console.warn('Failed to generate character sheet for token', token.name, err);
        return false;
      }
    }

    return openCharacterSheetByPath(sheetPath, sheetEndpoint);
  }, [ensureCharacterSheetForToken, openCharacterSheetByPath, setTokens]);

  // Refresh token stats from character sheets
  const handleRefreshTokenStats = async () => {
    console.log('🔄 Refreshing token stats from character sheets...');
    
    const updatedTokens = await Promise.all(
      tokens.map(async (token) => {
        const sheetPath = token.characterSheetPath || (token.name ? `PCs/${token.name}/${token.name} character sheet.md` : null);
        if (!sheetPath) return token;

        try {
          const parsed = await parseCharacterSheetForToken(
            sheetPath, 
            token.characterSheetEndpoint || 'player_root',
            token.isTempCharacterSheet || false
          );
          if (!parsed) return token;

          const newCurrentHp = parsed.currentHp ?? token.currentHp;
          const newMaxHp = parsed.maxHp ?? token.maxHp;
          let newConditions = parsed.conditions?.length ? parsed.conditions : (token.conditions || []);

          // Auto-add "Bleeding out" if HP is 0 or below
          const isBleedingOut = newMaxHp > 0 && newCurrentHp <= 0;
          if (isBleedingOut && !newConditions.includes('Bleeding out')) {
            newConditions = [...newConditions, 'Bleeding out'];
          } else if (!isBleedingOut) {
            newConditions = newConditions.filter(c => c !== 'Bleeding out');
          }

          return {
            ...token,
            currentHp: newCurrentHp,
            maxHp: newMaxHp,
            conditions: newConditions,
            defensive: Object.keys(parsed.defensive || {}).length ? parsed.defensive : token.defensive
          };
        } catch (err) {
          console.warn(`⚠️ Could not refresh data for ${token.name || token.id}:`, err);
          return token;
        }
      })
    );
    
    setTokens(updatedTokens);
    console.log('✅ Token stats refreshed');
  };

  // Clear grid
  const handleClearGrid = async () => {
    if (window.confirm('Clear all painted hexagons and tokens?')) {
      // Save state before clearing
      saveToHistory();
      
      // Clear the state
      const emptyGrid = initializeHexGrid(gridSize.rows, gridSize.cols);
      setHexGrid(emptyGrid);
      setTokens([]);
      
      // Force immediate save to prevent sync from reverting changes
      // We need to save with the cleared state before the next sync poll
      try {
        console.log('🧹 Clear Grid: Forcing immediate save');
        const stateToSave = {
          gridSize: gridSizeRef.current,
          hexGrid: emptyGrid,
          tokens: [],
          backgroundImage: selectedImageRef.current,
          hexSize: hexSizeRef.current,
          lastModified: Date.now(),
          format: 'graph',
          hexGraph: gridToGraphData(emptyGrid, gridSizeRef.current)
        };
        
        const saveUrl = `${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`;
        const response = await fetch(saveUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: JSON.stringify(stateToSave) })
        });
        
        if (response.ok) {
          console.log('✅ Clear Grid: Save successful');
          setLastSyncTime(stateToSave.lastModified);
        } else {
          console.error('❌ Clear Grid: Save failed with status:', response.status);
        }
      } catch (err) {
        console.error('❌ Clear Grid: Save error:', err);
      }
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

  // Get all hexes surrounding a multi-tile token at given distance
  // For multi-tile tokens, this finds ALL hexes that are exactly 'distance' away from ANY token cell
  const getTokenNeighborHexes = (tokenRow, tokenCol, tokenWidth, tokenHeight, distance = 1) => {
    const tokenCells = getTokenCells(tokenRow, tokenCol, tokenWidth, tokenHeight);
    const tokenCellSet = new Set(tokenCells.map(c => `${c.row},${c.col}`));
    
    // Use BFS from all token cells simultaneously
    const visited = new Set(tokenCellSet);
    let currentLayer = tokenCells.map(c => ({ row: c.row, col: c.col }));
    
    // Expand outward for 'distance' layers
    for (let layer = 0; layer < distance; layer++) {
      const nextLayer = [];
      for (const cell of currentLayer) {
        const neighbors = getHexNeighbors(cell.row, cell.col);
        for (const neighbor of neighbors) {
          const key = `${neighbor.row},${neighbor.col}`;
          if (!visited.has(key)) {
            visited.add(key);
            nextLayer.push(neighbor);
          }
        }
      }
      currentLayer = nextLayer;
    }
    
    return currentLayer; // Returns only the hexes at exactly 'distance' away
  };

  // Generate aura pattern for multi-tile tokens
  // Diameter represents the distance from the token edge, not from center
  const generateTokenAuraPattern = (tokenRow, tokenCol, tokenWidth, tokenHeight, diameter) => {
    const diameterNum = parseInt(diameter);
    if (diameterNum <= 0) return [];
    
    // For diameter=1, get all hexes that are 1 hex away from any token cell
    // For diameter=2, get all hexes that are 1 or 2 hexes away, etc.
    const auraHexes = [];
    const tokenCells = getTokenCells(tokenRow, tokenCol, tokenWidth, tokenHeight);
    const tokenCellSet = new Set(tokenCells.map(c => `${c.row},${c.col}`));
    
    // Use BFS to find all hexes within diameter distance from ANY token cell
    const visited = new Set(tokenCellSet);
    const queue = tokenCells.map(c => ({ row: c.row, col: c.col, distance: 0 }));
    
    while (queue.length > 0) {
      const { row, col, distance } = queue.shift();
      
      // Add to aura if we're beyond the token cells
      if (!tokenCellSet.has(`${row},${col}`)) {
        auraHexes.push({ row, col });
      }
      
      // Continue expanding if within range
      if (distance < diameterNum) {
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
    
    return auraHexes;
  };

  // Get the outline path vertices for a multi-tile token
  // Returns an array of {x, y} coordinates tracing the perimeter
  const getTokenOutlinePath = (tokenRow, tokenCol, tokenWidth, tokenHeight) => {
    const tokenCells = getTokenCells(tokenRow, tokenCol, tokenWidth, tokenHeight);
    const tokenCellSet = new Set(tokenCells.map(c => `${c.row},${c.col}`));
    
    // Collect all outer edges (edges not shared with another token cell)
    const outerEdges = [];
    
    tokenCells.forEach(cell => {
      const { cx, cy } = getHexCoordinates(cell.row, cell.col);
      const neighbors = getHexNeighbors(cell.row, cell.col);
      
      // Get hex vertices (6 corners)
      const hexVertices = [];
      for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i + Math.PI / 2;
        const x = cx + hexSize * Math.cos(angle);
        const y = cy + hexSize * Math.sin(angle);
        hexVertices.push({ x, y });
      }
      
      // Map edge indices to neighbor indices (rotated for odd-r)
      const edgeToNeighborMap = [4, 5, 0, 1, 2, 3];
      
      // Check each edge
      for (let i = 0; i < 6; i++) {
        const neighborIdx = edgeToNeighborMap[i];
        const neighbor = neighbors[neighborIdx];
        const isNeighborInToken = neighbor && tokenCellSet.has(`${neighbor.row},${neighbor.col}`);
        
        if (!isNeighborInToken) {
          // This edge is on the outer boundary
          const v1 = hexVertices[i];
          const v2 = hexVertices[(i + 1) % 6];
          outerEdges.push({ x1: v1.x, y1: v1.y, x2: v2.x, y2: v2.y });
        }
      }
    });
    
    return outerEdges;
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
    const directions = ['NW', 'NE', 'E', 'SE', 'SW', 'W'];
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
    const directions = ['NW', 'NE', 'E', 'SE', 'SW', 'W'];
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
    
    // Add the origin hex
    addHex(originRow, originCol);
    
    // Add the two initial direction hexes (the first row of the cone)
    addHex(dir1Row, dir1Col);
    addHex(dir2Row, dir2Col);
    
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
      const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;
      
      hexes.forEach(({ row, col }) => {
        // Calculate position relative to center for whirlwind effect
        const deltaRow = row - centerRow;
        const deltaCol = col - centerCol;
        
        // Calculate angle around the center (in radians)
        const angle = Math.atan2(deltaRow, deltaCol);
        
        // Calculate distance from center
        const distance = calculateHexDistance(centerRow, centerCol, row, col);
        
        // Create pulsing animation offset based on distance from center
        // Hexes at the same distance will pulse together, creating an outward wave effect
        // Higher multiplier = slower pulse propagation from center
        const pulseOffset = distance * 8;
        
        // Completely overwrite the cell with coordinated pulse data
        updated[row][col] = {
          filled: true,
          color: baseColor,
          effect: currentEffect,
          animationOffset: pulseOffset, // Distance-based pulse offset
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
      const baseColor = (effectPreset && effectPreset.colors) ? effectPreset.colors[0] : brushColor;
      
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

  // Array-form vertices for computed overlays/previews
  const getHexVerticesArray = (cx, cy) => {
    const points = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i + Math.PI / 2;
      const x = cx + hexSize * Math.cos(angle);
      const y = cy + hexSize * Math.sin(angle);
      points.push({ x, y });
    }
    return points;
  };

  // Get CSS animation class for effects
  const getEffectAnimationClass = (cell) => {
    if (!cell.filled || cell.effect === 'none') {
      return '';
    }
    return `hex-effect-${cell.effect}`;
  };
  
  // Get base color for effect
  const getEffectBaseColor = (cell) => {
    if (!cell.filled || cell.effect === 'none') {
      return cell.color;
    }
    
    const effectPreset = EFFECT_PRESETS[cell.effect];
    if (!effectPreset || !effectPreset.colors) {
      return cell.color;
    }
    
    return effectPreset.colors[0];
  };

  // Calculate SVG dimensions
  const svgWidth = gridSize.cols * (hexSize * Math.sqrt(3)) + (hexSize * Math.sqrt(3));
  const svgHeight = gridSize.rows * (hexSize * 1.5) + hexSize;

  // Pre-compute hex center coordinates and vertex strings for every cell.
  // Only recalculated when hexSize or grid dimensions change — not on every render.
  const hexGeometry = useMemo(() => {
    const hexWidth = hexSize * Math.sqrt(3);
    const vertSpacing = hexSize * 1.5;
    const angles = Array.from({ length: 6 }, (_, i) => (Math.PI / 3) * i + Math.PI / 2);
    const cosines = angles.map(Math.cos);
    const sines = angles.map(Math.sin);

    return Array.from({ length: gridSize.rows }, (_, rIdx) => {
      const tessOffset = (rIdx % 2 === 1) ? (hexWidth / 2) : 0;
      const cy = rIdx * vertSpacing + hexSize;
      return Array.from({ length: gridSize.cols }, (_, cIdx) => {
        const cx = cIdx * hexWidth + (hexWidth / 2) + tessOffset;
        const points = Array.from({ length: 6 }, (__, i) =>
          `${cx + hexSize * cosines[i]},${cy + hexSize * sines[i]}`
        ).join(' ');
        return { cx, cy, points };
      });
    });
  }, [hexSize, gridSize.rows, gridSize.cols]);

  // Render custom effect graphics for a hex cell.
  // All animation is driven purely by CSS (compositor thread) — no animationFrame state needed.
  // Per-cell stagger is achieved via animationDelay calculated from cellOffset.
  const renderEffectGraphics = (effect, cx, cy, rIdx, cIdx) => {
    if (!effect || effect === 'none') return null;

    const cellKey = `${rIdx}-${cIdx}`;
    // Unique integer per cell — used to stagger animationDelay so neighboring cells
    // don't pulse in lockstep. Negative delays start mid-cycle (already animating).
    const cellOffset = (rIdx * gridSize.cols + cIdx) * 17;
    const d = (base, spread = 100, scale = 0.01) =>
      `${-(((cellOffset + base) % spread) * scale).toFixed(2)}s`;

    switch (effect) {
      case 'fire':
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <circle cx={cx} cy={cy} r={hexSize * 0.78} fill="url(#fireGradient)" opacity="0.5" />
            {[0, 1, 2, 3, 4, 5].map((edge) => {
              const angle = (Math.PI / 3) * edge - Math.PI / 2;
              const baseX = cx + hexSize * 0.72 * Math.cos(angle);
              const baseY = cy + hexSize * 0.72 * Math.sin(angle);
              return (
                <ellipse
                  key={`flame-${edge}`}
                  cx={baseX}
                  cy={baseY}
                  rx={hexSize * 0.13}
                  ry={hexSize * 0.3}
                  fill={['#ff4444', '#ff6b1a', '#ffaa00'][edge % 3]}
                  className="effect-flame"
                  style={{
                    animationDelay: d(edge * 17),
                    animationDuration: `${0.9 + (edge % 3) * 0.18}s`
                  }}
                />
              );
            })}
          </g>
        );

      case 'water':
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <circle cx={cx} cy={cy} r={hexSize * 0.75} fill="url(#waterGradient)" opacity="0.5" />
            {[0, 1, 2].map((ring) => (
              <circle
                key={`ripple-${ring}`}
                cx={cx} cy={cy} r={3}
                fill="none"
                stroke="#66b3ff"
                strokeWidth="1.8"
                className="effect-ripple"
                style={{
                  animationDelay: d(ring * 33),
                  animationDuration: `${1.8 + ring * 0.3}s`
                }}
              />
            ))}
            <line
              x1={cx - hexSize * 0.48} y1={cy - hexSize * 0.1}
              x2={cx + hexSize * 0.48} y2={cy - hexSize * 0.1}
              stroke="#aaddff" strokeWidth="1.5" strokeLinecap="round"
              className="effect-wisp"
              style={{ animationDelay: d(0), animationDuration: '2.2s' }}
            />
            <line
              x1={cx - hexSize * 0.3} y1={cy + hexSize * 0.15}
              x2={cx + hexSize * 0.3} y2={cy + hexSize * 0.15}
              stroke="#88ccff" strokeWidth="1.2" strokeLinecap="round"
              className="effect-wisp"
              style={{ animationDelay: d(50), animationDuration: '2.6s' }}
            />
          </g>
        );

      case 'ice':
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <polygon points={getHexVertices(cx, cy)} fill="url(#iceGradient)" opacity="0.55" />
            {[0, 1, 2, 3, 4, 5].map((crystal) => {
              const angle = (Math.PI / 3) * crystal;
              const crystalX = cx + hexSize * 0.5 * Math.cos(angle);
              const crystalY = cy + hexSize * 0.5 * Math.sin(angle);
              return (
                <g
                  key={`crystal-${crystal}`}
                  className="effect-crystal"
                  style={{ animationDelay: d(crystal * 20) }}
                >
                  <line
                    x1={crystalX} y1={crystalY}
                    x2={crystalX + hexSize * 0.36 * Math.cos(angle)}
                    y2={crystalY + hexSize * 0.36 * Math.sin(angle)}
                    stroke="#ccffff" strokeWidth="2"
                  />
                  <line
                    x1={crystalX} y1={crystalY}
                    x2={crystalX + hexSize * 0.22 * Math.cos(angle + 0.5)}
                    y2={crystalY + hexSize * 0.22 * Math.sin(angle + 0.5)}
                    stroke="#88ccff" strokeWidth="1.5"
                  />
                  <line
                    x1={crystalX} y1={crystalY}
                    x2={crystalX + hexSize * 0.22 * Math.cos(angle - 0.5)}
                    y2={crystalY + hexSize * 0.22 * Math.sin(angle - 0.5)}
                    stroke="#88ccff" strokeWidth="1.5"
                  />
                </g>
              );
            })}
          </g>
        );

      case 'earth':
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <polygon points={getHexVertices(cx, cy)} fill="url(#earthPattern)" opacity="0.7" />
            <ellipse cx={cx} cy={cy + 2} rx={hexSize * 0.5} ry={hexSize * 0.4} fill="#6f5436" opacity="0.8" />
            <ellipse cx={cx - 3} cy={cy - 1} rx={hexSize * 0.4} ry={hexSize * 0.35} fill="#8b6f47" opacity="0.7" />
            <ellipse cx={cx + 4} cy={cy} rx={hexSize * 0.3} ry={hexSize * 0.25} fill="#9a7b5a" opacity="0.6" />
            <path
              d={`M ${cx - 5} ${cy} Q ${cx} ${cy - 3} ${cx + 5} ${cy + 1}`}
              stroke="#4a3a2a" strokeWidth="1" fill="none" opacity="0.5"
            />
          </g>
        );

      case 'spirit':
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <circle cx={cx} cy={cy} r={hexSize * 0.72} fill="url(#spiritGradient)" opacity="0.45" />
            {[0, 1, 2, 3, 4, 5].map((orb) => {
              const angle = (Math.PI / 3) * orb;
              return (
                <circle
                  key={`orb-${orb}`}
                  cx={cx + hexSize * 0.52 * Math.cos(angle)}
                  cy={cy + hexSize * 0.52 * Math.sin(angle)}
                  r={2.5}
                  fill={orb % 2 === 0 ? '#dda0dd' : '#b19cd9'}
                  className="effect-spirit-orb"
                  style={{ animationDelay: d(orb * 25) }}
                />
              );
            })}
            <circle
              cx={cx} cy={cy} r={hexSize * 0.2}
              fill="#9370db" opacity="0.6"
              className="effect-spirit-orb"
              style={{ animationDelay: d(0), animationDuration: '1.8s' }}
            />
          </g>
        );

      case 'poison': {
        const bubblePositions = [
          { x: -0.3, y: -0.2 },
          { x:  0.3, y: -0.3 },
          { x: -0.2, y:  0.2 },
          { x:  0.25, y: 0.3 },
          { x:  0,    y: 0   }
        ];
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {bubblePositions.map((pos, idx) => (
              <circle
                key={`bubble-${idx}`}
                cx={cx + pos.x * hexSize}
                cy={cy + pos.y * hexSize}
                r={3.5}
                fill="#88ff44"
                className="effect-bubble"
                style={{
                  animationDelay: d(idx * 40),
                  animationDuration: `${1.6 + idx * 0.25}s`
                }}
              />
            ))}
          </g>
        );
      }

      case 'lightning': {
        // Use deterministic jitter from cellOffset — no Math.random() in render
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {[0, 1, 2].map((bolt) => {
              const angle = (bolt * Math.PI * 2 / 3) + (cellOffset * 0.031);
              const x2 = cx + Math.cos(angle) * hexSize * 0.75;
              const y2 = cy + Math.sin(angle) * hexSize * 0.75;
              const jitter = ((cellOffset + bolt * 31) % 12) - 6;
              const midX = (cx + x2) / 2 + jitter;
              const midY = (cy + y2) / 2 + jitter * 0.5;
              return (
                <path
                  key={`bolt-${bolt}`}
                  d={`M ${cx} ${cy} L ${midX} ${midY} L ${x2} ${y2}`}
                  stroke="#ffffff"
                  strokeWidth="2"
                  fill="none"
                  filter="drop-shadow(0 0 4px #aaffff)"
                  className="effect-bolt"
                  style={{
                    animationDelay: d(bolt * 30, 90),
                    animationDuration: '0.9s'
                  }}
                />
              );
            })}
            <circle
              cx={cx} cy={cy} r={hexSize * 0.15}
              fill="#ffff88" opacity="0.7"
              className="effect-bolt"
              style={{ animationDelay: d(0) }}
            />
          </g>
        );
      }

      case 'healing': {
        const sparklePositions = [
          { x: -0.4, y: -0.3 },
          { x:  0.4, y: -0.2 },
          { x: -0.3, y:  0.3 },
          { x:  0.3, y:  0.4 },
          { x:  0,   y: -0.45 },
          { x:  0,   y:  0.45 }
        ];
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <circle
              cx={cx} cy={cy} r={hexSize * 0.38}
              fill="#ffee88" opacity="0.2"
              className="effect-sparkle"
              style={{ animationDelay: d(0), animationDuration: '1.4s' }}
            />
            {sparklePositions.map((pos, idx) => (
              <g
                key={`sparkle-${idx}`}
                className="effect-sparkle"
                style={{
                  animationDelay: d(idx * 18),
                  animationDuration: `${1.5 + idx * 0.1}s`
                }}
              >
                <line
                  x1={cx + pos.x * hexSize - 4} y1={cy + pos.y * hexSize}
                  x2={cx + pos.x * hexSize + 4} y2={cy + pos.y * hexSize}
                  stroke="#ffffaa" strokeWidth="2.5" strokeLinecap="round"
                />
                <line
                  x1={cx + pos.x * hexSize} y1={cy + pos.y * hexSize - 4}
                  x2={cx + pos.x * hexSize} y2={cy + pos.y * hexSize + 4}
                  stroke="#ffdd88" strokeWidth="2.5" strokeLinecap="round"
                />
              </g>
            ))}
          </g>
        );
      }

      case 'darkness':
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            <circle cx={cx} cy={cy} r={hexSize * 0.9} fill="#050505" opacity="0.75" />
            {[0, 1, 2, 3, 4].map((tendril) => {
              const angle = (tendril * Math.PI * 2 / 5) + (cellOffset * 0.022);
              const x = cx + Math.cos(angle) * hexSize * 0.65;
              const y = cy + Math.sin(angle) * hexSize * 0.65;
              return (
                <line
                  key={`tendril-${tendril}`}
                  x1={cx} y1={cy} x2={x} y2={y}
                  stroke="#2a0a3a"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  strokeDasharray="4 3"
                  className="effect-tendril"
                  style={{ animationDelay: d(tendril * 22) }}
                />
              );
            })}
          </g>
        );

      case 'air': {
        const R = hexSize * 0.58;
        const r = hexSize * 0.13;
        return (
          <g key={`effect-${cellKey}`} pointerEvents="none">
            {/* Outer rotating spiral arms */}
            <g
              className="vortex-spin"
              style={{
                transformOrigin: `${cx}px ${cy}px`,
                animationDelay: d(cellOffset * 12),
                animationDuration: `${3.2 + (cellOffset % 5) * 0.15}s`
              }}
            >
              {[0, 1, 2].map((i) => {
                const a = (i * Math.PI * 2 / 3) + cellOffset * 0.04;
                const sx = cx + R * Math.cos(a);
                const sy = cy + R * Math.sin(a);
                const ex = cx + r * Math.cos(a + Math.PI);
                const ey = cy + r * Math.sin(a + Math.PI);
                const c1x = cx + R * 0.55 * Math.cos(a + Math.PI / 2.8);
                const c1y = cy + R * 0.55 * Math.sin(a + Math.PI / 2.8);
                const c2x = cx + r * 2.4 * Math.cos(a + Math.PI * 0.72);
                const c2y = cy + r * 2.4 * Math.sin(a + Math.PI * 0.72);
                return (
                  <path
                    key={`arm-${i}`}
                    d={`M ${sx} ${sy} C ${c1x} ${c1y} ${c2x} ${c2y} ${ex} ${ey}`}
                    stroke={i === 1 ? '#a8d8f8' : '#ddf0ff'}
                    strokeWidth={i === 0 ? 2.2 : 1.6}
                    fill="none"
                    strokeLinecap="round"
                    opacity="0.78"
                  />
                );
              })}
            </g>
            {/* Inner counter-rotating debris particles */}
            <g
              className="vortex-spin-reverse"
              style={{
                transformOrigin: `${cx}px ${cy}px`,
                animationDelay: d(cellOffset * 8),
                animationDuration: `${2.1 + (cellOffset % 4) * 0.12}s`
              }}
            >
              {[0, 1, 2, 3, 4].map((p) => {
                const angle = (p * Math.PI * 2 / 5) + cellOffset * 0.07;
                const radius = hexSize * (0.18 + (p % 3) * 0.12);
                return (
                  <circle
                    key={`debris-${p}`}
                    cx={cx + Math.cos(angle) * radius}
                    cy={cy + Math.sin(angle) * radius}
                    r={p % 2 === 0 ? 1.8 : 1.1}
                    fill={p % 3 === 0 ? '#ffffff' : p % 3 === 1 ? '#b8e0ff' : '#88c4f0'}
                    opacity="0.72"
                  />
                );
              })}
            </g>
            {/* Eye of the vortex */}
            <circle
              cx={cx}
              cy={cy}
              r={hexSize * 0.09}
              fill="none"
              stroke="#e8f6ff"
              strokeWidth="1.5"
              className="vortex-eye"
              style={{ animationDelay: d(cellOffset * 15) }}
            />
          </g>
        );
      }

      default:
        return null;
    }
  };

  return (
    <div className="battlemap-shell" style={{ minHeight: '100vh', background: '#1a1a1a', color: '#e0e0e0' }}>
      {/* Sticky Navigation - Hidden in Watcher Mode or Advanced Fullscreen */}
      {!watcherMode && !advancedFullscreen && (
      <header className="bm-header">
        <div className="bm-header-bar">
          <span className="bm-title">🗺️ Battlemap</span>
          <nav className="bm-nav">
            {NAV_SECTIONS.map((section) => {
              const isActive = sectionVisibility[section.id];
              return (
                <button
                  key={section.id}
                  className={`bm-nav-btn${isActive ? ' active' : ''}`}
                  onClick={() => {
                    const wasVisible = sectionVisibility[section.id];
                    setSectionVisibility(prev => ({ ...prev, [section.id]: !prev[section.id] }));
                    if (!wasVisible) {
                      section.onNavigate?.();
                      requestAnimationFrame(() => scrollToSection(section.id));
                    } else {
                      setCurrentTool('select');
                      if (activeSection === section.id) {
                        const fallback = NAV_SECTIONS.find(s => s.id !== section.id && sectionVisibility[s.id])?.id;
                        if (fallback) setActiveSection(fallback);
                      }
                    }
                  }}
                  title={`${isActive ? 'Hide' : 'Show'} ${section.label}`}
                >
                  <span>{section.icon}</span>
                  <span>{section.label}</span>
                </button>
              );
            })}
            {advancedMode && (
              <button
                className="bm-nav-btn"
                onClick={toggleAdvancedFullscreen}
                title="Toggle Fullscreen Canvas"
              >
                {advancedFullscreen ? '🪟' : '🔲'}
              </button>
            )}
          </nav>
        </div>
      </header>
      )}

      <div style={{ padding: advancedFullscreen ? '0' : '12px', paddingTop: advancedFullscreen ? '0' : '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="battlemap-viewer" style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', gap: '10px', overflow: 'visible' }}>
          {/* Toolbar - Hidden in Watcher Mode, Advanced Fullscreen, or when toggled off */}
          {sectionVisibility.toolbar && !watcherMode && !advancedFullscreen && (
          <section id="toolbar" data-section-id="toolbar" style={{ scrollMarginTop: '90px' }}>
          <div className="resizable-panel" style={{
            background: '#2a2a2a',
            borderRadius: '10px',
            overflow: 'hidden',
            flexShrink: 0,
            resize: 'vertical',
            border: '1px solid #333'
          }}>
        {/* Toolbar Header */}
        <div className="bm-section-header">
          <span>⚙️</span>
          <span>Toolbar</span>
          <span style={{ opacity: 0.5, fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>core controls</span>
        </div>

        {/* Toolbar Content */}
      <div
        ref={toolbarContentRef}
        className="toolbar-content"
        style={{
          padding: '8px 10px',
          display: 'flex',
          gap: '10px',
          flexWrap: 'wrap',
          alignItems: 'center',
          background: '#242424'
        }}
      >
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

        {/* Refresh Token Stats Button */}
        <button
          onClick={handleRefreshTokenStats}
          disabled={tokens.filter(t => t.type === 'player').length === 0}
          style={{
            padding: '8px 16px',
            background: tokens.filter(t => t.type === 'player').length > 0 ? '#3498db' : '#555',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            cursor: tokens.filter(t => t.type === 'player').length > 0 ? 'pointer' : 'not-allowed',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            opacity: tokens.filter(t => t.type === 'player').length > 0 ? 1 : 0.5
          }}
          title="Refresh HP and conditions from character sheets"
        >
          🔄 Refresh Stats
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
        </div>
      </section>
      )}

      {/* Drawing Tools - Hidden in Watcher Mode, Advanced Fullscreen, or when toggled off */}
      {sectionVisibility.drawing && !watcherMode && !advancedFullscreen && (
      <div data-section-id="drawing" id="drawing" style={{
        background: '#2a2a2a',
        borderRadius: '8px',
        overflow: 'hidden',
        flexShrink: 0,
        border: '1px solid #333'
      }}>
        {/* Drawing Tools Header */}
        <div className="bm-section-header" style={{ cursor: 'pointer' }} onClick={() => setDrawingToolsCollapsed(!drawingToolsCollapsed)}>
          <span>🎨</span>
          <span>Drawing Tools</span>
          {drawingToolsCollapsed && (
            <span style={{ opacity: 0.7, fontWeight: 600, textTransform: 'none', letterSpacing: 0, color: '#2ecc71' }}>
              — {currentToolLabel} active
            </span>
          )}
          <span className={`collapse-chevron${!drawingToolsCollapsed ? ' open' : ''}`} style={{ marginLeft: 'auto' }}>›</span>
        </div>

        {/* Drawing Tools Content - Only show when not collapsed */}
        {!drawingToolsCollapsed && (
      <div
        ref={drawingToolsContentRef}
        style={{
          padding: '8px 10px',
          display: 'flex',
          gap: '6px',
          flexWrap: 'wrap',
          alignItems: 'center',
          background: '#242424'
        }}
      >
        {/* Tool buttons */}
        {[
          { id: 'paint', icon: '🖌️', label: 'Paint' },
          { id: 'eraser', icon: '🧹', label: 'Eraser' },
          { id: 'edit', icon: '✏️', label: 'Edit', title: 'Edit Data (tokens & hexes)' },
          { id: 'measure', icon: '📏', label: 'Measure' },
          { id: 'sphere', icon: '⭕', label: 'Sphere', title: 'Sphere (click hex or token)' },
          { id: 'cone', icon: '📐', label: 'Cone', title: 'Cone (click hex or token)' },
          { id: 'line', icon: '➖', label: 'Line' },
          { id: 'aura', icon: '✨', label: 'Aura', title: 'Aura (click token)' },
          { id: 'place-token', icon: '🎭', label: 'Place', title: 'Place Token' },
          { id: 'token', icon: '👤', label: 'Move', title: 'Move tokens' }
        ].map(tool => (
          <button
            key={tool.id}
            className={`bm-tool-btn${currentTool === tool.id ? ' active' : ''}`}
            onClick={() => { setCurrentTool(tool.id); resetAreaEffect(); }}
            title={tool.title || tool.label}
          >
            <span>{tool.icon}</span>
            <span>{tool.label}</span>
          </button>
        ))}

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
      </div>
        )}
      </div>
      )}

        {/* Aura Tool Settings - Effects Section (independent from Drawing Tools) */}
        {sectionVisibility.effects && !watcherMode && !advancedFullscreen && (
        <section id="effects" data-section-id="effects" style={{ scrollMarginTop: '90px' }}>
        {currentTool === 'aura' ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            background: 'linear-gradient(135deg, rgba(255, 107, 107, 0.15), rgba(231, 76, 60, 0.15))',
            padding: '10px 14px',
            borderRadius: '8px',
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
            
            {/* Aura Effect Presets */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontWeight: '600', color: '#e0e0e0', fontSize: '13px' }}>
                Effect Presets:
              </label>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(5, 1fr)',
                gap: '4px',
                maxWidth: '240px'
              }}>
                {Object.entries(EFFECT_PRESETS).map(([key, preset]) => (
                  <button
                    key={key}
                    onClick={() => {
                      // Extract primary color from gradient for aura
                      const gradientMatch = preset.gradient.match(/#[0-9a-fA-F]{6}/);
                      if (gradientMatch) {
                        setAuraOutlineColor(gradientMatch[0]);
                      }
                    }}
                    style={{
                      padding: '0',
                      width: '40px',
                      height: '40px',
                      background: preset.gradient,
                      border: '1px solid #4e4e52',
                      borderRadius: '6px',
                      color: '#fff',
                      cursor: 'pointer',
                      fontSize: '20px',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'transform 0.1s ease, box-shadow 0.1s ease'
                    }}
                    title={preset.name}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.05)';
                      e.currentTarget.style.boxShadow = `0 0 12px ${preset.glowColor}`;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)';
                      e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.3)';
                    }}
                  >
                    {preset.emoji}
                  </button>
                ))}
              </div>
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
                  display: 'grid',
                  gridTemplateColumns: 'repeat(5, 1fr)',
                  gap: '4px',
                  maxWidth: '240px'
                }}>
                  {Object.entries(EFFECT_PRESETS).map(([key, preset]) => (
                    <button
                      key={key}
                      onClick={(e) => {
                        setCurrentEffect(key);
                        animateEffectSelection(e.currentTarget, preset.glowColor);
                      }}
                      style={{
                        padding: '0',
                        width: '40px',
                        height: '40px',
                        background: currentEffect === key ? preset.gradient : 'rgba(42, 42, 42, 0.8)',
                        border: currentEffect === key ? '2px solid #fff' : '1px solid #4e4e52',
                        borderRadius: '6px',
                        color: '#fff',
                        cursor: 'pointer',
                        fontSize: '20px',
                        boxShadow: currentEffect === key 
                          ? `0 0 12px ${preset.glowColor}, 0 2px 6px rgba(0,0,0,0.5)` 
                          : '0 1px 3px rgba(0,0,0,0.3)',
                        transform: currentEffect === key ? 'scale(1.05)' : 'scale(1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                      title={preset.name}
                      onMouseEnter={(e) => {
                        if (currentEffect !== key) {
                          animateEffectHover(e.currentTarget, preset.gradient, preset.glowColor, true);
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (currentEffect !== key) {
                          animateEffectHover(e.currentTarget, 'rgba(42, 42, 42, 0.8)', preset.glowColor, false);
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
        ) : (
          <div style={{
            marginTop: '8px',
            padding: '12px 14px',
            background: '#1f1f1f',
            borderRadius: '8px',
            border: '1px dashed #444',
            color: '#999',
            fontWeight: '600'
          }}>
            Switch to the Aura tool to see aura controls.
          </div>
        )}
        </section>
        )}

        {/* Camera Controls Section - Full controls in GM mode */}
        {sectionVisibility.camera && !watcherMode && !advancedFullscreen && (
        <section id="camera" data-section-id="camera" style={{ scrollMarginTop: '90px' }}>
        <div className="resizable-panel" style={{
          background: '#2a2a2a',
          borderRadius: '10px',
          overflow: 'hidden',
          flexShrink: 0,
          resize: 'vertical',
          border: '1px solid #333'
        }}>
          {/* Camera Header */}
          <div className="bm-section-header">
            <span>📹</span>
            <span>Camera</span>
            <span style={{ opacity: 0.5, fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>view & layers</span>
          </div>

          {/* Camera Content */}
          <div style={{
            padding: '16px',
            display: 'flex',
            gap: '12px',
            flexWrap: 'wrap',
            alignItems: 'center',
            background: '#242424'
          }}>
            {/* Watcher Mode Button */}
            <button
              onClick={toggleWatcherMode}
              style={{
                padding: '10px 16px',
                background: 'linear-gradient(135deg, #27ae60, #229954)',
                border: '2px solid #27ae60',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
                transition: 'all 0.3s ease',
                fontSize: '13px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}
              title="Enter Watcher Mode (Fullscreen)"
            >
              👁️ Watcher Mode
            </button>

            {/* Open Watcher Tab Button */}
            {filePath && (
              <button
                onClick={() => window.open(`/?watcher=${encodeURIComponent(filePath)}`, '_blank')}
                style={{
                  padding: '10px 16px',
                  background: 'linear-gradient(135deg, #8e44ad, #6c3483)',
                  border: '2px solid #8e44ad',
                  borderRadius: '8px',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: '700',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
                  transition: 'all 0.3s ease',
                  fontSize: '13px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}
                title="Open battlemap in a dedicated watcher tab (auto-updates within 2s)"
              >
                🔗 Open Watcher Tab
              </button>
            )}

            {/* Set Default Position Button */}
            <button
              onClick={setCurrentAsDefaultPosition}
              style={{
                padding: '10px 16px',
                background: 'linear-gradient(135deg, rgba(52, 152, 219, 0.8), rgba(41, 128, 185, 0.8))',
                border: '2px solid rgba(52, 152, 219, 0.6)',
                borderRadius: '8px',
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

            {/* Placeholder for future layer toggles */}
            <div style={{
              display: 'flex',
              gap: '8px',
              flexWrap: 'wrap',
              width: '100%',
              paddingTop: '8px',
              borderTop: '1px solid #3e3e42'
            }}>
              <span style={{
                fontSize: '12px',
                color: '#888',
                fontStyle: 'italic'
              }}>
                Layer toggles coming soon: Background, Hexgrid, Tokens
              </span>
            </div>
          </div>
        </div>
        </section>
        )}

        {/* Minimal Watcher Mode Exit Button - Floating overlay when in Watcher Mode */}
        {watcherMode && (
          <div style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 10000
          }}>
            <button
              onClick={toggleWatcherMode}
              style={{
                padding: '12px 20px',
                background: 'linear-gradient(135deg, #e74c3c, #c0392b)',
                border: '2px solid #c0392b',
                borderRadius: '10px',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 0 20px rgba(231, 76, 60, 0.6), 0 4px 12px rgba(0,0,0,0.4)',
                transition: 'all 0.3s ease',
                fontSize: '14px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}
              title="Exit Watcher Mode (ESC)"
            >
              🔴 Exit Watcher Mode
            </button>
          </div>
        )}

        {/* Token Placement Settings */}
        {sectionVisibility.tokens && !watcherMode && !advancedFullscreen && (
        <section id="tokens" data-section-id="tokens" style={{ scrollMarginTop: '90px' }}>
        {currentTool === 'place-token' ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: 'linear-gradient(135deg, rgba(52, 152, 219, 0.15), rgba(41, 128, 185, 0.15))',
            padding: '16px 20px',
            borderRadius: '10px',
            border: '2px solid rgba(52, 152, 219, 0.4)',
            boxShadow: '0 4px 12px rgba(52, 152, 219, 0.2)',
            minWidth: '600px'
          }}>
            <label style={{ 
              fontWeight: '800', 
              color: '#5dade2',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '1.5px'
            }}>
              🎭 Token Placement
            </label>
            
            {/* Token Size Input */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: '#2a2a2a',
              padding: '10px',
              borderRadius: '6px'
            }}>
              <label style={{ fontWeight: '600', color: '#e0e0e0', fontSize: '13px', minWidth: '80px' }}>
                Token Size:
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={tokenPlacementSize.width}
                onChange={(e) => setTokenPlacementSize(prev => ({ ...prev, width: parseInt(e.target.value) || 1 }))}
                style={{
                  width: '60px',
                  padding: '6px',
                  borderRadius: '4px',
                  border: '1px solid #3e3e42',
                  background: '#1a1a1a',
                  color: '#e0e0e0'
                }}
              />
              <span style={{ color: '#888' }}>×</span>
              <input
                type="number"
                min="1"
                max="10"
                value={tokenPlacementSize.height}
                onChange={(e) => setTokenPlacementSize(prev => ({ ...prev, height: parseInt(e.target.value) || 1 }))}
                style={{
                  width: '60px',
                  padding: '6px',
                  borderRadius: '4px',
                  border: '1px solid #3e3e42',
                  background: '#1a1a1a',
                  color: '#e0e0e0'
                }}
              />
              <span style={{ fontSize: '12px', color: '#888' }}>hexes (width × height)</span>
            </div>

            {/* Player Characters Section */}
            <div>
              <h5 style={{ 
                margin: '0 0 8px 0', 
                color: '#27ae60', 
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                👥 Player Characters
              </h5>
              <div style={{ 
                display: 'flex', 
                gap: '8px', 
                flexWrap: 'wrap',
                background: '#1a1a1a',
                padding: '10px',
                borderRadius: '6px',
                maxHeight: '150px',
                overflowY: 'auto'
              }}>
                {availableCharacters.map(char => (
                  <button
                    key={char.name}
                    onClick={() => setTokenToPlace({
                      ...char,
                      avatarPng: char.avatarPngNormalized || char.avatarPng,
                      type: 'player',
                      width: tokenPlacementSize.width,
                      height: tokenPlacementSize.height
                    })}
                    style={{
                      padding: '8px 10px',
                      background: tokenToPlace?.name === char.name 
                        ? 'linear-gradient(135deg, #27ae60, #2ecc71)' 
                        : 'rgba(39, 174, 96, 0.2)',
                      border: tokenToPlace?.name === char.name ? '2px solid #2ecc71' : '2px solid #27ae60',
                      borderRadius: '6px',
                      color: '#e0e0e0',
                      cursor: 'pointer',
                      fontSize: '11px',
                      fontWeight: '600',
                      transition: 'all 0.2s',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '6px',
                      minWidth: '70px'
                    }}
                    onMouseEnter={(e) => {
                      if (tokenToPlace?.name !== char.name) {
                        e.currentTarget.style.background = 'rgba(39, 174, 96, 0.4)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (tokenToPlace?.name !== char.name) {
                        e.currentTarget.style.background = 'rgba(39, 174, 96, 0.2)';
                      }
                    }}
                  >
                    {char.avatarPng || char.avatar ? (
                      <PixelAvatar
                        avatarPng={char.avatarPng}
                        size={40}
                        borderColor={char.color || '#27ae60'}
                        background="rgba(0,0,0,0.3)"
                        placeholderLabel={char.name}
                      />
                    ) : (
                      <div style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '20px'
                      }}>
                        👤
                      </div>
                    )}
                    <span style={{
                      fontSize: '10px',
                      textAlign: 'center',
                      lineHeight: '1.2',
                      maxWidth: '70px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {char.name}
                    </span>
                  </button>
                ))}
                {availableCharacters.length === 0 && (
                  <p style={{ 
                    color: '#888', 
                    margin: 0, 
                    fontSize: '11px',
                    textAlign: 'center',
                    width: '100%',
                    padding: '10px'
                  }}>
                    No player characters available
                  </p>
                )}
              </div>
            </div>

            {/* Enemy Tokens Section */}
            <div>
              <h5 style={{ 
                margin: '0 0 8px 0', 
                color: '#e74c3c', 
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                ⚔️ Enemy / NPC Tokens
              </h5>
              <div style={{ 
                display: 'flex', 
                gap: '8px', 
                flexWrap: 'wrap',
                background: '#1a1a1a',
                padding: '10px',
                borderRadius: '6px'
              }}>
                {enemyTokens.map(enemy => (
                  <button
                    key={enemy.name}
                    onClick={() => setTokenToPlace({
                      name: enemy.name,
                      color: enemy.color,
                      icon: enemy.icon,
                      type: 'enemy',
                      width: tokenPlacementSize.width,
                      height: tokenPlacementSize.height
                    })}
                    style={{
                      padding: '8px 12px',
                      background: tokenToPlace?.name === enemy.name 
                        ? 'linear-gradient(135deg, #e74c3c, #c0392b)' 
                        : 'rgba(231, 76, 60, 0.2)',
                      border: tokenToPlace?.name === enemy.name ? '2px solid #c0392b' : '2px solid #e74c3c',
                      borderRadius: '6px',
                      color: '#e0e0e0',
                      cursor: 'pointer',
                      fontSize: '12px',
                      fontWeight: '600',
                      transition: 'all 0.2s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                    onMouseEnter={(e) => {
                      if (tokenToPlace?.name !== enemy.name) {
                        e.currentTarget.style.background = 'rgba(231, 76, 60, 0.4)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (tokenToPlace?.name !== enemy.name) {
                        e.currentTarget.style.background = 'rgba(231, 76, 60, 0.2)';
                      }
                    }}
                  >
                    {enemy.icon} {enemy.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Instructions */}
            {tokenToPlace ? (
              <div style={{
                background: '#27ae60',
                padding: '10px 12px',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: '600',
                color: '#fff',
                textAlign: 'center'
              }}>
                ✓ Click on the hex grid to place "{tokenToPlace.name}" ({tokenToPlace.width}×{tokenToPlace.height})
              </div>
            ) : (
              <div style={{
                background: 'rgba(255, 255, 255, 0.1)',
                padding: '10px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#888',
                textAlign: 'center'
              }}>
                Select a token above to place on the grid
              </div>
            )}
          </div>
        ) : (
          <div style={{
            marginTop: '8px',
            padding: '12px',
            border: '1px dashed #3e3e42',
            borderRadius: '8px',
            color: '#b0b0b0',
            background: '#1f1f1f'
          }}>
            Select the Token tool from the toolbar to manage tokens.
          </div>
        )}
        </section>
        )}

        {/* Drawing Tools Additional Controls - Only visible when Drawing Tools section is on */}
        {sectionVisibility.drawing && !watcherMode && !advancedFullscreen && (
        <>
        {/* Enhanced Effect Presets - Horizontal Design */}
        {currentTool !== 'token' && currentTool !== 'place-token' && currentTool !== 'aura' && currentTool !== 'eraser' && currentTool !== 'measure' && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            width: '100%'
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
              gap: '4px',
              flexWrap: 'wrap',
              alignItems: 'center'
            }}>
              {Object.entries(EFFECT_PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={(e) => {
                    setCurrentEffect(key);
                    animateEffectSelection(e.currentTarget, preset.glowColor);
                  }}
                  style={{
                    position: 'relative',
                    width: '46px',
                    height: '52px',
                    padding: 0,
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '2px',
                    transition: 'transform 0.15s ease'
                  }}
                  title={preset.name}
                  onMouseEnter={(e) => animateToolHover(e.currentTarget, true)}
                  onMouseLeave={(e) => animateToolHover(e.currentTarget, false)}
                >
                  <div style={{
                    position: 'relative',
                    width: '38px',
                    height: '44px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <svg
                      viewBox="0 0 100 115"
                      style={{
                        position: 'absolute',
                        width: '100%',
                        height: '100%',
                        filter: currentEffect === key
                          ? `drop-shadow(0 0 8px ${preset.glowColor})`
                          : 'none',
                        transition: 'filter 0.2s ease'
                      }}
                    >
                      <defs>
                        <linearGradient id={`grad-${key}`} x1="0%" y1="0%" x2="100%" y2="100%">
                          {preset.colors && preset.colors.map((color, i) => (
                            <stop key={i} offset={`${(i / (preset.colors.length - 1)) * 100}%`} stopColor={color} />
                          ))}
                        </linearGradient>
                      </defs>
                      <polygon
                        points="50,2 95,28 95,87 50,113 5,87 5,28"
                        fill={currentEffect === key ? `url(#grad-${key})` : '#1a1a1a'}
                        stroke={currentEffect === key ? '#fff' : '#333'}
                        strokeWidth={currentEffect === key ? '3' : '2'}
                        style={{ transition: 'all 0.2s ease' }}
                      />
                    </svg>
                    <span style={{
                      position: 'relative',
                      fontSize: '22px',
                      zIndex: 1,
                      filter: currentEffect === key ? 'none' : 'grayscale(1) opacity(0.5)',
                      transition: 'filter 0.2s ease'
                    }}>
                      {preset.emoji}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Enhanced Animation Intensity Controls (Advanced Mode Only) */}
        {advancedMode && currentTool !== 'token' && currentTool !== 'place-token' && currentEffect !== 'none' && (
          <div style={{
            display: 'flex',
            gap: '15px',
            width: '100%',
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
        {currentTool !== 'token' && currentTool !== 'place-token' && currentEffect !== 'none' && (
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
        {currentTool !== 'token' && currentTool !== 'place-token' && currentTool !== 'eraser' && currentTool !== 'measure' && currentEffect === 'none' && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            width: '100%'
          }}>
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
          </div>
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
        </>
        )}
      
      {/* Canvas */}
      <div
        ref={canvasRef}
        style={{
          minHeight: watcherMode || advancedFullscreen ? '100vh' : '600px',
          flexGrow: 1,
          background: '#1a1a1a',
          borderRadius: watcherMode || advancedFullscreen ? '0' : '8px',
          overflow: 'auto', // Always allow scrolling for panning
          position: 'relative',
          // Dynamic padding: more padding when zoomed in to allow panning beyond edges
          // In watcher/fullscreen: 1000px, otherwise scale from 200px to 2000px based on zoom
          padding: watcherMode || advancedFullscreen 
            ? '1000px' 
            : `${Math.max(200, Math.min(2000, 200 * scale))}px`
        }}
      >
        {/* Exit Fullscreen Button - Only in Advanced Fullscreen */}
        {advancedFullscreen && (
          <button
            onClick={toggleAdvancedFullscreen}
            style={{
              position: 'fixed',
              top: '20px',
              right: '20px',
              zIndex: 15000,
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              border: '2px solid #3e3e42',
              background: 'rgba(42, 42, 42, 0.95)',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.1)';
              e.currentTarget.style.background = 'rgba(60, 60, 60, 0.95)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.background = 'rgba(42, 42, 42, 0.95)';
            }}
            title="Exit Fullscreen"
          >
            ✕
          </button>
        )}
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
            onClick={() => {
              setMarkerPopup(null);
              setContextMenu(null);
            }}
            onMouseUp={() => {
              setIsPainting(false);
              setIsPanning(false);
            }}
            onMouseLeave={() => {
              setIsPainting(false);
              setIsPanning(false);
            }}
            onMouseMove={(e) => {
              // Handle camera panning
              if (isPanning) {
                e.preventDefault();
                const canvas = canvasRef.current;
                if (canvas) {
                  const deltaX = panStart.x - e.clientX;
                  const deltaY = panStart.y - e.clientY;
                  canvas.scrollLeft = scrollStart.x + deltaX;
                  canvas.scrollTop = scrollStart.y + deltaY;
                }
              }
              
              // Handle token dragging
              if (draggedToken) {
                // Token dragging handled by hex click
              }
            }}
          >
            {/* SVG Definitions for effect patterns and gradients */}
            <defs>
              {/* Earth static pattern */}
              <pattern id="earthPattern" width="20" height="20" patternUnits="userSpaceOnUse">
                <rect width="20" height="20" fill="#8b6f47" />
                <circle cx="5" cy="5" r="2" fill="#6f5436" opacity="0.6" />
                <circle cx="15" cy="8" r="3" fill="#9a7b5a" opacity="0.5" />
                <circle cx="8" cy="15" r="2.5" fill="#6f5436" opacity="0.7" />
                <circle cx="18" cy="17" r="2" fill="#a0826d" opacity="0.6" />
              </pattern>
              {/* Fire radial glow gradient */}
              <radialGradient id="fireGradient" cx="50%" cy="60%" r="50%">
                <stop offset="0%"   stopColor="#ffaa00" stopOpacity="0.75" />
                <stop offset="50%"  stopColor="#ff6b1a" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#ff3300" stopOpacity="0" />
              </radialGradient>
              {/* Ice radial gradient */}
              <radialGradient id="iceGradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%"   stopColor="#ccffff" stopOpacity="0.65" />
                <stop offset="60%"  stopColor="#88ccff" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#4488cc" stopOpacity="0" />
              </radialGradient>
              {/* Spirit radial gradient */}
              <radialGradient id="spiritGradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%"   stopColor="#dda0dd" stopOpacity="0.7" />
                <stop offset="60%"  stopColor="#9370db" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#6a0dad" stopOpacity="0" />
              </radialGradient>
              {/* Water radial gradient */}
              <radialGradient id="waterGradient" cx="50%" cy="40%" r="55%">
                <stop offset="0%"   stopColor="#80c8ff" stopOpacity="0.7" />
                <stop offset="60%"  stopColor="#3399ff" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#1155aa" stopOpacity="0" />
              </radialGradient>
            </defs>

            {hexGrid.map((row, rIdx) =>
              row.map((cell, cIdx) => {
                const { cx, cy, points } = hexGeometry[rIdx]?.[cIdx] ?? (() => { const c = getHexCoordinates(rIdx, cIdx); return { ...c, points: getHexVertices(c.cx, c.cy) }; })();
                // Check if any token occupies this cell (O(1) via pre-computed set)
                const hasToken = tokenOccupiedCells.has(`${rIdx}-${cIdx}`);
                
                // Get base color and effect class
                const baseColor = cell.filled ? getEffectBaseColor(cell) : 'transparent';
                const effectClass = getEffectAnimationClass(cell);
                const effectPreset = cell.effect && EFFECT_PRESETS[cell.effect];
                
                // Get glow effect for animated cells
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
                    fill={baseColor}
                    fillOpacity={cell.filled ? 0.6 : 0}
                    stroke={hasToken ? '#64c8ff' : (isOuterEdge ? 'rgba(150, 150, 150, 0.6)' : 'rgba(150, 150, 150, 0.3)')}
                    strokeWidth={hasToken ? 3 : (isOuterEdge ? 2 : 1)}
                    className={effectClass}
                    style={{
                      cursor: currentTool === 'select' ? (isPanning ? 'grabbing' : 'grab') :
                              currentTool === 'edit' ? 'pointer' :
                              currentTool === 'token' ? 'pointer' : 
                              (showDirectionSelect && currentTool === 'cone') ? 'pointer' :
                              (currentTool === 'place-token' && tokenToPlace) ? 'copy' :
                              'crosshair',
                      transition: 'all 0.1s',
                      filter: glowFilter
                    }}
                    onMouseDown={(e) => {
                      if (currentTool === 'select') {
                        // In select mode, check if clicking on a token or empty space
                        const tokenAtPos = tokens.find(t => {
                          const cells = getTokenCells(t.row, t.col, t.width || 1, t.height || 1);
                          return cells.some(c => c.row === rIdx && c.col === cIdx);
                        });
                        
                        if (!tokenAtPos) {
                          // Clicking on empty space - start camera pan
                          e.preventDefault();
                          setIsPanning(true);
                          setPanStart({ x: e.clientX, y: e.clientY });
                          const canvas = canvasRef.current;
                          if (canvas) {
                            setScrollStart({ x: canvas.scrollLeft, y: canvas.scrollTop });
                          }
                          return;
                        }
                      }
                      
                      if (currentTool === 'edit') {
                        // Edit tool: always handle click (will open modal for token or hex)
                        handleHexClick(rIdx, cIdx, false);
                      } else if (currentTool === 'token') {
                        handleHexClick(rIdx, cIdx, false);
                      } else if (currentTool === 'measure' || currentTool === 'line' || 
                                 currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura' || currentTool === 'place-token') {
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
                        queueHexPaint(rIdx, cIdx, !paintMode);
                      } else if (isPainting && currentTool === 'eraser') {
                        queueHexPaint(rIdx, cIdx, true);
                      } else if (draggedToken) {
                        setDragPreview({ row: rIdx, col: cIdx });
                      }
                    }}
                    onMouseUp={() => {
                      if (draggedToken) {
                        handleTokenDrop(rIdx, cIdx);
                      }
                    }}
                    onMouseLeave={() => {
                      if (draggedToken) {
                        setDragPreview(null);
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
              
              // Always calculate aura pattern based on token position and diameter for border
              // This ensures the border is drawn correctly even if some hexes aren't filled
              const tokenWidth = token.width || 1;
              const tokenHeight = token.height || 1;
              const auraHexes = generateTokenAuraPattern(token.row, token.col, tokenWidth, tokenHeight, token.aura.diameter);
              
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
              
              // Convert hex color to rgba with 50% opacity
              const auraColor = token.aura.outlineColor || '#64c8ff';
              const hexToRgba = (hex, alpha = 0.5) => {
                const r = parseInt(hex.slice(1, 3), 16);
                const g = parseInt(hex.slice(3, 5), 16);
                const b = parseInt(hex.slice(5, 7), 16);
                return `rgba(${r}, ${g}, ${b}, ${alpha})`;
              };
              
              return (
                <g key={`aura-outline-${token.id}`}>
                  {/* Semi-transparent fill for aura hexes - only for empty cells */}
                  {auraHexes.map(({ row, col }, idx) => {
                    // Check if the cell is filled - if so, skip the fill
                    // BUT allow it if it's filled because of THIS aura (auraTokenId matches)
                    const cell = hexGrid[row]?.[col];
                    if (cell && cell.filled && cell.auraTokenId !== token.id) {
                      return null; // Don't fill already painted hexes (unless they're part of this aura)
                    }
                    
                    const { cx, cy } = getHexCoordinates(row, col);
                    const hexVertices = [];
                    for (let i = 0; i < 6; i++) {
                      const angle = (Math.PI / 3) * i + Math.PI / 2;
                      const x = cx + hexSize * Math.cos(angle);
                      const y = cy + hexSize * Math.sin(angle);
                      hexVertices.push(`${x},${y}`);
                    }
                    return (
                      <polygon
                        key={`aura-fill-${idx}`}
                        points={hexVertices.join(' ')}
                        fill={hexToRgba(auraColor, 0.5)}
                        style={{ pointerEvents: 'none' }}
                      />
                    );
                  })}
                  
                  {/* Outline edges */}
                  {outerEdges.map((edge, idx) => (
                    <line
                      key={`aura-edge-${idx}`}
                      x1={edge.x1}
                      y1={edge.y1}
                      x2={edge.x2}
                      y2={edge.y2}
                      stroke={auraColor}
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
            {draggedToken && dragPreview && (() => {
              const token = tokens.find(t => t.id === draggedToken);
              if (!token) return null;
              const tokenWidth = token.width || 1;
              const tokenHeight = token.height || 1;
              const previewCells = getTokenCells(dragPreview.row, dragPreview.col, tokenWidth, tokenHeight);
              return (
                <g pointerEvents="none" opacity={0.35}>
                  {previewCells.map(({ row, col }, idx) => {
                    const { cx, cy } = getHexCoordinates(row, col);
                    const verts = getHexVerticesArray(cx, cy).map(({ x, y }) => `${x},${y}`).join(' ');
                    return (
                      <polygon
                        key={`drag-preview-${row}-${col}-${idx}`}
                        points={verts}
                        fill={token.color || '#64c8ff'}
                        stroke="#64c8ff"
                        strokeWidth={3}
                        fillOpacity={0.25}
                        strokeOpacity={0.8}
                      />
                    );
                  })}
                </g>
              );
            })()}
            {tokens.map(token => {
              const isDragging = draggedToken === token.id;
              const tokenWidth = token.width || 1;
              const tokenHeight = token.height || 1;
              const cells = getTokenCells(token.row, token.col, tokenWidth, tokenHeight);
              
              // Get coordinates of the center of the token (middle of all occupied cells)
              const firstCell = getHexCoordinates(token.row, token.col);
              const lastCell = getHexCoordinates(token.row + tokenHeight - 1, token.col + tokenWidth - 1);
              const centerX = (firstCell.cx + lastCell.cx) / 2;
              const centerY = (firstCell.cy + lastCell.cy) / 2;
              
              // Calculate size of the token image/icon
              const tokenSizeMultiplier = Math.max(tokenWidth, tokenHeight);
              
              const isEnemy = token.type === 'enemy';
              const isPlayer = token.type === 'player';
              
              return (
                <g
                  key={token.id}
                  ref={(el) => {
                    if (el) {
                      tokenRefs.current.set(token.id, el);
                    } else {
                      tokenRefs.current.delete(token.id);
                    }
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation(); // Prevent hex click from firing
                    e.preventDefault(); // Prevent default browser behavior
                    
                    // Right-click should open context menu, not drag
                    if (e.button === 2) {
                      return;
                    }
                    
                    // For edit tool, open the edit modal
                    if (currentTool === 'edit') {
                      handleEditDataClick(token.row, token.col);
                      return;
                    }
                    
                    // For sphere/cone/aura tools, let the click pass through to the hex
                    if (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') {
                      // Don't handle the token drag, let it bubble to hex
                      return;
                    }
                    
                    // For token selection tool
                    if (currentTool === 'token') {
                      setSelectedToken(token.id);
                      return;
                    }
                    
                    // For select mode and other tools, handle token dragging
                    handleTokenDragStart(token.id);
                  }}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setContextMenu({
                      x: e.clientX,
                      y: e.clientY,
                      tokenId: token.id,
                      token: token
                    });
                  }}
                  style={{ 
                    cursor: currentTool === 'edit' ? 'pointer' :
                            (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') ? 'crosshair' : 
                            currentTool === 'token' ? 'pointer' :
                            currentTool === 'select' ? 'grab' :
                            'move',
                    pointerEvents: (currentTool === 'sphere' || currentTool === 'cone' || currentTool === 'aura') ? 'none' : 'auto',
                    opacity: isDragging ? 0.45 : 1,
                    filter: isDragging ? 'drop-shadow(0 0 8px rgba(100,200,255,0.7))' : undefined
                  }}
                >
                  {/* Token Background - render hexagons for all occupied cells */}
                  <defs>
                    <linearGradient id={`tokenGradient-${token.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor={token.color || '#888'} />
                      <stop offset="100%" stopColor={`${token.color || '#888'}dd`} />
                    </linearGradient>
                    
                    {/* Clipping path for all hexagons occupied by token */}
                    <clipPath id={`hex-clip-token-${token.id}`}>
                      {cells.map((cell, idx) => {
                        const { cx, cy } = getHexCoordinates(cell.row, cell.col);
                        const points = getHexVertices(cx, cy);
                        return <polygon key={idx} points={points} />;
                      })}
                    </clipPath>
                  </defs>
                  
                  {/* Render background hexagon for each occupied cell - only if color is not transparent */}
                  {token.color && token.color !== 'transparent' && token.color !== 'rgba(0,0,0,0)' && (
                    <>
                      {cells.map((cell, idx) => {
                        const { cx, cy } = getHexCoordinates(cell.row, cell.col);
                        const points = getHexVertices(cx, cy);
                        return (
                          <polygon
                            key={idx}
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
                        );
                      })}
                    </>
                  )}
                  
                  {/* Token Icon/Avatar - centered across all cells, scaled to fit */}
                  {(token.customBackgroundPng || token.avatarPng || token.icon) ? (
                    <g clipPath={`url(#hex-clip-token-${token.id})`}>
                      {(() => {
                        const characterMatch = availableCharacters.find(c => c.name === token.name);
                        const baseImage = characterMatch?.avatarPngNormalized
                          || token.customBackgroundPng
                          || token.avatarPng
                          || characterMatch?.avatarPng
                          || token.icon;
                        // Use stable mount timestamp — not Date.now() — so the URL is
                        // consistent across renders and the browser cache is not busted every frame.
                        const imageSrc = baseImage && typeof baseImage === 'string' && !baseImage.startsWith('data:')
                          ? `${baseImage}${baseImage.includes('?') ? '&' : '?'}cb=${mountTimestamp.current}`
                          : baseImage;
                        return (
                          <foreignObject
                            x={centerX - hexSize * tokenSizeMultiplier}
                            y={centerY - hexSize * tokenSizeMultiplier}
                            width={hexSize * 2 * tokenSizeMultiplier}
                            height={hexSize * 2 * tokenSizeMultiplier}
                          >
                            <div 
                              xmlns="http://www.w3.org/1999/xhtml"
                              style={{
                                width: '100%',
                                height: '100%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                overflow: 'hidden'
                              }}
                            >
                              <img
                                src={imageSrc}
                                alt={token.name}
                                style={{
                                  width: '100%',
                                  height: '100%',
                                  objectFit: 'cover',
                                  imageRendering: 'pixelated',
                                  filter: 'none',
                                  mixBlendMode: 'normal'
                                }}
                              />
                            </div>
                          </foreignObject>
                        );
                      })()}
                    </g>
                  ) : token.icon ? (
                    // Enemy token with icon emoji - centered across all cells, scaled
                    <text
                      x={centerX}
                      y={centerY}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={hexSize * 0.9 * tokenSizeMultiplier}
                    >
                      {token.icon}
                    </text>
                  ) : (
                    // Fallback: First 3 letters
                    <text
                      x={centerX}
                      y={centerY}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill="#fff"
                      fontSize={hexSize * 0.6 * tokenSizeMultiplier}
                      fontWeight="bold"
                      style={{ pointerEvents: 'none', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}
                    >
                      {token.name.slice(0, 3).toUpperCase()}
                    </text>
                  )}

                  {/* HP Bar and Condition Rings */}
                  {(() => {
                    // Calculate HP data - only show if we have valid HP data
                    const hasValidHp = token.currentHp !== undefined && token.maxHp !== undefined;
                    const currentHp = hasValidHp ? token.currentHp : (token.hp || 0);
                    const maxHp = hasValidHp ? token.maxHp : (token.hp ? 100 : 0);
                    const hpPercentage = maxHp > 0 ? (currentHp / maxHp) * 100 : 0;
                    
                    // Get conditions
                    const conditions = token.conditions || [];
                    
                    // Skip HP bar rendering if no valid HP data or showHp is explicitly false
                    // Default to true for player tokens if not set
                    const showHpEnabled = token.showHp !== false;
                    const shouldShowHpBar = hasValidHp && maxHp > 0 && showHpEnabled;
                    
                    // HP bar should be positioned outside the token's stroke edge
                    // Token background has strokeWidth=3, so we offset outward to avoid overlapping
                    const tokenStrokeWidth = 3; // Must match the polygon strokeWidth
                    const hpBarStrokeWidth = 4; // Thicker for better visibility outside the token
                    const hpBarOutset = 8; // Offset outward from hex edge to position HP bar outside token
                    const healthBarColor = getHealthBarColor(hpPercentage);
                    const hpTooltip = `HP: ${Math.round(currentHp)}/${maxHp}`;
                    
                    return (
                      <g>
                        {/* Draw HP bar around entire token outline - only if we have valid HP data */}
                        {shouldShowHpBar && (() => {
                          // Get all outer edges of the multi-tile token
                          const outerEdges = getTokenOutlinePath(token.row, token.col, tokenWidth, tokenHeight);
                          
                          if (outerEdges.length === 0) return null;
                          
                          // Calculate total perimeter length
                          let totalLength = 0;
                          outerEdges.forEach(edge => {
                            const dx = edge.x2 - edge.x1;
                            const dy = edge.y2 - edge.y1;
                            totalLength += Math.sqrt(dx * dx + dy * dy);
                          });
                          
                          // Calculate how much of the outline to fill based on HP percentage
                          const fillLength = (hpPercentage / 100) * totalLength;
                          
                          // Build paths
                          let fullPath = '';
                          let hpPath = '';
                          let currentLength = 0;
                          let hpPathComplete = false;
                          
                          outerEdges.forEach((edge, i) => {
                            const edgeLength = Math.sqrt(
                              (edge.x2 - edge.x1) ** 2 + (edge.y2 - edge.y1) ** 2
                            );
                            
                            // Add to full path
                            if (i === 0) {
                              fullPath = `M ${edge.x1},${edge.y1} L ${edge.x2},${edge.y2}`;
                            } else {
                              fullPath += ` M ${edge.x1},${edge.y1} L ${edge.x2},${edge.y2}`;
                            }
                            
                            // Add to HP path if we haven't completed the HP fill yet
                            if (!hpPathComplete && hpPercentage > 0) {
                              if (currentLength + edgeLength <= fillLength) {
                                // Full edge fits in HP fill
                                if (i === 0) {
                                  hpPath = `M ${edge.x1},${edge.y1} L ${edge.x2},${edge.y2}`;
                                } else {
                                  hpPath += ` M ${edge.x1},${edge.y1} L ${edge.x2},${edge.y2}`;
                                }
                                currentLength += edgeLength;
                              } else {
                                // Partial edge
                                const remainingLength = fillLength - currentLength;
                                const ratio = remainingLength / edgeLength;
                                const partialX = edge.x1 + (edge.x2 - edge.x1) * ratio;
                                const partialY = edge.y1 + (edge.y2 - edge.y1) * ratio;
                                
                                if (i === 0) {
                                  hpPath = `M ${edge.x1},${edge.y1} L ${partialX},${partialY}`;
                                } else {
                                  hpPath += ` M ${edge.x1},${edge.y1} L ${partialX},${partialY}`;
                                }
                                hpPathComplete = true;
                              }
                            }
                          });
                          
                          return (
                            <g>
                              {/* Health bar ring background (gray outline) */}
                              <path
                                d={fullPath}
                                fill="none"
                                stroke="#2c3e50"
                                strokeWidth={hpBarStrokeWidth}
                                opacity="0.3"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                style={{ pointerEvents: 'stroke', cursor: 'help' }}
                              >
                                <title>{hpTooltip}</title>
                              </path>
                              
                              {/* Health bar fill (colored portion) */}
                              {hpPath && (
                                <path
                                  d={hpPath}
                                  fill="none"
                                  stroke={healthBarColor}
                                  strokeWidth={hpBarStrokeWidth}
                                  opacity="0.95"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  style={{ pointerEvents: 'stroke', cursor: 'help' }}
                                >
                                  <title>{hpTooltip}</title>
                                </path>
                              )}
                            </g>
                          );
                        })()}
                        
                        {/* Token Markers (HP, Conditions, Defensive Stats) */}
                        <TokenMarkers
                          token={token}
                          tokenSizeMultiplier={tokenSizeMultiplier}
                          hexSize={hexSize}
                          getHexCoordinates={getHexCoordinates}
                          conditionDescriptions={conditionDescriptions}
                          setMarkerPopup={setMarkerPopup}
                        />
                      </g>
                    );
                  })()}
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
                  // Check if there's a token at origin (check all cells occupied by each token)
                  const tokenAtOrigin = tokens.find(t => {
                    const cells = getTokenCells(t.row, t.col, t.width || 1, t.height || 1);
                    return cells.some(c => c.row === areaOrigin.row && c.col === areaOrigin.col);
                  });
                  
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
      {sectionVisibility.camera && watcherMode && (
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

      {/* Edit Data Modal */}
      <EditDataModal
        isOpen={editModalOpen}
        onClose={() => {
          setEditModalOpen(false);
          setEditTarget(null);
        }}
        target={editTarget}
        onSave={handleEditDataSave}
        onOpenCharacterSheet={handleOpenCharacterSheet}
      />
      
      {/* Token Context Menu */}
      <TokenContextMenu
        contextMenu={contextMenu}
        setContextMenu={setContextMenu}
        setTokens={setTokens}
        setTokenToMove={setTokenToMove}
        handleToggleTokenHp={handleToggleTokenHp}
        handleEditDataClick={handleEditDataClick}
        handleRemoveToken={handleRemoveToken}
        handleOpenCharacterSheet={handleOpenCharacterSheet}
        handleOpenNpcCharacterSheet={handleOpenNpcCharacterSheet}
        onShowDetails={handleShowTokenDetails}
      />
      
      {/* Token Details Popup */}
      <TokenDetailsPopup
        token={detailsPopupToken}
        onClose={() => setDetailsPopupToken(null)}
      />
      
      {/* Water Cell Count Overlay — left border */}
      {waterCellCount > 0 && (
        <div style={{
          position: 'fixed',
          left: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 9000,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '6px',
          background: 'linear-gradient(180deg, rgba(20,40,70,0.92) 0%, rgba(10,30,60,0.96) 100%)',
          border: '1px solid rgba(77,166,255,0.35)',
          borderLeft: 'none',
          borderRadius: '0 10px 10px 0',
          padding: '14px 10px',
          boxShadow: '3px 0 18px rgba(30,120,220,0.25)',
          backdropFilter: 'blur(6px)',
          minWidth: '52px',
          pointerEvents: 'none',
        }}>
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M11 2 C11 2 4 10 4 14.5 C4 18.09 7.13 21 11 21 C14.87 21 18 18.09 18 14.5 C18 10 11 2 11 2Z"
              fill="rgba(60,160,255,0.7)" stroke="#80c8ff" strokeWidth="1.2"/>
            <path d="M8 15.5 C8 13.5 9.5 12 11 11" stroke="rgba(200,235,255,0.6)" strokeWidth="1.1" strokeLinecap="round"/>
          </svg>
          <span style={{
            color: '#80c8ff',
            fontSize: '18px',
            fontWeight: '700',
            lineHeight: 1,
            fontVariantNumeric: 'tabular-nums',
          }}>
            {waterCellCount}
          </span>
          <span style={{
            color: 'rgba(160,210,255,0.7)',
            fontSize: '9px',
            fontWeight: '600',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            textAlign: 'center',
            lineHeight: 1.2,
          }}>
            water<br/>cells
          </span>
        </div>
      )}

      {/* Marker Popup (for conditions and defensive stats) */}
      {markerPopup && (
        <MarkerPopup
          markerPopup={markerPopup}
          setMarkerPopup={setMarkerPopup}
          setTokens={setTokens}
          onSyncTokenSheet={syncTokenSheetUpdates}
        />
      )}
    </div>
    </div>
    </div>
  );
};

export default BattlemapViewer;
