import React, { useState, useEffect, useRef } from 'react';
import { hexToRgba } from '../utils/colorUtils';
import './CharacterSheet.css';
import { API_BASE_URL } from '../config/api';

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
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
  const saveTimeoutRef = useRef(null);
  const initialLoadRef = useRef(true);

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
    "Spirit bending slot":
      "Spirit level. Restored on short rest. Max half can be spent per move.",
    "spiritbending slot":
      "Spirit level. Restored on short rest. Max half can be spent per move.",
    Water_charge:
      "Total = Waterbottle Charge + Environmental Water Charge. Max 2× Water level per move.",
    "Waterbottle Charge": "2 × Water level (personal water supply, refillable)",
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

  useEffect(() => {
    if (file) {
      initialLoadRef.current = true;
      loadCharacterSheet();
    }
  }, [file]);

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

  const parseCharacterSheet = (markdown) => {
    const data = {
      name: '',
      vitals: {},
      coreStats: {},
      bending: { totalLevel: 0, elements: [] },
      defense: {},
      slots: {},
      waterCharges: {},
      consumables: []
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
        const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
        if (cells.length >= 2 && cells[0] !== 'Water charge type') {
          const chargeName = cells[0];
          const chargeValue = cells[1];
          data.waterCharges[chargeName] = chargeValue;
        }
      });
    }

    // Extract consumable resources from slots (those that are numeric and can be tracked)
    Object.entries(data.slots).forEach(([key, value]) => {
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

    // Add water charges as consumables too (except Environmental water charge - loaded globally)
    Object.entries(data.waterCharges).forEach(([key, value]) => {
      // Skip Environmental water charge - it will be loaded from global file
      if (key === 'Environmental water charge') {
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

  const serializeCharacterSheet = (data) => {
    let markdown = `Name: ${data.name}\n`;
    markdown += `## Vitals\n\n\n\n`;
    markdown += `| key               |                 value |\n`;
    markdown += `| ----------------- | --------------------: |\n`;
    Object.entries(data.vitals).forEach(([key, value]) => {
      markdown += `| ${key.padEnd(17)} | ${String(value).padStart(21)} |\n`;
    });

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

    markdown += `\n\n\n## Bending Slots\n`;
    markdown += `You can always only use maximum half of you current Bending slots (rounded up so if you have 3 left you can either spend 2 and then 1 or only 1 but 3 times)\n\n`;
    markdown += `| Slot                   |                    Amount |\n`;
    markdown += `| ---------------------- | ------------------------: |\n`;
    Object.entries(data.slots).forEach(([key, value]) => {
      markdown += `| ${key.padEnd(22)} | ${String(value).padStart(25)} |\n`;
    });

    markdown += `\n## Water charges\n`;
    markdown += `You can use maximum of 2 \\* water level water charges for any Move.\n\n`;
    markdown += `| Water charge type          |                          value |\n`;
    markdown += `| -------------------------- | -----------------------------: |\n`;
    // Filter out Environmental water charge from serialization - it's stored globally
    Object.entries(data.waterCharges).forEach(([key, value]) => {
      if (key !== 'Environmental water charge') {
        markdown += `| ${key.padEnd(26)} | ${String(value).padStart(30)} |\n`;
      }
    });

    markdown += `\n\n\n#${data.name.replace(/\s+/g, '_')} #Character_Sheet\n`;

    return markdown;
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const markdown = serializeCharacterSheet(characterData);
      
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

  return (
    <div className={`character-sheet ${lightMode ? 'light-mode' : ''}`}>
      <div className="character-header">
        <h1>{characterData.name || 'Character Sheet'}</h1>
        <div className="header-buttons">
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

      {/* Vitals Section - All fields editable except max_hp */}
      <section className="character-section">
        <h2>Vitals</h2>
        
        {/* Large HP Bar Display */}
        {characterData.vitals.current_hp !== undefined && characterData.vitals.max_hp !== undefined && (
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
              {(() => {
                const currentHp = parseFloat(characterData.vitals.current_hp) || 0;
                const maxHp = parseFloat(characterData.vitals.max_hp) || 0;
                const hpPercentage = maxHp > 0 ? Math.max(0, Math.min(100, (currentHp / maxHp) * 100)) : 0;
                
                const getHpColor = (percent) => {
                  if (percent > 75) return '#4ec9b0'; // Healthy green-cyan
                  if (percent > 50) return '#dcdcaa'; // Yellow
                  if (percent > 25) return '#ce9178'; // Orange
                  return '#f48771'; // Critical red
                };
                const hpColor = getHpColor(hpPercentage);
                
                return (
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
                );
              })()}
            </div>
          </div>
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
      </section>

      {/* Core Stats Section - Read-only */}
      <section className="character-section">
        <h2>Core Stats</h2>
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
      </section>

      {/* Bending Levels Section */}
      <section className="character-section">
        <h2>Bending Levels</h2>
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
      </section>

      {/* Defense Section */}
      <section className="character-section">
        <h2>Defensive Stats</h2>
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
      </section>

      {/* Bending Slots, Water Charges & Consumable Resources */}
      <section className="character-section">
        <h2>Bending Slots, Water Charges & Consumable Resources</h2>
        <p className="section-note">
          You can always only use maximum half of your current Bending slots 
          (rounded up so if you have 3 left you can either spend 2 and then 1 or only 1 but 3 times).
          You can use maximum of 2 * water level water charges for any Move.
        </p>
        
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

        {/* Other slots (non-numeric or empty) - excluding consumables tracked with checkboxes */}
        {Object.entries(characterData.slots).some(([key, value]) => {
          // Exclude slots that are in "current/max" format (tracked by checkboxes)
          const slashMatch = String(value).match(/^\d+\s*\/\s*\d+$/);
          if (slashMatch) return false;
          
          const numValue = parseInt(value);
          return isNaN(numValue) || numValue <= 0 || value === '';
        }) && (
          <div className="stat-grid stat-grid-3" style={{ marginTop: '20px' }}>
            {Object.entries(characterData.slots)
              .filter(([key, value]) => {
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
      </section>
    </div>
  );
};

export default CharacterSheet;
