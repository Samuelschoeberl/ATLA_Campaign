import DOMPurify from "dompurify";
import { marked } from "marked";

// Configure marked for Obsidian-like markdown behaviour
try {
  marked.setOptions({
    gfm: true,
    breaks: true,
    headerIds: false,
    mangle: false,
    smartLists: true,
    smartypants: false,
  });
} catch (e) {
  console.warn("marked.setOptions failed", e);
}

// Escape HTML special characters
export function escapeHtml(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Hash text using SHA-256
export async function hashText(s) {
  if (!s) return "";
  try {
    const enc = new TextEncoder();
    const data = enc.encode(s);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => ("00" + b.toString(16)).slice(-2)).join("");
  } catch (e) {
    // Fallback: simple JS hash
    let h = 0;
    for (let i = 0; i < s.length; i++) {
      h = (h * 31 + s.charCodeAt(i)) >>> 0;
    }
    return ("00000000" + (h >>> 0).toString(16)).slice(-8) + "00000000";
  }
}

// Render markdown to HTML
export function renderMarkdown(src) {
  if (!src) return "";
  try {
    // First, convert image embeds ![[image]] and wikilinks [[text]] before marked processes it
    let processed = convertImageEmbeds(src);
    processed = convertWikilinks(processed);

    let html = marked(processed);
    // Make dice expressions clickable (e.g., "1d20+6", "2d6", "1d20 + 3")
    html = makeDiceExpressionsClickable(html);
    return DOMPurify.sanitize(html, {
      ADD_ATTR: [
        "data-dice-expression",
        "data-wikilink",
        "data-image-src",
        "onclick",
      ],
      ADD_TAGS: ["span", "img"],
    });
  } catch (e) {
    console.warn("markdown rendering failed", e);
    return escapeHtml(src);
  }
}

// Convert ![[image]] embeds to actual images
export function convertImageEmbeds(text) {
  // Match ![[image.ext]] or ![[image.ext|alt text]]
  const imageEmbedPattern = /!\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]/g;

  return text.replace(imageEmbedPattern, (match, imageName, altText) => {
    const trimmedName = imageName.trim();
    const alt = altText ? altText.trim() : trimmedName;

    // Check if it looks like an image file
    const imageExtensions = [
      ".jpg",
      ".jpeg",
      ".png",
      ".gif",
      ".webp",
      ".svg",
      ".bmp",
    ];
    const isImage = imageExtensions.some((ext) =>
      trimmedName.toLowerCase().endsWith(ext)
    );

    if (isImage) {
      // Create an img tag with a special data attribute for later resolution
      return `<img src="#" data-image-src="${escapeHtml(
        trimmedName
      )}" alt="${escapeHtml(
        alt
      )}" style="max-width: 100%; height: auto; border-radius: 4px; margin: 8px 0;" />`;
    }

    // If not an image, treat as a regular wikilink (remove the !)
    return `[[${trimmedName}${altText ? "|" + altText : ""}]]`;
  });
}

// Convert [[wikilinks]] to clickable spans
export function convertWikilinks(text) {
  // Match [[link]] or [[link|display text]]
  const wikilinkPattern = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g;

  return text.replace(wikilinkPattern, (match, target, displayText) => {
    const display = displayText || target;
    // Create a span that will be made clickable
    return `<span class="wikilink" data-wikilink="${escapeHtml(
      target.trim()
    )}" style="cursor: pointer; color: #6366f1; text-decoration: underline; font-weight: 500;">${escapeHtml(
      display.trim()
    )}</span>`;
  });
}

// Convert dice expressions in HTML to clickable elements
export function makeDiceExpressionsClickable(html) {
  // Match dice expressions with multiple modifiers: 1d20, 2d6+3, 1d20 + 6, 1d20 + 2 + 6, etc.
  // Pattern: \d+d\d+ followed by any number of [+-] \d+ sequences
  const dicePattern = /(\d+d\d+(?:\s*[+-]\s*\d+)*)/gi;

  return html.replace(dicePattern, (match) => {
    // Normalize the expression (remove spaces around operators)
    const normalized = match.replace(/\s+/g, "");
    return `<span class="dice-expression" data-dice-expression="${normalized}" style="cursor: pointer; color: #4a3ab5; text-decoration: underline; font-weight: 500;">${match}</span>`;
  });
}

// Generate a consistent, pastel HSL color for a repo node
export function nodeColorForKey(key) {
  key = key || "";
  let syncHash = 0;
  for (let i = 0; i < key.length; i++) {
    syncHash = (syncHash * 31 + key.charCodeAt(i)) >>> 0;
  }
  const h = syncHash % 360;
  const s = 38 + ((syncHash >> 8) % 10); // 38-47%
  const l = 90 - ((syncHash >> 16) % 6); // 90-85%
  return `hsl(${h} ${s}% ${l}%)`;
}

// Adjust HSL lightness
export function adjustHslLightness(hslStr, delta) {
  if (!hslStr || typeof hslStr !== "string") return hslStr;
  const m = hslStr.match(
    /hsl\s*\(\s*([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s*\)/i
  );
  if (!m) return hslStr;
  const h = m[1];
  const s = m[2];
  let l = parseFloat(m[3]);
  l = Math.max(0, Math.min(100, l + delta));
  return `hsl(${h} ${s}% ${l}%)`;
}

// Style table cells with adjusted colors
export function stylePreviewTables(previewEl, nodeBg) {
  try {
    if (!previewEl) return;
    const cellBg = adjustHslLightness(nodeBg, -6);
    const headerBg = adjustHslLightness(nodeBg, 6);
    const tables = previewEl.querySelectorAll("table");
    tables.forEach((tbl) => {
      if (tbl.style) tbl.style.background = "transparent";
      const ths = tbl.querySelectorAll("th");
      ths.forEach((th) => {
        th.style.background = headerBg;
      });
      const tds = tbl.querySelectorAll("td");
      tds.forEach((td) => {
        td.style.background = cellBg;
      });
    });
  } catch (e) {
    console.warn("stylePreviewTables failed", e);
  }
}

// Encode path segments for URL
export function encodeSegments(path) {
  return path
    .split("/")
    .map((s) => encodeURIComponent(s))
    .join("/");
}

// Ensure Player Root prefix
export function ensurePlayerRoot(path) {
  if (!path) return "Player Root";
  if (/^Player Root\//i.test(path)) return path;
  return `Player Root/${path}`;
}

// Roll dice expression (e.g., "2d6+3", "1d20+2+6")
export function rollDiceExpression(expression) {
  // Parse dice expression with potentially multiple modifiers
  // Examples: 1d20, 2d6+3, 1d20+2+6, 3d6-1+2
  const basePattern = /^(\d+)d(\d+)/i;
  const match = expression.trim().match(basePattern);

  if (!match) {
    return {
      total: 0,
      numDice: 0,
      sides: 0,
      rolls: [],
      modifier: 0,
      error: "Invalid dice expression",
    };
  }

  const numDice = parseInt(match[1], 10);
  const sides = parseInt(match[2], 10);

  // Extract all modifiers (everything after the dice part)
  const remainingExpression = expression.trim().substring(match[0].length);

  // Parse all modifiers: +3, -2, +6, etc.
  let totalModifier = 0;
  const modifierMatches = remainingExpression.matchAll(/([+-]\d+)/g);
  for (const modMatch of modifierMatches) {
    totalModifier += parseInt(modMatch[1], 10);
  }

  const rolls = [];
  let sum = 0;
  for (let i = 0; i < numDice; i++) {
    const roll = Math.floor(Math.random() * sides) + 1;
    rolls.push(roll);
    sum += roll;
  }

  return {
    total: sum + totalModifier,
    numDice,
    sides,
    rolls,
    modifier: totalModifier,
  };
}
