import React, { useState, useEffect, useRef } from 'react';
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
    const diceRegex = /(\d+)d(\d+)/gi;
    let expression = diceString.trim();
    let rolls = [];
    let modifierParts = [];
    
    const originalExpression = expression;
    
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
    
    const modifierString = originalExpression.replace(diceRegex, '').trim();
    if (modifierString) {
      const parts = modifierString.split(/([+\-])/).filter(p => p.trim());
      let currentModifier = '';
      for (let i = 0; i < parts.length; i++) {
        const part = parts[i].trim();
        if (part === '+' || part === '-') {
          currentModifier = part;
        } else if (part && currentModifier) {
          modifierParts.push({ operator: currentModifier, value: part });
          currentModifier = '';
        }
      }
    }
    
    expression = expression.replace(/\s+/g, '');
    expression = expression.replace(/[^0-9+\-*/().]/g, '');
    
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
};

// Helper to convert hex to rgba
const hexToRgba = (hex, alpha) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const ShapeshiftingForm = ({ file, lightMode = false }) => {
  const [content, setContent] = useState('');
  const [formData, setFormData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);
  const [imageUrl, setImageUrl] = useState(null);

  useEffect(() => {
    if (file) {
      loadShapeshiftingForm();
    }
  }, [file]);

  // Resolve image path when formData.image changes
  useEffect(() => {
    if (formData && formData.image) {
      resolveImagePath(formData.image);
    }
  }, [formData?.image]);

  const resolveImagePath = async (imageName) => {
    if (!imageName) return;

    // Get the directory of the current file
    const fileDir = file.path.substring(0, file.path.lastIndexOf('/'));
    
    // Build possible paths
    const possiblePaths = [];

    // First priority: shared Rules folder (where images are commonly stored)
    possiblePaths.push(`Rules/Bending Rules/Spirit/Shapeshifting Pics/${imageName}`);

    // If the file is in "Shapeshifting Forms", look in "Shapeshifting Pics" at the Spirit level
    if (fileDir.includes('Spiritbending Moves/Shapeshifting Forms')) {
      // Go up to Spirit level and look in Shapeshifting Pics
      const spiritPath = fileDir.split('Spiritbending Moves')[0];
      possiblePaths.push(`${spiritPath}Shapeshifting Pics/${imageName}`);
    }

    // Add common relative paths
    possiblePaths.push(
      `${fileDir}/${imageName}`,
      `${fileDir}/../${imageName}`,
      `${fileDir}/../../${imageName}`,
      `${fileDir}/../../Shapeshifting Pics/${imageName}`,
      // Other known image directories
      `NPCs/${imageName}`,
      `visuals/${imageName}`,
      imageName // Fallback: just the filename
    );

    // Try each path until one works (silently)
    for (const path of possiblePaths) {
      try {
        // Encode path segments individually to preserve forward slashes
        const encodedPath = path.split('/').map(segment => encodeURIComponent(segment)).join('/');
        const testUrl = `${API_BASE_URL}/player_root/${encodedPath}`;
        // Use a silent fetch without logging each attempt
        const response = await fetch(testUrl, { 
          method: 'HEAD',
          // Add signal for timeout to fail fast
          signal: AbortSignal.timeout(1000)
        }).catch(() => null);
        
        if (response && response.ok) {
          setImageUrl(testUrl);
          return;
        }
      } catch (err) {
        // Silently continue trying other paths
      }
    }
    
    // Fallback: use the first attempt (even if it might 404)
    const encodedPath = possiblePaths[0].split('/').map(segment => encodeURIComponent(segment)).join('/');
    const fallbackUrl = `${API_BASE_URL}/player_root/${encodedPath}`;
    setImageUrl(fallbackUrl);
  };

  const loadShapeshiftingForm = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const normalizedPath = (file.path || '').replace(/^Player Root\//i, '');
      const segments = normalizedPath.split('/').map(s => encodeURIComponent(s)).join('/');
      const url = `${API_BASE_URL}/player_root/${segments}`;
      
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Failed to fetch file: ${response.status}`);
      }
      
      const data = await response.json();
      setContent(data.content || '');
      const parsed = parseShapeshiftingForm(data.content || '');
      setFormData(parsed);
    } catch (err) {
      setError(err.message);
      console.error('Error loading shapeshifting form:', err);
    } finally {
      setLoading(false);
    }
  };

  const parseShapeshiftingForm = (markdown) => {
    const data = {
      name: '',
      tags: [],
      transformationCost: null,
      bendingLevels: [],
      image: null,
      size: null,
      onTransform: [],
      vitalityStats: {
        evasion: null,
        armor: [],
        hp: null
      },
      stats: {},
      movement: [],
      specialAbilities: [],
      attacks: [],
      otherContent: [],  // Store unrecognized content
      rawContent: markdown
    };

    const lines = markdown.split('\n');
    const processedLines = new Set();  // Track which lines we've processed
    
    // Extract tags
    const tagLines = lines.filter(line => line.trim().startsWith('#') && !line.trim().startsWith('##'));
    data.tags = tagLines.flatMap(line => 
      line.trim().split(/\s+/).filter(tag => tag.startsWith('#')).map(tag => tag.substring(1))
    );
    // Mark tag lines as processed
    tagLines.forEach(line => processedLines.add(line));

    // Extract name from file or heading
    const headingLine = lines.find(line => line.trim().startsWith('# ') && !line.trim().startsWith('##'));
    if (headingLine) {
      data.name = headingLine.replace(/^#+\s*/, '').trim();
      processedLines.add(headingLine);
    }

    // Parse transformation cost - handles both "Transformation Points:" and "Transformation Points cost:"
    const costLine = lines.find(line => {
      const lower = line.toLowerCase();
      return (lower.includes('transformation points:') || lower.includes('transformation points cost:'));
    });
    if (costLine) {
      // Flexible regex - handles markdown bold markers and various formats
      // Matches: "**Transformation Points:** 2" or "Transformation Points cost: 2" etc.
      const costMatch = costLine.match(/Transformation\s+Points[^:]*:\*?\*?\s*(\d+)/i);
      if (costMatch) {
        data.transformationCost = parseInt(costMatch[1]);
        processedLines.add(costLine);
      }
    }

    // Parse bending levels
    let inBendingLevels = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().toLowerCase().startsWith('bending levels:')) {
        inBendingLevels = true;
        processedLines.add(line);
        continue;
      }
      if (inBendingLevels) {
        if (line.trim() === '' || line.trim().startsWith('![[')) {
          inBendingLevels = false;
          continue;
        }
        // Parse lines like "[[Earth]] (0): Level 1" OR "Earth: Level 1"
        const match1 = line.match(/\[\[([^\]]+)\]\]\s*\((\d+)\):\s*Level\s*(\d+)/i);
        const match2 = line.match(/^\s*([A-Za-z]+):\s*Level\s*(\d+)/i);
        if (match1) {
          data.bendingLevels.push({
            element: match1[1],
            value: parseInt(match1[2]),
            level: parseInt(match1[3])
          });
          processedLines.add(line);
        } else if (match2) {
          data.bendingLevels.push({
            element: match2[1],
            value: 0,  // Default value when not specified
            level: parseInt(match2[2])
          });
          processedLines.add(line);
        }
      }
    }

    // Parse image
    const imageLine = lines.find(line => line.trim().startsWith('![['));
    if (imageLine) {
      const imageMatch = imageLine.match(/!\[\[([^\]]+)\]\]/);
      if (imageMatch) {
        data.image = imageMatch[1];
        processedLines.add(imageLine);
      }
    }

    // Parse size
    const sizeLine = lines.find(line => line.trim().toLowerCase().includes('**size:**'));
    if (sizeLine) {
      const sizeMatch = sizeLine.match(/\*\*Size:\*\*\s*(.+)/i);
      if (sizeMatch) {
        data.size = sizeMatch[1].trim();
        processedLines.add(sizeLine);
      }
    }

    // Parse On Transform effects - handles both "On Transform:" and "On Transformation:"
    let inOnTransform = false;
    let onTransformItemCount = 0;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim().toLowerCase();
      // Remove markdown formatting for comparison
      const cleanedForCheck = trimmed.replace(/\*\*/g, '').replace(/\*/g, '');
      
      // Match "On Transform:" or "On Transformation:" (can be in list format like "- **On Transform:**")
      if (cleanedForCheck.includes('on transform:') || cleanedForCheck.includes('on transformation:')) {
        inOnTransform = true;
        onTransformItemCount = 0;
        processedLines.add(line);
        continue;
      }
      
      if (inOnTransform) {
        // Empty lines are ok, just skip them
        if (line.trim() === '') {
          continue;
        }
        
        // Check if this is a new section header
        const isNewSection = (trimmed.includes('vitality and defense stats:') || 
                             trimmed.includes('**movement:**') ||
                             (trimmed.match(/^-\s*\*\*[^*]+\*\*:/) && 
                              !cleanedForCheck.includes('on transform') && 
                              !cleanedForCheck.includes('on transformation')));
        
        // End the section if we hit a new section AND we've already processed at least one item
        if (isNewSection && onTransformItemCount > 0) {
          inOnTransform = false;
          // Don't continue - let other parsers handle this line
        } else if (line.trim().startsWith('-')) {
          if (!isNewSection) {
            // This is a content line within On Transform
            // Format 1: "- **Name**: description" (named effect)
            const namedEffect = line.match(/^\s*-\s*\*\*([^*:]+):\*\*\s*(.+)/);
            if (namedEffect) {
              data.onTransform.push({
                name: namedEffect[1].trim(),
                description: namedEffect[2].trim()
              });
              processedLines.add(line);
              onTransformItemCount++;
            } 
            // Format 2: "- description" (unnamed effect, just plain text)
            else {
              const plainEffect = line.match(/^\s*-\s*(.+)/);
              if (plainEffect) {
                data.onTransform.push({
                  name: null,  // No specific name
                  description: plainEffect[1].trim()
                });
                processedLines.add(line);
                onTransformItemCount++;
              }
            }
          }
        }
      }
    }

    // Parse Vitality and Defense Stats
    let inVitalityStats = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().toLowerCase().includes('vitality and defense stats:')) {
        inVitalityStats = true;
        processedLines.add(line);
        continue;
      }
      if (inVitalityStats) {
        if (line.trim() === '' || line.trim().startsWith('|')) {
          // Check if we've hit the stats table
          if (line.trim().startsWith('|')) {
            inVitalityStats = false;
          }
          continue;
        }
        
        // Parse Evasion
        if (line.toLowerCase().includes('evasion:')) {
          const evasionMatch = line.match(/evasion:\s*(\d+)/i);
          if (evasionMatch) {
            data.vitalityStats.evasion = parseInt(evasionMatch[1]);
            processedLines.add(line);
          }
        }
        
        // Parse Armor (can be nested)
        if (line.toLowerCase().includes('armor:') && !line.toLowerCase().includes('general armor') && !line.toLowerCase().includes('physical armor')) {
          // This is the armor header, armor values come on next lines
          processedLines.add(line);
          continue;
        }
        if (line.trim().startsWith('-') && (line.includes('[[') && line.includes('Armor'))) {
          const armorMatch = line.match(/(\d+)\s*\[\[([^\]]+Armor[^\]]*)\]\]/);
          if (armorMatch) {
            data.vitalityStats.armor.push({
              value: parseInt(armorMatch[1]),
              type: armorMatch[2]
            });
            processedLines.add(line);
          }
        }
        // Also handle standalone armor lines like "- 3 General Armor"
        if (line.trim().startsWith('-') && line.match(/(\d+)\s+(General|Physical|Magical|Elemental)\s+Armor/i)) {
          const armorMatch = line.match(/(\d+)\s+(General|Physical|Magical|Elemental)\s+Armor/i);
          if (armorMatch) {
            data.vitalityStats.armor.push({
              value: parseInt(armorMatch[1]),
              type: `${armorMatch[2]} Armor`
            });
            processedLines.add(line);
          }
        }
        
        // Parse HP
        if (line.toLowerCase().includes('hp:')) {
          const hpMatch = line.match(/hp:\s*(\d+)/i);
          if (hpMatch) {
            data.vitalityStats.hp = parseInt(hpMatch[1]);
            processedLines.add(line);
          }
        }
      }
    }

    // Parse Stats table
    let inStatsTable = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().startsWith('|') && line.toLowerCase().includes('stat')) {
        inStatsTable = true;
        processedLines.add(line);
        continue;
      }
      if (inStatsTable) {
        if (line.trim() === '' || !line.trim().startsWith('|')) {
          inStatsTable = false;
          continue;
        }
        // Skip separator line
        if (line.includes('---')) {
          processedLines.add(line);
          continue;
        }
        // Parse stat rows like "| [[Strength]] (3)     | 6         |" OR "| Strength     | -2         |"
        const statMatch1 = line.match(/\|\s*\[\[([^\]]+)\]\]\s*\((-?\d+)\)\s*\|\s*(-?\d+)\s*\|/);
        const statMatch2 = line.match(/\|\s*([A-Za-z]+)\s*\|\s*(-?\d+)\s*\|/);
        if (statMatch1) {
          data.stats[statMatch1[1]] = {
            baseValue: parseInt(statMatch1[2]),
            formValue: parseInt(statMatch1[3])
          };
          processedLines.add(line);
        } else if (statMatch2) {
          data.stats[statMatch2[1]] = {
            baseValue: 0,  // No base value in this format
            formValue: parseInt(statMatch2[2])
          };
          processedLines.add(line);
        }
      }
    }

    // Parse Movement
    let inMovement = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim().toLowerCase().includes('**movement:**')) {
        inMovement = true;
        processedLines.add(line);
        continue;
      }
      if (inMovement) {
        if (line.trim() === '' || line.trim().toLowerCase().includes('special abilities')) {
          if (line.trim().toLowerCase().includes('special abilities')) {
            inMovement = false;
          }
          continue;
        }
        if (line.trim().startsWith('-')) {
          const movementMatch = line.match(/^\s*-\s*(.+)/);
          if (movementMatch) {
            data.movement.push(movementMatch[1].trim().replace(/\.$/, ''));
            processedLines.add(line);
          }
        }
      }
    }

    // Parse Special Abilities (complex nested structure)
    let inSpecialAbilities = false;
    let currentAbility = null;
    let currentSubAbility = null;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      if (line.trim().toLowerCase().includes('**special abilities')) {
        inSpecialAbilities = true;
        processedLines.add(line);
        continue;
      }
      
      if (inSpecialAbilities) {
        // Check if we've reached Attacks section (it can be nested or standalone)
        if (line.trim().toLowerCase().startsWith('attacks:') || line.trim().toLowerCase().startsWith('- attacks:')) {
          if (currentSubAbility && currentAbility) {
            currentAbility.subAbilities.push(currentSubAbility);
            currentSubAbility = null;
          }
          if (currentAbility) {
            data.specialAbilities.push(currentAbility);
            currentAbility = null;
          }
          inSpecialAbilities = false;
          continue;
        }
        
        // Empty line might end current sub-ability
        if (line.trim() === '') {
          if (currentSubAbility && currentAbility) {
            currentAbility.subAbilities.push(currentSubAbility);
            currentSubAbility = null;
          }
          continue;
        }
        
        // Check for main ability (indented with "- **Name:**" with possible trailing content)
        const mainAbilityMatch = line.match(/^\s*-\s*\*\*([^*:]+):\*\*\s*(.*)$/);
        if (mainAbilityMatch) {
          if (currentSubAbility && currentAbility) {
            currentAbility.subAbilities.push(currentSubAbility);
            currentSubAbility = null;
          }
          if (currentAbility) {
            data.specialAbilities.push(currentAbility);
          }
          currentAbility = {
            name: mainAbilityMatch[1].trim(),
            tags: [],
            description: [],
            subAbilities: []
          };
          if (mainAbilityMatch[2].trim()) {
            currentAbility.description.push(mainAbilityMatch[2].trim());
          }
          processedLines.add(line);
          continue;
        }
        
        // Check for sub-ability (same pattern but indented more, like "**Name:**" or "**Name**: description")
        const subAbilityMatch = line.match(/^\s+\*\*([^*:]+):\*\*\s*(.*)$/);
        if (subAbilityMatch && currentAbility) {
          if (currentSubAbility) {
            currentAbility.subAbilities.push(currentSubAbility);
          }
          currentSubAbility = {
            name: subAbilityMatch[1].trim(),
            tags: [],
            description: subAbilityMatch[2].trim() || null
          };
          processedLines.add(line);
          continue;
        }
        
        // Check for tags within abilities (can be for main ability or sub-ability)
        if (line.trim().startsWith('#')) {
          const abilityTags = line.trim().split(/\s+/).filter(tag => tag.startsWith('#')).map(tag => tag.substring(1));
          if (currentSubAbility) {
            currentSubAbility.tags.push(...abilityTags);
          } else if (currentAbility) {
            currentAbility.tags.push(...abilityTags);
          }
          processedLines.add(line);
          continue;
        }
        
        // Otherwise it's description text
        if (line.trim().length > 0) {
          if (currentSubAbility) {
            // Add to sub-ability description
            if (currentSubAbility.description === null) {
              currentSubAbility.description = line.trim();
            } else {
              currentSubAbility.description += ' ' + line.trim();
            }
          } else if (currentAbility) {
            // Add to main ability description
            currentAbility.description.push(line.trim());
          }
          processedLines.add(line);
        }
      }
    }
    
    // Don't forget the last sub-ability and ability
    if (currentSubAbility && currentAbility) {
      currentAbility.subAbilities.push(currentSubAbility);
    }
    if (currentAbility) {
      data.specialAbilities.push(currentAbility);
    }

    // Parse Attacks (can be standalone or nested under Special Abilities)
    let inAttacks = false;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Match both "Attacks:" and "- Attacks:"
      if (line.trim().toLowerCase().startsWith('attacks:') || line.trim().toLowerCase().startsWith('- attacks:')) {
        inAttacks = true;
        processedLines.add(line);
        continue;
      }
      
      if (inAttacks) {
        // End attacks section on empty line followed by tags or end of special abilities section
        if (line.trim() === '') {
          continue;
        }
        if (line.trim().startsWith('#') && !line.includes(':')) {
          inAttacks = false;
          continue;
        }
        
        // Parse attack lines like "- **Powerful Swipe:** Melee Weapon Attack, 1d20 + 6 to hit, 2d6 +6 slashing damage."
        const attackMatch = line.match(/^\s*-\s*\*\*([^*:]+):\*\*\s*(.+)/);
        if (attackMatch) {
          data.attacks.push({
            name: attackMatch[1].trim(),
            description: attackMatch[2].trim()
          });
          processedLines.add(line);
        }
      }
    }

    // Collect any unprocessed content (lines not in specific sections)
    // This helps ensure no information is lost
    const contentLines = lines.filter(line => {
      const trimmed = line.trim();
      // Skip empty lines
      if (!trimmed) return false;
      // Skip if already processed
      if (processedLines.has(line)) {
        return false;
      }
      // Skip header lines
      if (trimmed.startsWith('# ') && !trimmed.startsWith('##')) return false;
      // Keep everything else that hasn't been explicitly processed
      return true;
    });
    
    // Store non-empty lines
    data.otherContent = contentLines
      .filter(line => line.trim().length > 0)
      .map(line => line.trim());

    return data;
  };

  // Helper to process text with variable references and dice notation
  const processText = (text) => {
    if (!text) return null;
    
    const variableRegex = /\[\[([^\]]+)\]\]\s*\(([^)]+)\)/g;
    const diceRegex = /\b(\d+d\d+(?:\s*[+\-]\s*\d+)*)\b/gi;
    
    let processedText = text
      .replace(/\\\*/g, '*')
      .replace(/\\_/g, '_')
      .replace(/\\\[/g, '[')
      .replace(/\\\]/g, ']')
      .replace(/\*\*\*([^\*]+?)\*\*\*/g, '$1')
      .replace(/\*\*([^\*]+?)\*\*/g, '$1')
      .replace(/\*([^\*\s][^\*]*?[^\*\s])\*/g, '$1')
      .replace(/__(.+?)__/g, '$1')
      .replace(/_([^_\s][^_]*?[^_\s])_/g, '$1');
    
    const parts = [];
    let lastIndex = 0;
    
    const varMatches = [];
    let varMatch;
    const varRegex = new RegExp(variableRegex.source, variableRegex.flags);
    while ((varMatch = varRegex.exec(processedText)) !== null) {
      varMatches.push({
        start: varMatch.index,
        end: varMatch.index + varMatch[0].length,
        name: varMatch[1],
        value: varMatch[2],
        fullMatch: varMatch[0]
      });
    }
    
    varMatches.forEach((vm) => {
      if (vm.start > lastIndex) {
        parts.push({ type: 'text', content: processedText.substring(lastIndex, vm.start) });
      }
      parts.push({
        type: 'variable',
        name: vm.name,
        value: vm.value
      });
      lastIndex = vm.end;
    });
    
    if (varMatches.length > 0) {
      if (lastIndex < processedText.length) {
        parts.push({ type: 'text', content: processedText.substring(lastIndex) });
      }
    } else {
      parts.push({ type: 'text', content: processedText });
    }
    
    const finalParts = [];
    parts.forEach(part => {
      if (part.type === 'variable') {
        finalParts.push(part);
      } else {
        const textContent = part.content;
        let textLastIndex = 0;
        const diceMatches = [];
        let diceMatch;
        const diceReg = new RegExp(diceRegex.source, diceRegex.flags);
        while ((diceMatch = diceReg.exec(textContent)) !== null) {
          diceMatches.push({
            start: diceMatch.index,
            end: diceMatch.index + diceMatch[0].length,
            dice: diceMatch[1]
          });
        }
        
        diceMatches.forEach(dm => {
          if (dm.start > textLastIndex) {
            finalParts.push({ type: 'text', content: textContent.substring(textLastIndex, dm.start) });
          }
          finalParts.push({ type: 'dice', dice: dm.dice });
          textLastIndex = dm.end;
        });
        
        if (textLastIndex < textContent.length) {
          finalParts.push({ type: 'text', content: textContent.substring(textLastIndex) });
        }
        if (diceMatches.length === 0) {
          // No dice found, just add the text as is (but we already added it as part above)
        }
      }
    });
    
    return finalParts.map((part, idx) => {
      if (part.type === 'dice') {
        return <DiceRollText key={idx} text={part.dice} />;
      } else if (part.type === 'variable') {
        return (
          <span 
            key={idx}
            style={{
              backgroundColor: lightMode ? '#e3f2fd' : '#1a2332',
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: '500',
              border: `1px solid ${lightMode ? '#90caf9' : '#42a5f5'}`
            }}
            title={part.name}
          >
            {part.value}
          </span>
        );
      } else {
        return <span key={idx}>{part.content}</span>;
      }
    });
  };

  const getElementColor = (tags) => {
    for (const tag of tags) {
      const lowerTag = tag.toLowerCase();
      if (lowerTag.includes('fire')) return ELEMENT_COLORS.fire;
      if (lowerTag.includes('water')) return ELEMENT_COLORS.water;
      if (lowerTag.includes('air')) return ELEMENT_COLORS.air;
      if (lowerTag.includes('spirit')) return ELEMENT_COLORS.spirit;
      if (lowerTag.includes('earth')) return ELEMENT_COLORS.earth;
    }
    return '#ffcaf4'; // Default to spirit color for shapeshifting
  };

  if (loading) {
    return (
      <div className="shapeshifting-form">
        <div className="loading">Loading shapeshifting form...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="shapeshifting-form">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (!formData) {
    return (
      <div className="shapeshifting-form">
        <div className="no-data">No shapeshifting form data available</div>
      </div>
    );
  }

  const elementColor = getElementColor(formData.tags);
  const formName = file.name ? file.name.replace('.md', '') : 'Shapeshifting Form';

  return (
    <div 
      className={`shapeshifting-form ${lightMode ? 'light-mode' : ''}`}
      style={{
        height: '100%',
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: '20px',
        boxSizing: 'border-box'
      }}
    >
      {/* Header with form name */}
      <div 
        className="form-header"
        style={{
          backgroundColor: hexToRgba(elementColor, 0.2),
          borderLeft: `6px solid ${elementColor}`,
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}
      >
        <h1 style={{ margin: 0, marginBottom: '15px' }}>{formName}</h1>
        
        {/* Tags */}
        <div className="tags">
          {formData.tags.map((tag, idx) => (
            <span 
              key={idx}
              className="tag"
              style={{
                display: 'inline-block',
                padding: '4px 10px',
                margin: '4px 4px 4px 0',
                backgroundColor: lightMode ? '#e0e0e0' : '#3a3a3a',
                color: lightMode ? '#333' : '#e0e0e0',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: '500'
              }}
            >
              #{tag}
            </span>
          ))}
        </div>
      </div>

      {/* Transformation Points Section */}
      {formData.transformationCost !== null && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Transformation Points
          </h2>
          <div style={{
            padding: '20px',
            backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
            borderRadius: '8px',
            borderLeft: `4px solid ${elementColor}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: '600', color: elementColor, marginBottom: '8px' }}>
                Cost to Transform
              </div>
              <div style={{ 
                fontSize: '36px', 
                fontWeight: '700',
                color: elementColor,
                textShadow: `0 2px 4px ${hexToRgba(elementColor, 0.3)}`
              }}>
                {formData.transformationCost} TP
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Image Display */}
      {imageUrl && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <div 
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              padding: '20px',
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              borderRadius: '8px',
              borderLeft: `4px solid ${elementColor}`
            }}
          >
            <img 
              src={imageUrl} 
              alt={formData.image || formName}
              style={{
                maxWidth: '100%',
                maxHeight: '500px',
                objectFit: 'contain',
                borderRadius: '8px',
                boxShadow: '0 4px 8px rgba(0,0,0,0.2)'
              }}
              onError={(e) => {
                console.error('Failed to load image:', imageUrl);
                e.target.style.display = 'none';
              }}
            />
          </div>
        </section>
      )}

      {/* Bending Levels */}
      {formData.bendingLevels.length > 0 && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Granted Bending Levels
          </h2>
          <div className="bending-levels-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            {formData.bendingLevels.map((level, idx) => (
              <div 
                key={idx}
                style={{
                  padding: '12px',
                  backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
                  borderRadius: '6px',
                  borderLeft: `3px solid ${ELEMENT_COLORS[level.element.toLowerCase()] || elementColor}`
                }}
              >
                <div style={{ fontWeight: '600', fontSize: '14px', color: ELEMENT_COLORS[level.element.toLowerCase()] || elementColor }}>
                  {level.element}
                </div>
                <div style={{ fontSize: '15px', marginTop: '4px' }}>
                  Level {level.level}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Size and On Transform */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '20px' }}>
        {/* Size */}
        {formData.size && (
          <section className="form-section">
            <h2 style={{ 
              borderBottom: `2px solid ${elementColor}`,
              paddingBottom: '10px',
              marginBottom: '15px'
            }}>
              Size
            </h2>
            <div style={{
              padding: '12px',
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              borderRadius: '6px',
              borderLeft: `3px solid ${elementColor}`,
              fontSize: '16px',
              fontWeight: '500'
            }}>
              {formData.size}
            </div>
          </section>
        )}

        {/* On Transform */}
        {formData.onTransform.length > 0 && (
          <section className="form-section">
            <h2 style={{ 
              borderBottom: `2px solid ${elementColor}`,
              paddingBottom: '10px',
              marginBottom: '15px'
            }}>
              On Transform
            </h2>
            <div style={{
              padding: '15px',
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              borderRadius: '8px',
              borderLeft: `4px solid ${elementColor}`
            }}>
              {formData.onTransform.map((effect, idx) => (
                <div key={idx} style={{ marginBottom: idx < formData.onTransform.length - 1 ? '12px' : '0' }}>
                  {effect.name && (
                    <div style={{ fontWeight: '600', color: elementColor, marginBottom: '4px' }}>
                      {effect.name}
                    </div>
                  )}
                  <div style={{ 
                    fontSize: '15px', 
                    lineHeight: '1.6',
                    marginLeft: effect.name ? '0' : '0'  // Could add indent if desired
                  }}>
                    {effect.name ? '' : '• '}{processText(effect.description)}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {/* Vitality and Defense Stats */}
      <section className="form-section" style={{ marginBottom: '20px' }}>
        <h2 style={{ 
          borderBottom: `2px solid ${elementColor}`,
          paddingBottom: '10px',
          marginBottom: '15px'
        }}>
          Vitality & Defense
        </h2>
        <div className="vitality-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
          {formData.vitalityStats.evasion !== null && (
            <div style={{
              padding: '12px',
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              borderRadius: '6px',
              borderLeft: `3px solid ${elementColor}`,
              textAlign: 'center'
            }}>
              <div style={{ fontWeight: '600', fontSize: '14px', color: elementColor, marginBottom: '4px' }}>
                Evasion
              </div>
              <div style={{ fontSize: '20px', fontWeight: '700' }}>
                {formData.vitalityStats.evasion}
              </div>
            </div>
          )}
          
          {formData.vitalityStats.armor.map((armor, idx) => (
            <div key={idx} style={{
              padding: '12px',
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              borderRadius: '6px',
              borderLeft: `3px solid ${elementColor}`,
              textAlign: 'center'
            }}>
              <div style={{ fontWeight: '600', fontSize: '14px', color: elementColor, marginBottom: '4px' }}>
                {armor.type}
              </div>
              <div style={{ fontSize: '20px', fontWeight: '700' }}>
                {armor.value}
              </div>
            </div>
          ))}
          
          {formData.vitalityStats.hp !== null && (
            <div style={{
              padding: '12px',
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              borderRadius: '6px',
              borderLeft: `3px solid ${elementColor}`,
              textAlign: 'center'
            }}>
              <div style={{ fontWeight: '600', fontSize: '14px', color: elementColor, marginBottom: '4px' }}>
                HP
              </div>
              <div style={{ fontSize: '20px', fontWeight: '700' }}>
                {formData.vitalityStats.hp}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Stats Table */}
      {Object.keys(formData.stats).length > 0 && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Ability Scores
          </h2>
          <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
            {Object.entries(formData.stats).map(([statName, statData]) => (
              <div 
                key={statName}
                style={{
                  padding: '12px',
                  backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
                  borderRadius: '6px',
                  borderLeft: `3px solid ${elementColor}`,
                  textAlign: 'center'
                }}
              >
                <div style={{ fontWeight: '600', fontSize: '14px', color: elementColor, marginBottom: '4px' }}>
                  {statName}
                </div>
                <div style={{ fontSize: '18px', fontWeight: '700' }}>
                  {statData.formValue}
                </div>
                <div style={{ fontSize: '12px', color: lightMode ? '#666' : '#999', marginTop: '2px' }}>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Movement */}
      {formData.movement.length > 0 && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Movement
          </h2>
          <div style={{
            padding: '15px',
            backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
            borderRadius: '8px',
            borderLeft: `4px solid ${elementColor}`
          }}>
            {formData.movement.map((move, idx) => (
              <div 
                key={idx}
                style={{
                  marginBottom: idx < formData.movement.length - 1 ? '8px' : '0',
                  fontSize: '15px',
                  lineHeight: '1.6'
                }}
              >
                • {processText(move)}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Special Abilities */}
      {formData.specialAbilities.length > 0 && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Special Abilities
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {formData.specialAbilities.map((ability, idx) => (
              <div 
                key={idx}
                style={{
                  padding: '15px',
                  backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
                  borderRadius: '8px',
                  borderLeft: `4px solid ${elementColor}`
                }}
              >
                <div style={{ fontWeight: '700', fontSize: '16px', color: elementColor, marginBottom: '10px' }}>
                  {ability.name}
                </div>
                
                {ability.tags.length > 0 && (
                  <div style={{ marginBottom: '10px' }}>
                    {ability.tags.map((tag, tagIdx) => (
                      <span 
                        key={tagIdx}
                        style={{
                          display: 'inline-block',
                          padding: '3px 8px',
                          margin: '2px 4px 2px 0',
                          backgroundColor: lightMode ? '#e0e0e0' : '#3a3a3a',
                          color: lightMode ? '#333' : '#e0e0e0',
                          borderRadius: '10px',
                          fontSize: '11px',
                          fontWeight: '500'
                        }}
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
                
                {ability.description.length > 0 && (
                  <div style={{ fontSize: '15px', lineHeight: '1.6', marginBottom: '10px' }}>
                    {ability.description.map((desc, descIdx) => (
                      <div key={descIdx} style={{ marginBottom: '4px' }}>
                        {processText(desc)}
                      </div>
                    ))}
                  </div>
                )}
                
                {ability.subAbilities.length > 0 && (
                  <div style={{ marginLeft: '15px', marginTop: '10px' }}>
                    {ability.subAbilities.map((subAbility, subIdx) => (
                      <div 
                        key={subIdx}
                        style={{
                          marginBottom: '10px',
                          padding: '10px',
                          backgroundColor: lightMode ? '#fff' : '#1e1e1e',
                          borderRadius: '6px',
                          borderLeft: `2px solid ${elementColor}`
                        }}
                      >
                        <div style={{ fontWeight: '600', fontSize: '15px', marginBottom: '4px' }}>
                          {subAbility.name}
                        </div>
                        {subAbility.tags && subAbility.tags.length > 0 && (
                          <div style={{ marginBottom: '6px' }}>
                            {subAbility.tags.map((tag, tagIdx) => (
                              <span 
                                key={tagIdx}
                                style={{
                                  display: 'inline-block',
                                  padding: '2px 6px',
                                  margin: '2px 4px 2px 0',
                                  backgroundColor: lightMode ? '#e0e0e0' : '#3a3a3a',
                                  color: lightMode ? '#333' : '#e0e0e0',
                                  borderRadius: '8px',
                                  fontSize: '10px',
                                  fontWeight: '500'
                                }}
                              >
                                #{tag}
                              </span>
                            ))}
                          </div>
                        )}
                        {subAbility.description && (
                          <div style={{ fontSize: '14px', lineHeight: '1.6' }}>
                            {processText(subAbility.description)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Attacks */}
      {formData.attacks.length > 0 && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Attacks
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {formData.attacks.map((attack, idx) => (
              <div 
                key={idx}
                style={{
                  padding: '15px',
                  backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
                  borderRadius: '8px',
                  borderLeft: `4px solid ${elementColor}`
                }}
              >
                <div style={{ fontWeight: '700', fontSize: '16px', color: elementColor, marginBottom: '6px' }}>
                  {attack.name}
                </div>
                <div style={{ fontSize: '15px', lineHeight: '1.6' }}>
                  {processText(attack.description)}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Additional Information Section - unrecognized content */}
      {formData.otherContent && formData.otherContent.length > 0 && (
        <section className="form-section" style={{ marginBottom: '20px' }}>
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Additional Information
          </h2>
          <div 
            className="other-content-list"
            style={{
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              padding: '15px',
              borderRadius: '8px',
              borderLeft: `4px solid ${elementColor}`
            }}
          >
            {formData.otherContent.map((content, idx) => (
              <div 
                key={idx}
                style={{
                  marginBottom: '8px',
                  lineHeight: '1.6',
                  fontSize: '15px'
                }}
              >
                {processText(content)}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Raw Markdown Section */}
      <section className="form-section">
        <div 
          onClick={() => setShowRawMarkdown(!showRawMarkdown)}
          style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: showRawMarkdown ? '15px' : '0',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            userSelect: 'none'
          }}
        >
          <h2 style={{ margin: 0 }}>Raw Markdown</h2>
          <span style={{
            fontSize: '20px',
            fontWeight: 'bold',
            color: elementColor,
            transition: 'transform 0.3s ease'
          }}>
            {showRawMarkdown ? '▼' : '▶'}
          </span>
        </div>
        
        {showRawMarkdown && (
          <pre 
            style={{
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              padding: '15px',
              borderRadius: '8px',
              borderLeft: `4px solid ${elementColor}`,
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
              fontFamily: 'monospace',
              fontSize: '13px',
              lineHeight: '1.5',
              color: lightMode ? '#333' : '#e0e0e0',
              overflowX: 'auto',
              marginTop: '15px'
            }}
          >
            {formData.rawContent}
          </pre>
        )}
      </section>
    </div>
  );
};

export default ShapeshiftingForm;
