/**
 * Hex patterns for AOE shapes
 */
export const AREA_PATTERNS = {
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
