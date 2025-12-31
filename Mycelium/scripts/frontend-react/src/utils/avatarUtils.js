export const AVATAR_SIZE = 100;

const clampByte = (value) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.min(255, Math.max(0, Math.round(n)));
};

export const normalizePixel = (pixel) => {
  if (Array.isArray(pixel)) {
    const [r = 0, g = 0, b = 0, a = 0] = pixel;
    return [clampByte(r), clampByte(g), clampByte(b), clampByte(a)];
  }
  if (pixel && typeof pixel === 'object') {
    const { r = 0, g = 0, b = 0, a = 0 } = pixel;
    return [clampByte(r), clampByte(g), clampByte(b), clampByte(a)];
  }
  return [0, 0, 0, 0];
};

export const createEmptyAvatar = () =>
  Array.from({ length: AVATAR_SIZE }, () =>
    Array.from({ length: AVATAR_SIZE }, () => [0, 0, 0, 0])
  );

export const normalizeAvatarMatrix = (matrix = []) => {
  const safeMatrix = Array.isArray(matrix) ? matrix : [];
  return Array.from({ length: AVATAR_SIZE }, (_, rowIdx) => {
    const row = Array.isArray(safeMatrix[rowIdx]) ? safeMatrix[rowIdx] : [];
    return Array.from(
      { length: AVATAR_SIZE },
      (_, colIdx) => normalizePixel(row[colIdx])
    );
  });
};

export const avatarHasPixels = (matrix = []) => {
  try {
    return normalizeAvatarMatrix(matrix).some((row) =>
      row.some((pixel) => (pixel?.[3] || 0) > 0)
    );
  } catch (err) {
    return false;
  }
};

export const rgbaArrayFromHex = (hex = '#000000', alpha = 1) => {
  const safeHex = (hex || '#000000').replace('#', '');
  const padded = safeHex.length === 3
    ? safeHex.split('').map((c) => c + c).join('')
    : safeHex.padEnd(6, '0').slice(0, 6);
  const r = parseInt(padded.slice(0, 2), 16) || 0;
  const g = parseInt(padded.slice(2, 4), 16) || 0;
  const b = parseInt(padded.slice(4, 6), 16) || 0;
  const a = clampByte(alpha * 255);
  return [r, g, b, a];
};

export const pixelToCssRgba = (pixel) => {
  const [r, g, b, a] = normalizePixel(pixel);
  const alpha = (a || 0) / 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};
