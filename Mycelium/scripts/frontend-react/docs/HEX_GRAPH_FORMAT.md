# Hex Grid Graph Format

## Overview

The **graph-based format** is a more efficient way to store hexagonal battlemap data compared to the traditional 2D array format.

## Format Comparison

### Legacy Array Format (v1.0)
```json
{
  "format": "array",
  "version": "1.0",
  "gridSize": { "rows": 45, "cols": 20 },
  "hexGrid": [
    [
      { "filled": false, "color": "#3498db", "effect": "none", ... },
      { "filled": false, "color": "#3498db", "effect": "none", ... },
      ...
    ],
    ...
  ],
  "tokens": [...],
  "backgroundImage": "...",
  "hexSize": 40,
  "lastModified": 1234567890
}
```

**Problems with Array Format:**
- Stores **every hex** even if empty (45 × 20 = 900 hexes)
- Large file size (often 50-100+ KB for empty grids)
- Redundant data for unfilled hexes
- Slow to parse for large grids

### Graph Format (v2.0)
```json
{
  "format": "graph",
  "version": "2.0",
  "gridSize": { "rows": 45, "cols": 20 },
  "hexGraph": {
    "0,0": {
      "id": "0,0",
      "row": 0,
      "col": 0,
      "neighbors": {
        "NE": "0,1",
        "E": "1,1",
        "SE": "1,0",
        "SW": null,
        "W": null,
        "NW": null
      },
      "data": {
        "filled": true,
        "color": "#ff6b1a",
        "effect": "fire",
        "animationOffset": 3.2,
        "paintedAt": 1234567890
      }
    },
    "5,3": {
      "id": "5,3",
      "row": 5,
      "col": 3,
      "neighbors": {
        "NE": "4,4",
        "E": "5,4",
        "SE": "6,4",
        "SW": "6,3",
        "W": "5,2",
        "NW": "4,3"
      },
      "data": {
        "filled": true,
        "color": "#88ccff",
        "effect": "ice",
        "animationOffset": 7.8,
        "paintedAt": 1234567891
      }
    }
  },
  "tokens": [...],
  "backgroundImage": "...",
  "hexSize": 40,
  "lastModified": 1234567890
}
```

**Benefits of Graph Format:**
- Only stores **filled/painted hexes** (sparse representation)
- Explicit neighbor connections enable graph algorithms
- Typical space savings: **60-90%** for grids with effects
- Empty grids are tiny (just metadata)
- Enables advanced pathfinding and area-of-effect calculations

## Graph Structure

Each hex is a **node** with:

### Node Properties
- `id`: Unique identifier (`"row,col"`)
- `row`: Row position in grid
- `col`: Column position in grid
- `neighbors`: Object mapping directions to neighbor IDs
- `data`: Hex cell data (filled, color, effect, etc.)

### Neighbor Directions (Flat-Top Hex, Odd-R Offset)
```
      NW  NE
       \ /
    W - • - E
       / \
      SW  SE
```

- **NE** (Northeast): Upper-right
- **E** (East): Right
- **SE** (Southeast): Lower-right
- **SW** (Southwest): Lower-left
- **W** (West): Left
- **NW** (Northwest): Upper-left

### Neighbor Offsets by Row Parity

**Even Rows (0, 2, 4, ...):**
```
Direction | Offset
----------|--------
NE        | [-1, -1]
E         | [-1,  0]
SE        | [ 0,  1]
SW        | [ 1,  0]
W         | [ 1, -1]
NW        | [ 0, -1]
```

**Odd Rows (1, 3, 5, ...):**
```
Direction | Offset
----------|--------
NE        | [-1,  0]
E         | [-1,  1]
SE        | [ 0,  1]
SW        | [ 1,  1]
W         | [ 1,  0]
NW        | [ 0, -1]
```

## Example: Small 3×3 Grid

### Visual Representation
```
   0   1   2
 +---+---+---+
0|   | 🔥|   |  (Fire at 0,1)
 +---+---+---+
1| ❄️|   | ⚡|  (Ice at 1,0, Lightning at 1,2)
 +---+---+---+
2|   |   |   |
 +---+---+---+
```

### Graph Format (Only 3 nodes!)
```json
{
  "format": "graph",
  "version": "2.0",
  "gridSize": { "rows": 3, "cols": 3 },
  "hexGraph": {
    "0,1": {
      "id": "0,1",
      "row": 0,
      "col": 1,
      "neighbors": {
        "NE": null,
        "E": null,
        "SE": "1,1",
        "SW": "1,0",
        "W": "0,0",
        "NW": null
      },
      "data": {
        "filled": true,
        "color": "#ff6b1a",
        "effect": "fire",
        "animationOffset": 2.1,
        "paintedAt": 1234567890
      }
    },
    "1,0": {
      "id": "1,0",
      "row": 1,
      "col": 1,
      "neighbors": {
        "NE": "0,0",
        "E": "0,1",
        "SE": "1,1",
        "SW": "2,1",
        "W": "2,0",
        "NW": "1,-1"
      },
      "data": {
        "filled": true,
        "color": "#88ccff",
        "effect": "ice",
        "animationOffset": 5.4,
        "paintedAt": 1234567891
      }
    },
    "1,2": {
      "id": "1,2",
      "row": 1,
      "col": 2,
      "neighbors": {
        "NE": "0,2",
        "E": "0,3",
        "SE": "1,3",
        "SW": "2,3",
        "W": "2,2",
        "NW": "1,1"
      },
      "data": {
        "filled": true,
        "color": "#ffeb3b",
        "effect": "lightning",
        "animationOffset": 8.7,
        "paintedAt": 1234567892
      }
    }
  },
  "tokens": [],
  "backgroundImage": null,
  "hexSize": 40,
  "lastModified": 1234567890
}
```

### Array Format (All 9 cells!)
```json
{
  "format": "array",
  "version": "1.0",
  "gridSize": { "rows": 3, "cols": 3 },
  "hexGrid": [
    [
      { "filled": false, "color": "#3498db", "effect": "none", ... },
      { "filled": true, "color": "#ff6b1a", "effect": "fire", ... },
      { "filled": false, "color": "#3498db", "effect": "none", ... }
    ],
    [
      { "filled": true, "color": "#88ccff", "effect": "ice", ... },
      { "filled": false, "color": "#3498db", "effect": "none", ... },
      { "filled": true, "color": "#ffeb3b", "effect": "lightning", ... }
    ],
    [
      { "filled": false, "color": "#3498db", "effect": "none", ... },
      { "filled": false, "color": "#3498db", "effect": "none", ... },
      { "filled": false, "color": "#3498db", "effect": "none", ... }
    ]
  ],
  "tokens": [],
  "backgroundImage": null,
  "hexSize": 40,
  "lastModified": 1234567890
}
```

**Size Comparison:** Graph format is ~60% smaller even with just 3 filled hexes!

## Use Cases

### Graph Format Excels At:
- **Pathfinding**: Use neighbor connections for A* or Dijkstra's algorithm
- **Area Effects**: Flood fill for spheres/cones using graph traversal
- **Sparse Grids**: Large battlemap with few painted hexes
- **Network Analysis**: Calculate connectivity, find clusters
- **Memory Efficiency**: Less data to sync across clients

### When to Use Array Format:
- **Dense Grids**: Most hexes are filled (>80%)
- **Simplicity**: Quick prototyping without graph logic
- **Legacy Systems**: Compatibility with old code
- **Sequential Access**: Iterating all rows/cols frequently

## Implementation

The BattlemapViewer component now supports both formats:

- **Loading**: Automatically detects format and converts graph → array for display
- **Saving**: Saves in graph format by default (60-90% smaller files)
- **Compatibility**: Can read old array format files
- **Migration**: Use "Compare Formats" button to see space savings

## Future Enhancements

With graph format, we can now implement:
- **Pathfinding**: Show shortest path between hexes
- **Flood Fill**: Smart area selection tools
- **Distance Fields**: Quickly calculate range to all hexes
- **Connectivity Analysis**: Find isolated regions
- **Graph Algorithms**: PageRank for importance, clustering, etc.
