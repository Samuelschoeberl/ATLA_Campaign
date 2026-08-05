import React, { useState, useEffect, useRef, useCallback } from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragOverlay } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { API_BASE_URL } from '../config/api';
import { useReadyState } from '../context/ReadyStateContext';
import PixelAvatar from './PixelAvatar';
import { subscribe as subscribeToVaultPath, patchInitiativeTurn } from '../data/vaultResource';
import './InitiativeTracker.css';

function DraggableSidebarCharacter({ character, isInInitiative, onClick, avatarPng, accentColor }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: character.id,
    data: { type: 'sidebar', character },
  });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), opacity: isDragging ? 0.5 : 1 }}
      className={`available-character ${isInInitiative ? 'in-initiative' : ''} ${isDragging ? 'dragging' : ''}`}
      title={isInInitiative ? 'Click to remove from initiative' : 'Click to add or drag into position'}
    >
      <div className="sidebar-char-content" onClick={() => !isDragging && onClick()}>
        <PixelAvatar
          className="character-icon"
          avatarPng={avatarPng}
          size={56}
          borderColor={accentColor || 'rgba(255,255,255,0.3)'}
          placeholderLabel={character.name?.[0] || 'C'}
        />
        <span className="character-name">{character.name}</span>
        {isInInitiative && <span className="in-initiative-badge">✓</span>}
      </div>
      <div className="sidebar-drag-handle" {...attributes} {...listeners}>⋮⋮</div>
    </div>
  );
}

function SortableInitiativeItem({
  character, index, isCurrentTurn, onUpdate, onRemove,
  showDropIndicatorBefore, characters, pcStats, onToggleEnemy,
  onUpdateManualHp, onToggleDamageMode, isReady, avatarPng, accentColor
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: character.id });

  const characterStats = pcStats[character.name];
  const currentHp = characterStats?.vitality?.find(s => s.key === 'current_hp')
    ? parseFloat(characterStats.vitality.find(s => s.key === 'current_hp').value)
    : null;
  const maxHp = characterStats?.vitality?.find(s => s.key === 'max_hp')
    ? parseFloat(characterStats.vitality.find(s => s.key === 'max_hp').value)
    : null;

  const hasManualHp = character.manualCurrentHp !== undefined && character.manualMaxHp !== undefined && character.manualMaxHp > 0;
  const displayCurrentHp = currentHp !== null ? currentHp : (hasManualHp ? character.manualCurrentHp : null);
  const displayMaxHp = maxHp !== null ? maxHp : (hasManualHp ? character.manualMaxHp : null);
  const hpPercentage = (displayCurrentHp !== null && displayMaxHp > 0)
    ? Math.max(0, Math.min(100, (displayCurrentHp / displayMaxHp) * 100))
    : null;

  const getHpColor = (p) => p > 75 ? '#4ec9b0' : p > 50 ? '#dcdcaa' : p > 25 ? '#ce9178' : '#f48771';
  const hpColor = hpPercentage !== null ? getHpColor(hpPercentage) : null;
  const showManualHpInput = currentHp === null && maxHp === null && !hasManualHp;

  const dropInitiativeBefore = showDropIndicatorBefore
    ? (index === 0 ? character.initiative + 1 : characters[index - 1].initiative - 1)
    : null;

  return (
    <>
      {showDropIndicatorBefore && (
        <div className="drop-indicator">
          <div className="drop-indicator-line" />
          <div className="drop-indicator-badge">Will be assigned: {dropInitiativeBefore}</div>
        </div>
      )}
      <div
        ref={setNodeRef}
        style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.3 : 1 }}
        className={`initiative-item ${isCurrentTurn ? 'current-turn' : ''} ${isDragging ? 'dragging' : ''} ${character.isEnemy ? 'enemy' : ''}`}
      >
        {isCurrentTurn && (
          <div className="current-turn-indicator">
            <span className="indicator-arrow">▶</span>
            <span className="indicator-text">Current Turn</span>
          </div>
        )}

        <div className="drag-handle" {...attributes} {...listeners}>⋮⋮</div>

        <button
          onClick={() => onToggleEnemy(character.id)}
          className={`btn-enemy-toggle ${character.isEnemy ? 'active' : ''}`}
          title={character.isEnemy ? 'Mark as ally' : 'Mark as enemy'}
        >
          {character.isEnemy ? '👹' : (
            <PixelAvatar
              className="enemy-toggle-avatar"
              avatarPng={avatarPng}
              size={44}
              borderColor={accentColor || 'rgba(255,255,255,0.6)'}
              placeholderLabel={character.name?.[0] || 'C'}
            />
          )}
        </button>

        <div className="item-body">
          <div className="character-fields">
            <input
              type="text"
              value={character.name}
              onChange={(e) => onUpdate(character.id, e.target.value, character.initiative)}
              className="editable-field name-field"
              placeholder="Character name"
            />
            {(isReady || character.isEnemy) && (
              <span className="ready-badge" title={character.isEnemy ? 'Enemy (always ready)' : 'Turn planned and ready'}>✓</span>
            )}
            <div className="initiative-control">
              <input
                type="number"
                value={character.initiative}
                onChange={(e) => onUpdate(character.id, character.name, parseInt(e.target.value) || 0)}
                className="editable-field initiative-field"
                placeholder="Init"
              />
              <div className="initiative-buttons">
                <button onClick={() => onUpdate(character.id, character.name, character.initiative + 1)} className="init-btn init-up">▲</button>
                <button onClick={() => onUpdate(character.id, character.name, character.initiative - 1)} className="init-btn init-down">▼</button>
              </div>
            </div>
          </div>

          {hpPercentage !== null && (
            <div className="it-hp-bar">
              <div className="hp-bar-header">
                <span>{character.isEnemy && character.damageMode ? 'Damage' : 'HP'}</span>
                {hasManualHp ? (
                  <div className="hp-inputs">
                    {character.isEnemy && character.damageMode ? (
                      <>
                        <input
                          type="number"
                          value={(character.manualMaxHp ?? 0) - (character.manualCurrentHp ?? 0)}
                          onChange={(e) => {
                            const dmg = parseInt(e.target.value) || 0;
                            onUpdateManualHp(character.id, (character.manualMaxHp ?? 0) - dmg, character.manualMaxHp);
                          }}
                          className="hp-input"
                        />
                        <span>dealt</span>
                      </>
                    ) : (
                      <>
                        <input
                          type="number"
                          value={character.manualCurrentHp ?? 0}
                          onChange={(e) => onUpdateManualHp(character.id, parseInt(e.target.value) || 0, character.manualMaxHp)}
                          className="hp-input"
                        />
                        <span>/</span>
                        <input
                          type="number"
                          value={character.manualMaxHp ?? 0}
                          onChange={(e) => onUpdateManualHp(character.id, character.manualCurrentHp, parseInt(e.target.value) || 0)}
                          className="hp-input"
                        />
                      </>
                    )}
                    {character.isEnemy && (
                      <button
                        onClick={() => onToggleDamageMode(character.id)}
                        className={`btn-damage-mode ${character.damageMode ? 'active' : ''}`}
                        title={character.damageMode ? 'Switch to HP mode' : 'Switch to damage mode'}
                      >
                        {character.damageMode ? '💢' : '❤️'}
                      </button>
                    )}
                  </div>
                ) : (
                  <span>{displayCurrentHp} / {displayMaxHp}</span>
                )}
              </div>
              {!(character.isEnemy && character.damageMode) && (
                <div className="hp-track">
                  <div className="hp-fill" style={{ width: `${hpPercentage}%`, backgroundColor: hpColor, boxShadow: `0 0 8px ${hpColor}` }} />
                  <span className="hp-percent">{Math.round(hpPercentage)}%</span>
                </div>
              )}
            </div>
          )}

          {showManualHpInput && (
            <div className="it-hp-bar">
              <div className="hp-inputs">
                <span className="hp-label">HP:</span>
                <input
                  type="number"
                  value={character.manualCurrentHp ?? ''}
                  onChange={(e) => onUpdateManualHp(character.id, e.target.value === '' ? undefined : parseInt(e.target.value) || 0, character.manualMaxHp)}
                  placeholder="Current"
                  className="hp-input hp-input-lg"
                />
                <span>/</span>
                <input
                  type="number"
                  value={character.manualMaxHp ?? ''}
                  onChange={(e) => onUpdateManualHp(character.id, character.manualCurrentHp, e.target.value === '' ? undefined : parseInt(e.target.value) || 0)}
                  placeholder="Max"
                  className="hp-input hp-input-lg"
                />
              </div>
            </div>
          )}
        </div>

        <button onClick={() => onRemove(character.id)} className="btn-remove">✕</button>
      </div>
    </>
  );
}

function EndOfRoundMarker({ showDropIndicatorBefore, characters }) {
  const { setNodeRef, transform, transition } = useSortable({ id: 'end-of-round' });
  const dropInit = showDropIndicatorBefore
    ? (characters.length > 0 ? characters[characters.length - 1].initiative - 1 : 20)
    : null;

  return (
    <>
      {showDropIndicatorBefore && (
        <div className="drop-indicator">
          <div className="drop-indicator-line" />
          <div className="drop-indicator-badge">Will be assigned: {dropInit}</div>
        </div>
      )}
      <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition }} className="end-of-round-marker">
        <div className="end-marker-content">
          <span className="end-marker-text">End of Round</span>
          <span className="end-marker-initiative">0</span>
        </div>
      </div>
    </>
  );
}

function parseInitiativeFile(content) {
  const turnMatch = content.match(/\*\*Current Turn:\*\*.*\(Index:\s*(\d+)\)/);
  const roundMatch = content.match(/\*\*Round:\*\*\s*(\d+)/);
  const turnIndex = turnMatch ? parseInt(turnMatch[1]) || 0 : 0;
  const round = roundMatch ? parseInt(roundMatch[1]) || 1 : 1;

  const lines = content.split('\n').filter(l => l.trim());
  const characters = lines
    .slice(2)
    .filter(l => l.includes('|') && !l.includes('Last generated') && !l.includes('Current Turn'))
    .map((line, index) => {
      const parts = line.split('|').map(p => p.trim()).filter(p => p);
      if (parts.length < 2 || parts[0] === 'End of Round') return null;
      const char = {
        id: `char-${index}-${Date.now()}`,
        name: parts[0],
        initiative: parseInt(parts[1]) || 0,
        isEnemy: parts[2] === '👹',
        damageMode: parts[4] === '💢',
      };
      if (parts[3]) {
        const hp = parts[3].match(/(-?\d+)\/(\d+)/);
        if (hp) { char.manualCurrentHp = parseInt(hp[1]); char.manualMaxHp = parseInt(hp[2]); }
      }
      return char;
    })
    .filter(Boolean);

  return { characters, turnIndex, round };
}

function InitiativeTracker({ filePath, lightMode = false }) {
  const [characters, setCharacters] = useState([]);
  const [currentTurnIndex, setCurrentTurnIndex] = useState(0);
  const [newCharName, setNewCharName] = useState('');
  const [newCharInitiative, setNewCharInitiative] = useState('');
  const [roundNumber, setRoundNumber] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [availableCharacters, setAvailableCharacters] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [overId, setOverId] = useState(null);
  const [showSidebar, setShowSidebar] = useState(false);
  const [pcStats, setPcStats] = useState({});
  const [customizations, setCustomizations] = useState({});

  const { isReady, clearReady, setReady } = useReadyState();

  // Refs to access latest state inside intervals without re-creating them
  const charactersRef = useRef(characters);
  const currentTurnIndexRef = useRef(currentTurnIndex);
  const roundNumberRef = useRef(roundNumber);
  const lastSavedRef = useRef(0);
  const isSavingRef = useRef(false);
  const lastReadyUpdateRef = useRef({});
  // Server-side version for the SQLite-backed initiative_state row (see
  // db.py / routes_initiative.py). Turn/round advance -- the highest-
  // frequency, most contested action in a live session -- used to have NO
  // server-side conflict check at all on its whole-file save; this is what
  // actually protects it now instead of just detecting a clobber after the
  // fact.
  const initiativeVersionRef = useRef(null);

  useEffect(() => { charactersRef.current = characters; }, [characters]);
  useEffect(() => { currentTurnIndexRef.current = currentTurnIndex; }, [currentTurnIndex]);
  useEffect(() => { roundNumberRef.current = roundNumber; }, [roundNumber]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Initial load
  useEffect(() => {
    loadInitiativeData();
    loadAvailableCharacters();
    loadCustomizations();
  }, [filePath]);

  // Tracker-file changes (roster edits, or a turn/round PATCH from this or
  // another tab) now arrive via SSE instead of a blind poll -- the backend
  // publishes a file_changed event for Initiative Tracker.md on every write,
  // whether that write came from this component's own save/patch calls or
  // another connected client's.
  useEffect(() => {
    const unsubscribe = subscribeToVaultPath(filePath, () => {
      loadInitiativeDataSilently();
    });
    return unsubscribe;
  }, [filePath]);

  // Per-character HP/ready-state sync: still on a 2-second poll for now.
  // These read from N separate per-character files (each PC's
  // _current_hp.md/_max_hp.md variable files, plus their sheet's `ready`
  // row) -- subscribing to all of them individually via vaultResource is a
  // reasonable next step, but out of scope for this pass; the turn/round
  // advance path above (the highest-frequency, least-protected action) is
  // what's been moved onto the new SSE + DB-backed PATCH infrastructure.
  // Paused when the tab is hidden to avoid keeping the server busy while the
  // user is on a different app (especially important on mobile).
  useEffect(() => {
    let id = null;

    const start = () => {
      if (id !== null) return;
      id = setInterval(() => {
        loadPcStatsForChars(charactersRef.current);
        loadReadyStates(charactersRef.current);
      }, 2000);
    };

    const stop = () => {
      if (id !== null) {
        clearInterval(id);
        id = null;
      }
    };

    const onVisibilityChange = () => {
      if (document.hidden) stop(); else start();
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    start();
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      stop();
    };
  }, []); // runs once, uses refs for latest characters

  // Turn/round advance: PATCH the DB-backed initiative_state row under a
  // real transaction (see db.py/routes_initiative.py) instead of POSTing the
  // entire tracker file with no version check. On a conflict (another
  // client advanced the turn between our load and this save), adopt the
  // server's state rather than clobbering it.
  useEffect(() => {
    if (isLoading || characters.length === 0) return;
    (async () => {
      try {
        const result = await patchInitiativeTurn(
          { currentTurnIndex, roundNumber },
          initiativeVersionRef.current
        );
        if (result.conflict) {
          console.warn('Initiative turn/round conflict -- adopting server state.', result.current);
          if (result.current) {
            initiativeVersionRef.current = result.current.version;
            if (Array.isArray(result.current.order) && result.current.order.length) {
              setCurrentTurnIndex(result.current.currentTurnIndex);
              setRoundNumber(result.current.roundNumber);
            }
          }
        } else {
          initiativeVersionRef.current = result.initiative?.version ?? initiativeVersionRef.current;
        }
      } catch (e) {
        console.error('Error patching initiative turn/round, falling back to full-file save:', e);
        saveInitiativeData(characters, currentTurnIndex, roundNumber);
      }
    })();
  }, [currentTurnIndex, roundNumber]);

  const loadInitiativeData = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
      const data = await res.json();
      const { characters: chars, turnIndex, round } = parseInitiativeFile(data.content || '');
      setCharacters(chars);
      setCurrentTurnIndex(Math.min(turnIndex, Math.max(0, chars.length - 1)));
      setRoundNumber(round);

      // Best-effort: grab the SQLite-backed version for conflict-aware turn/
      // round PATCHes. If the runtime DB hasn't been rebuilt yet (fresh
      // checkout, never ran rebuild_database.py), this just 404s and the
      // PATCH below force-applies (expected_version stays null) instead of
      // blocking on it.
      try {
        const verRes = await fetch(`${API_BASE_URL}/api/initiative`);
        if (verRes.ok) {
          const verData = await verRes.json();
          initiativeVersionRef.current = verData.version ?? null;
        }
      } catch { /* non-fatal */ }
    } catch (e) {
      console.error('Error loading initiative data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadInitiativeDataSilently = async () => {
    if (Date.now() - lastSavedRef.current < 2000 || isSavingRef.current) return;
    try {
      const res = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
      const data = await res.json();
      const { characters: newChars, turnIndex, round } = parseInitiativeFile(data.content || '');

      const currentChars = charactersRef.current;
      const currentTurn = currentTurnIndexRef.current;
      const currentRound = roundNumberRef.current;

      const charsChanged = JSON.stringify(currentChars.map(c => ({ name: c.name, initiative: c.initiative, isEnemy: c.isEnemy, manualCurrentHp: c.manualCurrentHp, manualMaxHp: c.manualMaxHp, damageMode: c.damageMode })))
        !== JSON.stringify(newChars.map(c => ({ name: c.name, initiative: c.initiative, isEnemy: c.isEnemy, manualCurrentHp: c.manualCurrentHp, manualMaxHp: c.manualMaxHp, damageMode: c.damageMode })));

      if (charsChanged) setCharacters(newChars);
      if (turnIndex !== currentTurn) setCurrentTurnIndex(Math.min(turnIndex, Math.max(0, newChars.length - 1)));
      if (round !== currentRound) setRoundNumber(round);
    } catch (e) {
      console.error('Error silently reloading:', e);
    }
  };

  const loadPcStatsForChars = async (chars) => {
    if (!chars.length) return;
    try {
      const stats = {};
      await Promise.all(chars.map(async (char) => {
        try {
          const [curRes, maxRes] = await Promise.all([
            fetch(`${API_BASE_URL}/player_root/variable/PC_variables/${encodeURIComponent(char.name)}/${encodeURIComponent(char.name)}_current_hp.md`),
            fetch(`${API_BASE_URL}/player_root/variable/PC_variables/${encodeURIComponent(char.name)}/${encodeURIComponent(char.name)}_max_hp.md`),
          ]);
          if (curRes.ok && maxRes.ok) {
            const [curData, maxData] = await Promise.all([curRes.json(), maxRes.json()]);
            const cur = curData.content?.split('\n')[0]?.trim();
            const max = maxData.content?.split('\n')[0]?.trim();
            if (cur && max) {
              stats[char.name] = { vitality: [{ key: 'current_hp', value: cur }, { key: 'max_hp', value: max }] };
            }
          }
        } catch { /* character has no HP files */ }
      }));
      setPcStats(stats);
    } catch (e) {
      console.error('Error loading PC stats:', e);
    }
  };

  const loadReadyStates = async (chars) => {
    for (const char of chars) {
      if (char.isEnemy) continue;
      const lastUpdate = lastReadyUpdateRef.current[char.name];
      if (lastUpdate && Date.now() - lastUpdate < 1000) continue;
      try {
        const res = await fetch(`${API_BASE_URL}/player_root/PCs/${encodeURIComponent(char.name)}/${encodeURIComponent(char.name)}%20character%20sheet.md`);
        if (!res.ok) continue;
        const data = await res.json();
        const lines = (data.content || '').split('\n');
        let inVitals = false;
        for (const line of lines) {
          if (line.includes('## Vitals')) { inVitals = true; continue; }
          if (inVitals && line.startsWith('##')) break;
          if (inVitals && line.includes('| ready')) {
            const parts = line.split('|').map(p => p.trim());
            if (parts.length >= 3) setReady(char.name, parts[2].toLowerCase() === 'yes');
            break;
          }
        }
      } catch { /* skip */ }
    }
  };

  const loadAvailableCharacters = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent('pc_primary_stats.md')}`);
      const data = await res.json();
      const lines = (data.content || '').split('\n').filter(l => l.trim());
      const chars = lines.slice(2)
        .filter(l => l.includes('|') && l.includes('yes'))
        .map((line, i) => {
          const parts = line.split('|').map(p => p.trim()).filter(p => p);
          if (parts.length < 2) return null;
          const nameMatch = parts[0].match(/\[\[([^\]]+)\]\]/);
          return { id: `available-${i}-${Date.now()}`, name: nameMatch ? nameMatch[1] : parts[0] };
        })
        .filter(Boolean);
      setAvailableCharacters(chars);
    } catch (e) {
      console.error('Error loading available characters:', e);
    }
  };

  const loadCustomizations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/characters/customizations`);
      if (!res.ok) return;
      const data = await res.json();
      const raw = data.customizations || {};
      const result = {};

      await Promise.all(Object.entries(raw).map(async ([name, c]) => {
        let avatarPng = c.avatarPng || null;
        if (avatarPng && !avatarPng.startsWith('data:image')) {
          try {
            const imgRes = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(avatarPng)}?cb=${Date.now()}`);
            if (imgRes.ok) {
              const blob = await imgRes.blob();
              avatarPng = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
              });
            }
          } catch { avatarPng = null; }
        }
        result[name] = { ...c, avatarPng };
      }));

      setCustomizations(result);
    } catch (e) {
      console.error('Error loading customizations:', e);
    }
  };

  const saveInitiativeData = async (chars, turnIdx = currentTurnIndexRef.current, round = roundNumberRef.current) => {
    isSavingRef.current = true;
    lastSavedRef.current = Date.now();
    const header = '| Character | Initiative | Enemy | Manual HP | Damage Mode |\n| --------- | ---------: | :---: | :-------: | :---------: |';
    const rows = chars.map(c => {
      const hp = (c.manualCurrentHp !== undefined && c.manualMaxHp !== undefined) ? `${c.manualCurrentHp}/${c.manualMaxHp}` : '';
      return `| ${c.name} | ${c.initiative} | ${c.isEnemy ? '👹' : ''} | ${hp} | ${c.damageMode ? '💢' : ''} |`;
    }).join('\n');
    const currentName = chars[turnIdx]?.name || '';
    const content = `${header}\n${rows}\n| End of Round | 0 | | | |\n\n**Current Turn:** ${currentName} (Index: ${turnIdx})\n**Round:** ${round}\n\n_Last generated by Mycelium/scripts/Python/generate_initiative.py_`;
    try {
      await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
    } catch (e) {
      console.error('Error saving initiative data:', e);
    } finally {
      isSavingRef.current = false;
    }
  };

  const handleUpdate = useCallback((id, name, initiative) => {
    setCharacters(prev => {
      const updated = prev.map(c => c.id === id ? { ...c, name, initiative } : c);
      saveInitiativeData(updated);
      return updated;
    });
  }, []);

  const handleRemove = useCallback((id) => {
    setCharacters(prev => {
      const idx = prev.findIndex(c => c.id === id);
      const updated = prev.filter(c => c.id !== id);
      saveInitiativeData(updated);
      setCurrentTurnIndex(cur => {
        if (idx < cur) return Math.max(0, cur - 1);
        if (idx === cur && updated.length > 0) return cur % updated.length;
        return cur;
      });
      return updated;
    });
  }, []);

  const handleToggleEnemy = useCallback((id) => {
    setCharacters(prev => {
      const updated = prev.map(c => c.id === id ? { ...c, isEnemy: !c.isEnemy } : c);
      saveInitiativeData(updated);
      return updated;
    });
  }, []);

  const handleUpdateManualHp = useCallback((id, currentHp, maxHp) => {
    setCharacters(prev => {
      const updated = prev.map(c => c.id === id ? { ...c, manualCurrentHp: currentHp, manualMaxHp: maxHp } : c);
      saveInitiativeData(updated);
      return updated;
    });
  }, []);

  const handleToggleDamageMode = useCallback((id) => {
    setCharacters(prev => {
      const updated = prev.map(c => c.id === id ? { ...c, damageMode: !c.damageMode } : c);
      saveInitiativeData(updated);
      return updated;
    });
  }, []);

  const handleToggleFromAvailable = (name) => {
    const existing = charactersRef.current.find(c => c.name === name);
    if (existing) {
      handleRemove(existing.id);
    } else {
      setCharacters(prev => {
        const newChar = { id: `char-${name}-${Date.now()}`, name, initiative: 10, isEnemy: false };
        const updated = [...prev, newChar].sort((a, b) => b.initiative - a.initiative);
        saveInitiativeData(updated);
        return updated;
      });
    }
  };

  const handleAddCharacter = () => {
    if (!newCharName.trim() || !newCharInitiative) return;
    setCharacters(prev => {
      const newChar = { id: `char-new-${Date.now()}`, name: newCharName.trim(), initiative: parseInt(newCharInitiative), isEnemy: false };
      const updated = [...prev, newChar].sort((a, b) => b.initiative - a.initiative);
      saveInitiativeData(updated);
      return updated;
    });
    setNewCharName('');
    setNewCharInitiative('');
  };

  const handleNextTurn = () => {
    if (!characters.length) return;
    const nextIndex = (currentTurnIndex + 1) % characters.length;
    const newRound = nextIndex === 0 ? roundNumber + 1 : roundNumber;
    setCurrentTurnIndex(nextIndex);
    if (nextIndex === 0) setRoundNumber(newRound);

    const current = characters[currentTurnIndex];
    if (current && !current.isEnemy) {
      lastReadyUpdateRef.current[current.name] = Date.now();
      clearReady(current.name);
      fetch(`${API_BASE_URL}/api/clear_ready/${encodeURIComponent(current.name)}`, { method: 'POST' })
        .catch(e => console.error('Error clearing ready state:', e));
    }
  };

  const handlePreviousTurn = () => {
    if (!characters.length) return;
    const prevIndex = currentTurnIndex === 0 ? characters.length - 1 : currentTurnIndex - 1;
    setCurrentTurnIndex(prevIndex);
    if (currentTurnIndex === 0 && roundNumber > 1) setRoundNumber(r => r - 1);
  };

  const handleResetInitiative = () => {
    setCurrentTurnIndex(0);
    setRoundNumber(1);
  };

  const handleSortInitiative = () => {
    const sorted = [...characters].sort((a, b) => b.initiative - a.initiative);
    setCharacters(sorted);
    setCurrentTurnIndex(0);
    saveInitiativeData(sorted, 0, roundNumber);
  };

  const handleDragStart = (e) => setActiveId(e.active.id);
  const handleDragOver = (e) => setOverId(e.over?.id || null);
  const handleDragCancel = () => { setActiveId(null); setOverId(null); };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);
    setOverId(null);
    if (!over) return;

    const isFromSidebar = active.data.current?.type === 'sidebar';

    if (isFromSidebar) {
      const char = active.data.current.character;
      if (characters.some(c => c.name === char.name)) return;

      const overIndex = characters.findIndex(c => c.id === over.id);
      let newInitiative, insertIndex;

      if (over.id === 'end-of-round') {
        newInitiative = characters.length ? characters[characters.length - 1].initiative - 1 : 20;
        insertIndex = characters.length;
      } else if (overIndex === -1) {
        newInitiative = 10; insertIndex = characters.length;
      } else if (overIndex === 0) {
        newInitiative = characters[0].initiative + 1; insertIndex = 0;
      } else {
        newInitiative = characters[overIndex - 1].initiative - 1; insertIndex = overIndex;
      }

      const newChar = { id: `char-${char.name}-${Date.now()}`, name: char.name, initiative: newInitiative, isEnemy: false };
      setCharacters(prev => {
        const updated = [...prev];
        updated.splice(insertIndex, 0, newChar);
        saveInitiativeData(updated);
        return updated;
      });
    } else if (active.id !== over.id) {
      setCharacters(prev => {
        const oldIdx = prev.findIndex(c => c.id === active.id);
        const newIdx = prev.findIndex(c => c.id === over.id);
        const updated = arrayMove(prev, oldIdx, newIdx);
        saveInitiativeData(updated);
        setCurrentTurnIndex(cur => {
          if (oldIdx === cur) return newIdx;
          if (oldIdx < cur && newIdx >= cur) return cur - 1;
          if (oldIdx > cur && newIdx <= cur) return cur + 1;
          return cur;
        });
        return updated;
      });
    }
  };

  if (isLoading) {
    return <div className={`initiative-tracker loading ${lightMode ? 'light-mode' : ''}`}>Loading initiative data...</div>;
  }

  const activeCharacter = activeId
    ? characters.find(c => c.id === activeId) || availableCharacters.find(c => c.id === activeId)
    : null;
  const activeCustom = activeCharacter ? customizations?.[activeCharacter.name] : null;
  const isFromSidebarDrag = activeId && availableCharacters.some(c => c.id === activeId);

  return (
    <div className={`initiative-tracker-container ${lightMode ? 'light-mode' : ''}`}>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        {showSidebar && (
          <div className="available-characters-sidebar">
            <h3>Available Characters</h3>
            <p className="sidebar-hint">Drag or click to add/remove</p>
            <SortableContext items={availableCharacters.map(c => c.id)} strategy={verticalListSortingStrategy}>
              <div className="available-characters-list">
                {availableCharacters.map((char) => (
                  <DraggableSidebarCharacter
                    key={char.id}
                    character={char}
                    isInInitiative={characters.some(c => c.name === char.name)}
                    onClick={() => handleToggleFromAvailable(char.name)}
                    avatarPng={customizations?.[char.name]?.avatarPng || null}
                    accentColor={customizations?.[char.name]?.folderColor}
                  />
                ))}
                {availableCharacters.length === 0 && <div className="no-characters">No active characters found</div>}
              </div>
            </SortableContext>
          </div>
        )}

        <div className="initiative-tracker-wrapper">
          <div className="initiative-tracker">
            <div className="tracker-header">
              <h2>⚔️ Initiative Tracker</h2>
              <div className="header-right">
                <button onClick={() => setShowSidebar(s => !s)} className="btn-toggle-sidebar" title="Toggle character sidebar">☰</button>
                <div className="round-counter">
                  <span className="round-label">Round:</span>
                  <span className="round-number">{roundNumber}</span>
                </div>
                <button onClick={handleSortInitiative} className="btn-sort" title="Sort by initiative" disabled={characters.length === 0}>⇅</button>
                <button onClick={handleResetInitiative} className="btn-reset-small" title="Reset to Round 1">↺</button>
              </div>
            </div>

            <div className="turn-controls-secondary">
              <button onClick={handlePreviousTurn} className="btn-control btn-previous" disabled={characters.length === 0}>← Previous</button>
            </div>

            <div className="initiative-list">
              <SortableContext items={[...characters.map(c => c.id), 'end-of-round']} strategy={verticalListSortingStrategy}>
                {characters.map((char, index) => (
                  <SortableInitiativeItem
                    key={char.id}
                    character={char}
                    index={index}
                    isCurrentTurn={index === currentTurnIndex}
                    onUpdate={handleUpdate}
                    onRemove={handleRemove}
                    onToggleEnemy={handleToggleEnemy}
                    onUpdateManualHp={handleUpdateManualHp}
                    onToggleDamageMode={handleToggleDamageMode}
                    showDropIndicatorBefore={isFromSidebarDrag && overId === char.id}
                    characters={characters}
                    pcStats={pcStats}
                    isReady={isReady(char.name)}
                    avatarPng={customizations?.[char.name]?.avatarPng || null}
                    accentColor={customizations?.[char.name]?.folderColor}
                  />
                ))}
                <EndOfRoundMarker
                  showDropIndicatorBefore={isFromSidebarDrag && overId === 'end-of-round'}
                  characters={characters}
                />
              </SortableContext>
              {characters.length === 0 && <div className="empty-state">No characters in initiative. Add some below!</div>}
            </div>

            <div className="add-character-form">
              <h3>Add Character</h3>
              <div className="form-inputs">
                <input
                  type="text"
                  value={newCharName}
                  onChange={(e) => setNewCharName(e.target.value)}
                  placeholder="Character name"
                  className="input-name"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCharacter()}
                />
                <input
                  type="number"
                  value={newCharInitiative}
                  onChange={(e) => setNewCharInitiative(e.target.value)}
                  placeholder="Initiative"
                  className="input-initiative"
                  onKeyPress={(e) => e.key === 'Enter' && handleAddCharacter()}
                />
                <button onClick={handleAddCharacter} className="btn-add">+ Add</button>
              </div>
            </div>
          </div>

          <button onClick={handleNextTurn} className="btn-next-vertical" disabled={characters.length === 0} title="Next Turn">
            <span className="next-turn-text">N<br/>E<br/>X<br/>T<br/><br/>T<br/>U<br/>R<br/>N</span>
            <span className="next-turn-arrow">↓</span>
          </button>
        </div>

        <DragOverlay>
          {activeCharacter && (
            <div className="drag-overlay-item">
              <PixelAvatar
                className="character-icon"
                avatarPng={activeCustom?.avatarPng || null}
                size={56}
                borderColor={activeCustom?.folderColor || 'rgba(255,255,255,0.5)'}
                placeholderLabel={activeCharacter.name?.[0] || 'C'}
              />
              <span className="character-name">{activeCharacter.name}</span>
              {activeCharacter.initiative !== undefined && (
                <span className="character-initiative">{activeCharacter.initiative}</span>
              )}
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

export default InitiativeTracker;
