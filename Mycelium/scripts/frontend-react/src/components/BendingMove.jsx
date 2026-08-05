import React, { useState, useEffect, useRef } from 'react';
import { hexToRgba } from '../utils/colorUtils';
import './BendingMove.css';
import { API_BASE_URL } from '../config/api';
import ShapeshiftingForm from './ShapeshiftingForm';
import HexGridSVG from './HexGridSVG';
import { fetchCharacterSheet } from '../utils/characterSheetParser';

const ELEMENT_COLORS = {
  fire: '#ffb3b3',
  water: '#91bbff',
  air: '#fdffd1',
  spirit: '#ffcaf4',
  earth: '#c8f0a6'
};

const AREA_PATTERNS = {
  // Cone: expands from 1 hex to wider spread (matches BattlemapViewer cone brush)
  // Pattern expands symmetrically: 1 -> 2 -> 3 hexes
  // Offset compensates for HexGridSVG's automatic tessellation (odd rows shift right by half-width)
  cone: [
    { count: 1, offset: 0 },   // Row 0 (even): 1 hex at center (origin)
    { count: 2, offset: -1 },  // Row 1 (odd): 2 hexes, offset -1 to counter tessellation shift
    { count: 3, offset: 0 }    // Row 2 (even): 3 hexes at wide end, centered
  ],
  // Sphere/burst: circular pattern around a point
  sphere: [
    { count: 2, offset: 1 },
    { count: 3, offset: 0 },
    { count: 2, offset: 1 }
  ],
  // Aura: larger circular area around caster
  aura: [
    { count: 1, offset: 2 },
    { count: 3, offset: 1 },
    { count: 4, offset: 0 },
    { count: 3, offset: 1 },
    { count: 1, offset: 2 }
  ],
  // Line: straight line of hexes
  line: [
    { count: 5, offset: 0 }
  ],
  // Wall: two parallel rows
  wall: [
    { count: 4, offset: 0 },
    { count: 4, offset: 0 }
  ],
  // Cluster: scattered hexes
  cluster: [
    { count: 1, offset: 2 },
    { count: 2, offset: 1 },
    { count: 2, offset: 1 },
    { count: 1, offset: 2 }
  ],
  // Self: single hex (the caster)
  self: [
    { count: 1, offset: 0 }
  ],
  // Melee: hexes immediately adjacent to caster (all 6 surrounding hexes in proper hex grid)
  // This represents a proper hex ring around center hex
  melee: [
    { count: 2, offset: 1 },  // Row 0 (even): 2 hexes above center
    { count: 3, offset: 0 },  // Row 1 (odd): 3 hexes including sides (tessellation places them correctly)
    { count: 2, offset: 1 }   // Row 2 (even): 2 hexes below center
  ]
};

const AREA_MATCHERS = [
  { type: 'cone', label: 'Cone', keywords: ['cone'] },
  { type: 'line', label: 'Line', keywords: ['line', 'beam'] },
  { type: 'wall', label: 'Wall', keywords: ['wall'] },
  { type: 'aura', label: 'Aura', keywords: ['aura'] },
  { type: 'sphere', label: 'Sphere', keywords: ['sphere', 'radius', 'burst', 'cloud'] },
  { type: 'cluster', label: 'Cluster', keywords: ['cluster'] },
  { type: 'melee', label: 'Melee', keywords: ['melee', 'touch'] },
  { type: 'self', label: 'Self', keywords: ['self'] }
];

// Dice roller utility (same as CharacterSheet)
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
        } else if (part) {
          const value = parseInt(part);
          if (!isNaN(value)) {
            modifierParts.push({ operator: currentModifier || '+', value });
            currentModifier = '';
          }
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

const BendingMove = ({ file, lightMode = false, characterData = null }) => {
  const [content, setContent] = useState('');
  const [moveData, setMoveData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [useMarkdown, setUseMarkdown] = useState(false);
  const [showRawMarkdown, setShowRawMarkdown] = useState(false);
  const [loadedCharacterData, setLoadedCharacterData] = useState(null);
  const [characterSheet, setCharacterSheet] = useState(null);

  useEffect(() => {
    if (file) {
      loadBendingMove();
    }
  }, [file]);

  // Extract character name from filename like "Fireball - Ash.md"
  const extractCharacterName = (fileName) => {
    if (!fileName) return null;
    // Remove .md extension
    const withoutExt = fileName.replace(/\.md$/i, '');
    // Look for pattern "Move Name - Character Name"
    const match = withoutExt.match(/\s+-\s+(.+)$/);
    return match ? match[1].trim() : null;
  };

  // Load character customization data for avatar and full sheet data
  const loadCharacterCustomization = async (characterName) => {
    if (!characterName) return;
    
    try {
      // Load avatar customization
      const response = await fetch(`${API_BASE_URL}/api/characters/${encodeURIComponent(characterName)}/customization`);
      if (response.ok) {
        const data = await response.json();
        setLoadedCharacterData({ pixels: data.avatar });
      }
      
      // Load full character sheet for slot values
      const sheet = await fetchCharacterSheet(characterName, API_BASE_URL);
      if (sheet) {
        setCharacterSheet(sheet);
      }
    } catch (err) {
      console.error('Error loading character data:', err);
    }
  };

  const loadBendingMove = async () => {
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
      const parsed = parseBendingMove(data.content || '');
      
      // Extract character name from filename and load their customization
      const characterName = extractCharacterName(file.name);
      if (characterName) {
        await loadCharacterCustomization(characterName);
      }
      
      // If parsing failed or didn't find structure, fall back to markdown
      if (!parsed || Object.keys(parsed.metadata).length === 0) {
        setUseMarkdown(true);
        setMoveData(null);
      } else {
        setUseMarkdown(false);
        setMoveData(parsed);
      }
    } catch (err) {
      setError(err.message);
      console.error('Error loading bending move:', err);
    } finally {
      setLoading(false);
    }
  };

  const parseBendingMove = (markdown) => {
    const data = {
      name: '',
      tags: [],
      metadata: {},
      effects: [],
      otherContent: [],  // Store unrecognized content
      rawContent: markdown
    };

    // Extract name from file name or first heading
    const lines = markdown.split('\n');
    
    // Extract tags (lines starting with #)
    const tagLines = lines.filter(line => line.trim().startsWith('#') && !line.trim().startsWith('##'));
    data.tags = tagLines.flatMap(line => 
      line.trim().split(/\s+/).filter(tag => tag.startsWith('#')).map(tag => tag.substring(1))
    );

    // Detect element from tags
    const elementTags = data.tags.filter(tag => 
      tag.toLowerCase().includes('fire') || 
      tag.toLowerCase().includes('water') || 
      tag.toLowerCase().includes('air') || 
      tag.toLowerCase().includes('earth') || 
      tag.toLowerCase().includes('spirit')
    );

    // Extract action type from tags
    const actionType = data.tags.find(tag => 
      tag.toLowerCase().includes('action') || 
      tag.toLowerCase().includes('reaction') || 
      tag.toLowerCase().includes('bonus')
    );

    // Extract level from tags and remove from tags array to avoid duplication
    const levelTag = data.tags.find(tag => tag.toLowerCase().match(/level\d+/));
    if (levelTag) {
      const levelMatch = levelTag.match(/level(\d+)/i);
      if (levelMatch) {
        data.metadata.Level = levelMatch[1];
        // Remove the level tag from tags array to avoid showing it twice
        data.tags = data.tags.filter(tag => tag.toLowerCase() !== levelTag.toLowerCase());
      }
    }

    // Parse metadata (lines with - or | that contain key:value or key: value patterns)
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
          data.metadata[currentMetadataKey] = fullValue;
          currentMetadataKey = null;
          currentMetadataValue = [];
        }
        continue;
      }
      
      // First check for special pattern: - [[Key Name]] (value)
      // This is for lines like "- [[Earth Attack Roll]] (1d20 + 1 + 3)"
      const specialPattern = trimmedLine.match(/^-?\s*\[\[([^\]]+)\]\]\s*\(([^)]+)\)$/);
      
      if (specialPattern) {
        // Save previous metadata if any
        if (currentMetadataKey && currentMetadataValue.length > 0) {
          let fullValue = currentMetadataValue.join('\n').trim();
          fullValue = fullValue.replace(/^\*+\s*/, '').replace(/\s*\*+$/, '');
          data.metadata[currentMetadataKey] = fullValue;
        }
        
        // Extract key and value from the special pattern
        const key = specialPattern[1].trim();
        const value = specialPattern[2].trim();
        
        // Store directly as metadata
        data.metadata[key] = value;
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
            data.metadata[currentMetadataKey] = fullValue;
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
        } else {
          // Not a recognized metadata line - store as other content
          data.otherContent.push(trimmedLine);
        }
      }
    }
    
    // Save any pending metadata at the end
    if (currentMetadataKey && currentMetadataValue.length > 0) {
      let fullValue = currentMetadataValue.join('\n').trim();
      fullValue = fullValue.replace(/^\*+\s*/, '').replace(/\s*\*+$/, '');
      data.metadata[currentMetadataKey] = fullValue;
    }

    // Extract effects from metadata if present (Effect or Effects field)
    const effectKey = Object.keys(data.metadata).find(key => key.toLowerCase().match(/^effects?$/i));
    if (effectKey) {
      const effectContent = data.metadata[effectKey];
      delete data.metadata[effectKey]; // Remove from metadata
      data.effects = effectContent.split('\n').filter(line => line.trim().length > 0);
    }

    return data;
  };

  // Helper to process text with variable references and dice notation
  const processText = (text) => {
    if (!text) return null;
    
    // Match [[variable]] (value) pattern for slots/variables with values
    // Match [[variable]] pattern for wiki-style links (conditions, etc.)
    const variableWithValueRegex = /\[\[([^\]]+)\]\]\s*\(([^)]+)\)/g;
    const wikiLinkRegex = /\[\[([^\]]+)\]\]/g;
    const diceRegex = /\b(\d+d\d+(?:\s*[+\-]\s*\d+)*)\b/gi;
    
    // First, clean up Obsidian escape characters
    let processedText = text
      .replace(/\\\*/g, '*')  // Remove backslash before asterisk (\* -> *)
      .replace(/\\_/g, '_')   // Remove backslash before underscore (\_ -> _)
      .replace(/\\\[/g, '[')  // Remove backslash before bracket (\[ -> [)
      .replace(/\\\]/g, ']'); // Remove backslash before bracket (\] -> ])
    
    // Then, clean up markdown formatting (bold, italic, etc.)
    processedText = processedText
      .replace(/\*\*\*([^\*]+?)\*\*\*/g, '$1')
      .replace(/\*\*([^\*]+?)\*\*/g, '$1')
      .replace(/\*([^\*\s][^\*]*?[^\*\s])\*/g, '$1')
      .replace(/__(.+?)__/g, '$1')
      .replace(/_([^_\s][^_]*?[^_\s])_/g, '$1');
    
    // Build an array of parts (text, variable, wikiLink, or dice)
    const parts = [];
    let lastIndex = 0;
    
    // First pass: Extract variables with values [[var]] (value)
    const varMatches = [];
    let varMatch;
    const varWithValueRegex = new RegExp(variableWithValueRegex.source, variableWithValueRegex.flags);
    while ((varMatch = varWithValueRegex.exec(processedText)) !== null) {
      varMatches.push({
        start: varMatch.index,
        end: varMatch.index + varMatch[0].length,
        name: varMatch[1],
        value: varMatch[2],
        type: 'variable',
        fullMatch: varMatch[0]
      });
    }
    
    // Second pass: Extract wiki-style links [[link]] that aren't already matched as variables
    const wikiMatches = [];
    let wikiMatch;
    const wikiRegex = new RegExp(wikiLinkRegex.source, wikiLinkRegex.flags);
    while ((wikiMatch = wikiRegex.exec(processedText)) !== null) {
      // Check if this position is already covered by a variable match
      const isAlreadyMatched = varMatches.some(vm => 
        wikiMatch.index >= vm.start && wikiMatch.index < vm.end
      );
      if (!isAlreadyMatched) {
        wikiMatches.push({
          start: wikiMatch.index,
          end: wikiMatch.index + wikiMatch[0].length,
          name: wikiMatch[1],
          type: 'wikiLink',
          fullMatch: wikiMatch[0]
        });
      }
    }
    
    // Combine and sort all matches by position
    const allMatches = [...varMatches, ...wikiMatches].sort((a, b) => a.start - b.start);
    
    // Process text with all matches
    allMatches.forEach((match) => {
      // Add text before this match
      if (match.start > lastIndex) {
        const textBefore = processedText.substring(lastIndex, match.start);
        parts.push({ type: 'text', content: textBefore });
      }
      
      // Add the match
      if (match.type === 'variable') {
        parts.push({
          type: 'variable',
          name: match.name,
          value: match.value
        });
      } else if (match.type === 'wikiLink') {
        parts.push({
          type: 'wikiLink',
          name: match.name
        });
      }
      
      lastIndex = match.end;
    });
    
    // Add any remaining text after the last match, or all text if no matches
    if (allMatches.length > 0) {
      if (lastIndex < processedText.length) {
        parts.push({ type: 'text', content: processedText.substring(lastIndex) });
      }
    } else {
      // If no matches found, add all text as one part
      parts.push({ type: 'text', content: processedText });
    }
    
    // Third pass: Split text parts by dice notation
    const finalParts = [];
    parts.forEach(part => {
      if (part.type === 'variable' || part.type === 'wikiLink') {
        finalParts.push(part);
      } else if (part.type === 'text') {
        // Split by dice notation
        const segments = part.content.split(/(\b\d+d\d+(?:\s*[+\-]\s*\d+)*\b)/gi);
        segments.forEach(seg => {
          if (seg && /\d+d\d+/i.test(seg)) {
            finalParts.push({ type: 'dice', content: seg });
          } else if (seg) {
            finalParts.push({ type: 'text', content: seg });
          }
        });
      }
    });
    
    // Render the parts
    return finalParts.map((part, idx) => {
      if (part.type === 'dice') {
        return <DiceRollText key={idx} text={part.content} />;
      } else if (part.type === 'variable') {
        // Variables with explicit values: display name, show value in tooltip
        let actualValue = part.value;
        if (characterSheet?.bendingSlots) {
          // Try to match slot name (e.g., "Firebending_slot" or "firebending slot")
          const slotKey = Object.keys(characterSheet.bendingSlots).find(key => 
            key.toLowerCase().replace(/[_\s]+/g, '') === part.name.toLowerCase().replace(/[_\s]+/g, '')
          );
          if (slotKey) {
            actualValue = characterSheet.bendingSlots[slotKey];
          }
        }
        
        return (
          <span 
            key={idx}
            className="variable-reference"
            title={`${part.name}: ${actualValue}`}
            style={{
              backgroundColor: hexToRgba('#3498db', 0.2),
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: '500',
              cursor: 'help'
            }}
          >
            {part.name}
          </span>
        );
      } else if (part.type === 'wikiLink') {
        // Wiki-style links (conditions, etc.): display the link name
        return (
          <span 
            key={idx}
            className="wiki-link"
            title={`Link to: ${part.name}`}
            style={{
              backgroundColor: hexToRgba('#9b59b6', 0.15),
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: '500',
              cursor: 'help',
              fontStyle: 'italic'
            }}
          >
            {part.name}
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
    return '#95a5a6'; // Default gray
  };

const getActionTypeFromTags = (tags) => {
  for (const tag of tags) {
    const lowerTag = tag.toLowerCase();
    if (lowerTag.includes('danger_sense_reaction')) return 'Danger Sense Reaction';
    if (lowerTag.includes('bonus_action')) return 'Bonus Action';
      if (lowerTag.includes('reaction')) return 'Reaction';
      if (lowerTag.includes('action')) return 'Action';
    }
    return null;
  };

  const detectAreaInfo = (key, value) => {
    if (!value && !key) return null;
    const text = `${key || ''} ${value || ''}`.toLowerCase();
    const keyIsRangeLike = (key || '').toLowerCase().match(/range|area|radius/);
    if (
      !keyIsRangeLike &&
      !(value || '').toLowerCase().match(/cone|sphere|aura|line|wall|burst|cloud/)
    ) {
      return null;
    }

    const matcher = AREA_MATCHERS.find(({ keywords }) =>
      keywords.some(keyword => {
        const safeKeyword = keyword.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`\\b${safeKeyword}\\b`);
        return regex.test(text);
      })
    );

    if (!matcher) return null;
    const pattern = AREA_PATTERNS[matcher.type];
    if (!pattern) return null;

    return { ...matcher, pattern };
  };

  // Extract target range multiplier from metadata
  const getTargetRangeMultiplier = (metadata) => {
    if (!metadata) return 0;
    
    // Look for "Target Range" or similar field
    for (const [key, value] of Object.entries(metadata)) {
      const keyLower = key.toLowerCase();
      if (keyLower.includes('target') && keyLower.includes('range')) {
        const rangeMatch = String(value).match(/(\d+)\s*\*\s*/);
        if (rangeMatch) {
          return parseInt(rangeMatch[1]);
        }
      }
    }
    return 0;
  };

  const targetRangeMultiplier = moveData?.metadata ? getTargetRangeMultiplier(moveData.metadata) : 0;


  // Render markdown fallback
  const renderMarkdown = () => {
    return (
      <div className={`bending-move-markdown ${lightMode ? 'light-mode' : ''}`}>
        <pre style={{
          whiteSpace: 'pre-wrap',
          wordWrap: 'break-word',
          fontFamily: 'monospace',
          fontSize: '14px',
          lineHeight: '1.6',
          padding: '20px',
          backgroundColor: lightMode ? '#f8f9fa' : '#1e1e1e',
          color: lightMode ? '#333' : '#e0e0e0',
          borderRadius: '8px'
        }}>
          {content}
        </pre>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="bending-move">
        <div className="loading">Loading bending move...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bending-move">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  // Use markdown rendering if parsing failed
  if (useMarkdown) {
    return renderMarkdown();
  }

  if (!moveData) {
    return (
      <div className="bending-move">
        <div className="no-data">No bending move data available</div>
      </div>
    );
  }

  const isShapeshiftingMove =
    (moveData.tags || []).some(tag => tag.toLowerCase().startsWith('shapeshifting')) ||
    (content && /#shapeshifting(?:\b|_)/i.test(content)) ||
    (file.path && file.path.toLowerCase().includes('shapeshifting forms'));

  if (isShapeshiftingMove) {
    return <ShapeshiftingForm file={file} lightMode={lightMode} />;
  }

  const elementColor = getElementColor(moveData.tags);
  const actionType = getActionTypeFromTags(moveData.tags);
  const moveName = file.name ? file.name.replace('.md', '') : 'Bending Move';
  
  // Use loaded character data if available, otherwise fall back to prop
  const activeCharacterData = loadedCharacterData || characterData;
  
  const renderAreaPreview = (areaInfo, rangeMultiplier = 0) => {
    if (!areaInfo) return null;

    const opacity = lightMode ? 0.5 : 0.35;

    return (
      <div className="area-preview">
        <div className="area-preview-label">
          {areaInfo.label} area {rangeMultiplier > 0 && `(Range: ${rangeMultiplier}×)`}
        </div>
        <HexGridSVG 
          pattern={areaInfo.pattern}
          color={elementColor}
          opacity={opacity}
          lightMode={lightMode}
          range={rangeMultiplier}
          characterData={activeCharacterData}
          patternType={areaInfo.type}
        />
      </div>
    );
  };

  return (
    <div className={`bending-move ${lightMode ? 'light-mode' : ''}`}>
      {/* Header with move name and action type */}
      <div 
        className="move-header"
        style={{
          backgroundColor: hexToRgba(elementColor, 0.2),
          borderLeft: `6px solid ${elementColor}`,
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}
      >
        <h1 style={{ margin: 0, marginBottom: '10px' }}>{moveName}</h1>
        {actionType && (
          <div 
            className="action-type-badge"
            style={{
              display: 'inline-block',
              padding: '6px 12px',
              backgroundColor: elementColor,
              color: '#1e1e1e',
              borderRadius: '20px',
              fontWeight: '600',
              fontSize: '14px'
            }}
          >
            {actionType}
          </div>
        )}
        
        {/* Tags */}
        <div className="tags" style={{ marginTop: '15px' }}>
          {moveData.tags.map((tag, idx) => (
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

      {/* Metadata Section */}
      {Object.keys(moveData.metadata).length > 0 && (
        <section className="move-section">
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Move Details
          </h2>
          
          {/* Short fields in grid */}
          {Object.entries(moveData.metadata).some(([key, value]) => String(value).length <= 50) && (
            <div className="metadata-grid">
              {Object.entries(moveData.metadata)
                .filter(([key, value]) => String(value).length <= 50)
                .map(([key, value]) => {
                  const areaInfo = detectAreaInfo(key, value);
                  
                  return (
                    <div 
                      key={key} 
                      className="metadata-item"
                      style={{
                        padding: '12px',
                        backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
                        borderRadius: '6px',
                        borderLeft: `3px solid ${elementColor}`
                      }}
                    >
                      <div style={{ 
                        fontWeight: '600', 
                        fontSize: '14px',
                        color: elementColor,
                        marginBottom: '6px'
                      }}>
                        {key}
                      </div>
                      <div style={{ fontSize: '15px' }}>
                        {processText(value)}
                      </div>
                      {renderAreaPreview(areaInfo, targetRangeMultiplier)}
                    </div>
                  );
                })}
            </div>
          )}
          
          {/* Long fields - each gets full width */}
          {Object.entries(moveData.metadata)
            .filter(([key, value]) => String(value).length > 50)
            .map(([key, value]) => {
              const areaInfo = detectAreaInfo(key, value);
              
              return (
                <div 
                  key={key} 
                  className="metadata-item-full"
                  style={{
                    padding: '15px',
                    backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
                    borderRadius: '8px',
                    borderLeft: `4px solid ${elementColor}`,
                    marginTop: '15px'
                  }}
                >
                  <div style={{ 
                    fontWeight: '600', 
                    fontSize: '16px',
                    color: elementColor,
                    marginBottom: '10px'
                  }}>
                    {key}
                  </div>
                  <div style={{ 
                    fontSize: '15px',
                    lineHeight: '1.6'
                  }}>
                    {processText(value)}
                  </div>
                  {renderAreaPreview(areaInfo, targetRangeMultiplier)}
                </div>
              );
            })}
        </section>
      )}

      {/* Effects Section */}
      {moveData.effects.length > 0 && (
        <section className="move-section">
          <h2 style={{ 
            borderBottom: `2px solid ${elementColor}`,
            paddingBottom: '10px',
            marginBottom: '15px'
          }}>
            Effects
          </h2>
          <div 
            className="effects-list"
            style={{
              backgroundColor: lightMode ? '#f8f9fa' : '#2a2a2a',
              padding: '15px',
              borderRadius: '8px',
              borderLeft: `4px solid ${elementColor}`
            }}
          >
            {moveData.effects.map((effect, idx) => (
              <div 
                key={idx}
                style={{
                  marginBottom: '10px',
                  lineHeight: '1.6',
                  fontSize: '15px'
                }}
              >
                {processText(effect)}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Other Content Section - unrecognized lines */}
      {moveData.otherContent && moveData.otherContent.length > 0 && (
        <section className="move-section">
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
            {moveData.otherContent.map((content, idx) => (
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

      {/* Raw Markdown Section - for debugging */}
      <section className="move-section">
        <div 
          onClick={(e) => {
            e.stopPropagation();
            setShowRawMarkdown(!showRawMarkdown);
          }}
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
              marginTop: '15px',
              animation: 'slideDown 0.3s ease-out'
            }}
          >
            {moveData?.rawContent || content || 'No content available'}
          </pre>
        )}
      </section>
    </div>
  );
};

export default BendingMove;
