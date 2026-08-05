import React, { useState, useEffect, useRef } from 'react';
import './Quicklinks.css';
import { API_BASE_URL } from '../config/api';
import { hexToRgba } from '../utils/colorUtils';
import { parseCharacterSheet } from '../utils/characterSheetParser';
import CharacterToken from './CharacterToken';

// ── Token overlay geometry (size=90 matches CharacterToken default) ───────────
const TOK_SIZE  = 90;
const TOK_CX    = TOK_SIZE / 2; // 45
const TOK_CY    = TOK_SIZE / 2; // 45
const OUTER_R   = TOK_CX * 0.95; // 42.75 — CharacterToken HP ring outer radius
const BUBBLE_D  = OUTER_R + 13;  // 55.75 — distance from token centre to bubble centre

// HP bubble: top-center (same as battlemap)
const HP_POS = { x: TOK_CX, y: TOK_CY - BUBBLE_D };

// Defensive stats: left side, stacked vertically (same as battlemap TokenMarkers)
// markerStartX = cx - outerR - 15
const DEF_LEFT_X = TOK_CX - OUTER_R - 15; // ≈ -12.75 (overflow:visible shows it)
const DEF_SPACING = 20; // px between stacked bubbles

// Full defensive stat config — mirrors TokenMarkers.jsx
const DEF_STAT_CONFIG = [
  { key: 'evasion',       label: 'Evasion',        color: '#3498db' },
  { key: 'barrier',       label: 'Barrier',         color: '#9b59b6' },
  { key: 'generalArmor',  label: 'General Armor',   color: '#95a5a6' },
  { key: 'physicalArmor', label: 'Physical Armor',  color: '#7f8c8d' },
  { key: 'fireArmor',     label: 'Fire Armor',      color: '#e74c3c' },
  { key: 'iceArmor',      label: 'Ice Armor',       color: '#5dade2' },
  { key: 'spiritArmor',   label: 'Spirit Armor',    color: '#af7ac5' },
];

function hpFillColor(pct) {
  if (pct > 66) return '#2ecc71';
  if (pct > 33) return '#f39c12';
  if (pct >  0) return '#e74c3c';
  return '#95a5a6';
}

// ── Component ─────────────────────────────────────────────────────────────────
const Quicklinks = ({ lightMode = false, onFileSelect }) => {
  const [content,        setContent]        = useState('');
  const [loading,        setLoading]        = useState(true);
  const [error,          setError]          = useState(null);
  const [fileColors,     setFileColors]     = useState({});
  const [customizations, setCustomizations] = useState({});
  const [avatarImages,   setAvatarImages]   = useState({});
  const [statOverview,   setStatOverview]   = useState({});
  const [charConditions, setCharConditions] = useState({});
  const [editPopup,      setEditPopup]      = useState(null); // { char, stat, label, color, value, inputValue, x, y }
  const [savingEdit,     setSavingEdit]     = useState(false);
  const editInputRef = useRef(null);

  useEffect(() => {
    loadQuicklinks();
    loadFileColors();
    loadCustomizations();
    loadStatOverview();
  }, []);

  // Close edit popup on Escape
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setEditPopup(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Auto-focus input when popup opens
  useEffect(() => {
    if (editPopup && editInputRef.current) editInputRef.current.focus();
  }, [editPopup?.char, editPopup?.stat]);

  // ── Data loading ────────────────────────────────────────────────────────────

  const extractCharacters = (raw) => {
    const chars = [];
    let inTable = false;
    for (let i = 0; i < raw.length; i++) {
      const line = raw[i].trim();
      if (!line) continue;
      if (line.startsWith('|') && !inTable && line.toLowerCase().includes('characters')) {
        inTable = true; i++; continue;
      }
      if (inTable && line.startsWith('|')) {
        const m = line.match(/\[\[([^\]]+)\]\]/);
        if (m) chars.push(m[1]);
      }
    }
    return chars;
  };

  const loadQuicklinks = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE_URL}/player_root/Quicklinks.md`);
      if (res.ok) {
        const data = await res.json();
        const rawContent = data.content || '';
        setContent(rawContent);
        setError(null);
        // Kick off condition loading as soon as we know the character list
        const chars = extractCharacters(rawContent.trim().split('\n'));
        loadConditions(chars);
      } else {
        setError('Failed to load Quicklinks');
      }
    } catch (err) {
      setError('Error loading Quicklinks: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadFileColors = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/file-colors`);
      if (res.ok) setFileColors((await res.json()).colors || {});
    } catch (err) { console.error('Error loading file colors:', err); }
  };

  const loadCustomizations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/characters/customizations`);
      if (!res.ok) return;
      const cusData = (await res.json()).customizations || {};
      setCustomizations(cusData);

      // Fetch all avatars in parallel
      const results = await Promise.allSettled(
        Object.entries(cusData)
          .filter(([, c]) => c?.avatarPng)
          .map(async ([name, c]) => {
            if (c.avatarPng.startsWith('data:image')) return [name, c.avatarPng];
            const imgRes = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(c.avatarPng)}`);
            if (!imgRes.ok) throw new Error(`HTTP ${imgRes.status}`);
            const blob = await imgRes.blob();
            const dataUrl = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onloadend = () => resolve(reader.result);
              reader.onerror = reject;
              reader.readAsDataURL(blob);
            });
            return [name, dataUrl];
          })
      );
      const images = {};
      for (const r of results) {
        if (r.status === 'fulfilled') images[r.value[0]] = r.value[1];
      }
      setAvatarImages(images);
    } catch (err) { console.error('Error loading customizations:', err); }
  };

  const loadStatOverview = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/stat_overview`);
      if (!res.ok) return;
      const pcs = (await res.json()).pcs || {};
      const parsed = {};
      for (const [name, charData] of Object.entries(pcs)) {
        const vit = charData.vitality  || [];
        const def = charData.defensive || [];
        const get = (arr, key) => {
          const item = arr.find(i => i.key?.toLowerCase() === key.toLowerCase());
          return item ? parseFloat(item.value) ?? null : null;
        };
        parsed[name] = {
          currentHp:     get(vit, 'current_hp'),
          maxHp:         get(vit, 'max_hp') || 100,
          evasion:       get(def, 'Evasion'),
          barrier:       get(def, 'Barrier'),
          generalArmor:  get(def, 'General Armor') ?? get(def, 'general_armor'),
          physicalArmor: get(def, 'Physical Armor'),
          fireArmor:     get(def, 'Fire Armor'),
          iceArmor:      get(def, 'Ice Armor'),
          spiritArmor:   get(def, 'Spirit Armor'),
        };
      }
      setStatOverview(parsed);
    } catch (err) { console.error('Error loading stat overview:', err); }
  };

  const loadConditions = async (characters) => {
    const results = await Promise.allSettled(
      characters.map(async (name) => {
        const namePaths = [
          `PCs/${name}/${name} Character Sheet.md`,
          `PCs/${name}/${name} character sheet.md`,
        ];
        for (const path of namePaths) {
          try {
            const encoded = path.split('/').map(encodeURIComponent).join('/');
            const res = await fetch(`${API_BASE_URL}/player_root/${encoded}`);
            if (res.ok) {
              const data = await res.json();
              const parsed = parseCharacterSheet(data.content || '');
              const active = (parsed.conditions || []).filter(c => c.active);
              return [name, active];
            }
          } catch { continue; }
        }
        return [name, []];
      })
    );
    const conds = {};
    for (const r of results) {
      if (r.status === 'fulfilled') conds[r.value[0]] = r.value[1];
    }
    setCharConditions(conds);
  };

  // ── Stat edit ───────────────────────────────────────────────────────────────

  const openEditPopup = (charName, stat, currentValue, event) => {
    const LABELS = Object.fromEntries([['currentHp', 'Current HP'], ...DEF_STAT_CONFIG.map(s => [s.key, s.label])]);
    const COLORS = Object.fromEntries([['currentHp', null], ...DEF_STAT_CONFIG.map(s => [s.key, s.color])]);
    const stats = statOverview[charName];
    const pct = stats ? (stats.currentHp / stats.maxHp) * 100 : 100;
    setEditPopup({
      char:       charName,
      stat,
      label:      LABELS[stat] || stat,
      color:      COLORS[stat] || hpFillColor(pct),
      value:      currentValue,
      inputValue: String(currentValue),
      x:          event.clientX,
      y:          event.clientY,
    });
  };

  const handleEditSave = async () => {
    if (!editPopup || savingEdit) return;
    const newValue = parseFloat(editPopup.inputValue);
    if (isNaN(newValue)) return;
    setSavingEdit(true);
    try {
      await saveStatToSheet(editPopup.char, editPopup.stat, newValue);
      setStatOverview(prev => ({
        ...prev,
        [editPopup.char]: { ...prev[editPopup.char], [editPopup.stat]: newValue },
      }));
      setEditPopup(null);
    } catch (err) {
      alert('Failed to save: ' + err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const saveStatToSheet = async (charName, stat, newValue) => {
    // Find the character sheet file
    const searchRes = await fetch(
      `${API_BASE_URL}/player_root/search?q=${encodeURIComponent(charName)}`
    );
    if (!searchRes.ok) throw new Error('Search failed');
    const results = (await searchRes.json()).results || [];
    const sheetFile = results.find(r => {
      const fn = r.path.toLowerCase();
      return fn.includes(charName.toLowerCase()) && fn.includes('character sheet');
    });
    if (!sheetFile) throw new Error(`No character sheet found for ${charName}`);

    const relativePath = sheetFile.path.replace(/^Player Root\//, '');
    const encoded = relativePath.split('/').map(encodeURIComponent).join('/');

    // Load current content
    const fetchRes = await fetch(`${API_BASE_URL}/player_root/${encoded}`);
    if (!fetchRes.ok) throw new Error('Failed to load character sheet');
    let content = (await fetchRes.json()).content || '';

    // Regex-replace the stat value in the markdown table
    const patterns = {
      currentHp:     /(\|\s*current_hp\s*\|\s*)\d+(\s*\|)/i,
      evasion:       /(\|\s*Evasion\s*\|\s*)\d+(\s*\|)/i,
      barrier:       /(\|\s*Barrier\s*\|\s*)\d+(\s*\|)/i,
      generalArmor:  /(\|\s*General Armor\s*\|\s*)\d+(\s*\|)/i,
      physicalArmor: /(\|\s*Physical Armor\s*\|\s*)\d+(\s*\|)/i,
      fireArmor:     /(\|\s*Fire Armor\s*\|\s*)\d+(\s*\|)/i,
      iceArmor:      /(\|\s*Ice Armor\s*\|\s*)\d+(\s*\|)/i,
      spiritArmor:   /(\|\s*Spirit Armor\s*\|\s*)\d+(\s*\|)/i,
    };
    const pattern = patterns[stat];
    if (!pattern) throw new Error(`Unknown stat: ${stat}`);
    content = content.replace(pattern, `$1${Math.round(newValue)}$2`);

    // Save
    const saveRes = await fetch(`${API_BASE_URL}/player_root/${encoded}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!saveRes.ok) throw new Error('Failed to save');
  };

  // ── Quicklinks parsing ──────────────────────────────────────────────────────

  const parseQuicklinks = () => {
    if (!content) return { topLinks: [], characters: [] };
    const lines = content.trim().split('\n');
    const topLinks = [], characters = [];
    let inTable = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const wiki = line.match(/\[\[([^\]]+)\]\]/);
      if (wiki && !inTable) { topLinks.push(wiki[1]); continue; }
      if (line.startsWith('|') && !inTable && line.toLowerCase().includes('characters')) {
        inTable = true; i++; continue;
      }
      if (inTable && line.startsWith('|')) {
        const m = line.match(/\[\[([^\]]+)\]\]/);
        if (m) characters.push(m[1]);
      }
    }
    return { topLinks, characters };
  };

  // ── Navigation ──────────────────────────────────────────────────────────────

  const handleLinkClick = async (linkName) => {
    if (linkName.toLowerCase().endsWith('battlemap.json') || linkName.toLowerCase().includes('battlemap')) {
      try {
        const paths = ['Maps/Battlemap.json', 'Maps/battlemap.json', linkName];
        for (const path of paths) {
          try {
            const r = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(path)}`);
            if (r.ok) { onFileSelect({ name: path.split('/').pop(), path, type: 'battlemap' }); return; }
          } catch { continue; }
        }
        const sr = await fetch(`${API_BASE_URL}/player_root/search?q=${encodeURIComponent('battlemap.json')}`);
        if (sr.ok) {
          const m = (await sr.json()).results?.find(r =>
            r.path.toLowerCase().includes('battlemap') && r.path.toLowerCase().endsWith('.json')
          );
          if (m) {
            const rel = m.path.replace(/^Player Root\//, '');
            onFileSelect({ name: rel.split('/').pop(), path: rel, type: 'battlemap' });
            return;
          }
        }
        alert(`Could not find battlemap file. Tried:\n${paths.join('\n')}`);
      } catch (err) { alert('Error loading battlemap: ' + err.message); }
      return;
    }

    try {
      const sr = await fetch(`${API_BASE_URL}/player_root/search?q=${encodeURIComponent(linkName)}`);
      if (!sr.ok) return;
      const results = (await sr.json()).results || [];
      const nl = linkName.toLowerCase(), ns = linkName.replace(/_/g, ' ').toLowerCase();
      let match = results.find(r => {
        const fn = r.path.split('/').pop().toLowerCase();
        return fn === nl || fn === `${nl}.md` || fn === ns || fn === `${ns}.md`;
      }) || results.find(r => {
        const fn = r.path.split('/').pop().toLowerCase();
        return fn === `${nl} character sheet.md` || fn === `${ns} character sheet.md`;
      });
      if (match) {
        const rel = match.path.replace(/^Player Root\//, '');
        onFileSelect({ name: rel.split('/').pop(), path: rel });
      } else {
        alert(`Could not find file for: ${linkName}`);
      }
    } catch { alert(`Error navigating to: ${linkName}`); }
  };

  // ── Helpers ─────────────────────────────────────────────────────────────────

  const getEmojiForLink = (name) => {
    const n = name.toLowerCase();
    if (n.includes('battlemap') || n.endsWith('.json')) return '🗺️';
    if (n.includes('stat') || n.includes('overview'))   return '📊';
    if (n.includes('initiative') || n.includes('tracker')) return '⚔️';
    if (n.includes('inventory'))  return '🎒';
    if (n.includes('quest') || n.includes('mission')) return '📜';
    if (n.includes('map'))    return '🗺️';
    if (n.includes('rule'))   return '📖';
    if (n.includes('note'))   return '📝';
    if (n.includes('lore') || n.includes('story')) return '📚';
    if (n.includes('combat')) return '⚔️';
    if (n.includes('spell') || n.includes('bending')) return '✨';
    return '🔗';
  };

  const getLinkColor = (name) => {
    const n = name.toLowerCase();
    if (n.includes('battlemap'))  return '#c8a96a';
    if (n.includes('stat'))       return '#91bbff';
    if (n.includes('initiative')) return '#ff8a80';
    if (n.includes('note'))       return '#a0d4a0';
    return '#8899aa';
  };

  const cleanLinkName = (name) =>
    name.replace(/\.json$/i, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className={`quicklinks-container ${lightMode ? 'light-mode' : ''}`}>
        <div className="quicklinks-loading">
          <div className="hex-loading-spinner">⬡</div>
          <span>Loading Quicklinks…</span>
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className={`quicklinks-container ${lightMode ? 'light-mode' : ''}`}>
        <div className="quicklinks-error">{error}</div>
      </div>
    );
  }

  const { topLinks, characters } = parseQuicklinks();

  return (
    <div className={`quicklinks-container ${lightMode ? 'light-mode' : ''}`}>
      <div className="quicklinks-header">
        <span className="hex-decoration" aria-hidden="true">⬡</span>
        <h1>Quicklinks</h1>
        <span className="hex-decoration" aria-hidden="true">⬡</span>
      </div>

      {/* ── Quick Access ── */}
      {topLinks.length > 0 && (
        <div className="quicklinks-section">
          <h2>Quick Access</h2>
          <div className="quicklinks-hex-row">
            {topLinks.map((link, index) => {
              const lc = getLinkColor(link);
              return (
                <button
                  key={index}
                  className="hex-quick-tile"
                  onClick={() => handleLinkClick(link)}
                  style={{
                    '--link-color':          lc,
                    '--link-color-bg':       hexToRgba(lc, 0.13),
                    '--link-color-bg-hover': hexToRgba(lc, 0.26),
                  }}
                >
                  <div className="hex-quick-glow">
                    <div className="hex-quick-bg">
                      <span className="hex-emoji">{getEmojiForLink(link)}</span>
                    </div>
                  </div>
                  <span className="hex-quick-name">{cleanLinkName(link)}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Characters ── */}
      {characters.length > 0 && (
        <div className="quicklinks-section">
          <h2>Characters</h2>
          <div className="quicklinks-hex-grid">
            {characters.map((character) => {
              const folderPath    = `PCs/${character}/`;
              const customization = customizations?.[character];
              const avatarPng     = avatarImages[character] || null;
              const charColor     = customization?.folderColor || fileColors[folderPath] || '#888888';
              const accentColor   = charColor === '#e6e6e6' ? '#666666' : charColor;
              const stats         = statOverview[character] || null;
              const conditions    = charConditions[character] || [];

              const hpPct  = stats ? Math.max(0, Math.min(100, (stats.currentHp / stats.maxHp) * 100)) : null;
              const hpFill = hpPct != null ? hpFillColor(hpPct) : '#95a5a6';

              return (
                <div key={character} className="hex-char-wrapper" style={{ '--char-color': accentColor }}>
                      {/* Main button — click opens character sheet */}
                      <button
                        className="hex-char-tile"
                        onClick={() => handleLinkClick(character)}
                      >
                        <div className="hex-tile-glow">
                          {/* CharacterToken handles: hex avatar, HP ring, condition rings */}
                          <CharacterToken
                            token={{
                              name:       character,
                              avatarPng:  avatarPng,
                              color:      accentColor,
                              currentHp:  stats?.currentHp ?? 100,
                              maxHp:      stats?.maxHp      ?? 100,
                              conditions: conditions,
                            }}
                            size={TOK_SIZE}
                            isSelected={false}
                            onClick={() => handleLinkClick(character)}
                          />

                          {/* ── Bubble overlay — exact TokenMarkers.jsx design ── */}
                          {(() => {
                            // Build active defensive stats for left-side stacking
                            const defStats = DEF_STAT_CONFIG
                              .filter(s => stats?.[s.key] > 0)
                              .map(s => ({ ...s, value: stats[s.key] }));
                            const defStartY = TOK_CY - (defStats.length * 10) / 2;

                            return (
                              <svg
                                width={TOK_SIZE}
                                height={TOK_SIZE}
                                viewBox={`0 0 ${TOK_SIZE} ${TOK_SIZE}`}
                                overflow="visible"
                                className="quicklink-bubble-overlay"
                              >
                                {/* HP — top center */}
                                {stats?.currentHp != null && (
                                  <g
                                    transform={`translate(${HP_POS.x.toFixed(1)},${HP_POS.y.toFixed(1)})`}
                                    style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                                    onClick={(e) => { e.stopPropagation(); openEditPopup(character, 'currentHp', stats.currentHp, e); }}
                                  >
                                    <circle r="12" fill={hpFill} opacity="0.3" />
                                    <circle r="10" fill={hpFill} stroke="#1a1a1a" strokeWidth="2" opacity="0.95" />
                                    <text
                                      textAnchor="middle" dominantBaseline="central"
                                      fontSize="11" fontWeight="bold" fill="#fff"
                                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                                    >
                                      {Math.round(stats.currentHp)}
                                    </text>
                                    <title>{`HP: ${Math.round(stats.currentHp)} / ${stats.maxHp} — click to edit`}</title>
                                  </g>
                                )}

                                {/* Defensive stats — left side, stacked vertically */}
                                {defStats.map((stat, idx) => {
                                  const dy = defStartY + idx * DEF_SPACING;
                                  return (
                                    <g
                                      key={stat.key}
                                      transform={`translate(${DEF_LEFT_X.toFixed(1)},${dy.toFixed(1)})`}
                                      style={{ pointerEvents: 'auto', cursor: 'pointer' }}
                                      onClick={(e) => { e.stopPropagation(); openEditPopup(character, stat.key, stat.value, e); }}
                                    >
                                      <circle r="10" fill={stat.color} opacity="0.3" />
                                      <circle r="8"  fill={stat.color} stroke="#1a1a1a" strokeWidth="2" opacity="0.95" />
                                      <text
                                        textAnchor="middle" dominantBaseline="central"
                                        fontSize="10" fontWeight="bold" fill="#fff"
                                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                                      >
                                        {stat.value}
                                      </text>
                                      <title>{`${stat.label}: ${stat.value} — click to edit`}</title>
                                    </g>
                                  );
                                })}
                              </svg>
                            );
                          })()}
                        </div>
                        <span className="hex-char-name">{character}</span>
                      </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Edit popup — MarkerPopup design ── */}
      {editPopup && (
        <>
          {/* Click-outside dismiss */}
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
            onClick={() => setEditPopup(null)}
          />
          <div
            className="quicklink-edit-popup"
            style={{
              left: Math.min(editPopup.x, window.innerWidth  - 220),
              top:  Math.max(editPopup.y - 110, 8),
              borderColor: editPopup.color,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="qep-label" style={{ color: editPopup.color }}>
              {editPopup.char} — {editPopup.label}
            </div>
            <input
              ref={editInputRef}
              type="number"
              className="qep-input"
              value={editPopup.inputValue}
              onChange={(e) => setEditPopup(p => ({ ...p, inputValue: e.target.value }))}
              onKeyDown={(e) => {
                if (e.key === 'Enter')  handleEditSave();
                if (e.key === 'Escape') setEditPopup(null);
              }}
            />
            <div className="qep-buttons">
              <button
                className="qep-save"
                onClick={handleEditSave}
                disabled={savingEdit}
              >
                {savingEdit ? '…' : 'Save'}
              </button>
              <button className="qep-cancel" onClick={() => setEditPopup(null)}>
                Cancel
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Quicklinks;
