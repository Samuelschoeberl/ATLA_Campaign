import React, { useState, useEffect, useRef } from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragOverlay } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { API_BASE_URL } from '../config/api';
import { hexToRgba } from '../utils/colorUtils';
import { useReadyState } from '../context/ReadyStateContext';
import './InitiativeTracker.css';

// Draggable Sidebar Character Component
function DraggableSidebarCharacter({ character, isInInitiative, onClick }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  } = useSortable({ id: character.id, data: { type: 'sidebar', character } });

  const style = {
    transform: CSS.Transform.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  };

  const handleClick = (e) => {
    // Only trigger click if we're not dragging
    if (!isDragging) {
      onClick();
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`available-character ${isInInitiative ? 'in-initiative' : ''} ${isDragging ? 'dragging' : ''}`}
      title={isInInitiative ? 'Click to remove from initiative' : 'Click to add or drag into position'}
    >
      <div className="sidebar-char-content" onClick={handleClick}>
        <span className="character-icon">👤</span>
        <span className="character-name">{character.name}</span>
        {isInInitiative && <span className="in-initiative-badge">✓</span>}
      </div>
      <div className="sidebar-drag-handle" {...attributes} {...listeners}>
        ⋮⋮
      </div>
    </div>
  );
}

// Sortable Initiative Item Component
function SortableInitiativeItem({ character, index, isCurrentTurn, onUpdate, onRemove, showDropIndicatorBefore, showDropIndicatorAfter, characters, pcStats, onToggleEnemy, onUpdateManualHp, isReady }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: character.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  const handleNameChange = (e) => {
    onUpdate(character.id, e.target.value, character.initiative);
  };

  const handleInitiativeChange = (e) => {
    const value = parseInt(e.target.value) || 0;
    onUpdate(character.id, character.name, value);
  };

  const incrementInitiative = () => {
    onUpdate(character.id, character.name, character.initiative + 1);
  };

  const decrementInitiative = () => {
    onUpdate(character.id, character.name, character.initiative - 1);
  };

  // Get HP data for this character if they're a PC
  const characterStats = pcStats[character.name];
  const currentHpStat = characterStats?.vitality?.find(s => s.key === 'current_hp');
  const maxHpStat = characterStats?.vitality?.find(s => s.key === 'max_hp');
  const currentHp = currentHpStat ? parseFloat(currentHpStat.value) : null;
  const maxHp = maxHpStat ? parseFloat(maxHpStat.value) : null;
  
  // Use manual HP if no PC stats found
  const hasManualHp = character.manualCurrentHp !== undefined && character.manualMaxHp !== undefined && 
                      character.manualMaxHp > 0;
  const displayCurrentHp = currentHp !== null ? currentHp : (hasManualHp ? character.manualCurrentHp : null);
  const displayMaxHp = maxHp !== null ? maxHp : (hasManualHp ? character.manualMaxHp : null);
  
  const hpPercentage = (displayCurrentHp !== null && displayMaxHp !== null && displayMaxHp > 0) 
    ? Math.max(0, Math.min(100, (displayCurrentHp / displayMaxHp) * 100)) 
    : null;
  
  // Determine life bar color based on HP percentage
  const getHpColor = (percent) => {
    if (percent > 75) return '#4ec9b0'; // Healthy green-cyan
    if (percent > 50) return '#dcdcaa'; // Yellow
    if (percent > 25) return '#ce9178'; // Orange
    return '#f48771'; // Critical red
  };
  const hpColor = hpPercentage !== null ? getHpColor(hpPercentage) : null;
  
  // Show manual HP input if no PC stats and no valid manual HP set yet
  const showManualHpInput = currentHp === null && maxHp === null && !hasManualHp;

  // Calculate what initiative will be assigned if dropped here
  let dropInitiativeBefore = null;
  
  if (showDropIndicatorBefore) {
    if (index === 0) {
      // Dropping before first item
      dropInitiativeBefore = character.initiative + 1;
    } else {
      // Dropping before this item (between previous and this)
      dropInitiativeBefore = characters[index - 1].initiative - 1;
    }
  }
  
  let dropInitiativeAfter = null;
  if (showDropIndicatorAfter) {
    dropInitiativeAfter = character.initiative - 1;
  }

  return (
    <>
      {showDropIndicatorBefore && (
        <div className="drop-indicator">
          <div className="drop-indicator-line"></div>
          <div className="drop-indicator-badge">
            Will be assigned: {dropInitiativeBefore}
          </div>
        </div>
      )}
      <div
        ref={setNodeRef}
        style={style}
        className={`initiative-item ${isCurrentTurn ? 'current-turn' : ''} ${isDragging ? 'dragging' : ''} ${character.isEnemy ? 'enemy' : ''}`}
      >
      <div className="drag-handle" {...attributes} {...listeners}>
        ⋮⋮
      </div>
      
      <button 
        onClick={() => onToggleEnemy(character.id)} 
        className={`btn-enemy-toggle ${character.isEnemy ? 'active' : ''}`}
        title={character.isEnemy ? 'Mark as ally' : 'Mark as enemy'}
      >
        {character.isEnemy ? '👹' : '👤'}
      </button>
      
      <div className="character-fields">
        <input
          type="text"
          value={character.name}
          onChange={handleNameChange}
          className="editable-field name-field"
          placeholder="Character name"
          style={{ flex: (isReady || character.isEnemy) ? '0 1 auto' : 1 }}
        />
        {(isReady || character.isEnemy) && (
          <span 
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              backgroundColor: '#2ecc71',
              color: '#fff',
              fontWeight: 'bold',
              fontSize: '16px',
              flexShrink: 0,
              boxShadow: '0 2px 4px rgba(46, 204, 113, 0.4)',
              animation: 'pulse 2s infinite',
              marginLeft: '-4px'
            }}
            title={character.isEnemy ? "Enemy (always ready)" : "Turn planned and ready"}
          >
            ✓
          </span>
        )}
        <div className="initiative-control">
          <input
            type="number"
            value={character.initiative}
            onChange={handleInitiativeChange}
            className="editable-field initiative-field"
            placeholder="Init"
          />
          <div className="initiative-buttons">
            <button onClick={incrementInitiative} className="init-btn init-up" title="Increase initiative">▲</button>
            <button onClick={decrementInitiative} className="init-btn init-down" title="Decrease initiative">▼</button>
          </div>
        </div>
      </div>
      
      {/* Health Bar for Player Characters */}
      {hpPercentage !== null && (
        <div style={{
          marginTop: '8px',
          width: '100%',
          padding: '4px 8px',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
          borderRadius: '4px',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '4px',
            fontSize: '10px',
            fontWeight: '600',
            color: '#cccccc'
          }}>
            <span>HP</span>
            {hasManualHp ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <input
                  type="number"
                  value={character.manualCurrentHp ?? 0}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 0;
                    onUpdateManualHp(character.id, value, character.manualMaxHp);
                  }}
                  style={{
                    width: '40px',
                    padding: '2px 4px',
                    fontSize: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    borderRadius: '3px',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: '#fff',
                    textAlign: 'center'
                  }}
                />
                <span>/</span>
                <input
                  type="number"
                  value={character.manualMaxHp ?? 0}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 0;
                    onUpdateManualHp(character.id, character.manualCurrentHp, value);
                  }}
                  style={{
                    width: '40px',
                    padding: '2px 4px',
                    fontSize: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    borderRadius: '3px',
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: '#fff',
                    textAlign: 'center'
                  }}
                />
              </div>
            ) : (
              <span>{displayCurrentHp} / {displayMaxHp}</span>
            )}
          </div>
          <div style={{
            width: '100%',
            height: '12px',
            backgroundColor: '#2d2d30',
            borderRadius: '6px',
            overflow: 'hidden',
            border: '1px solid #444',
            position: 'relative',
            boxShadow: 'inset 0 1px 2px rgba(0, 0, 0, 0.3)'
          }}>
            <div style={{
              width: `${hpPercentage}%`,
              height: '100%',
              backgroundColor: hpColor,
              transition: 'width 0.5s ease, background-color 0.5s ease',
              boxShadow: `0 0 8px ${hpColor}, inset 0 1px 2px rgba(255, 255, 255, 0.3)`,
              borderRadius: '5px'
            }} />
            <span style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              fontSize: '9px',
              fontWeight: 'bold',
              color: '#fff',
              textShadow: '0 1px 2px rgba(0, 0, 0, 0.8)',
              pointerEvents: 'none'
            }}>
              {Math.round(hpPercentage)}%
            </span>
          </div>
        </div>
      )}
      
      {/* Manual HP Input for non-PC characters */}
      {showManualHpInput && (
        <div style={{
          marginTop: '8px',
          width: '100%',
          padding: '6px 8px',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
          borderRadius: '4px',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11px'
          }}>
            <span style={{ color: '#cccccc', fontWeight: '600', minWidth: '25px' }}>HP:</span>
            <input
              type="number"
              value={character.manualCurrentHp ?? ''}
              onChange={(e) => {
                const value = e.target.value === '' ? undefined : parseInt(e.target.value) || 0;
                onUpdateManualHp(character.id, value, character.manualMaxHp);
              }}
              placeholder="Current"
              style={{
                width: '60px',
                padding: '4px 6px',
                fontSize: '11px',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                borderRadius: '4px',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                color: '#fff',
                textAlign: 'center'
              }}
            />
            <span style={{ color: '#888' }}>/</span>
            <input
              type="number"
              value={character.manualMaxHp ?? ''}
              onChange={(e) => {
                const value = e.target.value === '' ? undefined : parseInt(e.target.value) || 0;
                onUpdateManualHp(character.id, character.manualCurrentHp, value);
              }}
              placeholder="Max"
              style={{
                width: '60px',
                padding: '4px 6px',
                fontSize: '11px',
                border: '1px solid rgba(255, 255, 255, 0.3)',
                borderRadius: '4px',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                color: '#fff',
                textAlign: 'center'
              }}
            />
          </div>
        </div>
      )}
      
      <button onClick={() => onRemove(character.id)} className="btn-remove">✕</button>
      
      {isCurrentTurn && (
        <div className="current-turn-indicator">
          <span className="indicator-arrow">▶</span>
          <span className="indicator-text">Current Turn</span>
        </div>
      )}
    </div>
    {showDropIndicatorAfter && (
      <div className="drop-indicator">
        <div className="drop-indicator-line"></div>
        <div className="drop-indicator-badge">
          Will be assigned: {dropInitiativeAfter}
        </div>
      </div>
    )}
    </>
  );
}

// End of Round Marker Component (sortable but not editable)
function EndOfRoundMarker({ showDropIndicatorBefore, characters }) {
  const {
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: 'end-of-round' });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // Calculate initiative for dropping before end marker
  let dropInitiativeBefore = null;
  if (showDropIndicatorBefore && characters.length > 0) {
    dropInitiativeBefore = characters[characters.length - 1].initiative - 1;
  } else if (showDropIndicatorBefore && characters.length === 0) {
    dropInitiativeBefore = 20; // Default if no characters
  }

  return (
    <>
      {showDropIndicatorBefore && (
        <div className="drop-indicator">
          <div className="drop-indicator-line"></div>
          <div className="drop-indicator-badge">
            Will be assigned: {dropInitiativeBefore}
          </div>
        </div>
      )}
      
      <div ref={setNodeRef} style={style} className="end-of-round-marker">
        <div className="end-marker-content">
          <span className="end-marker-text">End of Round</span>
          <span className="end-marker-initiative">0</span>
        </div>
      </div>
    </>
  );
}

// Main Initiative Tracker Component
function InitiativeTracker({ filePath, lightMode = false, advancedMode = false }) {
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
  
  // Get ready state from context
  const { isReady, clearReady, setReady } = useReadyState();
  
  // Track last ready state update to prevent race conditions
  const lastReadyUpdateRef = useRef({});
  
  // Track last initiative update time to prevent race conditions
  const lastInitiativeUpdateRef = useRef(0);
  const isSavingRef = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Load initiative data from file
  useEffect(() => {
    loadInitiativeData();
    loadAvailableCharacters();
    loadPcStats();
  }, [filePath]);

  // Load ready states after characters are loaded
  useEffect(() => {
    if (characters.length > 0) {
      loadReadyStates();
    }
  }, [characters.length]);

  // Save initiative data whenever current turn or round changes
  useEffect(() => {
    // Don't save on initial load
    if (characters.length > 0 && !isLoading) {
      saveInitiativeData(characters, currentTurnIndex, roundNumber);
    }
  }, [currentTurnIndex, roundNumber]);

  // Periodically refresh PC stats for HP updates and initiative state
  useEffect(() => {
    const intervalId = setInterval(() => {
      loadPcStats();
      loadReadyStates();
      // Reload initiative data to sync current turn across devices
      loadInitiativeDataSilently();
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(intervalId); // Cleanup on unmount
  }, [characters]); // Re-create interval when characters change

  const loadPcStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/stat_overview`);
      if (response.ok) {
        const data = await response.json();
        setPcStats(data.pcs || {});
      }
    } catch (error) {
      console.error('Error loading PC stats:', error);
    }
  };

  const loadReadyStates = async () => {
    try {
      // Load ready states for all characters in the initiative
      for (const character of characters) {
        if (!character.isEnemy) {
          // Skip if we recently updated this character's ready state (within last 3 seconds)
          const lastUpdate = lastReadyUpdateRef.current[character.name];
          const timeSinceUpdate = lastUpdate ? Date.now() - lastUpdate : Infinity;
          
          if (lastUpdate && timeSinceUpdate < 3000) {
            continue;
          }
          
          // Fetch the character sheet
          const response = await fetch(`${API_BASE_URL}/player_root/PCs/${encodeURIComponent(character.name)}/${encodeURIComponent(character.name)}%20character%20sheet.md`);
          if (response.ok) {
            const data = await response.json();
            const content = data.content || '';
            
            // Parse the Vitals section for ready state
            const lines = content.split('\n');
            let inVitals = false;
            for (const line of lines) {
              if (line.includes('## Vitals')) {
                inVitals = true;
                continue;
              }
              if (inVitals && line.startsWith('##')) {
                break;
              }
              if (inVitals && line.includes('| ready')) {
                const parts = line.split('|').map(p => p.trim());
                if (parts.length >= 3) {
                  const readyValue = parts[2].toLowerCase();
                  const isReadyFromFile = readyValue === 'yes';
                  const currentState = isReady(character.name);
                  setReady(character.name, isReadyFromFile);
                }
                break;
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error loading ready states:', error);
    }
  };

  const loadAvailableCharacters = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent('pc_primary_stats.md')}`);
      const data = await response.json();
      const content = data.content || '';
      
      // Parse markdown table
      const lines = content.split('\n').filter(line => line.trim());
      const dataLines = lines.slice(2); // Skip header and separator
      
      const parsedCharacters = dataLines
        .filter(line => line.includes('|') && line.includes('yes'))
        .map((line, index) => {
          const parts = line.split('|').map(p => p.trim()).filter(p => p);
          if (parts.length >= 2) {
            // Extract character name from wiki link [[Name]]
            const nameMatch = parts[0].match(/\[\[([^\]]+)\]\]/);
            const name = nameMatch ? nameMatch[1] : parts[0];
            return {
              id: `available-${index}-${Date.now()}`,
              name: name,
            };
          }
          return null;
        })
        .filter(char => char !== null);

      setAvailableCharacters(parsedCharacters);
    } catch (error) {
      console.error('Error loading available characters:', error);
    }
  };

  const loadInitiativeData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
      const data = await response.json();
      const content = data.content || '';
      
      // Parse metadata for current turn and round
      let loadedTurnIndex = 0;
      let loadedRound = 1;
      
      const turnMatch = content.match(/\*\*Current Turn:\*\*.*\(Index:\s*(\d+)\)/);
      if (turnMatch) {
        loadedTurnIndex = parseInt(turnMatch[1]) || 0;
      }
      
      const roundMatch = content.match(/\*\*Round:\*\*\s*(\d+)/);
      if (roundMatch) {
        loadedRound = parseInt(roundMatch[1]) || 1;
      }
      
      // Parse markdown table
      const lines = content.split('\n').filter(line => line.trim());
      const dataLines = lines.slice(2); // Skip header and separator
      
      const parsedCharacters = dataLines
        .filter(line => line.includes('|') && !line.includes('Last generated') && !line.includes('Current Turn'))
        .map((line, index) => {
          const parts = line.split('|').map(p => p.trim()).filter(p => p);
          if (parts.length >= 2 && parts[0] !== 'End of Round') {
            const character = {
              id: `char-${index}-${Date.now()}`,
              name: parts[0],
              initiative: parseInt(parts[1]) || 0,
              isEnemy: false,
            };
            
            // Parse enemy status (column 3, if it exists)
            if (parts.length >= 3 && parts[2] === '👹') {
              character.isEnemy = true;
            }
            
            // Parse manual HP (column 4, if it exists)
            if (parts.length >= 4 && parts[3]) {
              const hpMatch = parts[3].match(/(\d+)\/(\d+)/);
              if (hpMatch) {
                character.manualCurrentHp = parseInt(hpMatch[1]);
                character.manualMaxHp = parseInt(hpMatch[2]);
              }
            }
            
            return character;
          }
          return null;
        })
        .filter(char => char !== null);

      setCharacters(parsedCharacters);
      setCurrentTurnIndex(Math.min(loadedTurnIndex, parsedCharacters.length - 1));
      setRoundNumber(loadedRound);
      setIsLoading(false);
    } catch (error) {
      console.error('Error loading initiative data:', error);
      setIsLoading(false);
    }
  };

  // Silently reload initiative data to sync across devices (don't show loading)
  const loadInitiativeDataSilently = async () => {
    // Don't reload if we just saved (within last 2 seconds) to prevent overwriting our own changes
    const timeSinceLastUpdate = Date.now() - lastInitiativeUpdateRef.current;
    if (timeSinceLastUpdate < 2000 || isSavingRef.current) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`);
      const data = await response.json();
      const content = data.content || '';
      
      // Parse metadata for current turn and round
      let loadedTurnIndex = 0;
      let loadedRound = 1;
      
      const turnMatch = content.match(/\*\*Current Turn:\*\*.*\(Index:\s*(\d+)\)/);
      if (turnMatch) {
        loadedTurnIndex = parseInt(turnMatch[1]) || 0;
      }
      
      const roundMatch = content.match(/\*\*Round:\*\*\s*(\d+)/);
      if (roundMatch) {
        loadedRound = parseInt(roundMatch[1]) || 1;
      }
      
      // Parse markdown table
      const lines = content.split('\n').filter(line => line.trim());
      const dataLines = lines.slice(2); // Skip header and separator
      
      const parsedCharacters = dataLines
        .filter(line => line.includes('|') && !line.includes('Last generated') && !line.includes('Current Turn'))
        .map((line, index) => {
          const parts = line.split('|').map(p => p.trim()).filter(p => p);
          if (parts.length >= 2 && parts[0] !== 'End of Round') {
            const character = {
              id: `char-${index}-${Date.now()}`,
              name: parts[0],
              initiative: parseInt(parts[1]) || 0,
              isEnemy: false,
            };
            
            // Parse enemy status (column 3, if it exists)
            if (parts.length >= 3 && parts[2] === '👹') {
              character.isEnemy = true;
            }
            
            // Parse manual HP (column 4, if it exists)
            if (parts.length >= 4 && parts[3]) {
              const hpMatch = parts[3].match(/(\d+)\/(\d+)/);
              if (hpMatch) {
                character.manualCurrentHp = parseInt(hpMatch[1]);
                character.manualMaxHp = parseInt(hpMatch[2]);
              }
            }
            
            return character;
          }
          return null;
        })
        .filter(char => char !== null);

      // Only update if data has actually changed
      const hasCharacterChanges = JSON.stringify(characters.map(c => ({ name: c.name, initiative: c.initiative, isEnemy: c.isEnemy, manualCurrentHp: c.manualCurrentHp, manualMaxHp: c.manualMaxHp }))) 
        !== JSON.stringify(parsedCharacters.map(c => ({ name: c.name, initiative: c.initiative, isEnemy: c.isEnemy, manualCurrentHp: c.manualCurrentHp, manualMaxHp: c.manualMaxHp })));
      const hasTurnChange = loadedTurnIndex !== currentTurnIndex;
      const hasRoundChange = loadedRound !== roundNumber;

      if (hasCharacterChanges) {
        setCharacters(parsedCharacters);
      }
      if (hasTurnChange) {
        setCurrentTurnIndex(Math.min(loadedTurnIndex, parsedCharacters.length - 1));
      }
      if (hasRoundChange) {
        setRoundNumber(loadedRound);
      }
    } catch (error) {
      console.error('Error silently reloading initiative data:', error);
    }
  };

  // Save initiative data to file
  const saveInitiativeData = async (updatedCharacters, turnIndex = currentTurnIndex, round = roundNumber) => {
    // Mark that we're saving and update the timestamp
    isSavingRef.current = true;
    lastInitiativeUpdateRef.current = Date.now();

    const tableHeader = '| Character | Initiative | Enemy | Manual HP |\n| --------- | ---------: | :---: | :-------: |';
    const tableRows = updatedCharacters
      .map(char => {
        const enemyStatus = char.isEnemy ? '👹' : '';
        const manualHp = (char.manualCurrentHp !== undefined && char.manualMaxHp !== undefined) 
          ? `${char.manualCurrentHp}/${char.manualMaxHp}` 
          : '';
        return `| ${char.name} | ${char.initiative} | ${enemyStatus} | ${manualHp} |`;
      })
      .join('\n');
    const endMarker = '\n| End of Round | 0 | | |';
    
    // Add metadata about current turn and round
    const currentCharName = updatedCharacters[turnIndex]?.name || '';
    const metadata = `\n\n**Current Turn:** ${currentCharName} (Index: ${turnIndex})\n**Round:** ${round}`;
    
    const footer = '\n\n_Last generated by Mycelium/scripts/Python/generate_initiative.py_';
    const content = `${tableHeader}\n${tableRows}${endMarker}${metadata}${footer}`;

    try {
      await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
    } catch (error) {
      console.error('Error saving initiative data:', error);
    } finally {
      isSavingRef.current = false;
    }
  };

  // Handle drag start
  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  // Handle drag over
  const handleDragOver = (event) => {
    setOverId(event.over?.id || null);
  };

  // Handle drag cancel
  const handleDragCancel = () => {
    setActiveId(null);
    setOverId(null);
  };

  // Handle drag end
  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);
    setOverId(null);

    if (!over) return;

    const activeData = active.data.current;
    const isFromSidebar = activeData?.type === 'sidebar';

    if (isFromSidebar) {
      // Dragging from sidebar into initiative
      const character = activeData.character;
      
      // Check if character is already in initiative
      if (characters.some(char => char.name === character.name)) {
        return;
      }

      // Find the position where we're dropping
      const overIndex = characters.findIndex((item) => item.id === over.id);
      
      let newInitiative;
      let insertIndex;
      
      if (over.id === 'end-of-round') {
        // Dropped on end of round marker - insert at the end
        if (characters.length === 0) {
          newInitiative = 20; // Default if no characters
        } else {
          newInitiative = characters[characters.length - 1].initiative - 1;
        }
        insertIndex = characters.length;
      } else if (overIndex === -1) {
        // Dropped outside list, add with default initiative
        newInitiative = 10;
        insertIndex = characters.length;
      } else if (overIndex === 0) {
        // Dropped at first position - one above the highest
        newInitiative = characters[0].initiative + 1;
        insertIndex = 0;
      } else {
        // Dropped before this character - one below the character above it
        newInitiative = characters[overIndex - 1].initiative - 1;
        insertIndex = overIndex;
      }

      const newChar = {
        id: `char-${character.name}-${Date.now()}`,
        name: character.name,
        initiative: newInitiative,
        isEnemy: false,
      };

      // Insert at the correct position
      const newCharacters = [...characters];
      newCharacters.splice(insertIndex, 0, newChar);

      setCharacters(newCharacters);
      saveInitiativeData(newCharacters);
    } else if (active.id !== over.id) {
      // Reordering within initiative list
      setCharacters((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);
        const newItems = arrayMove(items, oldIndex, newIndex);
        saveInitiativeData(newItems);
        
        // Update current turn index if needed
        if (oldIndex === currentTurnIndex) {
          setCurrentTurnIndex(newIndex);
        } else if (oldIndex < currentTurnIndex && newIndex >= currentTurnIndex) {
          setCurrentTurnIndex(currentTurnIndex - 1);
        } else if (oldIndex > currentTurnIndex && newIndex <= currentTurnIndex) {
          setCurrentTurnIndex(currentTurnIndex + 1);
        }
        
        return newItems;
      });
    }
  };

  // Update character
  const handleUpdate = (id, name, initiative) => {
    const updatedCharacters = characters.map(char =>
      char.id === id ? { ...char, name, initiative } : char
    );
    setCharacters(updatedCharacters);
    saveInitiativeData(updatedCharacters);
  };

  // Remove character
  const handleRemove = (id) => {
    const index = characters.findIndex(char => char.id === id);
    const updatedCharacters = characters.filter(char => char.id !== id);
    setCharacters(updatedCharacters);
    saveInitiativeData(updatedCharacters);
    
    // Adjust current turn index if needed
    if (index < currentTurnIndex) {
      setCurrentTurnIndex(Math.max(0, currentTurnIndex - 1));
    } else if (index === currentTurnIndex && updatedCharacters.length > 0) {
      setCurrentTurnIndex(currentTurnIndex % updatedCharacters.length);
    }
  };

  // Toggle enemy status
  const handleToggleEnemy = (id) => {
    const updatedCharacters = characters.map(char =>
      char.id === id ? { ...char, isEnemy: !char.isEnemy } : char
    );
    setCharacters(updatedCharacters);
    saveInitiativeData(updatedCharacters);
  };

  // Update manual HP for non-PC characters
  const handleUpdateManualHp = (id, currentHp, maxHp) => {
    const updatedCharacters = characters.map(char =>
      char.id === id ? { ...char, manualCurrentHp: currentHp, manualMaxHp: maxHp } : char
    );
    setCharacters(updatedCharacters);
    saveInitiativeData(updatedCharacters);
  };

  // Toggle character from available list (add or remove)
  const handleToggleFromAvailable = (characterName) => {
    // Check if character is already in initiative
    const existingChar = characters.find(char => char.name === characterName);
    
    if (existingChar) {
      // Remove from initiative
      handleRemove(existingChar.id);
    } else {
      // Add to initiative with default value
      const newChar = {
        id: `char-${characterName}-${Date.now()}`,
        name: characterName,
        initiative: 10, // Default initiative
        isEnemy: false,
      };
      
      // Insert in sorted position by initiative (descending)
      const updatedCharacters = [...characters, newChar].sort((a, b) => b.initiative - a.initiative);
      setCharacters(updatedCharacters);
      saveInitiativeData(updatedCharacters);
    }
  };

  // Add new character
  const handleAddCharacter = () => {
    if (newCharName.trim() && newCharInitiative) {
      const newChar = {
        id: `char-new-${Date.now()}`,
        name: newCharName.trim(),
        initiative: parseInt(newCharInitiative),
        isEnemy: false,
      };
      
      // Insert in sorted position by initiative (descending)
      const updatedCharacters = [...characters, newChar].sort((a, b) => b.initiative - a.initiative);
      setCharacters(updatedCharacters);
      saveInitiativeData(updatedCharacters);
      
      setNewCharName('');
      setNewCharInitiative('');
    }
  };

  // Navigate turns
  // Navigate turns
  const handleNextTurn = async () => {
    if (characters.length === 0) return;
    
    // Clear the ready state for the character whose turn is ending
    const currentCharacter = characters[currentTurnIndex];
    
    if (currentCharacter && !currentCharacter.isEnemy) {
      // Only clear ready state for non-enemies
      
      // Record that we're updating this character's ready state
      lastReadyUpdateRef.current[currentCharacter.name] = Date.now();
      
      // First update the character sheet file with explicit "no" state
      try {
        await fetch(`${API_BASE_URL}/api/clear_ready/${encodeURIComponent(currentCharacter.name)}`, {
          method: 'POST'
        });
        
        // After file is updated, update context to match
        clearReady(currentCharacter.name);
      } catch (error) {
        console.error(`Error clearing ready state in file for ${currentCharacter.name}:`, error);
        // Still update context even if file update fails
        clearReady(currentCharacter.name);
      }
    }
    
    const nextIndex = (currentTurnIndex + 1) % characters.length;
    setCurrentTurnIndex(nextIndex);
    
    // Increment round when we loop back to the first character
    const newRound = nextIndex === 0 ? roundNumber + 1 : roundNumber;
    if (nextIndex === 0) {
      setRoundNumber(newRound);
    }
    
    // Save is triggered automatically by useEffect
  };

  const handlePreviousTurn = () => {
    if (characters.length === 0) return;
    
    const prevIndex = currentTurnIndex === 0 ? characters.length - 1 : currentTurnIndex - 1;
    setCurrentTurnIndex(prevIndex);
    
    // Decrement round when we loop back from the first character
    const newRound = (currentTurnIndex === 0 && roundNumber > 1) ? roundNumber - 1 : roundNumber;
    if (currentTurnIndex === 0 && roundNumber > 1) {
      setRoundNumber(newRound);
    }
    
    // Save is triggered automatically by useEffect
  };

  const handleResetInitiative = () => {
    setCurrentTurnIndex(0);
    setRoundNumber(1);
    // Save is triggered automatically by useEffect
  };

  const handleSortInitiative = () => {
    const sortedCharacters = [...characters].sort((a, b) => b.initiative - a.initiative);
    setCharacters(sortedCharacters);
    saveInitiativeData(sortedCharacters, 0, roundNumber);
    // Reset to first turn after sorting
    setCurrentTurnIndex(0);
  };

  if (isLoading) {
    return <div className={`initiative-tracker loading ${lightMode ? 'light-mode' : ''}`}>Loading initiative data...</div>;
  }

  // Get the active character for drag overlay
  const activeCharacter = activeId 
    ? characters.find(c => c.id === activeId) || availableCharacters.find(c => c.id === activeId)
    : null;

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
        {/* Sidebar with available characters */}
        {showSidebar && (
          <div className="available-characters-sidebar">
            <h3>Available Characters</h3>
            <p className="sidebar-hint">Drag or click to add/remove</p>
            <SortableContext
              items={availableCharacters.map(c => c.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="available-characters-list">
                {availableCharacters.map((char) => {
                  const isInInitiative = characters.some(c => c.name === char.name);
                  return (
                    <DraggableSidebarCharacter
                      key={char.id}
                      character={char}
                      isInInitiative={isInInitiative}
                      onClick={() => handleToggleFromAvailable(char.name)}
                    />
                  );
                })}
                {availableCharacters.length === 0 && (
                  <div className="no-characters">
                    No active characters found
                  </div>
                )}
              </div>
            </SortableContext>
          </div>
        )}

      {/* Main tracker */}
      <div className="initiative-tracker-wrapper">
        <div className="initiative-tracker">
        <div className="tracker-header">
          <h2>⚔️ Initiative Tracker</h2>
          <div className="header-right">
            <button 
              onClick={() => setShowSidebar(!showSidebar)} 
              className="btn-toggle-sidebar"
              title={showSidebar ? "Hide character sidebar" : "Show character sidebar"}
            >
              ☰
            </button>
            <div className="round-counter">
              <span className="round-label">Round:</span>
              <span className="round-number">{roundNumber}</span>
            </div>
            <button onClick={handleSortInitiative} className="btn-sort" title="Sort by initiative (highest to lowest)" disabled={characters.length === 0}>
              ⇅
            </button>
            <button onClick={handleResetInitiative} className="btn-reset-small" title="Reset to Round 1">
              ↺
            </button>
          </div>
        </div>

        <div className="turn-controls-secondary">
          <button onClick={handlePreviousTurn} className="btn-control btn-previous" disabled={characters.length === 0}>
            ← Previous
          </button>
        </div>

      <div className="initiative-list">
          <SortableContext
            items={[...characters.map(c => c.id), 'end-of-round']}
            strategy={verticalListSortingStrategy}
          >
            {characters.map((character, index) => {
              // Check if we should show drop indicator
              const isFromSidebar = activeId && availableCharacters.some(c => c.id === activeId);
              const showDropIndicatorBefore = isFromSidebar && overId === character.id;
              
              // Check if character is ready from context
              const isCharacterReady = isReady(character.name);
              
              return (
                <SortableInitiativeItem
                  key={character.id}
                  character={character}
                  index={index}
                  isCurrentTurn={index === currentTurnIndex}
                  onUpdate={handleUpdate}
                  onRemove={handleRemove}
                  onToggleEnemy={handleToggleEnemy}
                  onUpdateManualHp={handleUpdateManualHp}
                  showDropIndicatorBefore={showDropIndicatorBefore}
                  showDropIndicatorAfter={false}
                  characters={characters}
                  pcStats={pcStats}
                  isReady={isCharacterReady}
                />
              );
            })}
            
            {/* End of Round marker - sortable drop target */}
            <EndOfRoundMarker 
              showDropIndicatorBefore={activeId && availableCharacters.some(c => c.id === activeId) && overId === 'end-of-round'}
              characters={characters}
            />
          </SortableContext>

        {characters.length === 0 && (
          <div className="empty-state">
            No characters in initiative. Add some below!
          </div>
        )}
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
          <button onClick={handleAddCharacter} className="btn-add">
            + Add
          </button>
        </div>
      </div>
      </div>

        {/* Vertical Next Turn Button */}
        <button 
          onClick={handleNextTurn} 
          className="btn-next-vertical" 
          disabled={characters.length === 0}
          title="Next Turn"
        >
          <span className="next-turn-text">
            N<br/>E<br/>X<br/>T<br/><br/>T<br/>U<br/>R<br/>N
          </span>
          <span className="next-turn-arrow">↓</span>
        </button>
      </div>
      
      <DragOverlay>
        {activeCharacter ? (
          <div className="drag-overlay-item">
            <span className="character-icon">👤</span>
            <span className="character-name">{activeCharacter.name}</span>
            {activeCharacter.initiative !== undefined && (
              <span className="character-initiative">{activeCharacter.initiative}</span>
            )}
          </div>
        ) : null}
      </DragOverlay>
      </DndContext>
    </div>
  );
}

export default InitiativeTracker;
