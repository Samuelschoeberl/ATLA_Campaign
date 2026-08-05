/**
 * Hex grid utility functions for coordinate conversion and calculations
 * Supports flat-top hexagons with odd-r offset coordinates
 */

/**
 * Convert odd-r offset coordinates to cube coordinates
 */
export const offsetToCube = (row, col) => {
  const q = col - (row - (row & 1)) / 2;
  const r = row;
  const s = -q - r;
  return { q, r, s };
};

/**
 * Convert cube coordinates to odd-r offset coordinates
 */
export const cubeToOffset = (q, r, s) => {
  const col = q + (r - (r & 1)) / 2;
  const row = r;
  return { row, col };
};

/**
 * Calculate distance between two hexes using cube coordinates
 */
export const calculateHexDistance = (row1, col1, row2, col2) => {
  // Convert odd-r offset coordinates to cube coordinates
  const q1 = col1 - Math.floor((row1 + (row1 % 2)) / 2);
  const r1 = row1;
  const s1 = -q1 - r1;
  
  const q2 = col2 - Math.floor((row2 + (row2 % 2)) / 2);
  const r2 = row2;
  const s2 = -q2 - r2;
  
  // Manhattan distance in cube coordinates
  return (Math.abs(q1 - q2) + Math.abs(r1 - r2) + Math.abs(s1 - s2)) / 2;
};

/**
 * Get the 6 neighbors of a hex in odd-r offset coordinates (flat-top orientation)
 */
export const getHexNeighbors = (row, col, gridSize) => {
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

/**
 * Get neighbor in a specific direction
 */
export const getNeighborInDirection = (row, col, direction, gridSize) => {
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

/**
 * Get the direction from one hex to an adjacent neighbor
 */
export const getDirectionToNeighbor = (fromRow, fromCol, toRow, toCol) => {
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

/**
 * Calculate hex coordinates for rendering
 */
export const getHexCoordinates = (row, col, hexSize) => {
  const hexWidth = hexSize * Math.sqrt(3);
  const vertSpacing = hexSize * 1.5;
  const horizSpacing = hexWidth;
  const tessellationOffset = (row % 2 === 1) ? (hexWidth / 2) : 0;
  
  const cx = col * horizSpacing + (hexWidth / 2) + tessellationOffset;
  const cy = row * vertSpacing + hexSize;
  
  return { cx, cy };
};

/**
 * Get hex vertex points for SVG polygon
 */
export const getHexVertices = (cx, cy, hexSize) => {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i + Math.PI / 2;
    const x = cx + hexSize * Math.cos(angle);
    const y = cy + hexSize * Math.sin(angle);
    points.push(`${x},${y}`);
  }
  return points.join(' ');
};

/**
 * Generate sphere pattern dynamically based on diameter
 * Creates concentric rings around the center hex using proper odd-r offset conversion
 * Diameter 1 = only center tile, Diameter 2 = radius 1, Diameter 3 = radius 2, etc.
 */
export const generateSpherePattern = (centerRow, centerCol, diameter, gridSize) => {
  const hexes = [];
  const diameterNum = parseInt(diameter);
  
  // Convert diameter to radius
  const radius = Math.ceil((diameterNum - 1) / 2);
  
  console.log(`🎯 generateSpherePattern: center=(${centerRow},${centerCol}) [${centerRow % 2 === 0 ? 'EVEN' : 'ODD'} row], diameter=${diameter}, radius=${radius}`);
  
  // Use BFS to find all hexes within radius
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
      const neighbors = getHexNeighbors(row, col, gridSize);
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

/**
 * Generate cone pattern based on selecting 2 adjacent hexes as first row
 * Fills ALL hexes between the two boundary lines to create a solid cone
 */
export const generateConePattern = (originRow, originCol, dir1Row, dir1Col, dir2Row, dir2Col, range, gridSize) => {
  const hexSet = new Set();
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
  
  // Add the two initial direction hexes
  addHex(dir1Row, dir1Col);
  addHex(dir2Row, dir2Col);
  
  // Build cone by extending both boundaries and filling between them at each layer
  for (let layer = 1; layer <= rangeNum; layer++) {
    let currentBoundary1 = { row: originRow, col: originCol };
    let currentBoundary2 = { row: originRow, col: originCol };
    
    // Move to the current layer along each direction
    for (let step = 0; step < layer; step++) {
      const next1 = getNeighborInDirection(currentBoundary1.row, currentBoundary1.col, direction1, gridSize);
      const next2 = getNeighborInDirection(currentBoundary2.row, currentBoundary2.col, direction2, gridSize);
      
      if (next1) currentBoundary1 = next1;
      if (next2) currentBoundary2 = next2;
    }
    
    // Flood fill between boundary points at this distance
    const targetDist = layer;
    
    for (let row = 0; row < gridSize.rows; row++) {
      for (let col = 0; col < gridSize.cols; col++) {
        const dist = calculateHexDistance(originRow, originCol, row, col);
        
        if (dist === targetDist) {
          const dist1 = calculateHexDistance(row, col, currentBoundary1.row, currentBoundary1.col);
          const dist2 = calculateHexDistance(row, col, currentBoundary2.row, currentBoundary2.col);
          
          const maxBoundaryDist = calculateHexDistance(currentBoundary1.row, currentBoundary1.col, 
                                                       currentBoundary2.row, currentBoundary2.col) - 1;
          
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

/**
 * Get all cells occupied by a token based on its position and size
 */
export const getTokenCells = (row, col, width, height) => {
  const cells = [];
  for (let r = row; r < row + height; r++) {
    for (let c = col; c < col + width; c++) {
      cells.push({ row: r, col: c });
    }
  }
  return cells;
};

/**
 * Convert hex grid to graph data (sparse representation)
 * Only stores filled/painted hexes to save space
 */
export const gridToGraphData = (hexGrid, gridSize) => {
  const nodes = {};
  const directions = ['NW', 'NE', 'E', 'SE', 'SW', 'W'];
  
  const getNeighborsInline = (row, col) => {
    const isOddRow = row % 2 === 1;
    const offsets = isOddRow
      ? [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [0, -1]]
      : [[-1, -1], [-1, 0], [0, 1], [1, 0], [1, -1], [0, -1]];
    
    return offsets.map(([dr, dc]) => ({
      row: row + dr,
      col: col + dc
    }));
  };
  
  for (let row = 0; row < gridSize.rows; row++) {
    for (let col = 0; col < gridSize.cols; col++) {
      const cell = hexGrid[row]?.[col];
      
      // Skip empty/unfilled hexes to save space
      if (!cell || !cell.filled) continue;
      
      const nodeId = `${row},${col}`;
      const neighbors = getNeighborsInline(row, col);
      const neighborMap = {};
      
      neighbors.forEach((neighbor, idx) => {
        const { row: nRow, col: nCol } = neighbor;
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

/**
 * Initialize hex grid with empty cells
 */
export const initializeHexGrid = (rows, cols) => {
  return Array(rows).fill(null).map(() =>
    Array(cols).fill(null).map(() => ({
      filled: false,
      color: '#3498db',
      effect: 'none',
      animationOffset: Math.random() * 10,
      paintedAt: null,
      auraTokenId: null
    }))
  );
};

/**
 * Convert graph data back to 2D array format
 */
export const graphDataToGrid = (graphData, gridSize) => {
  const grid = initializeHexGrid(gridSize.rows, gridSize.cols);
  
  Object.values(graphData).forEach(node => {
    const { row, col, data } = node;
    if (grid[row] && grid[row][col]) {
      grid[row][col] = { ...data };
    }
  });
  
  return grid;
};

/**
 * Calculate grid size that covers image dimensions plus buffer
 */
export const calculateGridSizeForImage = (imageWidth, imageHeight, hexSize) => {
  const hexWidth = hexSize * Math.sqrt(3);
  const vertSpacing = hexSize * 1.5;
  
  // Calculate base grid size needed to cover image
  const baseRows = Math.ceil(imageHeight / vertSpacing) + 2;
  const baseCols = Math.ceil(imageWidth / hexWidth) + 2;
  
  // Add 10-hex buffer on each side
  const rows = baseRows + 20;
  const cols = baseCols + 20;
  
  return { rows, cols };
};

/**
 * Helper functions for HP bars and condition rings
 */
export const generateHexPathPoints = (centerX, centerY, radius) => {
  const points = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i + Math.PI / 2;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    points.push({ x, y });
  }
  return points;
};

export const generateArcPath = (centerX, centerY, radius, percentage) => {
  const points = generateHexPathPoints(centerX, centerY, radius);
  
  if (percentage >= 100) {
    const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z';
    return pathData;
  }
  
  if (percentage <= 0) {
    return '';
  }
  
  const totalEdges = 6;
  const edgesToFill = (percentage / 100) * totalEdges;
  const fullEdges = Math.floor(edgesToFill);
  const partialEdge = edgesToFill - fullEdges;
  
  let pathData = `M ${centerX} ${centerY}`;
  
  pathData += ` L ${points[0].x} ${points[0].y}`;
  
  for (let i = 0; i < fullEdges; i++) {
    const nextPoint = points[(i + 1) % points.length];
    pathData += ` L ${nextPoint.x} ${nextPoint.y}`;
  }
  
  if (partialEdge > 0 && fullEdges < totalEdges) {
    const startPoint = points[fullEdges];
    const endPoint = points[(fullEdges + 1) % points.length];
    const partialX = startPoint.x + (endPoint.x - startPoint.x) * partialEdge;
    const partialY = startPoint.y + (endPoint.y - startPoint.y) * partialEdge;
    pathData += ` L ${partialX} ${partialY}`;
  }
  
  pathData += ' Z';
  return pathData;
};

export const getHealthBarColor = (percentage) => {
  if (percentage > 50) return '#4caf50';
  if (percentage > 25) return '#ff9800';
  return '#f44336';
};
