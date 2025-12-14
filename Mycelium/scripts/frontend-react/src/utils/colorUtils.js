function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

export function hsvToHex(h, s, v) {
  const hh = h % 1.0;
  const i = Math.floor(hh * 6);
  const f = hh * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  
  let r, g, b;
  switch (i % 6) {
    case 0: r = v; g = t; b = p; break;
    case 1: r = q; g = v; b = p; break;
    case 2: r = p; g = v; b = t; break;
    case 3: r = p; g = q; b = v; break;
    case 4: r = t; g = p; b = v; break;
    case 5: r = v; g = p; b = q; break;
    default: r = 0; g = 0; b = 0;
  }
  
  const toHex = (x) => {
    const hex = Math.round(Math.max(0, Math.min(1, x)) * 255).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };
  
  return '#' + toHex(r) + toHex(g) + toHex(b);
}

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

function getElementFromPath(path) {
  const lowerPath = path.toLowerCase();
  
  if (lowerPath.includes('bending rules')) {
    const parts = path.split('/');
    const bendingIndex = parts.findIndex(p => p.toLowerCase().includes('bending rules'));
    if (bendingIndex >= 0 && bendingIndex < parts.length - 1) {
      const nextPart = parts[bendingIndex + 1].toLowerCase();
      if (nextPart.includes('fire')) return 'fire';
      if (nextPart.includes('water')) return 'water';
      if (nextPart.includes('air')) return 'air';
      if (nextPart.includes('spirit')) return 'spirit';
      if (nextPart.includes('earth')) return 'earth';
    }
  }
  
  if (lowerPath.includes('fire') || lowerPath.includes('firebending')) {
    return 'fire';
  }
  if (lowerPath.includes('water') || lowerPath.includes('waterbending')) {
    return 'water';
  }
  if (lowerPath.includes('air') || lowerPath.includes('airbending')) {
    return 'air';
  }
  if (lowerPath.includes('spirit') || lowerPath.includes('spiritbending')) {
    return 'spirit';
  }
  if (lowerPath.includes('earth') || lowerPath.includes('earthbending')) {
    return 'earth';
  }
  
  return null;
}

export function getColorForPath(path, isDirectory = false) {
  const element = getElementFromPath(path);
  if (element) {
    return ELEMENT_COLORS[element];
  }
  
  const parts = path.split('/').filter(Boolean);
  if (parts.length === 0) {
    return '#dddddd';
  }
  
  let hue = 0;
  
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    const partHash = simpleHash(part);
    hue = (hue + (partHash / 1000000.0)) % 1.0;
  }
  
  const sat = isDirectory ? 0.30 : 0.35;
  const val = 0.98;
  
  return hsvToHex(hue, sat, val);
}

export function getLighterColor(hexColor) {
  if (!hexColor || hexColor === '#dddddd') {
    return '#3a3d41';
  }
  
  const hex = hexColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16) / 255;
  const g = parseInt(hex.substring(2, 4), 16) / 255;
  const b = parseInt(hex.substring(4, 6), 16) / 255;
  
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  
  let h = 0;
  if (delta !== 0) {
    if (max === r) {
      h = ((g - b) / delta) % 6;
    } else if (max === g) {
      h = (b - r) / delta + 2;
    } else {
      h = (r - g) / delta + 4;
    }
    h /= 6;
    if (h < 0) h += 1;
  }
  
  const s = max === 0 ? 0 : delta / max;
  const v = max;
  
  const newS = Math.min(1, s * 1.2);
  const newV = Math.min(1, v * 1.1);
  
  return hsvToHex(h, newS, newV);
}

export function hexToRgba(hex, alpha = 0.3) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
}
