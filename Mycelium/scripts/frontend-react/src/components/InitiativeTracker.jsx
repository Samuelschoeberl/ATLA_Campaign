import React, { useState, useEffect } from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragOverlay } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { API_BASE_URL } from '../config/api';
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
function SortableInitiativeItem({ character, index, isCurrentTurn, onUpdate, onRemove, showDropIndicatorBefore, showDropIndicatorAfter, characters }) {
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
        className={`initiative-item ${isCurrentTurn ? 'current-turn' : ''} ${isDragging ? 'dragging' : ''}`}
      >
      <div className="drag-handle" {...attributes} {...listeners}>
        ⋮⋮
      </div>
      
      <div className="character-fields">
        <input
          type="text"
          value={character.name}
          onChange={handleNameChange}
          className="editable-field name-field"
          placeholder="Character name"
        />
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
  const [showSidebar, setShowSidebar] = useState(true);

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
  }, [filePath]);

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
      
      // Parse markdown table
      const lines = content.split('\n').filter(line => line.trim());
      const dataLines = lines.slice(2); // Skip header and separator
      
      const parsedCharacters = dataLines
        .filter(line => line.includes('|') && !line.includes('Last generated'))
        .map((line, index) => {
          const parts = line.split('|').map(p => p.trim()).filter(p => p);
          if (parts.length >= 2 && parts[0] !== 'End of Round') {
            return {
              id: `char-${index}-${Date.now()}`,
              name: parts[0],
              initiative: parseInt(parts[1]) || 0,
            };
          }
          return null;
        })
        .filter(char => char !== null);

      setCharacters(parsedCharacters);
      setIsLoading(false);
    } catch (error) {
      console.error('Error loading initiative data:', error);
      setIsLoading(false);
    }
  };

  // Save initiative data to file
  const saveInitiativeData = async (updatedCharacters) => {
    const tableHeader = '| Character | Initiative |\n| --------- | ---------: |';
    const tableRows = updatedCharacters
      .map(char => `| ${char.name} | ${char.initiative} |`)
      .join('\n');
    const endMarker = '\n| End of Round | 0 |';
    const footer = '\n\n_Last generated by Mycelium/scripts/Python/generate_initiative.py_';
    const content = `${tableHeader}\n${tableRows}${endMarker}${footer}`;

    try {
      await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
    } catch (error) {
      console.error('Error saving initiative data:', error);
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
  const handleNextTurn = () => {
    if (characters.length === 0) return;
    
    const nextIndex = (currentTurnIndex + 1) % characters.length;
    setCurrentTurnIndex(nextIndex);
    
    // Increment round when we loop back to the first character
    if (nextIndex === 0) {
      setRoundNumber(roundNumber + 1);
    }
  };

  const handlePreviousTurn = () => {
    if (characters.length === 0) return;
    
    const prevIndex = currentTurnIndex === 0 ? characters.length - 1 : currentTurnIndex - 1;
    setCurrentTurnIndex(prevIndex);
    
    // Decrement round when we loop back from the first character
    if (currentTurnIndex === 0 && roundNumber > 1) {
      setRoundNumber(roundNumber - 1);
    }
  };

  const handleResetInitiative = () => {
    setCurrentTurnIndex(0);
    setRoundNumber(1);
  };

  const handleSortInitiative = () => {
    const sortedCharacters = [...characters].sort((a, b) => b.initiative - a.initiative);
    setCharacters(sortedCharacters);
    saveInitiativeData(sortedCharacters);
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
              
              return (
                <SortableInitiativeItem
                  key={character.id}
                  character={character}
                  index={index}
                  isCurrentTurn={index === currentTurnIndex}
                  onUpdate={handleUpdate}
                  onRemove={handleRemove}
                  showDropIndicatorBefore={showDropIndicatorBefore}
                  showDropIndicatorAfter={false}
                  characters={characters}
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
