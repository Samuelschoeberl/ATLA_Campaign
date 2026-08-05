/**
 * Effect presets with enhanced animation patterns and visual styles
 */
export const EFFECT_PRESETS = {
  fire: {
    name: '🔥 Fire',
    colors: ['#ff6b1a', '#ffaa00', '#ff4444', '#ff8800', '#ff3300'],
    animation: 'flicker',
    glowColor: 'rgba(255, 100, 0, 0.6)',
    pattern: 'chaos',
    emoji: '🔥',
    gradient: 'radial-gradient(circle, #ffaa00 0%, #ff6b1a 50%, #ff3300 100%)'
  },
  water: {
    name: '💧 Water',
    colors: ['#4da6ff', '#66b3ff', '#3399ff', '#80c1ff', '#3d8fd9'],
    animation: 'flow',
    glowColor: 'rgba(77, 166, 255, 0.5)',
    pattern: 'wave',
    emoji: '💧',
    gradient: 'linear-gradient(180deg, #80c1ff 0%, #4da6ff 50%, #3399ff 100%)'
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
  air: {
    name: '🌪️ Air',
    colors: ['#e6f3ff', '#d0e8ff', '#ffd9a8', '#ffe5c2', '#c0dcf0'],
    animation: 'swirl',
    glowColor: 'rgba(230, 243, 255, 0.4)',
    pattern: 'vortex',
    emoji: '🌪️',
    gradient: 'conic-gradient(from 45deg, #e6f3ff, #ffd9a8, #d0e8ff, #ffe5c2, #e6f3ff)'
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
  spirit: {
    name: '🌀 Spirit',
    colors: ['#b19cd9', '#dda0dd', '#9370db', '#c9a0dc', '#a484c7'],
    animation: 'pulse',
    glowColor: 'rgba(177, 156, 217, 0.5)',
    pattern: 'ethereal',
    emoji: '🌀',
    gradient: 'conic-gradient(from 0deg, #dda0dd, #b19cd9, #9370db, #c9a0dc, #dda0dd)'
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
  }
};

export const STANDARD_COLORS = [
  '#ff6b6b', '#ffb347', '#ffd166', '#9b59b6', '#6c5ce7', '#3498db',
  '#5f81fd', '#2ecc71', '#1abc9c', '#16a085', '#e67e22', '#e74c3c'
];

export const CONDITION_COLORS = {
  'Bleeding out': '#8b0000',
  'Blinded': '#2c3e50',
  'Dazed': '#f39c12',
  'Immobilised': '#7f8c8d',
  'Paralysed': '#9b59b6',
  'Prone': '#95a5a6',
  'Slowed': '#3498db',
  'Empowered': '#f1c40f',
  'Armor Surge': '#16a085',
  'Barrier Surge': '#8e44ad',
  'Harmonic Flow': '#e91e63'
};
