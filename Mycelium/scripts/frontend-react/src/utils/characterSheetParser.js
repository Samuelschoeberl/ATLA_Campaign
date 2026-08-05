export const CONDITION_NAMES = [
  'Bleeding out',
  'Blinded',
  'Dazed',
  'Immobilised',
  'Paralysed',
  'Prone',
  'Slowed',
  'Exhausted',
  'Empowered',
  'Quickened',
  'Armor Surge',
  'Barrier Surge',
  'Harmonic Flow'
];

/**
 * Load NPC state JSON file (stores current HP, slots, water charges)
 * Path pattern: NPCs/temp_token_<id>_<slug>_state.json
 */
export const loadNpcState = async (sheetPath, apiBaseUrl) => {
  if (!sheetPath) return null;
  
  // Convert sheet path to state JSON path
  // e.g., NPCs/temp_token_123_soldier_character_sheet.md -> NPCs/temp_token_123_soldier_state.json
  const statePath = sheetPath
    .replace(/_character_sheet\.md$/, '_state.json')
    .replace(/\.md$/, '_state.json');
  
  try {
    const response = await fetch(`${apiBaseUrl}/player_root/${encodeURIComponent(statePath)}`);
    if (!response.ok) {
      // State file doesn't exist yet - this is normal for new NPCs
      return null;
    }
    
    const data = await response.json();
    return data.content ? JSON.parse(data.content) : null;
  } catch (err) {
    console.warn('Failed to load NPC state:', err);
    return null;
  }
};

/**
 * Save NPC state JSON file
 */
export const saveNpcState = async (sheetPath, state, apiBaseUrl) => {
  if (!sheetPath || !state) return false;
  
  const statePath = sheetPath
    .replace(/_character_sheet\.md$/, '_state.json')
    .replace(/\.md$/, '_state.json');
  
  try {
    const response = await fetch(`${apiBaseUrl}/player_root/${encodeURIComponent(statePath)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: JSON.stringify(state, null, 2) })
    });
    
    return response.ok;
  } catch (err) {
    console.error('Failed to save NPC state:', err);
    return false;
  }
};

/**
 * Parse vitals + conditions using the same rules as CharacterSheet.jsx
 * Returns numeric HP and a normalized conditions array.
 * If npcState is provided, it will override consumable values from the sheet.
 */
export const parseSheetVitalsAndConditions = (markdownContent, npcState = null) => {
  const result = {
    name: '',
    currentHp: undefined,
    maxHp: undefined,
    conditions: [], // array of condition names that are active
    vitals: {},
    defensive: {},
    slots: {},
    waterCharges: {}
  };

  if (!markdownContent) return result;

  // Name line
  const nameMatch = markdownContent.match(/^Name:\s*(.+)$/m);
  if (nameMatch) {
    result.name = nameMatch[1].trim();
  }

  // Vitals table
  const vitalsMatch = markdownContent.match(/## Vitals\s*\n\n([\s\S]*?)\n\n##/);
  if (vitalsMatch) {
    const tableContent = vitalsMatch[1];
    const rows = tableContent.split('\n').filter(line => line.trim() && !line.includes('---'));
    rows.forEach(row => {
      const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
      if (cells.length >= 2 && cells[0] !== 'key') {
        result.vitals[cells[0]] = cells[1];
        if (cells[0] === 'current_hp') {
          const parsed = parseFloat(cells[1]);
          if (!Number.isNaN(parsed)) result.currentHp = parsed;
        }
        if (cells[0] === 'max_hp') {
          const parsed = parseFloat(cells[1]);
          if (!Number.isNaN(parsed)) result.maxHp = parsed;
        }
      }
    });
  }

  // Defensive table (optional)
  const defensiveMatch = markdownContent.match(/## Defensive\s*\n\n([\s\S]*?)\n\n##/);
  if (defensiveMatch) {
    const rows = defensiveMatch[1].split('\n').filter(line => line.trim() && !line.includes('---'));
    rows.forEach(row => {
      const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
      if (cells.length >= 2 && cells[0] !== 'key') {
        const val = parseFloat(cells[1]);
        result.defensive[cells[0]] = Number.isNaN(val) ? 0 : val;
      }
    });
  }

  // Conditions table (yes/no)
  const conditionsMatch = markdownContent.match(/## Conditions\s*\n\n([\s\S]*?)(?:\n\n##|\n#|$)/);
  if (conditionsMatch) {
    const rows = conditionsMatch[1].split('\n').filter(line => line.trim() && !line.includes('---'));
    rows.forEach(row => {
      const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
      if (cells.length >= 2 && cells[0] !== 'Condition') {
        const conditionName = cells[0];
        const activeRaw = cells[1].toLowerCase();
        const isActive = ['yes', 'true', '1', 'active', 'x', 'y'].includes(activeRaw);
        if (isActive) {
          result.conditions.push(conditionName);
        }
      }
    });
  }

  // Hash-tagged conditions (#condition_Bleeding_out)
  const conditionPattern = /#condition[_\s-](\w+)/gi;
  let match;
  while ((match = conditionPattern.exec(markdownContent)) !== null) {
    const conditionName = match[1].replace(/_/g, ' ');
    if (!result.conditions.includes(conditionName)) {
      result.conditions.push(conditionName);
    }
  }

  // Parse Bending Slots table
  const slotsMatch = markdownContent.match(/## Bending Slots\s*\n[^#]*?\n\n([\s\S]*?)\n\n##/i);
  if (slotsMatch) {
    const rows = slotsMatch[1].split('\n').filter(line => line.trim() && !line.includes('---'));
    rows.forEach(row => {
      const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
      if (cells.length >= 2 && cells[0] !== 'Slot') {
        result.slots[cells[0]] = cells[1];
      }
    });
  }

  // Parse Water charges table
  const waterMatch = markdownContent.match(/## Water charges\s*\n[^#]*?\n\n([\s\S]*?)\n\n##/i);
  if (waterMatch) {
    const rows = waterMatch[1].split('\n').filter(line => line.trim() && !line.includes('---'));
    rows.forEach(row => {
      const cells = row.split('|').map(cell => cell.trim()).filter(Boolean);
      if (cells.length >= 2 && cells[0] !== 'Water charge type') {
        result.waterCharges[cells[0]] = cells[1];
      }
    });
  }

  // Override with NPC state if provided (current consumable values)
  if (npcState) {
    if (npcState.currentHp !== undefined) result.currentHp = npcState.currentHp;
    if (npcState.slots) result.slots = { ...result.slots, ...npcState.slots };
    if (npcState.waterCharges) result.waterCharges = { ...result.waterCharges, ...npcState.waterCharges };
    if (npcState.conditions) result.conditions = npcState.conditions;
  }

  return result;
};

/**
 * Build a minimal but CharacterSheet-compatible markdown document.
 */
export const buildBasicCharacterSheet = ({
  name,
  currentHp = 100,
  maxHp = 100,
  conditions = [],
  defensive = {},
  type = 'npc'
}) => {
  const conditionSet = new Set(conditions.map(c => (typeof c === 'string' ? c : c?.name).trim()).filter(Boolean));

  const pickDef = (key) => (Number.isFinite(defensive[key]) ? defensive[key] : 0);

  let markdown = '';
  markdown += `Name: ${name || 'Unnamed Token'}\n`;
  markdown += `## Vitals\n\n`;
  markdown += `| key               |                 value |\n`;
  markdown += `| ----------------- | --------------------: |\n`;
  markdown += `| current_hp        | ${String(Math.round(currentHp)).padStart(21)} |\n`;
  markdown += `| max_hp            | ${String(Math.round(maxHp)).padStart(21)} |\n`;
  markdown += `| initiative        | ${String(0).padStart(21)} |\n`;
  markdown += `| type              | ${String(type).padStart(21)} |\n`;
  markdown += `\n## Core Stats\n\n`;
  markdown += `| Stat         |   Value |\n`;
  markdown += `| ------------ | ------: |\n`;
  ['Strength','Dexterity','Constitution','Intelligence','Wisdom','Charisma'].forEach(stat => {
    markdown += `| ${stat.padEnd(12)} | ${String(0).padStart(6)} |\n`;
  });
  markdown += `\n## Bending Levels\n\n`;
  markdown += `Total Bending Level: 0\n\n`;
  markdown += `| Element | Level | Attack Roll | DC |\n`;
  markdown += `| ------- | ----: | ----------- | -- |\n`;
  ['Air','Water','Earth','Fire','Spirit'].forEach(elem => {
    markdown += `| ${elem.padEnd(6)} | ${String(0).padStart(4)} |             |    |\n`;
  });
  markdown += `\n## Defensive\n\n`;
  markdown += `| key             |   base |\n`;
  markdown += `| --------------- | -----: |\n`;
  const defensiveKeys = [
    'Evasion',
    'Barrier',
    'General Armor',
    'Physical Armor',
    'Fire Armor',
    'Ice Armor',
    'Spirit Armor'
  ];
  defensiveKeys.forEach(key => {
    markdown += `| ${key.padEnd(15)} | ${String(pickDef(key)).padStart(5)} |\n`;
  });

  markdown += `\n## Bending Slots\n\n`;
  markdown += `| Slot                 | Amount |\n`;
  markdown += `| -------------------- | -----: |\n`;
  ['Airbending slot','Waterbending slot','Earthbending slot','Firebending slot','Spirit bending slot'].forEach(slot => {
    markdown += `| ${slot.padEnd(20)} | ${String(0).padStart(5)} |\n`;
  });
  markdown += `| Bonus bending slots  | ${String(0).padStart(5)} |\n`;

  markdown += `\n## Water charges\n\n`;
  markdown += `You can use maximum of 2 * water level water charges for any Move.\n\n`;
  markdown += `| Water charge type          |                          value |\n`;
  markdown += `| -------------------------- | -----------------------------: |\n`;
  markdown += `| Environmental water charge | ${'0/0'.padStart(29)} |\n`;
  markdown += `| Waterbottle charge         | ${'0/0'.padStart(29)} |\n`;
  markdown += `| Bonus water charges        | ${'0'.padStart(29)} |\n`;

  markdown += `\n## Conditions\n\n`;
  markdown += `| Condition        | Active |\n`;
  markdown += `| ---------------- | ------ |\n`;
  CONDITION_NAMES.forEach(cond => {
    const active = conditionSet.has(cond) ? 'yes' : 'no';
    markdown += `| ${cond.padEnd(16)} | ${active.padEnd(6)} |\n`;
  });

  markdown += `\n#${(name || 'Token').replace(/\s+/g, '_')} #Character_Sheet\n`;
  return markdown;
};

/**
 * Parse character sheet markdown to extract structured data
 * Now includes vitals/conditions parsing consistent with CharacterSheet.
 */
export const parseCharacterSheet = (markdownContent) => {
  if (!markdownContent) return null;

  const data = {
    name: '',
    vitals: {},
    coreStats: {},
    conditions: [],
    bendingLevels: {},
    defensive: {},
    bendingSlots: {},
    waterCharges: {},
    conditionsMap: {}
  };

  const lines = markdownContent.split('\n');
  
  // Extract name from first heading
  for (const line of lines) {
    if (line.startsWith('Name:')) {
      data.name = line.replace('Name:', '').trim();
      break;
    }
    if (line.startsWith('# ') && !data.name) {
      data.name = line.replace('# ', '').trim();
      break;
    }
  }

  // Parse tables
  let currentSection = null;
  let inTable = false;
  let tableHeaders = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Detect section headers
    if (line.startsWith('## ')) {
      currentSection = line.replace('## ', '').trim().toLowerCase();
      inTable = false;
      continue;
    }

    // Detect table start (header row)
    if (line.startsWith('|') && line.endsWith('|')) {
      const nextLine = lines[i + 1]?.trim();
      
      // Check if next line is separator (---|---|---)
      if (nextLine && nextLine.match(/^\|[\s\-:]+\|/)) {
        inTable = true;
        tableHeaders = line
          .split('|')
          .map(h => h.trim())
          .filter(h => h);
        i++; // Skip separator line
        continue;
      }
    }

    // Parse table rows
    if (inTable && line.startsWith('|') && line.endsWith('|')) {
      const values = line
        .split('|')
        .map(v => v.trim())
        .filter(v => v);

      if (values.length === tableHeaders.length) {
        const rowData = {};
        tableHeaders.forEach((header, idx) => {
          rowData[header.toLowerCase()] = values[idx];
        });

        // Store data based on current section
        switch (currentSection) {
          case 'vitals':
            if (rowData.key) {
              data.vitals[rowData.key] = rowData.value;
            }
            break;
          
          case 'core stats':
            if (rowData.stat) {
              data.coreStats[rowData.stat] = parseFloat(rowData.value) || 0;
            }
            break;
          
          case 'bending levels':
            if (rowData.element) {
              data.bendingLevels[rowData.element.toLowerCase()] = {
                level: parseFloat(rowData.level) || 0,
                attackRoll: rowData['attack roll'],
                dc: rowData.dc
              };
            }
            break;
          
          case 'defensive':
            if (rowData.key) {
              data.defensive[rowData.key] = parseFloat(rowData.base) || 0;
            }
            break;
          
          case 'bending slots':
            if (rowData.slot) {
              data.bendingSlots[rowData.slot] = rowData.amount;
            }
            break;
          
          case 'water charges':
            if (rowData['water charge type']) {
              data.waterCharges[rowData['water charge type']] = rowData.value;
            }
            break;
          
          case 'conditions':
            if (rowData.condition) {
              const conditionName = rowData.condition;
              const isActive = rowData.active?.toLowerCase();
              const activeBool = ['yes', 'true', '1', 'active', 'x', 'y'].includes(isActive);
              data.conditionsMap[conditionName] = activeBool;
              if (activeBool) {
                data.conditions.push(conditionName);
              }
            }
            break;
        }
      }
    } else {
      inTable = false;
    }
  }

  // Parse conditions from tags or explicit condition section
  const conditionPattern = /#condition[_\s-](\w+)/gi;
  let match;
  while ((match = conditionPattern.exec(markdownContent)) !== null) {
    const conditionName = match[1].replace(/_/g, ' ');
    if (!data.conditions.find(c => c === conditionName)) {
      data.conditions.push(conditionName);
      data.conditionsMap[conditionName] = true;
    }
  }

  return data;
};

/**
 * Fetch and parse character sheet from file path
 * 
 * @param {string} characterName - Name of the character
 * @param {string} apiBaseUrl - Base URL for API
 * @returns {Promise<Object>} Parsed character sheet data
 */
export const fetchCharacterSheet = async (characterName, apiBaseUrl) => {
  try {
    // Try player root first
    let path = `Player Root/PCs/${characterName}/${characterName} character sheet.md`;
    let response = await fetch(`${apiBaseUrl}/player_root/${encodeURIComponent(path)}`);
    
    if (!response.ok) {
      // Try DM root
      path = `Dms Root/NPCs/${characterName}/${characterName} character sheet.md`;
      response = await fetch(`${apiBaseUrl}/file/${encodeURIComponent(path)}`);
    }
    
    if (!response.ok) {
      throw new Error(`Character sheet not found for ${characterName}`);
    }
    
    const content = await response.text();
    return parseCharacterSheet(content);
  } catch (error) {
    console.error(`Error fetching character sheet for ${characterName}:`, error);
    return null;
  }
};

/**
 * Load condition descriptions from markdown files
 * 
 * @param {string} apiBaseUrl - Base URL for API
 * @returns {Promise<Object>} Map of condition names to descriptions
 */
export const loadConditionDescriptions = async (apiBaseUrl) => {
  const conditionFiles = {
    'Bleeding out': 'Bleeding_out.md',
    'Blinded': 'Blinded.md',
    'Dazed': 'Dazed.md',
    'Immobilised': 'Immobilised.md',
    'Paralysed': 'Paralysed.md',
    'Prone': 'Prone.md',
    'Slowed': 'Slowed.md',
    'Empowered': 'Empowered.md',
    'Armor Surge': 'Armor_Surge.md',
    'Barrier Surge': 'Barrier_Surge.md',
    'Harmonic Flow': 'Harmonic_Flow.md',
    'Exhausted': 'Exhausted.md'
  };

  const descriptions = {};
  
  await Promise.all(
    Object.entries(conditionFiles).map(async ([conditionName, fileName]) => {
      try {
        const path = `Player Root/Rules/core rules/Conditions/${fileName}`;
        const response = await fetch(`${apiBaseUrl}/player_root/${encodeURIComponent(path)}`);
        
        if (response.ok) {
          // API returns JSON with a 'content' field
          const data = await response.json();
          const content = data.content || '';
          
          // Extract description (remove metadata tags like #condition #Curse)
          const cleanContent = content
            .split('\n')
            .filter(line => !line.trim().startsWith('#') || line.trim().startsWith('##'))
            .join('\n')
            .trim();
          descriptions[conditionName] = cleanContent;
        }
      } catch (error) {
        console.error(`Error loading condition ${conditionName}:`, error);
      }
    })
  );
  
  return descriptions;
};

/**
 * Update character sheet with new HP and condition values
 * 
 * @param {string} characterName - Name of the character
 * @param {Object} updates - Object containing currentHp, maxHp, and/or conditions array
 * @param {string} apiBaseUrl - Base URL for API
 * @returns {Promise<boolean>} True if update was successful
 */
export const updateCharacterSheet = async (characterName, updates, apiBaseUrl, options = {}) => {
  try {
    const endpoint = options.endpoint || 'player_root';
    const relativePath = options.sheetPath 
      ? options.sheetPath.replace(/^Player Root\//i, '') 
      : `PCs/${characterName}/${characterName} character sheet.md`;

    // Fetch current character sheet
    const response = await fetch(`${apiBaseUrl}/${endpoint}/${encodeURIComponent(relativePath)}`);
    
    if (!response.ok) {
      console.warn(`Character sheet not found for ${characterName}`);
      return false;
    }
    
    const data = await response.json();
    let content = data.content || '';
    
    // Update current_hp if provided
    if (updates.currentHp !== undefined) {
      content = content.replace(
        /(\|\s*current_hp\s*\|\s*)\d+(\s*\|)/,
        `$1${Math.round(updates.currentHp)}$2`
      );
    }
    
    // Update max_hp if provided
    if (updates.maxHp !== undefined) {
      content = content.replace(
        /(\|\s*max_hp\s*\|\s*)\d+(\s*\|)/,
        `$1${Math.round(updates.maxHp)}$2`
      );
    }
    
    // Update conditions if provided
    if (updates.conditions) {
      // Create a map of condition names to active status
      const conditionMap = {};
      updates.conditions.forEach(cond => {
        const name = cond.name || cond;
        conditionMap[name] = true;
      });
      
      // Update each condition in the markdown
      const conditionNames = [
        'Bleeding out', 'Blinded', 'Dazed', 'Immobilised', 'Paralysed',
        'Prone', 'Slowed', 'Exhausted', 'Empowered', 'Quickened',
        'Armor Surge', 'Barrier Surge', 'Harmonic Flow'
      ];
      
      conditionNames.forEach(conditionName => {
        const isActive = conditionMap[conditionName] || false;
        const status = isActive ? 'yes' : 'no';
        
        // Match condition row and update status
        const regex = new RegExp(
          `(\\|\\s*${conditionName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\|\\s*)(yes|no)(\\s*\\|)`,
          'i'
        );
        content = content.replace(regex, `$1${status}$3`);
      });
    }

    // Update defensive stats if provided
    if (updates.defensive) {
      Object.entries(updates.defensive).forEach(([key, value]) => {
        const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const numericVal = Number.isFinite(value) ? value : 0;
        const regex = new RegExp(`(\\|\\s*${escapedKey}\\s*\\|\\s*)(-?\\d+(?:\\.\\d+)?)?(\\s*\\|)`, 'i');
        if (regex.test(content)) {
          content = content.replace(regex, `$1${numericVal}$3`);
        }
      });
    }
    
    // Save updated content
    const saveResponse = await fetch(`${apiBaseUrl}/${endpoint}/${encodeURIComponent(relativePath)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    
    if (!saveResponse.ok) {
      throw new Error('Failed to save character sheet');
    }
    
    console.log(`Character sheet updated for ${characterName}`);
    return true;
  } catch (error) {
    console.error(`Error updating character sheet for ${characterName}:`, error);
    return false;
  }
};
