import React, { useState, useEffect, useRef } from 'react';
import { hexToRgba } from '../utils/colorUtils';
import './CharacterSheet.css';
import { API_BASE_URL } from '../config/api';
import StressLevel from './StressLevel';
import BendingMove from './BendingMove';
import ShapeshiftingForm from './ShapeshiftingForm';
import { useReadyState } from '../context/ReadyStateContext';

const CONDITION_NAMES = [
  'Bleeding out',
  'Blinded',
  'Immobilised',
  'Paralysed',
  'Prone',
  'Slowed'];

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

const ACTION_COLORS = {
  'Action': '#3498db',
  'Bonus Action': '#9b59b6',
  'Reaction': '#e67e22',
  'Danger Sense Reaction': '#e74c3c'
};

const parseCurrentMaxValue = (value) => {
  if (value === undefined || value === null) {
    return { current: 0, max: 0, hasValue: false };
  }
  const str = String(value).trim();
  const slashMatch = str.match(/^(\d+)\s*\/\s*(\d+)$/);
  if (slashMatch) {
    return {
      current: parseInt(slashMatch[1]) || 0,
      max: parseInt(slashMatch[2]) || 0,
      hasValue: true
    };
  }
  const num = parseInt(str);
  if (!isNaN(num)) {
    return { current: num, max: num, hasValue: true };
  }
  return { current: 0, max: 0, hasValue: false };
};

// Dice roller utility
const rollDice = (diceString) => {
  try {
    // Parse dice notation like "1d20", "2d6", etc.
    const diceRegex = /(\d+)d(\d+)/gi;
    let expression = diceString.trim();
    let rolls = [];
    let modifierParts = [];
    
    // Store original expression for extracting modifiers
    const originalExpression = expression;
    
    // Replace each dice notation with its roll result
    expression = expression.replace(diceRegex, (match, count, sides) => {
      const numDice = parseInt(count);
      const numSides = parseInt(sides);
      let total = 0;
      let individualRolls = [];
      
      for (let i = 0; i < numDice; i++) {
        const roll = Math.floor(Math.random() * numSides) + 1;
        individualRolls.push(roll);
        total += roll;
      }
      
      rolls.push({ dice: match, rolls: individualRolls, total });
      return `(${total})`;
    });
    
    // Extract modifiers (everything that's not dice notation)
    const modifierString = originalExpression.replace(diceRegex, '').trim();
    if (modifierString) {
      // Split by + and - while keeping the operators
      const parts = modifierString.split(/([+\-])/).filter(p => p.trim());
      let currentModifier = '';
      for (let i = 0; i < parts.length; i++) {
        const part = parts[i].trim();
        if (part === '+' || part === '-') {
          currentModifier = part;
        } else if (part) {
          const value = parseInt(part);
          if (!isNaN(value)) {
            modifierParts.push({ operator: currentModifier || '+', value });
            currentModifier = '';
          }
        }
      }
    }
    
    // Clean the expression - keep only valid math characters
    expression = expression.replace(/\s+/g, ''); // Remove whitespace
    expression = expression.replace(/[^0-9+\-*/().]/g, ''); // Keep only math chars
    
    // Safely evaluate the mathematical expression
    const result = Function('"use strict"; return (' + expression + ')')();
    
    return { result, rolls, modifiers: modifierParts, original: diceString };
  } catch (error) {
    console.error('Error rolling dice:', error, 'Expression:', expression);
    return null;
  }
};

// Component to render clickable dice rolls
const DiceRollText = ({ text }) => {
  const [rollResult, setRollResult] = useState(null);
  const [showPopup, setShowPopup] = useState(false);
  const [popupPosition, setPopupPosition] = useState({ top: 0, left: 0 });
  const spanRef = useRef(null);
  
  // Check if text contains dice notation
  const hasDiceNotation = /\d+d\d+/i.test(text);
  
  if (!hasDiceNotation) {
    return <span>{text}</span>;
  }
  
  const handleRoll = (e) => {
    const result = rollDice(text);
    if (result && spanRef.current) {
      const rect = spanRef.current.getBoundingClientRect();
      setPopupPosition({
        top: rect.bottom + window.scrollY + 5,
        left: rect.left + window.scrollX + (rect.width / 2)
      });
      setRollResult(result);
      setShowPopup(true);
      
      // Auto-hide popup after 3 seconds
      setTimeout(() => setShowPopup(false), 3000);
    }
  };
  
  return (
    <>
      <span
        ref={spanRef}
        onClick={handleRoll}
        style={{
          cursor: 'pointer',
          color: '#3498db',
          textDecoration: 'underline',
          fontWeight: '500'
        }}
        title="Click to roll"
      >
        {text}
      </span>
      {showPopup && rollResult && (
        <div
          style={{
            position: 'absolute',
            top: `${popupPosition.top}px`,
            left: `${popupPosition.left}px`,
            transform: 'translateX(-50%)',
            padding: '15px 20px',
            backgroundColor: '#2c3e50',
            color: '#ecf0f1',
            borderRadius: '8px',
            boxShadow: '0 8px 16px rgba(0,0,0,0.4)',
            zIndex: 9999,
            minWidth: '150px',
            textAlign: 'center',
            fontSize: '14px',
            whiteSpace: 'nowrap',
            border: '2px solid #3498db',
            pointerEvents: 'none'
          }}
        >
          <div style={{ fontWeight: 'bold', fontSize: '20px', marginBottom: '8px', color: '#3498db' }}>
            {rollResult.result}
          </div>
          <div style={{ fontSize: '13px', color: '#ecf0f1', marginBottom: '5px' }}>
            {rollResult.rolls.map((r, idx) => (
              <span key={idx}>
                {idx > 0 && ' + '}
                {r.dice}: [{r.rolls.join(', ')}] = {r.total}
              </span>
            ))}
            {rollResult.modifiers && rollResult.modifiers.length > 0 && (
              <>
                {rollResult.modifiers.map((m, idx) => (
                  <span key={`mod-${idx}`}>
                    {' '}{m.operator} {m.value}
                  </span>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
};const CharacterSheet = ({ file, lightMode = false }) => {
  const [content, setContent] = useState('');
  const [characterData, setCharacterData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [vitalsCollapsed, setVitalsCollapsed] = useState(false);
  const [conditionsCollapsed, setConditionsCollapsed] = useState(true);
  const [stressLevelCollapsed, setStressLevelCollapsed] = useState(true);
  const [coreStatsCollapsed, setCoreStatsCollapsed] = useState(true);
  const [bendingLevelsCollapsed, setBendingLevelsCollapsed] = useState(true);
  const [defenseCollapsed, setDefenseCollapsed] = useState(true);
  const [resourcesCollapsed, setResourcesCollapsed] = useState(false);
  const [bonusResourcesCollapsed, setBonusResourcesCollapsed] = useState(true);
  const [pinnedMovesCollapsed, setPinnedMovesCollapsed] = useState(true);
  const [conditionDescriptions, setConditionDescriptions] = useState({});
  const [movesByType, setMovesByType] = useState({ action: [], bonus: [], reaction: [], danger: [] });
  const [movesLoading, setMovesLoading] = useState(false);
  const [movesError, setMovesError] = useState(null);
  const [showReactionsModal, setShowReactionsModal] = useState(false);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [pinnedMoves, setPinnedMoves] = useState([]);
  const [movesLoadedFor, setMovesLoadedFor] = useState(null);
  const [expandedMoves, setExpandedMoves] = useState(new Set());
  const saveTimeoutRef = useRef(null);
  const initialLoadRef = useRef(true);
  const lastReadyUpdateRef = useRef(0); // Track last ready update timestamp
  
  // Ready state from context
  const { setReady, isReady } = useReadyState();

  // Stat calculation tooltips - based on game mechanics from recreate_pcs.py and rule definitions
  const statTooltips = {
    // Vitals
    current_hp:
      "Current hit points - editable during play. Restore to max on short rest.",
    max_hp: "Maximum HP = (Rolled HP + (CON × Character Level)) × 2",
    rolled_hp: "HP from rolling hit dice during character creation",
    "rolled.hp": "HP from rolling hit dice during character creation",
    Initiative:
      "Initiative roll = 1d20 + DEX (determines turn order in combat)",
    Evasion: "Evasion AC = 10 + DEX + Air level (defense against attacks)",
    Movement: "Movement per round = 5 meters + (Air level × 3)",
    cl: "Character Level = Air + Water + Earth + Fire + Spirit levels",

    // Core Stats
    Strength: "Physical power - affects Earth bending and melee attacks",
    Dexterity:
      "Agility and reflexes - affects Air/Fire bending, Initiative, and Evasion",
    Constitution: "Endurance - affects HP and concentration saves",
    Intelligence:
      "Mental acuity - affects Water bending and tactical abilities",
    Wisdom: "Awareness and insight - affects Fire/Spirit bending",
    Charisma: "Force of personality - affects social interactions",
    Str: "Physical power - affects Earth bending and melee attacks",
    Dex: "Agility and reflexes - affects Air/Fire bending, Initiative, and Evasion",
    Con: "Endurance - affects HP and concentration saves",
    Int: "Mental acuity - affects Water bending and tactical abilities",
    Wis: "Awareness and insight - affects Fire/Spirit bending",
    Cha: "Force of personality - affects social interactions",

    // Defensive Stats
    "Physical Armor": "Reduces piercing, slashing, and bludgeoning damage",
    "General Armor":
      "Base = Earth level. Reduces ALL damage except Spirit damage",
    "Spirit Armor": "Spirit Armor = Spirit level (reduces spirit damage)",
    "Fire Armor": "Fire Armor = Water level (reduces fire damage)",
    "Ice Armor": "Ice Armor = Fire level + Stress level (reduces ice damage)",
    "Barrier":
      "Armor that halves at first unblocked damage, destroyed on second. Applied before other armor.",

    // Bending Stats (Attack Rolls)
    "Air Attack Roll": "1d20 + Air level + DEX",
    "Water Attack Roll": "1d20 + Water level + INT",
    "Earth Attack Roll": "1d20 + Earth level + STR",
    "Fire Attack Roll": "1d20 + Fire level + WIS",
    "Spirit Attack Roll": "1d20 + Spirit level + WIS",

    // Bending Stats (DCs)
    "Airbending DC": "Air level + DEX (target must beat this to resist)",
    "Waterbending DC": "Water level + INT (target must beat this to resist)",
    "Earthbending DC": "Earth level + STR (target must beat this to resist)",
    "Firebending DC": "Fire level + WIS (target must beat this to resist)",
    "Spiritbending DC": "Spirit level + WIS (target must beat this to resist)",

    // Slots and Charges
    "Airbending slot":
      "3 × Air level. Restored on short rest. Max half can be spent per move.",
    "Waterbending slot":
      "3 × Water level. Restored on short rest. Max half can be spent per move.",
    "Earthbending slot":
      "3 × Earth level. Restored on short rest. Max half can be spent per move.",
    Firebending_slot:
      "3 × Fire level. Restored on short rest. Max half can be spent per move.",
    "Firebending slot":
      "3 × Fire level. Restored on short rest. Max half can be spent per move.",
    "Bonus bending slots":
      "Temporary bending slots granted by effects like Shapeshifting; track separately from base slots.",
    "Spirit bending slot":
      "Spirit level. Restored on short rest. Max half can be spent per move.",
    "spiritbending slot":
      "Spirit level. Restored on short rest. Max half can be spent per move.",
    Water_charge:
      "Total = Waterbottle Charge + Environmental Water Charge. Max 2× Water level per move.",
    "Waterbottle Charge": "2 × Water level (personal water supply, refillable)",
    "Bonus water charges":
      "Extra water charges granted by moves or effects; add on top of personal/environmental water.",
    "Environmental water charge":
      "Environmental water available - varies by location and context",
    "Danger Sense Reaction":
      "Special danger sense reactions available. Restored on rest.",
    "Danger Sense Reaction Slot":
      "Special danger sense reactions available. Restored on rest.",
    "stress level":
      "Per level: -1 Fire Attack Roll, -1 Firebending DC, +2 fire damage, +1 Ice Armor. \nGain 1: taking damage or using firebending slot on damaging move. \nLose 1: each turn end or certain moves.",
    chaos_energy:
      "Chaos energy points (base 0). Tell DM if exceeds Spirit level.",
    "Fire Damage Bonus":
      "Fire Damage Bonus = Stress level (added to fire attacks)",

    // Element Levels
    air: "Air bending level - affects Air moves, movement speed, and Evasion",
    water: "Water bending level - affects Water moves and Fire Armor",
    earth: "Earth bending level - affects Earth moves and General Armor",
    fire: "Fire bending level - affects Fire moves and Ice Armor",
    spirit: "Spirit bending level - affects Spirit moves and abilities",
    Air: "Air bending level - affects Air moves, movement speed, and Evasion",
    Water: "Water bending level - affects Water moves and Fire Armor",
    Earth: "Earth bending level - affects Earth moves and General Armor",
    Fire: "Fire bending level - affects Fire moves and Ice Armor",
    Spirit: "Spirit bending level - affects Spirit moves and abilities",

    // Concentration
    Concentration:
      "CON save DC = max(10, Damage Taken ÷ 2) to maintain concentration when damaged",
  };

  // Helper function to get tooltip for a stat
  const getStatTooltip = (statName) => {
    // First try exact match
    if (statTooltips[statName]) {
      return statTooltips[statName];
    }
    
    // Try normalized whitespace
    const normalized = statName.replace(/\s+/g, ' ').trim();
    if (statTooltips[normalized]) {
      return statTooltips[normalized];
    }
    
    // Try case-insensitive match
    const lowerStat = statName.toLowerCase();
    for (const [key, value] of Object.entries(statTooltips)) {
      if (key.toLowerCase() === lowerStat) {
        return value;
      }
    }
    
    return null;
  };

  // Helper function to detect element from consumable name
const getElementFromName = (name) => {
  const lowerName = name.toLowerCase();
  if (lowerName.includes('fire')) return 'fire';
  if (lowerName.includes('water')) return 'water';
  if (lowerName.includes('air')) return 'air';
  if (lowerName.includes('spirit')) return 'spirit';
  if (lowerName.includes('earth')) return 'earth';
  return null;
};

// Helper function to get color for slot name
const getSlotColor = (slotText) => {
  const element = getElementFromName(slotText);
  return element ? ELEMENT_COLORS[element] : null;
};

// Helper function to get colors for a move (consistent logic everywhere)
const getMoveColors = (move) => {
  const actionColor = ACTION_COLORS[move.actionType] || '#3498db';
  // Always use element color for border if available, otherwise default gray
  const elementColor = move.element ? (ELEMENT_COLORS[move.element] || '#95a5a6') : '#95a5a6';
  
  return { actionColor, elementColor };
};

// Helpers for bending move summaries
const getCharacterNameFromPath = (path) => {
  if (!path) return null;
  const normalized = path.replace(/^Player Root\//i, '');
  const match = normalized.match(/PCs\/([^/]+)/i);
  return match ? match[1] : null;
};

const prettifyMoveName = (name, characterName) => {
  if (!name) return '';
  let pretty = name.replace(/\.md$/i, '');
  if (characterName) {
    const suffix = new RegExp(`\\s*-\\s*${characterName}$`, 'i');
    pretty = pretty.replace(suffix, '');
  }
  return pretty.replace(/_/g, ' ').trim();
};

const detectElementFromContent = (content, fallback, path = '') => {
  // Only use element tags from content
  // Match #fire, #water, #air, #earth, #spirit with optional suffix (like _Anju, bending, etc)
  // Remove \b word boundary since we want to match #water_Anju, #waterbending, etc.
  const tagMatch = content.match(/#(fire|water|air|earth|spirit)/i);
  
  // Debug logging
  if (!tagMatch) {
    const allTags = content?.match(/#\w+/g);
    console.log('detectElementFromContent NO MATCH:', { 
      allTags: allTags?.slice(0, 10),
      firstLine: content?.split('\n')[0],
      first200chars: content?.substring(0, 200)
    });
  }
  
  if (tagMatch) return tagMatch[1].toLowerCase();
  
  // If no tag found, return null (don't use fallback or path)
  return null;
};

const detectLevelFromContent = (content, tags = []) => {
  for (const tag of tags) {
    const tagMatch = tag.match(/level[_-]?(\d+)/i);
    if (tagMatch) return parseInt(tagMatch[1]);
  }
  const inlineTag = content.match(/#level[_-]?(\d+)/i);
  if (inlineTag) return parseInt(inlineTag[1]);
  const inline = content.match(/level\s+(\d+)/i);
  if (inline) return parseInt(inline[1]);
  return null;
};

const parseMoveSummary = (content, fallbackElement, actionType, path) => {
  const metadata = {};
  
  // Extract tags and element FIRST before filtering lines
  const tags = [...content.matchAll(/#([A-Za-z0-9_]+)/g)].map((m) => m[1]);
  const element = detectElementFromContent(content, fallbackElement, path);
  const level = detectLevelFromContent(content, tags);
  
  // Parse all metadata fields (key: value patterns) - improved to match BendingMove.jsx
  const lines = content.split('\n');
  const contentLines = lines.filter(line => !line.trim().startsWith('#') || line.trim().startsWith('##'));
  
  let currentMetadataKey = null;
  let currentMetadataValue = [];
  
  for (let i = 0; i < contentLines.length; i++) {
    const line = contentLines[i];
    const trimmedLine = line.trim();
    
    // Skip empty lines
    if (!trimmedLine) {
      // Empty line might end a multi-line metadata value
      if (currentMetadataKey && currentMetadataValue.length > 0) {
        const fullValue = currentMetadataValue.join('\n').trim();
        metadata[currentMetadataKey] = fullValue;
        currentMetadataKey = null;
        currentMetadataValue = [];
      }
      continue;
    }
    
    // Check for special pattern: - [[Key Name]] (value)
    const specialPattern = trimmedLine.match(/^-?\s*\[\[([^\]]+)\]\]\s*\(([^)]+)\)$/);
    if (specialPattern) {
      // Save previous metadata if any
      if (currentMetadataKey && currentMetadataValue.length > 0) {
        let fullValue = currentMetadataValue.join('\n').trim();
        fullValue = fullValue.replace(/^\*+\s*/, '').replace(/\s*\*+$/, '');
        metadata[currentMetadataKey] = fullValue;
      }
      
      // Extract key and value from the special pattern
      const key = specialPattern[1].trim();
      const value = specialPattern[2].trim();
      metadata[key] = value;
      currentMetadataKey = null;
      currentMetadataValue = [];
    } else {
      // Check if this line starts a new metadata field
      // Match pattern: optional "- ", optional "**", key name, optional "**", ":", value
      const metadataMatch = trimmedLine.match(/^-?\s*\*{0,2}([A-Za-z\s]+?)\*{0,2}\s*:\s*(.*)$/);
      
      if (metadataMatch) {
        // Save previous metadata if any
        if (currentMetadataKey && currentMetadataValue.length > 0) {
          let fullValue = currentMetadataValue.join('\n').trim();
          fullValue = fullValue.replace(/^\*+\s*/, '').replace(/\s*\*+$/, '');
          metadata[currentMetadataKey] = fullValue;
        }
        
        // Clean the key: trim and remove any remaining asterisks
        let key = metadataMatch[1].trim().replace(/\*+/g, '');
        // Clean the value: trim and remove leading/trailing asterisks
        let value = metadataMatch[2].trim().replace(/^\*+\s*/, '').replace(/\s*\*+$/, '');
        
        // Start collecting this field
        if (value) {
          // Has content on same line
          currentMetadataKey = key;
          currentMetadataValue = [value];
        } else {
          // No content on same line, will collect from next lines
          currentMetadataKey = key;
          currentMetadataValue = [];
        }
      } else if (currentMetadataKey) {
        // Continuation of previous metadata field (indented content)
        // Clean leading ** from continuation lines
        let cleanedLine = trimmedLine.replace(/^\*+\s*/, '');
        currentMetadataValue.push(cleanedLine);
      }
    }
  }
  
  // Save any pending metadata at the end
  if (currentMetadataKey && currentMetadataValue.length > 0) {
    let fullValue = currentMetadataValue.join('\n').trim();
    fullValue = fullValue.replace(/^\*+\s*/, '').replace(/\s*\*+$/, '');
    metadata[currentMetadataKey] = fullValue;
  }
  
  const slots = [];
  const slotMatches = [...content.matchAll(/\[\[([^\]]*?slot[^\]]*)\]\](?:\s*\(([^)]+)\))?/gi)];
  slotMatches.forEach((m) => {
    const label = m[1]?.trim();
    const amount = m[2]?.trim();
    if (label) {
      slots.push(amount ? `${label} (${amount})` : label);
    }
  });
  
  return {
    metadata, // Store all metadata
    slots,
    tags,
    element,
    level,
    actionType,
    path
  };
};

  // Load condition descriptions from markdown files
  useEffect(() => {
    const loadConditionDescriptions = async () => {
      const descriptions = {};
      const conditionFiles = {
        'Bleeding out': 'Bleeding_out.md',
        'Blinded': 'Blinded.md',
        'Immobilised': 'Immobilised.md',
        'Paralysed': 'Paralysed.md',
        'Prone': 'Prone.md',
        'Slowed': 'Slowed.md',
      };

      for (const [conditionName, fileName] of Object.entries(conditionFiles)) {
        try {
          const url = `${API_BASE_URL}/player_root/Rules/core%20rules/Conditions/${fileName}`;
          const response = await fetch(url, { cache: 'no-store' });
          if (response.ok) {
            const data = await response.json();
            // Extract the description (everything before #condition tag)
            const content = data.content || '';
            const descriptionMatch = content.match(/^([\s\S]*?)(?:\n*#condition|$)/);
            if (descriptionMatch) {
              descriptions[conditionName] = descriptionMatch[1].trim();
            }
          }
        } catch (err) {
          console.error(`Error loading condition ${conditionName}:`, err);
        }
      }
      setConditionDescriptions(descriptions);
    };

    loadConditionDescriptions();
  }, []);

  useEffect(() => {
    if (file) {
      initialLoadRef.current = true;
      loadCharacterSheet();
    }
  }, [file]);

  useEffect(() => {
    const characterName = getCharacterNameFromPath(file?.path);
    if (!characterName) {
      setMovesByType({ action: [], bonus: [], reaction: [], danger: [] });
      setMovesLoadedFor(null);
      return;
    }
    
    if (characterName !== movesLoadedFor) {
      loadBendingMoves(characterName);
    }
  }, [file]);

  // Periodic check for ready state updates every 10 seconds
  useEffect(() => {
    if (!file || !characterData?.name) {
      return;
    }

    const intervalId = setInterval(async () => {
      // Skip if currently saving to avoid race conditions
      if (saving) {
        return;
      }
      
      const now = Date.now();
      const lastUpdate = lastReadyUpdateRef.current;
      const timeSince = now - lastUpdate;
      
      // Skip if we recently updated ready state (within last 3 seconds)
      if (timeSince < 3000) {
        return;
      }

      try {
        const normalizedPath = (file.path || '').replace(/^Player Root\//i, '');
        const segments = normalizedPath.split('/').map(s => encodeURIComponent(s)).join('/');
        const url = `${API_BASE_URL}/player_root/${segments}`;
        
        const response = await fetch(url, { cache: 'no-store' });
        if (response.ok) {
          const data = await response.json();
          const content = data.content || '';
          
          // Parse only the ready state from Vitals section
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
                const currentState = isReady(characterData.name);
                // Only update if different from current state
                if (currentState !== isReadyFromFile) {
                  setReady(characterData.name, isReadyFromFile);
                }
              }
              break;
            }
          }
        }
      } catch (error) {
        console.error('Error checking ready state:', error);
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(intervalId);
  }, [file, characterData?.name, isReady, setReady, saving]);

  // Auto-save effect with debouncing
  useEffect(() => {
    // Skip auto-save on initial load
    if (initialLoadRef.current) {
      initialLoadRef.current = false;
      return;
    }

    // Skip if no character data
    if (!characterData) {
      return;
    }

    // Clear any existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Set new timeout to save after 1 second of no changes
    saveTimeoutRef.current = setTimeout(() => {
      handleSave();
    }, 1000);

    // Cleanup timeout on unmount
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [characterData]);

  const loadCharacterSheet = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Remove "Player Root/" prefix if present
      const normalizedPath = (file.path || '').replace(/^Player Root\//i, '');
      const segments = normalizedPath.split('/').map(s => encodeURIComponent(s)).join('/');
      const url = `${API_BASE_URL}/player_root/${segments}`;
      
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to fetch file: ${response.status}`);
      }
      
      const data = await response.json();
      setContent(data.content || '');
      
      // Parse character sheet
      const parsedData = parseCharacterSheet(data.content || '');
      
      // Update ready state from the parsed vitals
      if (parsedData.vitals.ready) {
        const isReadyFromFile = parsedData.vitals.ready.toLowerCase() === 'yes';
        setReady(parsedData.name, isReadyFromFile);
        // Remove ready from vitals since it's stored in context
        delete parsedData.vitals.ready;
      }
      
      // Fetch environmental water charge from global file
      try {
        const envResponse = await fetch(`${API_BASE_URL}/api/environmental_variable/environmental_water_charge`);
        if (envResponse.ok) {
          const envData = await envResponse.json();
          
          // Remove any existing environmental water charge from consumables
          parsedData.consumables = parsedData.consumables.filter(
            c => c.name !== 'Environmental water charge'
          );
          
          // Add the global environmental water charge
          parsedData.consumables.push({
            name: 'Environmental water charge',
            max: envData.max,
            current: envData.current,
            type: 'environmental',
            isGlobal: true // Mark as global so we know to save it differently
          });
          
          // Also update waterCharges for serialization compatibility
          parsedData.waterCharges['Environmental water charge'] = `${envData.current}/${envData.max}`;
        }
      } catch (envErr) {
        console.error('Error loading environmental water charge:', envErr);
      }
      
      setCharacterData(parsedData);
    } catch (err) {
      setError(err.message);
      console.error('Error loading character sheet:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadBendingMoves = async (characterName) => {
    if (!characterName) {
      setMovesByType({ action: [], bonus: [], reaction: [], danger: [] });
      return;
    }
    
    try {
      setMovesLoading(true);
      setMovesError(null);
      const basePath = `PCs/${characterName}/Bending Rules - ${characterName}/by Action Type`;
      const typeFolders = {
        action: 'Action',
        bonus: 'Bonus Action',
        reaction: 'Reaction',
        danger: 'Danger Sense Reaction'
      };
      
      const aggregated = { action: [], bonus: [], reaction: [], danger: [] };
      
      for (const [key, folderName] of Object.entries(typeFolders)) {
        const folderPath = `${basePath}/${folderName}`;
        try {
          const listResp = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(folderPath)}`);
          if (!listResp.ok) continue;
          const listData = await listResp.json();
          const files = (listData.entries || []).filter(entry => (entry.type || '').toLowerCase().includes('file'));
          
          for (const fileEntry of files) {
            const fullPath = `${folderPath}/${fileEntry.name}`;
            try {
              const fileResp = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(fullPath)}`);
              if (!fileResp.ok) continue;
              const fileData = await fileResp.json();
              const summary = parseMoveSummary(
                fileData.content || '',
                getElementFromName(fileEntry.name),
                folderName,
                fullPath
              );
              aggregated[key].push({
                ...summary,
                name: prettifyMoveName(fileEntry.name, characterName),
                path: fullPath
              });
            } catch (err) {
              console.error('Error loading bending move file:', err);
            }
          }
        } catch (err) {
          console.error('Error loading bending moves folder:', err);
        }
      }
      
      setMovesByType(aggregated);
      setMovesLoadedFor(characterName);
      
      // Sort by level then name for each bucket
      Object.keys(aggregated).forEach(key => {
        aggregated[key].sort((a, b) => {
          const levelA = a.level ?? 999;
          const levelB = b.level ?? 999;
          if (levelA !== levelB) return levelA - levelB;
          return a.name.localeCompare(b.name);
        });
      });
    } catch (err) {
      setMovesError('Could not load bending moves');
    } finally {
      setMovesLoading(false);
    }
  };

  const parseCharacterSheet = (markdown) => {
    const data = {
      name: '',
      vitals: {},
      coreStats: {},
      bending: { totalLevel: 0, elements: [] },
      defense: {},
      slots: {},
      waterCharges: {},
      consumables: [],
      conditions: {}
    };

    // Extract character name
    const nameMatch = markdown.match(/^Name:\s*(.+)$/m);
    if (nameMatch) {
      data.name = nameMatch[1].trim();
    }

    // Parse vitals table
    const vitalsMatch = markdown.match(/## Vitals\s*\n\n([\s\S]*?)\n\n##/);
    if (vitalsMatch) {
      const tableContent = vitalsMatch[1];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'key') {
          data.vitals[cells[0]] = cells[1];
        }
      });
    }

    // Parse core stats table
    const statsMatch = markdown.match(/## Core Stats\s*\n\n([\s\S]*?)\n\n##/);
    if (statsMatch) {
      const tableContent = statsMatch[1];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'Stat') {
          data.coreStats[cells[0]] = parseInt(cells[1]) || 0;
        }
      });
    }

    // Parse bending levels
    const bendingMatch = markdown.match(/## Bending Levels\s*\n\nTotal Bending Level:\s*(\d+)\s*\n\n([\s\S]*?)\n\n##/);
    if (bendingMatch) {
      data.bending.totalLevel = parseInt(bendingMatch[1]) || 0;
      const tableContent = bendingMatch[2];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'Element') {
          data.bending.elements.push({
            element: cells[0],
            level: parseInt(cells[1]) || 0,
            attackRoll: cells[2] || '',
            dc: cells[3] || ''
          });
        }
      });
    }

    // Parse defensive stats
    const defenseMatch = markdown.match(/## Defensive\s*\n\n([\s\S]*?)\n\n##/);
    if (defenseMatch) {
      const tableContent = defenseMatch[1];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'key') {
          data.defense[cells[0]] = parseInt(cells[1]) || 0;
        }
      });
    }

    // Parse bending slots
    const slotsMatch = markdown.match(/## Bending Slots\s*\n[\s\S]*?\n\n([\s\S]*?)\n\n##/);
    if (slotsMatch) {
      const tableContent = slotsMatch[1];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        // Skip rows that only contain <details> tags (bonus slots)
        if (row.includes('<details>') && row.includes('</details>')) {
          // Extract bonus slot info from <details><summary>Name</summary>value</details>
          const detailsMatch = row.match(/<details><summary>(.*?)<\/summary>(.*?)<\/details>/);
          if (detailsMatch) {
            const slotName = detailsMatch[1].trim();
            const slotValue = detailsMatch[2].trim();
            data.slots[slotName] = slotValue;
          }
          return;
        }
        
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'Slot') {
          const slotName = cells[0];
          const slotValue = cells[1];
          data.slots[slotName] = slotValue;
        }
      });
    }

    // Parse water charges
    const waterMatch = markdown.match(/## Water charges\s*\n[\s\S]*?\n\n([\s\S]*?)(?:\n\n#|$)/);
    if (waterMatch) {
      const tableContent = waterMatch[1];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        // Skip rows that only contain <details> tags (bonus charges)
        if (row.includes('<details>') && row.includes('</details>')) {
          // Extract bonus charge info from <details><summary>Name</summary>value</details>
          const detailsMatch = row.match(/<details><summary>(.*?)<\/summary>(.*?)<\/details>/);
          if (detailsMatch) {
            const chargeName = detailsMatch[1].trim();
            const chargeValue = detailsMatch[2].trim();
            data.waterCharges[chargeName] = chargeValue;
          }
          return;
        }
        
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'Water charge type') {
          const chargeName = cells[0];
          const chargeValue = cells[1];
          data.waterCharges[chargeName] = chargeValue;
        }
      });
    }

    // Ensure bonus slots/charges exist even if zero so the UI can display and edit them
    if (data.slots['Bonus air slots'] === undefined) {
      data.slots['Bonus air slots'] = '0';
    }
    if (data.slots['Bonus earth slots'] === undefined) {
      data.slots['Bonus earth slots'] = '0';
    }
    if (data.slots['Bonus fire slots'] === undefined) {
      data.slots['Bonus fire slots'] = '0';
    }
    if (data.slots['Bonus spirit slots'] === undefined) {
      data.slots['Bonus spirit slots'] = '0';
    }
    if (data.waterCharges['Bonus water charges'] === undefined) {
      data.waterCharges['Bonus water charges'] = '0';
    }

    // Default conditions to false
    CONDITION_NAMES.forEach(name => {
      data.conditions[name] = false;
    });

    // Parse conditions table if present
    const conditionsMatch = markdown.match(/## Conditions\s*\n\n([\s\S]*?)(?:\n\n##|\n#|$)/);
    if (conditionsMatch) {
      const tableContent = conditionsMatch[1];
      const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
      rows.forEach(row => {
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'Condition') {
          const conditionName = cells[0];
          const activeRaw = cells[1].toLowerCase();
          const isActive = ['yes', 'true', '1', 'active', 'x', 'y'].includes(activeRaw);
          if (data.conditions.hasOwnProperty(conditionName)) {
            data.conditions[conditionName] = isActive;
          }
        }
      });
    }

    // Extract consumable resources from slots (those that are numeric and can be tracked)
    // EXCLUDE bonus slots - they're shown separately in the bonus resources section
    const bonusSlotNames = ['Bonus air slots', 'Bonus earth slots', 'Bonus fire slots', 'Bonus spirit slots', 'Bonus bending slots'];
    
    Object.entries(data.slots).forEach(([key, value]) => {
      // Skip bonus slots - they're displayed separately
      if (bonusSlotNames.includes(key)) {
        return;
      }
      
      // Check if value is in "current/max" format
      const slashMatch = String(value).match(/^(\d+)\s*\/\s*(\d+)$/);
      if (slashMatch) {
        const current = parseInt(slashMatch[1]);
        const max = parseInt(slashMatch[2]);
        data.consumables.push({
          name: key,
          max: max,
          current: current,
          type: 'slot'
        });
      } else {
        // Single number format - treat as max value with full current
        const numValue = parseInt(value);
        if (!isNaN(numValue) && numValue > 0) {
          data.consumables.push({
            name: key,
            max: numValue,
            current: numValue,
            type: 'slot'
          });
        }
      }
    });

    // Add water charges as consumables too (except Environmental water charge and Bonus water charges)
    Object.entries(data.waterCharges).forEach(([key, value]) => {
      // Skip Environmental water charge - it will be loaded from global file
      // Skip Bonus water charges - it's displayed separately in bonus resources
      if (key === 'Environmental water charge' || key === 'Bonus water charges') {
        return;
      }
      
      // Check if value is in "current/max" format
      const slashMatch = String(value).match(/^(\d+)\s*\/\s*(\d+)$/);
      if (slashMatch) {
        const current = parseInt(slashMatch[1]);
        const max = parseInt(slashMatch[2]);
        data.consumables.push({
          name: key,
          max: max,
          current: current,
          type: 'water'
        });
      } else {
        // Single number format - treat as max value with full current
        const numValue = parseInt(value);
        if (!isNaN(numValue) && numValue > 0) {
          data.consumables.push({
            name: key,
            max: numValue,
            current: numValue,
            type: 'water'
          });
        }
      }
    });

    return data;
  };

  const serializeCharacterSheet = (data, overrideReadyState = null) => {
    let markdown = `Name: ${data.name}\n`;
    markdown += `## Vitals\n\n\n\n`;
    markdown += `| key               |                 value |\n`;
    markdown += `| ----------------- | --------------------: |\n`;
    Object.entries(data.vitals).forEach(([key, value]) => {
      markdown += `| ${key.padEnd(17)} | ${String(value).padStart(21)} |\n`;
    });
    
    // Add ready state as a vitals field
    // Use override if provided, otherwise check context
    const actualReadyState = overrideReadyState !== null ? overrideReadyState : isReady(data.name);
    const readyValue = actualReadyState ? 'yes' : 'no';
    markdown += `| ${'ready'.padEnd(17)} | ${readyValue.padStart(21)} |\n`;

    markdown += `\n## Core Stats\n\n`;
    markdown += `| Stat         |   Value |\n`;
    markdown += `| ------------ | ------: |\n`;
    Object.entries(data.coreStats).forEach(([key, value]) => {
      markdown += `| ${key.padEnd(12)} | ${String(value).padStart(7)} |\n`;
    });

    markdown += `\n## Bending Levels\n\n`;
    markdown += `Total Bending Level: ${data.bending.totalLevel}\n\n`;
    markdown += `| Element |      Level | Attack Roll            | DC                   |\n`;
    markdown += `| ------- | ---------: | ---------------------- | -------------------- |\n`;
    data.bending.elements.forEach(el => {
      markdown += `| ${el.element.padEnd(7)} | ${String(el.level).padStart(10)} | ${el.attackRoll.padEnd(22)} | ${el.dc.padEnd(20)} |\n`;
    });

    markdown += `\n## Defensive\n\n`;
    markdown += `| key            |               Base |\n`;
    markdown += `| -------------- | -----------------: |\n`;
    Object.entries(data.defense).forEach(([key, value]) => {
      markdown += `| ${key.padEnd(14)} | ${String(value).padStart(18)} |\n`;
    });

    // Conditions - Bleeding out is auto-set from HP
    markdown += `\n\n## Conditions\n\n`;
    markdown += `| Condition     | Active |\n`;
    markdown += `| ------------- | :----: |\n`;
    CONDITION_NAMES.forEach(name => {
      const isBleeding = name === 'Bleeding out' && (parseFloat(data.vitals.current_hp) || 0) <= 0 && (parseFloat(data.vitals.max_hp) || 0) > 0;
      const active = name === 'Bleeding out' ? isBleeding : !!data.conditions[name];
      markdown += `| ${name.padEnd(13)} | ${active ? 'yes' : 'no '} |\n`;
    });

    markdown += `\n\n\n## Bending Slots\n`;
    markdown += `You can always only use maximum half of you current Bending slots (rounded up so if you have 3 left you can either spend 2 and then 1 or only 1 but 3 times)\n\n`;
    markdown += `| Slot                   |                    Amount |\n`;
    markdown += `| ---------------------- | ------------------------: |\n`;
    
    // Define order for slots - regular slots with their bonus slots underneath
    const slotOrder = [
      'Airbending slot',
      'Bonus air slots',
      'Danger Sense Reactions',
      'Firebending slot',
      'Bonus fire slots',
      'Earthbending slot',
      'Bonus earth slots',
      'Spiritbending slot',
      'Bonus spirit slots'
    ];
    
    // Write slots in order
    slotOrder.forEach(slotName => {
      if (data.slots[slotName] !== undefined) {
        const value = data.slots[slotName];
        // Check if this is a bonus slot (should be collapsed)
        if (slotName.toLowerCase().includes('bonus')) {
          markdown += `| <details><summary>${slotName}</summary>${value}</details> | |\n`;
        } else {
          markdown += `| ${slotName.padEnd(22)} | ${String(value).padStart(25)} |\n`;
        }
      }
    });
    
    // Add any remaining slots not in the order
    Object.entries(data.slots).forEach(([key, value]) => {
      if (!slotOrder.includes(key)) {
        markdown += `| ${key.padEnd(22)} | ${String(value).padStart(25)} |\n`;
      }
    });

    markdown += `\n## Water charges\n`;
    markdown += `You can use maximum of 2 \\* water level water charges for any Move.\n\n`;
    markdown += `| Water charge type          |                          value |\n`;
    markdown += `| -------------------------- | -----------------------------: |\n`;
    
    // Define order for water charges
    const chargeOrder = [
      'Environmental water charge',
      'Waterbottle charge',
      'Bonus water charges'
    ];
    
    // Write charges in order
    chargeOrder.forEach(chargeName => {
      if (data.waterCharges[chargeName] !== undefined) {
        const value = data.waterCharges[chargeName];
        // Skip Environmental water charge - it's stored globally
        if (chargeName === 'Environmental water charge') {
          return;
        }
        // Check if this is a bonus charge (should be collapsed)
        if (chargeName.toLowerCase().includes('bonus')) {
          markdown += `| <details><summary>${chargeName}</summary>${value}</details> | |\n`;
        } else {
          markdown += `| ${chargeName.padEnd(26)} | ${String(value).padStart(30)} |\n`;
        }
      }
    });
    
    // Add any remaining charges not in the order (excluding Environmental)
    Object.entries(data.waterCharges).forEach(([key, value]) => {
      if (!chargeOrder.includes(key) && key !== 'Environmental water charge') {
        markdown += `| ${key.padEnd(26)} | ${String(value).padStart(30)} |\n`;
      }
    });

    markdown += `\n\n\n#${data.name.replace(/\s+/g, '_')} #Character_Sheet\n`;

    return markdown;
  };

  const handleSave = async (overrideReadyState = null) => {
    try {
      setSaving(true);
      setError(null);

      const markdown = serializeCharacterSheet(characterData, overrideReadyState);
      
      const normalizedPath = (file.path || '').replace(/^Player Root\//i, '');
      const segments = normalizedPath.split('/').map(s => encodeURIComponent(s)).join('/');
      const url = `${API_BASE_URL}/player_root/${segments}`;

      const response = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: markdown })
      });

      if (!response.ok) {
        throw new Error(`Failed to save file: ${response.status}`);
      }

      // Also save environmental water charge if it changed
      const envWaterCharge = characterData.consumables.find(c => c.name === 'Environmental water charge' && c.isGlobal);
      if (envWaterCharge) {
        try {
          const envResponse = await fetch(`${API_BASE_URL}/api/environmental_variable`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: 'environmental_water_charge',
              current: envWaterCharge.current,
              max: envWaterCharge.max
            })
          });
          
          if (!envResponse.ok) {
            console.error('Failed to save environmental water charge');
          }
        } catch (envErr) {
          console.error('Error saving environmental water charge:', envErr);
        }
      }

      setContent(markdown);
      // Silent save - no alert
    } catch (err) {
      setError(err.message);
      console.error('Error saving character sheet:', err);
      // Only show error alerts
      alert('Failed to save character sheet: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRest = () => {
    if (!confirm('Reset all consumable resources to maximum? This simulates a rest.')) {
      return;
    }

    setCharacterData(prev => {
      // Reset all consumables to their max values
      const consumables = prev.consumables.map(c => ({
        ...c,
        current: c.max
      }));

      // Update slots and water charges to match reset consumables in "current/max" format
      const slots = { ...prev.slots };
      const waterCharges = { ...prev.waterCharges };

      consumables.forEach(consumable => {
        if (consumable.type === 'water') {
          waterCharges[consumable.name] = `${consumable.max}/${consumable.max}`;
        } else {
          slots[consumable.name] = `${consumable.max}/${consumable.max}`;
        }
      });

      // Reset current_hp to max_hp
      const vitals = { ...prev.vitals };
      if (vitals.max_hp) {
        vitals.current_hp = vitals.max_hp;
      }

      return {
        ...prev,
        consumables,
        slots,
        waterCharges,
        vitals
      };
    });

    alert('All consumable resources have been reset to maximum!');
  };

  const updateVital = (key, value) => {
    setCharacterData(prev => ({
      ...prev,
      vitals: { ...prev.vitals, [key]: value }
    }));
  };

  const updateCoreStat = (key, value) => {
    setCharacterData(prev => ({
      ...prev,
      coreStats: { ...prev.coreStats, [key]: parseInt(value) || 0 }
    }));
  };

  const updateDefense = (key, value) => {
    setCharacterData(prev => ({
      ...prev,
      defense: { ...prev.defense, [key]: parseInt(value) || 0 }
    }));
  };

  const updateSlot = (key, value) => {
    setCharacterData(prev => ({
      ...prev,
      slots: { ...prev.slots, [key]: value }
    }));
  };

  const updateWaterCharge = (key, value) => {
    setCharacterData(prev => ({
      ...prev,
      waterCharges: { ...prev.waterCharges, [key]: parseInt(value) || 0 }
    }));
  };

  const updateConsumable = (index, checked) => {
    setCharacterData(prev => {
      const consumables = [...prev.consumables];
      consumables[index] = {
        ...consumables[index],
        current: checked ? consumables[index].current + 1 : Math.max(0, consumables[index].current - 1)
      };
      
      // Update the corresponding slot or water charge value in "current/max" format
      const consumable = consumables[index];
      const slots = { ...prev.slots };
      const waterCharges = { ...prev.waterCharges };
      
      if (consumable.type === 'water') {
        waterCharges[consumable.name] = `${consumable.current}/${consumable.max}`;
      } else {
        slots[consumable.name] = `${consumable.current}/${consumable.max}`;
      }
      
      return {
        ...prev,
        consumables,
        slots,
        waterCharges
      };
    });
  };

  const updateCondition = (name, value) => {
    setCharacterData(prev => ({
      ...prev,
      conditions: { ...prev.conditions, [name]: value }
    }));
  };

  const refreshEnvironmentalWaterCharge = async () => {
    try {
      const envResponse = await fetch(`${API_BASE_URL}/api/environmental_variable/environmental_water_charge`);
      if (envResponse.ok) {
        const envData = await envResponse.json();
        
        // Update the environmental water charge in consumables
        setCharacterData(prev => {
          const consumables = [...prev.consumables];
          const envIndex = consumables.findIndex(c => c.name === 'Environmental water charge' && c.isGlobal);
          
          if (envIndex !== -1) {
            consumables[envIndex] = {
              ...consumables[envIndex],
              current: envData.current,
              max: envData.max
            };
            
            // Also update waterCharges
            const waterCharges = { ...prev.waterCharges };
            waterCharges['Environmental water charge'] = `${envData.current}/${envData.max}`;
            
            return { ...prev, consumables, waterCharges };
          }
          
          return prev;
        });
      }
    } catch (err) {
      console.error('Error refreshing environmental water charge:', err);
    }
  };

  const handlePinMove = (move) => {
    setPinnedMoves(prev => {
      if (prev.find(m => m.path === move.path)) {
        return prev;
      }
      return [...prev, move];
    });
  };

  const handleUnpinMove = (path) => {
    setPinnedMoves(prev => prev.filter(m => m.path !== path));
  };

  const toggleMoveExpanded = (movePath) => {
    setExpandedMoves(prev => {
      const newSet = new Set(prev);
      if (newSet.has(movePath)) {
        newSet.delete(movePath);
      } else {
        newSet.add(movePath);
      }
      return newSet;
    });
  };

  const isShapeshiftingMove = (move) => {
    if (!move) return false;
    if (move.tags && move.tags.some(tag => tag.toLowerCase().startsWith('shapeshifting'))) return true;
    if (move.path && move.path.toLowerCase().includes('shapeshifting')) return true;
    return false;
  };

  const renderMoveGroup = (title, moves) => {
    // Sort moves by element first, then by level
    const sortedMoves = [...moves].sort((a, b) => {
      // Define element order
      const elementOrder = { fire: 0, water: 1, earth: 2, air: 3, spirit: 4 };
      
      // Get element values, treating null/undefined as coming last
      const elementA = a.element ? elementOrder[a.element.toLowerCase()] : 999;
      const elementB = b.element ? elementOrder[b.element.toLowerCase()] : 999;
      
      // Sort by element first
      if (elementA !== elementB) {
        return elementA - elementB;
      }
      
      // If same element, sort by level
      const levelA = a.level ?? 999;
      const levelB = b.level ?? 999;
      if (levelA !== levelB) {
        return levelA - levelB;
      }
      
      // If same element and level, sort by name
      return a.name.localeCompare(b.name);
    });
    
    return (
      <div className="move-group">
        <div className="move-group-header">
          <span>{title}</span>
          <span className="move-count">{sortedMoves.length}</span>
        </div>
        {sortedMoves.length === 0 ? (
          <p className="muted-text">No moves found.</p>
        ) : (
          <div className="move-card-grid">
            {sortedMoves.map(move => {
              const { actionColor, elementColor } = getMoveColors(move);
              const isExpanded = expandedMoves.has(move.path);
              const isPinned = pinnedMoves.find(m => m.path === move.path);
              return (
                <div key={move.path} className={`move-card ${isExpanded ? 'expanded' : ''}`} style={{ borderColor: elementColor }}>
                  <div 
                    className="move-card-header" 
                    onClick={() => toggleMoveExpanded(move.path)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="move-card-title">
                      <h4>{move.name}</h4>
                      <span className="pill" style={{ backgroundColor: hexToRgba(actionColor, 0.2), color: actionColor }}>
                        {move.actionType || 'Move'}
                      </span>
                      {move.level && (
                        <span className="level-badge">Lvl {move.level}</span>
                      )}
                      <span style={{
                        marginLeft: '8px',
                        fontSize: '16px',
                        fontWeight: 'bold',
                        color: actionColor,
                        transition: 'transform 0.3s ease'
                      }}>
                        {isExpanded ? '▼' : '▶'}
                      </span>
                    </div>
                    <button 
                      className="pin-button" 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (isPinned) {
                          handleUnpinMove(move.path);
                        } else {
                          handlePinMove(move);
                        }
                      }}
                    >
                      {isPinned ? 'Unpin' : 'Pin'}
                    </button>
                  </div>
                  {isExpanded && (
                    <div className="move-card-expanded-content">
                      {isShapeshiftingMove(move) ? (
                        <ShapeshiftingForm file={{ path: move.path, name: move.name }} lightMode={lightMode} />
                      ) : (
                        <BendingMove file={{ path: move.path, name: move.name }} lightMode={lightMode} />
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="character-sheet">
        <div className="loading">Loading character sheet...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="character-sheet">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (!characterData) {
    return (
      <div className="character-sheet">
        <div className="no-data">No character sheet data available</div>
      </div>
    );
  }

  // Precompute HP state for UI and bleeding-out indicator
  const currentHp = parseFloat(characterData?.vitals?.current_hp) || 0;
  const maxHp = parseFloat(characterData?.vitals?.max_hp) || 0;
  const hpPercentage = maxHp > 0 ? Math.max(0, Math.min(100, (currentHp / maxHp) * 100)) : 0;
  const getHpColor = (percent) => {
    if (percent > 75) return '#4ec9b0'; // Healthy green-cyan
    if (percent > 50) return '#c4710bff'; // Yellow
    if (percent > 25) return '#c48600ff'; // Orange
    return '#840505ff'; // Critical red
  };
  const hpColor = getHpColor(hpPercentage);
  const isBleedingOut = maxHp > 0 && currentHp <= 0;
  const activeConditions = CONDITION_NAMES.filter(name =>
    name === 'Bleeding out'
      ? isBleedingOut
      : characterData.conditions?.[name]
  );
  const bonusResources = [
    {
      label: 'Bonus air slots',
      value: parseCurrentMaxValue(characterData.slots?.['Bonus air slots']),
      exists: characterData.slots && Object.prototype.hasOwnProperty.call(characterData.slots, 'Bonus air slots'),
      color: ELEMENT_COLORS.air
    },
    {
      label: 'Bonus water charges',
      value: parseCurrentMaxValue(characterData.waterCharges?.['Bonus water charges']),
      exists: characterData.waterCharges && Object.prototype.hasOwnProperty.call(characterData.waterCharges, 'Bonus water charges'),
      color: ELEMENT_COLORS.water
    },
    {
      label: 'Bonus earth slots',
      value: parseCurrentMaxValue(characterData.slots?.['Bonus earth slots']),
      exists: characterData.slots && Object.prototype.hasOwnProperty.call(characterData.slots, 'Bonus earth slots'),
      color: ELEMENT_COLORS.earth
    },
    {
      label: 'Bonus fire slots',
      value: parseCurrentMaxValue(characterData.slots?.['Bonus fire slots']),
      exists: characterData.slots && Object.prototype.hasOwnProperty.call(characterData.slots, 'Bonus fire slots'),
      color: ELEMENT_COLORS.fire
    },
    {
      label: 'Bonus spirit slots',
      value: parseCurrentMaxValue(characterData.slots?.['Bonus spirit slots']),
      exists: characterData.slots && Object.prototype.hasOwnProperty.call(characterData.slots, 'Bonus spirit slots'),
      color: ELEMENT_COLORS.spirit
    }
  ].filter(item => item.exists || item.value.hasValue);
  
  // Count non-zero bonus resources for display
  const nonZeroBonusCount = bonusResources.filter(item => item.value.current > 0).length;
  const bendingSlotConsumables = characterData.consumables.filter(c => c.type === 'slot');
  const waterChargeConsumables = characterData.consumables.filter(c => 
    c.name.toLowerCase().includes('water') && c.name.toLowerCase().includes('charge')
  );

  return (
    <div className={`character-sheet ${lightMode ? 'light-mode' : ''}`}>
      <div className="character-header">
        <h1>{characterData.name || 'Character Sheet'}</h1>
        <div className="header-buttons">
          <button 
            onClick={() => setShowReactionsModal(true)} 
            className="ghost-button"
            title="Open reactions & danger sense reactions"
            style={{
              background: `linear-gradient(135deg, ${ACTION_COLORS['Reaction']} 0%, ${ACTION_COLORS['Danger Sense Reaction']} 100%)`,
              color: '#fff',
              fontWeight: '600',
              border: 'none',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.2)'
            }}
          >
            Reactions
          </button>
          <button 
            onClick={() => setShowPlanModal(true)} 
            className="ghost-button"
            title="Plan your turn with actions and bonus actions"
            style={{
              background: `linear-gradient(135deg, ${ACTION_COLORS['Action']} 0%, ${ACTION_COLORS['Bonus Action']} 100%)`,
              color: '#fff',
              fontWeight: '600',
              border: 'none',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.2)'
            }}
          >
            Plan turn
          </button>
          <button 
            onClick={async () => {
              const currentState = isReady(characterData?.name);
              const newReadyState = !currentState;
              // Record that we're updating ready state
              lastReadyUpdateRef.current = Date.now();
              // Update context immediately for UI responsiveness
              setReady(characterData?.name, newReadyState);
              // Save to file with the explicit new state to avoid race conditions
              await handleSave(newReadyState);
            }}
            className="ghost-button"
            title={isReady(characterData?.name) ? "Mark turn as not ready" : "Mark turn as ready"}
            style={{
              background: isReady(characterData?.name) ? '#2ecc71' : '#7f8c8d',
              color: '#fff',
              fontWeight: '600',
              border: 'none',
              boxShadow: isReady(characterData?.name) 
                ? '0 2px 8px rgba(46, 204, 113, 0.4)' 
                : '0 2px 6px rgba(0, 0, 0, 0.2)',
              transition: 'all 0.3s ease'
            }}
          >
            {isReady(characterData?.name) ? '✓ Ready' : 'Ready'}
          </button>
          <button 
            onClick={handleRest} 
            className="rest-button"
            title="Reset all consumable resources to maximum"
          >
            Rest
          </button>
          {saving && <span className="auto-save-indicator">Saving...</span>}
        </div>
      </div>

      {showReactionsModal && (
        <div className="modal-overlay" onClick={() => setShowReactionsModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Reactions</h3>
              <button className="ghost-button" onClick={() => setShowReactionsModal(false)}>Close</button>
            </div>
            <div className="slot-summary-row">
              {bendingSlotConsumables.length === 0 ? (
                <span className="muted-text">No bending slot counters found.</span>
              ) : (
                bendingSlotConsumables.map(slot => {
                  const slotElement = getElementFromName(slot.name);
                  const color = slotElement ? ELEMENT_COLORS[slotElement] : '#3498db';
                  return (
                    <div key={slot.name} className="slot-summary-card" style={{ borderColor: color }}>
                      <span className="meta-label">{slot.name}</span>
                      <span className="meta-value">{slot.current} / {slot.max}</span>
                    </div>
                  );
                })
              )}
            </div>
            {waterChargeConsumables.length > 0 && (
              <div className="slot-summary-row" style={{ marginTop: '12px' }}>
                {waterChargeConsumables.map(charge => {
                  return (
                    <div key={charge.name} className="slot-summary-card" style={{ borderColor: ELEMENT_COLORS.water }}>
                      <span className="meta-label">{charge.name}</span>
                      <span className="meta-value">{charge.current} / {charge.max}</span>
                    </div>
                  );
                })}
              </div>
            )}
            {movesLoading ? (
              <p className="muted-text">Loading moves...</p>
            ) : movesError ? (
              <p className="error-text">{movesError}</p>
            ) : (
              <>
                {renderMoveGroup('Reactions', movesByType.reaction || [])}
                {renderMoveGroup('Danger Sense Reactions', movesByType.danger || [])}
              </>
            )}
          </div>
        </div>
      )}

      {showPlanModal && (
        <div className="modal-overlay" onClick={() => setShowPlanModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Plan Turn</h3>
              <button className="ghost-button" onClick={() => setShowPlanModal(false)}>Close</button>
            </div>
            <div className="slot-summary-row">{bendingSlotConsumables.length === 0 ? (
                <span className="muted-text">No bending slot counters found.</span>
              ) : (
                bendingSlotConsumables.map(slot => {
                  const slotElement = getElementFromName(slot.name);
                  const color = slotElement ? ELEMENT_COLORS[slotElement] : '#3498db';
                  return (
                    <div key={slot.name} className="slot-summary-card" style={{ borderColor: color }}>
                      <span className="meta-label">{slot.name}</span>
                      <span className="meta-value">{slot.current} / {slot.max}</span>
                    </div>
                  );
                })
              )}
            </div>
            {waterChargeConsumables.length > 0 && (
              <div className="slot-summary-row" style={{ marginTop: '12px' }}>
                {waterChargeConsumables.map(charge => {
                  return (
                    <div key={charge.name} className="slot-summary-card" style={{ borderColor: ELEMENT_COLORS.water }}>
                      <span className="meta-label">{charge.name}</span>
                      <span className="meta-value">{charge.current} / {charge.max}</span>
                    </div>
                  );
                })}
              </div>
            )}
            {movesLoading ? (
              <p className="muted-text">Loading moves...</p>
            ) : movesError ? (
              <p className="error-text">{movesError}</p>
            ) : (
              <>
                {renderMoveGroup('Actions', movesByType.action || [])}
                {renderMoveGroup('Bonus Actions', movesByType.bonus || [])}
              </>
            )}
          </div>
        </div>
      )}

      <div className={`character-layout ${pinnedMovesCollapsed ? 'pinned-collapsed' : ''}`}>
        <div className="character-main">

      {/* Vitals Section - All fields editable except max_hp */}
      <section className="character-section">
        <h2 
          onClick={() => setVitalsCollapsed(!vitalsCollapsed)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            userSelect: 'none',
            marginBottom: vitalsCollapsed ? '0' : '16px'
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            Vitals
            {vitalsCollapsed && (
              <span style={{
                fontSize: '14px',
                fontWeight: 'normal',
                opacity: 0.7,
                marginLeft: '4px'
              }}>
                (HP: {characterData.vitals.current_hp}/{characterData.vitals.max_hp})
              </span>
            )}
          </span>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            {vitalsCollapsed ? '▼' : '▲'}
          </span>
        </h2>

        {!vitalsCollapsed && (
          <>
            {/* Large HP Bar Display */}
            {characterData.vitals.current_hp !== undefined && characterData.vitals.max_hp !== undefined && (
          <>
            {isBleedingOut && (
              <div
                style={{
                  marginBottom: '12px',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  background: lightMode ? '#ffe1e1' : 'rgba(122, 11, 11, 0.6)',
                  border: lightMode ? '2px solid #d7263d' : '2px solid #f25f5c',
                  color: lightMode ? '#7a0b0b' : '#ffdede',
                  fontWeight: 700,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}
                title="Bleeding out: roll death saves each turn; move only 1m; max 1 bending slot per move."
              >
                <span>Bleeding out</span>
                <span style={{ fontWeight: 500 }}>
                  Roll death saves each turn; movement capped at 1m; spend max 1 bending slot per move.
                </span>
              </div>
            )}
            <div style={{
              marginBottom: '20px',
              padding: '12px',
              backgroundColor: lightMode ? '#f8f8f8' : 'rgba(0, 0, 0, 0.2)',
              borderRadius: '10px',
              border: lightMode ? '2px solid #ddd' : '2px solid #3e3e42'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px',
                fontSize: '14px',
                fontWeight: '600',
                color: lightMode ? '#333' : '#4ec9b0'
              }}>
                <span>Hit Points</span>
                <span>{characterData.vitals.current_hp} / {characterData.vitals.max_hp}</span>
              </div>
              <div style={{
                width: '100%',
                height: '24px',
                backgroundColor: lightMode ? '#e0e0e0' : '#2d2d30',
                borderRadius: '12px',
                overflow: 'hidden',
                border: lightMode ? '2px solid #ccc' : '2px solid #444',
                position: 'relative',
                boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)'
              }}>
                <>
                  <div style={{
                    width: `${hpPercentage}%`,
                    height: '100%',
                    backgroundColor: hpColor,
                    transition: 'width 0.5s ease, background-color 0.5s ease',
                    boxShadow: `0 0 12px ${hpColor}, inset 0 1px 3px rgba(255, 255, 255, 0.3)`,
                    borderRadius: '10px'
                  }} />
                  <span style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    fontSize: '13px',
                    fontWeight: 'bold',
                    color: '#fff',
                    textShadow: '0 1px 4px rgba(0, 0, 0, 0.9)',
                    pointerEvents: 'none',
                    letterSpacing: '0.5px'
                  }}>
                    {Math.round(hpPercentage)}%
                  </span>
                </>
              </div>
            </div>
          </>
        )}
        
        <div className="stat-grid">
          {Object.entries(characterData.vitals).map(([key, value]) => {
            const tooltip = getStatTooltip(key);
            return (
              <div key={key} className="stat-card">
                <label title={tooltip || undefined} style={tooltip ? { cursor: 'help', textDecoration: 'underline dotted' } : {}}>
                  {key}
                </label>
                {key === 'Initiative' ? (
                  <div style={{ 
                    padding: '8px', 
                    backgroundColor: lightMode ? '#f0f0f0' : '#2a2a2a',
                    borderRadius: '4px',
                    textAlign: 'center'
                  }}>
                    <DiceRollText text={value} />
                  </div>
                ) : (
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => updateVital(key, e.target.value)}
                    className="stat-input"
                    readOnly={key === 'max_hp'}
                    style={key === 'max_hp' ? { cursor: 'not-allowed', backgroundColor: lightMode ? '#f0f0f0' : '#2a2a2a' } : {}}
                  />
                )}
              </div>
            );
          })}
        </div>
          </>
        )}
      </section>

      {/* Stress Level Section - Only for Fire and Spirit Benders */}
      {(() => {
        const fireLevel = characterData.bending.elements.find(el => el.element.toLowerCase() === 'fire')?.level || 0;
        const spiritLevel = characterData.bending.elements.find(el => el.element.toLowerCase() === 'spirit')?.level || 0;
        const hasFireOrSpirit = fireLevel >= 1 || spiritLevel >= 1;
        
        if (hasFireOrSpirit) {
          const stressLevel = characterData.vitals['Stress Level'] || characterData.vitals['stress level'] || 0;
          const maxStressLevel = characterData.vitals['Max Stress Level'] || characterData.vitals['max stress level'] || 10;
          
          const handleStressLevelChange = (newLevel) => {
            setCharacterData(prev => ({
              ...prev,
              vitals: {
                ...prev.vitals,
                'Stress Level': newLevel,
                'Fire Damage Bonus': 2 * newLevel
              }
            }));
          };
          
          const handleMaxStressLevelChange = (newMax) => {
            setCharacterData(prev => ({
              ...prev,
              vitals: {
                ...prev.vitals,
                'Max Stress Level': newMax
              }
            }));
          };
          
          return (
            <section className="character-section">
              <h2 
                onClick={() => setStressLevelCollapsed(!stressLevelCollapsed)}
                style={{ 
                  cursor: 'pointer', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  userSelect: 'none',
                  marginBottom: stressLevelCollapsed ? '0' : '16px'
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '20px' }}>🔥</span>
                  Stress Level
                  <span style={{
                    fontSize: '14px',
                    fontWeight: 'normal',
                    opacity: 0.7,
                    marginLeft: '4px'
                  }}>
                    ({stressLevel}/{maxStressLevel})
                  </span>
                </span>
                <span style={{ fontSize: '14px', opacity: 0.7 }}>
                  {stressLevelCollapsed ? '▼' : '▲'}
                </span>
              </h2>

              {!stressLevelCollapsed && (
                <StressLevel 
                  currentLevel={stressLevel}
                  maxLevel={maxStressLevel}
                  fireLevel={fireLevel}
                  lightMode={lightMode}
                  onLevelChange={handleStressLevelChange}
                  onMaxLevelChange={handleMaxStressLevelChange}
                />
              )}
            </section>
          );
        }
        return null;
      })()}

      {/* Conditions Section */}
      <section className="character-section">
        <h2 
          onClick={() => setConditionsCollapsed(!conditionsCollapsed)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            userSelect: 'none'
          }}
        >
          <span>Conditions</span>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            {conditionsCollapsed ? '▼' : '▲'}
          </span>
        </h2>

        {/* Active conditions badges - always visible */}
        <div style={{ marginBottom: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap', minHeight: '24px' }}>
          {activeConditions.length === 0 ? (
            <span style={{ opacity: 0.5, fontSize: '12px' }}>No active conditions</span>
          ) : (
            activeConditions.map((cond) => (
              <span
                key={`active-${cond}`}
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  backgroundColor: cond === 'Bleeding out' ? '#d7263d' : '#c9944eff',
                  color: '#fff',
                  fontSize: '11px',
                  fontWeight: 600,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                }}
              >
                {cond}
              </span>
            ))
          )}
        </div>

        {/* Collapsible content */}
        {!conditionsCollapsed && (
          <>

            <div className="consumables-grid">
              {CONDITION_NAMES.map((cond) => {
                const isBleed = cond === 'Bleeding out';
                const isActive = isBleed ? isBleedingOut : !!characterData.conditions?.[cond];
                return (
                  <div
                    key={`cond-${cond}`}
                    className="consumable-card"
                    style={{
                      borderColor: isActive ? "#4ec9b0" : "#bdc3c7",
                      backgroundColor: isActive
                        ? "rgba(78, 201, 176, 0.08)"
                        : undefined,
                      padding: "8px",
                    }}
                  >
                    <h3
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        fontSize: "13px",
                        marginBottom: "4px",
                      }}
                    >
                      <span>{cond}</span>
                      <label
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "11px",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isActive}
                          onChange={(e) =>
                            updateCondition(cond, e.target.checked)
                          }
                          disabled={isBleed}
                          style={{ width: "14px", height: "14px" }}
                        />
                        <span>{isBleed ? "auto" : "toggle"}</span>
                      </label>
                    </h3>
                    <p
                      style={{
                        marginTop: "2px",
                        fontSize: "11px",
                        opacity: 0.7,
                        whiteSpace: "pre-line",
                      }}
                    >
                      {isBleed
                        ? "Movement capped at 1m.\nMax 1 bending slot per move.\nDeath saves each turn:\n- 3 success = stable for 3 rounds \n- 3 fails = dead"
                        : conditionDescriptions[cond] ||
                          "Manually toggle to track this condition."}
                    </p>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </section>

      {/* Core Stats Section - Read-only */}
      <section className="character-section">
        <h2 
          onClick={() => setCoreStatsCollapsed(!coreStatsCollapsed)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            userSelect: 'none',
            marginBottom: coreStatsCollapsed ? '0' : '16px'
          }}
        >
          <span>Core Stats</span>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            {coreStatsCollapsed ? '▼' : '▲'}
          </span>
        </h2>
        
        {!coreStatsCollapsed && (
          <div className="stat-grid stat-grid-6">
          {Object.entries(characterData.coreStats).map(([key, value]) => {
            const tooltip = getStatTooltip(key);
            return (
              <div key={key} className="stat-card">
                <label title={tooltip || undefined} style={tooltip ? { cursor: 'help', textDecoration: 'underline dotted' } : {}}>
                  {key}
                </label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => updateCoreStat(key, e.target.value)}
                  className="stat-input"
                  readOnly
                  style={{ cursor: 'not-allowed', backgroundColor: lightMode ? '#f0f0f0' : '#2a2a2a' }}
                />
              </div>
            );
          })}
        </div>
        )}
      </section>

      {/* Bending Levels Section */}
      <section className="character-section">
        <h2 
          onClick={() => setBendingLevelsCollapsed(!bendingLevelsCollapsed)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            userSelect: 'none',
            marginBottom: bendingLevelsCollapsed ? '0' : '16px'
          }}
        >
          <span>Bending Levels</span>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            {bendingLevelsCollapsed ? '▼' : '▲'}
          </span>
        </h2>
        
        {!bendingLevelsCollapsed && (
          <div className="bending-table">
          <table>
            <thead>
              <tr>
                <th>Element</th>
                <th>Level</th>
                <th title="Attack Roll = 1d20 + Element Level + Relevant Stat" style={{ cursor: 'help', textDecoration: 'underline dotted' }}>
                  Attack Roll
                </th>
                <th title="DC = Element Level + Relevant Stat" style={{ cursor: 'help', textDecoration: 'underline dotted' }}>
                  DC
                </th>
              </tr>
            </thead>
            <tbody>
              {characterData.bending.elements.map((el, idx) => {
                const elementName = el.element.toLowerCase();
                const bgColor = ELEMENT_COLORS[elementName] || '#e0e0e0';
                
                // Get specific tooltip for this element's attack roll and DC
                const attackRollTooltip = getStatTooltip(`${el.element} Attack Roll`);
                const dcTooltip = getStatTooltip(`${el.element}bending DC`);
                
                return (
                  <tr 
                    key={idx}
                    style={{
                      backgroundColor: hexToRgba(bgColor, 0.3),
                      borderLeft: `4px solid ${bgColor}`
                    }}
                  >
                    <td style={{ fontWeight: '600' }}>{el.element}</td>
                    <td>{el.level}</td>
                    <td title={attackRollTooltip || undefined} style={attackRollTooltip ? { cursor: 'help' } : {}}>
                      <DiceRollText text={el.attackRoll} />
                    </td>
                    <td title={dcTooltip || undefined} style={dcTooltip ? { cursor: 'help' } : {}}>
                      {el.dc}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        )}
      </section>

      {/* Defense Section */}
      <section className="character-section">
        <h2 
          onClick={() => setDefenseCollapsed(!defenseCollapsed)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            userSelect: 'none',
            marginBottom: defenseCollapsed ? '0' : '16px'
          }}
        >
          <span>Defensive Stats</span>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            {defenseCollapsed ? '▼' : '▲'}
          </span>
        </h2>
        
        {!defenseCollapsed && (
          <div className="stat-grid stat-grid-4">
          {Object.entries(characterData.defense).map(([key, value]) => {
            const tooltip = getStatTooltip(key);
            return (
              <div key={key} className="stat-card">
                <label title={tooltip || undefined} style={tooltip ? { cursor: 'help', textDecoration: 'underline dotted' } : {}}>
                  {key}
                </label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => updateDefense(key, e.target.value)}
                  className="stat-input"
                />
              </div>
            );
          })}
        </div>
        )}
      </section>

      {/* Bending Slots, Water Charges & Consumable Resources */}
      <section className="character-section">
        <h2 
          onClick={() => setResourcesCollapsed(!resourcesCollapsed)}
          style={{ 
            cursor: 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            userSelect: 'none',
            marginBottom: resourcesCollapsed ? '0' : '16px'
          }}
        >
          <span>Bending Slots, Water Charges & Consumable Resources</span>
          <span style={{ fontSize: '14px', opacity: 0.7 }}>
            {resourcesCollapsed ? '▼' : '▲'}
          </span>
        </h2>
        
        {!resourcesCollapsed && (
          <>
            <p className="section-note">
          You can always only use maximum half of your current Bending slots 
          (rounded up so if you have 3 left you can either spend 2 and then 1 or only 1 but 3 times).
          You can use maximum of 2 * water level water charges for any Move.
        </p>
        
        {/* Collapsible Bonus Resources Section - Only shows when there are non-zero bonus resources */}
        {bonusResources.length > 0 && (
          <div
            style={{
              marginBottom: '16px',
              padding: '10px 12px',
              borderRadius: '8px',
              border: lightMode ? '1px solid #d6d6d6' : '1px solid #3e3e42',
              background: lightMode ? '#f9f9f9' : 'rgba(255,255,255,0.03)'
            }}
          >
            <div
              onClick={() => setBonusResourcesCollapsed(!bonusResourcesCollapsed)}
              style={{
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                userSelect: 'none',
                fontSize: '13px',
                fontWeight: '600',
                marginBottom: bonusResourcesCollapsed ? '0' : '10px'
              }}
            >
              <span>
                💎 Bonus Resources
                {nonZeroBonusCount > 0 && (
                  <span style={{ fontSize: '11px', opacity: 0.7, fontWeight: 'normal', marginLeft: '8px' }}>
                    ({nonZeroBonusCount} active)
                  </span>
                )}
                <span style={{ fontSize: '11px', opacity: 0.6, fontWeight: 'normal', marginLeft: '6px' }}>
                  (from temporary effects)
                </span>
              </span>
              <span style={{ fontSize: '12px', opacity: 0.7 }}>
                {bonusResourcesCollapsed ? '▼' : '▲'}
              </span>
            </div>
            
            {!bonusResourcesCollapsed && (
              <div className="consumables-grid" style={{ marginTop: '8px' }}>
                {bonusResources.map((item) => {
                  const isWaterCharge = item.label.includes('water');
                  const maxValue = Math.max(item.value.current, 10);
                  
                  const updateValue = (newCurrent) => {
                    const dataKey = isWaterCharge ? 'waterCharges' : 'slots';
                    setCharacterData(prev => ({
                      ...prev,
                      [dataKey]: {
                        ...prev[dataKey],
                        [item.label]: newCurrent.toString()
                      }
                    }));
                  };
                  
                  return (
                    <div key={item.label} className="consumable-card" style={{ borderColor: item.color }}>
                      <h3 style={{ color: item.color }}>
                        {item.label.replace('Bonus ', '')}
                      </h3>
                      <div className="consumable-counter">
                        <span 
                          className="counter-display" 
                          style={{
                            backgroundColor: hexToRgba(item.color, 0.15),
                            color: item.color
                          }}
                        >
                          {item.value.current} / 
                        </span>
                        <input
                          type="number"
                          min="0"
                          value={maxValue}
                          onChange={(e) => {
                            const newMax = Math.max(0, parseInt(e.target.value) || 0);
                            updateValue(Math.min(item.value.current, newMax));
                          }}
                          className="max-input"
                          style={{
                            width: '50px',
                            padding: '2px 6px',
                            fontSize: '14px',
                            border: `1px solid ${item.color}`,
                            borderRadius: '4px',
                            backgroundColor: 'rgba(255, 255, 255, 0.9)',
                            color: '#2c3e50',
                            textAlign: 'center',
                            marginLeft: '4px'
                          }}
                        />
                      </div>
                      <div className="checkbox-grid">
                        {Array.from({ length: maxValue }, (_, i) => {
                          const isChecked = i < item.value.current;
                          return (
                            <label key={i} className="checkbox-label">
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  const newCurrent = e.target.checked 
                                    ? Math.max(i + 1, item.value.current)
                                    : Math.min(i, item.value.current);
                                  updateValue(newCurrent);
                                }}
                                className="resource-checkbox"
                              />
                              <span 
                                className="checkbox-mark" 
                                style={{
                                  borderColor: isChecked ? item.color : '#bdc3c7',
                                  backgroundColor: isChecked ? item.color : '#ecf0f1'
                                }}
                              />
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        
        {/* Consumables with checkbox trackers */}
        <div className="consumables-grid">
          {characterData.consumables.map((consumable, idx) => {
            const element = getElementFromName(consumable.name);
            const elementColor = element ? ELEMENT_COLORS[element] : '#3498db';
            const tooltip = getStatTooltip(consumable.name);
            
            return (
              <div key={idx} className="consumable-card" style={{
                borderColor: elementColor
              }}>
                <h3 title={tooltip || undefined} style={tooltip ? { cursor: 'help', textDecoration: 'underline dotted' } : {}}>
                  {consumable.name}
                  {consumable.name === 'Environmental water charge' && (
                    <button
                      onClick={refreshEnvironmentalWaterCharge}
                      style={{
                        marginLeft: '8px',
                        padding: '4px 8px',
                        fontSize: '11px',
                        backgroundColor: elementColor,
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontWeight: '600',
                        transition: 'opacity 0.2s'
                      }}
                      onMouseEnter={(e) => e.target.style.opacity = '0.8'}
                      onMouseLeave={(e) => e.target.style.opacity = '1'}
                      title="Refresh from global source"
                    >
                      ↻
                    </button>
                  )}
                </h3>
                <div className="consumable-counter">
                  {consumable.name === 'Environmental water charge' ? (
                    <>
                      <span className="counter-display" style={{
                        backgroundColor: hexToRgba(elementColor, 0.15),
                        color: elementColor
                      }}>
                        {consumable.current} / 
                      </span>
                      <input
                        type="number"
                        min="0"
                        value={consumable.max}
                        onChange={(e) => {
                          const newMax = Math.max(0, parseInt(e.target.value) || 0);
                          setCharacterData(prev => {
                            const consumables = [...prev.consumables];
                            const newCurrent = Math.min(consumables[idx].current, newMax);
                            consumables[idx] = { ...consumables[idx], max: newMax, current: newCurrent };
                            const slots = { ...prev.slots };
                            const waterCharges = { ...prev.waterCharges };
                            
                            // Update in "current/max" format
                            if (consumable.type === 'water') {
                              waterCharges[consumable.name] = `${newCurrent}/${newMax}`;
                            } else {
                              slots[consumable.name] = `${newCurrent}/${newMax}`;
                            }
                            
                            return { ...prev, consumables, slots, waterCharges };
                          });
                        }}
                        className="max-input"
                        style={{
                          width: '50px',
                          padding: '2px 6px',
                          fontSize: '14px',
                          border: `1px solid ${elementColor}`,
                          borderRadius: '4px',
                          backgroundColor: 'rgba(255, 255, 255, 0.9)',
                          color: '#2c3e50',
                          textAlign: 'center',
                          marginLeft: '4px'
                        }}
                      />
                    </>
                  ) : (
                    <span className="counter-display" style={{
                      backgroundColor: hexToRgba(elementColor, 0.15),
                      color: elementColor
                    }}>
                      {consumable.current} / {consumable.max}
                    </span>
                  )}
                </div>
                <div className="checkbox-grid">
                  {Array.from({ length: consumable.max }, (_, i) => (
                    <label key={i} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={i < consumable.current}
                        onChange={(e) => {
                          const newCurrent = e.target.checked 
                            ? Math.max(i + 1, consumable.current)
                            : Math.min(i, consumable.current);
                          setCharacterData(prev => {
                            const consumables = [...prev.consumables];
                            consumables[idx] = { ...consumables[idx], current: newCurrent };
                            const slots = { ...prev.slots };
                            const waterCharges = { ...prev.waterCharges };
                            
                            // Update in "current/max" format
                            if (consumable.type === 'water') {
                              waterCharges[consumable.name] = `${newCurrent}/${consumable.max}`;
                            } else {
                              slots[consumable.name] = `${newCurrent}/${consumable.max}`;
                            }
                            
                            return { ...prev, consumables, slots, waterCharges };
                          });
                        }}
                        className="resource-checkbox"
                      />
                      <span className="checkbox-mark" style={{
                        borderColor: i < consumable.current ? elementColor : '#bdc3c7',
                        backgroundColor: i < consumable.current ? elementColor : '#ecf0f1'
                      }}></span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Other slots (non-numeric or empty) - excluding consumables tracked with checkboxes and bonus slots */}
        {Object.entries(characterData.slots).some(([key, value]) => {
          // Exclude bonus slots - they're in the collapsible bonus section
          if (key.toLowerCase().includes('bonus')) return false;
          
          // Exclude slots that are in "current/max" format (tracked by checkboxes)
          const slashMatch = String(value).match(/^\d+\s*\/\s*\d+$/);
          if (slashMatch) return false;
          
          const numValue = parseInt(value);
          return isNaN(numValue) || numValue <= 0 || value === '';
        }) && (
          <div className="stat-grid stat-grid-3" style={{ marginTop: '20px' }}>
            {Object.entries(characterData.slots)
              .filter(([key, value]) => {
                // Exclude bonus slots - they're in the collapsible bonus section
                if (key.toLowerCase().includes('bonus')) return false;
                
                // Exclude slots that are in "current/max" format (tracked by checkboxes)
                const slashMatch = String(value).match(/^\d+\s*\/\s*\d+$/);
                if (slashMatch) return false;
                
                const numValue = parseInt(value);
                return isNaN(numValue) || numValue <= 0 || value === '';
              })
              .map(([key, value]) => {
                const tooltip = getStatTooltip(key);
                return (
                  <div key={key} className="stat-card">
                    <label title={tooltip || undefined} style={tooltip ? { cursor: 'help', textDecoration: 'underline dotted' } : {}}>
                      {key}
                    </label>
                    <input
                      type="text"
                      value={value}
                      onChange={(e) => updateSlot(key, e.target.value)}
                      className="stat-input"
                    />
                  </div>
                );
              })}
          </div>
        )}
          </>
        )}
      </section>
    </div>
    <aside className={`pinned-panel ${pinnedMovesCollapsed ? 'collapsed' : ''}`}>
      <div 
        className="pinned-header"
        onClick={() => setPinnedMovesCollapsed(!pinnedMovesCollapsed)}
        style={{ 
          cursor: 'pointer',
          userSelect: 'none'
        }}
      >
        {!pinnedMovesCollapsed ? (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3>Pinned moves</h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {pinnedMoves.length > 0 && (
                <button 
                  className="ghost-button" 
                  onClick={(e) => {
                    e.stopPropagation();
                    setPinnedMoves([]);
                  }}
                  style={{ pointerEvents: 'auto' }}
                >
                  Clear
                </button>
              )}
              <span style={{ fontSize: '14px', opacity: 0.7 }}>▲</span>
            </div>
          </>
        ) : (
          <>
            <h3 style={{ margin: 0 }}>Pinned moves</h3>
            {pinnedMoves.length > 0 && (
              <span style={{
                fontSize: '12px',
                fontWeight: 'normal',
                opacity: 0.7
              }}>
                ({pinnedMoves.length})
              </span>
            )}
            <span style={{ fontSize: '14px', opacity: 0.7 }}>◀</span>
          </>
        )}
      </div>
      {!pinnedMovesCollapsed && (
        <>
          {pinnedMoves.length === 0 ? (
        <p className="muted-text">Pin moves from the popups to keep their range and costs handy.</p>
      ) : (
        <div className="pinned-list">
          {pinnedMoves.map(move => {
            const { actionColor, elementColor } = getMoveColors(move);
            const isExpanded = expandedMoves.has(move.path);
            return (
              <div key={move.path} className={`pinned-card ${isExpanded ? 'expanded' : ''}`} style={{ borderColor: elementColor }}>
                <div 
                  className="pinned-card-header"
                  onClick={() => toggleMoveExpanded(move.path)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="pinned-title">
                    <h4>{move.name}</h4>
                    <span className="pill" style={{ backgroundColor: hexToRgba(actionColor, 0.2), color: actionColor }}>
                      {move.actionType || 'Move'}
                    </span>
                    {move.level && (
                      <span className="level-badge">Lvl {move.level}</span>
                    )}
                    <span style={{
                      marginLeft: '8px',
                      fontSize: '14px',
                      fontWeight: 'bold',
                      color: actionColor,
                      transition: 'transform 0.3s ease'
                    }}>
                      {isExpanded ? '▼' : '▶'}
                    </span>
                  </div>
                  <button 
                    className="close-button" 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUnpinMove(move.path);
                    }}
                  >
                    ✕
                  </button>
                </div>
                {isExpanded && (
                  <div className="pinned-card-expanded-content">
                    <BendingMove file={{ path: move.path, name: move.name }} lightMode={lightMode} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
        </>
      )}
    </aside>
    </div>
    </div>
);
};

export default CharacterSheet;
