import React, { useEffect, useMemo, useState, useRef } from 'react';
import './BattlemapViewer.css';
import { API_BASE_URL } from '../config/api';
import BattlemapToolbar from './BattlemapToolbar';
import PaintControls from './PaintControls';
import BattlemapCanvas from './BattlemapCanvas';

const sanitizeTiles = (tiles) => {
  if (!Array.isArray(tiles)) return [];
  return tiles.map((row) => {
    if (!Array.isArray(row)) return [];
    return row.map((pix) => (Array.isArray(pix) ? pix : [0, 0, 0, 0]));
  });
};

const makeBlankTiles = (rows, cols) =>
  Array.from({ length: rows }, () =>
    Array.from({ length: cols }, () => [0, 0, 0, 0])
  );

const SAFE_DEFAULT = {
  mapImage: '',
  tiles: []
};

const resolveImageUrl = (dirPath, imageName) => {
  if (!imageName) return '';
  const joined = dirPath ? `${dirPath}/${imageName}` : imageName;
  return `${API_BASE_URL}/player_root/${encodeURIComponent(joined)}`;
};

const BattlemapViewer = ({ filePath, content }) => {
  const [parsed, setParsed] = useState(SAFE_DEFAULT);
  const [imageOptions, setImageOptions] = useState([]);
  const [selectedImage, setSelectedImage] = useState('');
  const [localImageUrl, setLocalImageUrl] = useState('');
  const [tiles, setTiles] = useState([]);
  const [rows, setRows] = useState(0);
  const [cols, setCols] = useState(0);
  const [brushColor, setBrushColor] = useState('#ff6b6b');
  const [brushAlpha, setBrushAlpha] = useState(1);
  const [recentColors, setRecentColors] = useState([]);
  const [isPainting, setIsPainting] = useState(false);
  const [eraseMode, setEraseMode] = useState(false);
  const [scale, setScale] = useState(1.0);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [cellSize, setCellSize] = useState({ width: 50, height: 50 });
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
  const imageRef = useRef(null);
  const canvasRef = useRef(null);

  // Directory path to look for images
  const dirPath = useMemo(() => {
    if (!filePath || !filePath.includes('/')) return '';
    const parts = filePath.split('/');
    parts.pop();
    return parts.join('/');
  }, [filePath]);

  useEffect(() => {
    try {
      const data = JSON.parse(content || '{}');
      const tiles = sanitizeTiles(data.tiles || []);
      const mapImage = data.mapImage || data.image || '';
      const r = tiles.length || 10;
      const c = tiles[0]?.length || 10;
      const hydratedTiles = tiles.length ? tiles : makeBlankTiles(r, c);
      setParsed({ mapImage, tiles: hydratedTiles });
      setTiles(hydratedTiles);
      setRows(r);
      setCols(c);
      setSelectedImage(mapImage);
    } catch (err) {
      setParsed(SAFE_DEFAULT);
      setTiles([]);
      setRows(0);
      setCols(0);
    }
  }, [content]);

  useEffect(() => {
    const fetchImages = async () => {
      if (!dirPath) return;
      try {
        const resp = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(dirPath)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const files = (data.entries || []).filter((e) => {
          const n = (e.name || '').toLowerCase();
          return n.match(/\.(png|jpe?g|webp)$/);
        });
        setImageOptions(files.map((f) => f.name));
      } catch (err) {
        // ignore
      }
    };
    fetchImages();
  }, [dirPath]);

  useEffect(() => {
    const stopPaint = () => {
      setIsPainting(false);
      setEraseMode(false);
    };
    window.addEventListener('mouseup', stopPaint);
    return () => window.removeEventListener('mouseup', stopPaint);
  }, []);

  const backgroundUrl = localImageUrl
    ? localImageUrl
    : (selectedImage ? resolveImageUrl(dirPath, selectedImage) : '');

  // Measure canvas size
  useEffect(() => {
    if (!canvasRef.current) return;
    
    const updateCanvasSize = () => {
      const rect = canvasRef.current.getBoundingClientRect();
      setCanvasSize({ width: rect.width - 40, height: rect.height - 40 }); // Account for padding
    };
    
    updateCanvasSize();
    window.addEventListener('resize', updateCanvasSize);
    
    // Use ResizeObserver for better canvas size tracking
    const resizeObserver = new ResizeObserver(updateCanvasSize);
    if (canvasRef.current) {
      resizeObserver.observe(canvasRef.current);
    }
    
    return () => {
      window.removeEventListener('resize', updateCanvasSize);
      resizeObserver.disconnect();
    };
  }, []);

  // Load image and calculate dimensions
  useEffect(() => {
    if (!backgroundUrl) {
      setImageDimensions({ width: 0, height: 0 });
      return;
    }

    const img = new Image();
    img.onload = () => {
      setImageDimensions({ width: img.width, height: img.height });
      
      // Calculate base cell size from image dimensions and grid
      if (rows > 0 && cols > 0) {
        const baseCellWidth = img.width / cols;
        const baseCellHeight = img.height / rows;
        
        // Calculate initial scale to fit canvas (optional auto-fit on load)
        if (canvasSize.width > 0 && canvasSize.height > 0) {
          const naturalGridWidth = cols * baseCellWidth;
          const naturalGridHeight = rows * baseCellHeight;
          
          const scaleToFitWidth = (canvasSize.width * 0.9) / naturalGridWidth;
          const scaleToFitHeight = (canvasSize.height * 0.9) / naturalGridHeight;
          const autoScale = Math.min(scaleToFitWidth, scaleToFitHeight, 1);
          
          setScale(autoScale);
        }
        
        // Cell size is always base size, scale is applied separately
        setCellSize({ width: baseCellWidth, height: baseCellHeight });
      }
    };
    img.src = backgroundUrl;
  }, [backgroundUrl, rows, cols, canvasSize]);

  // Don't recalculate cell size when scale changes - scale is applied directly to dimensions
  // The base cell size remains constant based on image dimensions

  const addRecentColor = (color) => {
    if (!color) return;
    setRecentColors((prev) => {
      const existing = prev.filter((c) => c.toLowerCase() !== color.toLowerCase());
      return [color, ...existing].slice(0, 8);
    });
  };

  const handleResize = (nextRows, nextCols) => {
    const r = Math.max(1, Math.min(200, Number(nextRows) || 1));
    const c = Math.max(1, Math.min(200, Number(nextCols) || 1));
    setRows(r);
    setCols(c);
    setTiles((prev) => {
      const base = prev || [];
      const resized = makeBlankTiles(r, c);
      for (let i = 0; i < r; i++) {
        for (let j = 0; j < c; j++) {
          if (base[i] && base[i][j]) {
            resized[i][j] = base[i][j];
          }
        }
      }
      return resized;
    });
  };

  const paintCell = (rIdx, cIdx, erase) => {
    setTiles((prev) => {
      const base = prev || [];
      const next = base.map((row) => row.map((pix) => [...pix]));
      if (!next[rIdx]) next[rIdx] = [];
      if (!next[rIdx][cIdx]) next[rIdx][cIdx] = [0, 0, 0, 0];
      next[rIdx][cIdx] = erase ? [0, 0, 0, 0] : [
        parseInt(brushColor.slice(1, 3), 16),
        parseInt(brushColor.slice(3, 5), 16),
        parseInt(brushColor.slice(5, 7), 16),
        Math.round((brushAlpha || 0) * 255)
      ];
      return next;
    });
  };

  const handleStartPaint = (erase) => {
    setEraseMode(erase);
    setIsPainting(true);
  };

  const handleColorChange = (color) => {
    setBrushColor(color);
    addRecentColor(color);
  };

  const handleClearGrid = () => {
    if (window.confirm('Are you sure you want to clear the entire grid?')) {
      setTiles(makeBlankTiles(rows, cols));
    }
  };

  return (
    <div className="battlemap-viewer">
      <BattlemapToolbar
        selectedImage={selectedImage}
        imageOptions={imageOptions}
        rows={rows}
        cols={cols}
        scale={scale}
        imageDimensions={imageDimensions}
        cellSize={cellSize}
        onImageSelect={setSelectedImage}
        onImageTextChange={setSelectedImage}
        onFileUpload={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            const url = URL.createObjectURL(file);
            setLocalImageUrl(url);
          }
        }}
        onRowsChange={(val) => handleResize(val, cols)}
        onColsChange={(val) => handleResize(rows, val)}
        onScaleChange={setScale}
      />

      <PaintControls
        brushColor={brushColor}
        brushAlpha={brushAlpha}
        recentColors={recentColors}
        onColorChange={handleColorChange}
        onAlphaChange={setBrushAlpha}
        onClearGrid={handleClearGrid}
      />

      <BattlemapCanvas
        backgroundUrl={backgroundUrl}
        imageDimensions={imageDimensions}
        tiles={tiles}
        rows={rows}
        cols={cols}
        cellSize={cellSize}
        scale={scale}
        isPainting={isPainting}
        eraseMode={eraseMode}
        onStartPaint={handleStartPaint}
        onPaintCell={paintCell}
        onCanvasMount={(el) => {
          canvasRef.current = el;
        }}
      />
    </div>
  );
};

export default BattlemapViewer;
