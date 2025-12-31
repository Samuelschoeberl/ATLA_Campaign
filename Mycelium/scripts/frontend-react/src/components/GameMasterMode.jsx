import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import './GameMasterMode.css';
import { API_BASE_URL } from '../config/api';

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

// Balance Checker Component
const BalanceChecker = ({ lightMode = false }) => {
  const [selectedMove, setSelectedMove] = useState(null);
  const [compareMove, setCompareMove] = useState(null);
  const [movesList, setMovesList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedElement, setSelectedElement] = useState('all');
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [balanceMetrics, setBalanceMetrics] = useState(null);

  const elements = ['all', 'air', 'water', 'earth', 'fire', 'spirit'];
  const levels = ['all', 1, 2, 3, 4, 5];

  // Fetch all moves for comparison
  useEffect(() => {
    loadAllMoves();
  }, []);

  const loadAllMoves = async () => {
    setLoading(true);
    try {
      const allMoves = [];
      const elementsList = ['air', 'water', 'earth', 'fire', 'spirit'];
      
      for (const element of elementsList) {
        for (let level = 1; level <= 5; level++) {
          try {
            const response = await fetch(
              `${API_BASE_URL}/moves/${element}/${level}`,
              { cache: 'no-store' }
            );
            if (response.ok) {
              const data = await response.json();
              if (data.moves) {
                allMoves.push(...data.moves);
              }
            }
          } catch (err) {
            console.error(`Error loading ${element} level ${level}:`, err);
          }
        }
      }
      setMovesList(allMoves);
    } catch (error) {
      console.error('Error loading moves:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate balance metrics for a move
  const calculateBalanceMetrics = (move) => {
    const metrics = {
      damagePerSlot: 0,
      damagePerAction: 0,
      utilityScore: 0,
      efficiencyScore: 0,
      powerLevel: 0,
      costEffectiveness: 0,
      warnings: [],
      strengths: []
    };

    // Parse damage
    let totalDamage = 0;
    let damageRolls = [];
    if (move.damage) {
      const dicePattern = /(\d+)d(\d+)/gi;
      let match;
      while ((match = dicePattern.exec(move.damage)) !== null) {
        const numDice = parseInt(match[1]);
        const diceSize = parseInt(match[2]);
        const avgRoll = (diceSize + 1) / 2;
        totalDamage += numDice * avgRoll;
        damageRolls.push({ numDice, diceSize, avg: numDice * avgRoll });
      }
      // Add flat bonuses
      const flatBonus = move.damage.match(/[+-]\s*(\d+)(?!d)/);
      if (flatBonus) {
        totalDamage += parseInt(flatBonus[1]);
      }
    }

    // Parse cost
    let slotCost = 0;
    let waterCost = 0;
    if (move.cost) {
      const slotMatch = move.cost.match(/(\d+)\s*(?:bending\s*)?slot/i);
      if (slotMatch) slotCost = parseInt(slotMatch[1]);
      
      const waterMatch = move.cost.match(/(\d+)\s*water\s*charge/i);
      if (waterMatch) waterCost = parseInt(waterMatch[1]);
    }

    const totalCost = slotCost + (waterCost * 0.5); // Water charges worth half a slot

    // Damage efficiency
    if (totalDamage > 0 && totalCost > 0) {
      metrics.damagePerSlot = totalDamage / totalCost;
    }
    
    if (totalDamage > 0) {
      metrics.damagePerAction = totalDamage;
    }

    // Utility score based on effects
    const effectsText = ((move.effects || '') + (move.description || '')).toLowerCase();
    let utilityPoints = 0;
    
    // Positive utility
    if (effectsText.includes('push') || effectsText.includes('pull')) utilityPoints += 2;
    if (effectsText.includes('prone') || effectsText.includes('knock')) utilityPoints += 3;
    if (effectsText.includes('dazed') || effectsText.includes('stun')) utilityPoints += 4;
    if (effectsText.includes('immobilize') || effectsText.includes('restrain')) utilityPoints += 5;
    if (effectsText.includes('armor') && !effectsText.includes('reduce armor')) utilityPoints += 3;
    if (effectsText.includes('heal') || effectsText.includes('restore')) utilityPoints += 4;
    if (effectsText.includes('ally') || effectsText.includes('support')) utilityPoints += 2;
    if (effectsText.includes('lingering') || effectsText.includes('terrain')) utilityPoints += 3;
    if (effectsText.includes('aoe') || effectsText.includes('area')) utilityPoints += 2;
    if (effectsText.includes('movement') || effectsText.includes('dash')) utilityPoints += 1;
    
    metrics.utilityScore = utilityPoints;

    // Calculate power level (0-100 scale)
    const basePower = (move.level || 1) * 10;
    const damagePower = Math.min(totalDamage * 2, 30);
    const utilityPower = Math.min(utilityPoints * 3, 30);
    const costPenalty = totalCost * 3;
    
    metrics.powerLevel = Math.max(0, Math.min(100, basePower + damagePower + utilityPower - costPenalty));

    // Cost effectiveness (power per cost)
    if (totalCost > 0) {
      metrics.costEffectiveness = metrics.powerLevel / totalCost;
    } else {
      metrics.costEffectiveness = metrics.powerLevel;
    }

    // Efficiency score (combined metric)
    metrics.efficiencyScore = (
      (metrics.damagePerSlot * 2) +
      (metrics.utilityScore * 3) +
      (metrics.costEffectiveness * 1.5)
    ) / 6.5;

    // Generate warnings
    if (totalDamage === 0 && utilityPoints === 0) {
      metrics.warnings.push('⚠️ Move has no clear damage or utility value');
    }
    if (totalCost > move.level * 2) {
      metrics.warnings.push(`⚠️ Cost (${totalCost}) is high for level ${move.level}`);
    }
    if (totalDamage > 0 && totalCost > 0 && metrics.damagePerSlot < 3) {
      metrics.warnings.push(`⚠️ Low damage efficiency (${metrics.damagePerSlot.toFixed(1)} damage/slot)`);
    }
    if (totalDamage > move.level * 12) {
      metrics.warnings.push(`⚠️ Damage (${totalDamage.toFixed(1)}) may be too high for level ${move.level}`);
    }
    if (move.actionType === 'Bonus Action' && totalDamage > move.level * 8) {
      metrics.warnings.push('⚠️ High damage for a Bonus Action - may overshadow Actions');
    }
    if (move.actionType === 'Reaction' && totalCost > 1) {
      metrics.warnings.push('⚠️ Reactions with high costs may be rarely used');
    }

    // Generate strengths
    if (metrics.damagePerSlot >= 6) {
      metrics.strengths.push(`✨ Excellent damage efficiency (${metrics.damagePerSlot.toFixed(1)} damage/slot)`);
    }
    if (utilityPoints >= 6) {
      metrics.strengths.push('✨ High utility - provides strong tactical options');
    }
    if (totalDamage > 0 && utilityPoints >= 3) {
      metrics.strengths.push('✨ Good balance of damage and utility');
    }
    if (totalCost <= 1 && (totalDamage >= move.level * 4 || utilityPoints >= 3)) {
      metrics.strengths.push('✨ Excellent value for low cost');
    }
    if (move.actionType === 'Bonus Action' && totalCost <= 1) {
      metrics.strengths.push('✨ Efficient Bonus Action - good action economy');
    }
    if (metrics.costEffectiveness >= 15) {
      metrics.strengths.push('✨ Exceptional power-to-cost ratio');
    }

    return metrics;
  };

  // Filter moves based on selection
  const getFilteredMoves = () => {
    return movesList.filter(move => {
      if (selectedElement !== 'all' && move.element !== selectedElement) return false;
      if (selectedLevel !== 'all' && move.level !== selectedLevel) return false;
      if (searchTerm && !move.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });
  };

  // Compare two moves
  const compareMoves = (move1, move2) => {
    if (!move1 || !move2) return null;

    const metrics1 = calculateBalanceMetrics(move1);
    const metrics2 = calculateBalanceMetrics(move2);

    return {
      move1: { ...move1, metrics: metrics1 },
      move2: { ...move2, metrics: metrics2 },
      comparison: {
        damagePerSlot: metrics1.damagePerSlot - metrics2.damagePerSlot,
        utilityScore: metrics1.utilityScore - metrics2.utilityScore,
        powerLevel: metrics1.powerLevel - metrics2.powerLevel,
        costEffectiveness: metrics1.costEffectiveness - metrics2.costEffectiveness,
        efficiencyScore: metrics1.efficiencyScore - metrics2.efficiencyScore
      }
    };
  };

  const renderMoveSelector = (title, selectedMoveState, setSelectedMoveState) => {
    const filteredMoves = getFilteredMoves();

    return (
      <div className="controls-section">
        <h3 style={{ marginBottom: '12px', fontSize: '1.2rem' }}>{title}</h3>
        
        <select
          value={selectedMoveState?.name || ''}
          onChange={(e) => {
            const move = filteredMoves.find(m => m.name === e.target.value);
            setSelectedMoveState(move || null);
          }}
          style={{
            width: '100%',
            padding: '10px',
            borderRadius: '6px',
            border: `2px solid ${lightMode ? '#ccc' : '#3e3e42'}`,
            background: lightMode ? '#fff' : '#2d2d30',
            color: lightMode ? '#333' : '#d4d4d4',
            fontSize: '0.95rem',
            marginBottom: '12px',
            cursor: 'pointer'
          }}
        >
          <option value="">Select a move...</option>
          {filteredMoves.map(move => (
            <option key={move.name} value={move.name}>
              {move.name} (L{move.level} {move.element} {move.actionType})
            </option>
          ))}
        </select>

        {selectedMoveState && (
          <div style={{
            marginTop: '16px',
            padding: '12px',
            background: lightMode ? '#f9f9f9' : '#2d2d30',
            borderRadius: '6px',
            border: `2px solid ${ELEMENT_COLORS[selectedMoveState.element] || '#3498db'}`
          }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <span style={{
                padding: '4px 10px',
                background: ELEMENT_COLORS[selectedMoveState.element] || '#3498db',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: '600',
                color: '#000'
              }}>
                {selectedMoveState.element}
              </span>
              <span style={{
                padding: '4px 10px',
                background: ACTION_COLORS[selectedMoveState.actionType] || '#3498db',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: '600',
                color: '#fff'
              }}>
                {selectedMoveState.actionType}
              </span>
              <span style={{
                padding: '4px 10px',
                background: lightMode ? '#e0e0e0' : '#3e3e42',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: '600'
              }}>
                Level {selectedMoveState.level}
              </span>
            </div>
            {selectedMoveState.damage && (
              <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                <strong>Damage:</strong> {selectedMoveState.damage}
              </div>
            )}
            {selectedMoveState.cost && (
              <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                <strong>Cost:</strong> {selectedMoveState.cost}
              </div>
            )}
            {selectedMoveState.range && (
              <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                <strong>Range:</strong> {selectedMoveState.range}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderMetricsCard = (move, metrics) => {
    return (
      <div className="summary-section">
        <h3 style={{ marginBottom: '16px', fontSize: '1.3rem' }}>
          Balance Metrics: {move.name}
        </h3>

        {/* Core Metrics */}
        <div className="summary-grid">
          <div className="summary-card" style={{ borderColor: '#3498db', background: lightMode ? '#f0f4ff' : 'rgba(52, 152, 219, 0.15)' }}>
            <div className="summary-label" style={{ fontSize: '11px', opacity: 0.8, marginBottom: '4px' }}>
              Damage per Slot
            </div>
            <div className="summary-value" style={{ color: '#3498db', fontSize: '2rem' }}>
              {metrics.damagePerSlot > 0 ? metrics.damagePerSlot.toFixed(1) : 'N/A'}
            </div>
          </div>

          <div className="summary-card success">
            <div className="summary-label" style={{ fontSize: '11px', opacity: 0.8, marginBottom: '4px' }}>
              Utility Score
            </div>
            <div className="summary-value" style={{ color: '#2ecc71', fontSize: '2rem' }}>
              {metrics.utilityScore}
            </div>
          </div>

          <div className="summary-card warning">
            <div className="summary-label" style={{ fontSize: '11px', opacity: 0.8, marginBottom: '4px' }}>
              Power Level
            </div>
            <div className="summary-value" style={{ color: '#e67e22', fontSize: '2rem' }}>
              {metrics.powerLevel.toFixed(0)}/100
            </div>
          </div>

          <div className="summary-card" style={{ borderColor: '#9b59b6', background: lightMode ? '#f5f0ff' : 'rgba(155, 89, 182, 0.15)' }}>
            <div className="summary-label" style={{ fontSize: '11px', opacity: 0.8, marginBottom: '4px' }}>
              Efficiency Score
            </div>
            <div className="summary-value" style={{ color: '#9b59b6', fontSize: '2rem' }}>
              {metrics.efficiencyScore.toFixed(1)}
            </div>
          </div>
        </div>

        {/* Strengths */}
        {metrics.strengths.length > 0 && (
          <div style={{
            marginBottom: '12px',
            padding: '12px',
            background: lightMode ? '#d4edda' : 'rgba(46, 204, 113, 0.15)',
            borderRadius: '6px',
            border: '2px solid #2ecc71'
          }}>
            <strong style={{ color: lightMode ? '#155724' : '#2ecc71', display: 'block', marginBottom: '8px' }}>
              Strengths
            </strong>
            {metrics.strengths.map((strength, idx) => (
              <div key={idx} style={{ fontSize: '13px', marginBottom: '4px', color: lightMode ? '#155724' : '#27ae60' }}>
                {strength}
              </div>
            ))}
          </div>
        )}

        {/* Warnings */}
        {metrics.warnings.length > 0 && (
          <div style={{
            padding: '12px',
            background: lightMode ? '#fff3cd' : 'rgba(241, 196, 15, 0.15)',
            borderRadius: '6px',
            border: '2px solid #f1c40f'
          }}>
            <strong style={{ color: lightMode ? '#856404' : '#f1c40f', display: 'block', marginBottom: '8px' }}>
              Balance Warnings
            </strong>
            {metrics.warnings.map((warning, idx) => (
              <div key={idx} style={{ fontSize: '13px', marginBottom: '4px', color: lightMode ? '#856404' : '#f39c12' }}>
                {warning}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderComparison = () => {
    if (!selectedMove || !compareMove) return null;

    const comparison = compareMoves(selectedMove, compareMove);
    if (!comparison) return null;

    return (
      <div className="summary-section" style={{ marginTop: '24px' }}>
        <h2 style={{ marginBottom: '20px' }}>
          ⚔️ Head-to-Head Comparison
        </h2>

        {/* Comparison Metrics */}
        <div className="summary-grid">
          {[
            { key: 'damagePerSlot', label: 'Damage/Slot', icon: '⚔️' },
            { key: 'utilityScore', label: 'Utility', icon: '🛠️' },
            { key: 'powerLevel', label: 'Power', icon: '⚡' },
            { key: 'efficiencyScore', label: 'Efficiency', icon: '📊' }
          ].map(({ key, label, icon }) => {
            const diff = comparison.comparison[key];
            const winner = diff > 0 ? 'move1' : diff < 0 ? 'move2' : 'tie';
            
            return (
              <div key={key} className="summary-card">
                <div style={{ fontSize: '12px', opacity: 0.8, marginBottom: '6px' }}>
                  {icon} {label}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{
                    fontSize: '16px',
                    fontWeight: winner === 'move1' ? '700' : '400',
                    color: winner === 'move1' ? '#2ecc71' : (lightMode ? '#666' : '#999')
                  }}>
                    {comparison.move1.metrics[key].toFixed(1)}
                  </div>
                  <div style={{ fontSize: '14px', opacity: 0.6 }}>vs</div>
                  <div style={{
                    fontSize: '16px',
                    fontWeight: winner === 'move2' ? '700' : '400',
                    color: winner === 'move2' ? '#2ecc71' : (lightMode ? '#666' : '#999')
                  }}>
                    {comparison.move2.metrics[key].toFixed(1)}
                  </div>
                </div>
                {diff !== 0 && (
                  <div style={{
                    marginTop: '6px',
                    fontSize: '12px',
                    color: diff > 0 ? '#2ecc71' : '#e74c3c',
                    textAlign: 'center'
                  }}>
                    {diff > 0 ? '←' : '→'} {Math.abs(diff).toFixed(1)} difference
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Winner Summary */}
        <div style={{
          marginTop: '20px',
          padding: '16px',
          background: lightMode ? '#e8f5e9' : 'rgba(46, 204, 113, 0.1)',
          borderRadius: '8px',
          border: '2px solid #2ecc71'
        }}>
          <strong style={{ color: lightMode ? '#2e7d32' : '#2ecc71', display: 'block', marginBottom: '8px' }}>
            📊 Overall Assessment
          </strong>
          <div style={{ fontSize: '14px', lineHeight: '1.6', color: lightMode ? '#1b5e20' : '#27ae60' }}>
            {(() => {
              const scores = {
                move1: 0,
                move2: 0
              };
              
              Object.keys(comparison.comparison).forEach(key => {
                const diff = comparison.comparison[key];
                if (diff > 0) scores.move1++;
                else if (diff < 0) scores.move2++;
              });

              if (scores.move1 > scores.move2) {
                return `${selectedMove.name} appears stronger overall, winning ${scores.move1} out of ${Object.keys(comparison.comparison).length} metrics.`;
              } else if (scores.move2 > scores.move1) {
                return `${compareMove.name} appears stronger overall, winning ${scores.move2} out of ${Object.keys(comparison.comparison).length} metrics.`;
              } else {
                return 'Both moves are roughly balanced with similar overall power levels.';
              }
            })()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="balance-panel">
      <div className="controls-section">
        <h2>⚖️ Balance Checker</h2>
        <p style={{ marginBottom: '20px', opacity: 0.8 }}>
          Analyze damage calculations, resource costs, and power level comparisons between moves
        </p>

        {/* Filters */}
        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '20px',
          flexWrap: 'wrap'
        }}>
          <div className="control-group" style={{ flex: '0 0 auto' }}>
            <label>Element</label>
            <select
              value={selectedElement}
              onChange={(e) => setSelectedElement(e.target.value)}
            >
              {elements.map(el => (
                <option key={el} value={el}>
                  {el.charAt(0).toUpperCase() + el.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group" style={{ flex: '0 0 auto' }}>
            <label>Level</label>
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
            >
              {levels.map(lvl => (
                <option key={lvl} value={lvl}>
                  {lvl === 'all' ? 'All Levels' : `Level ${lvl}`}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group" style={{ flex: 1, minWidth: '200px' }}>
            <label>Search</label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search moves..."
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: `2px solid ${lightMode ? '#ccc' : '#3e3e42'}`,
                background: lightMode ? '#fff' : '#2d2d30',
                color: lightMode ? '#333' : '#d4d4d4',
                fontSize: '0.95rem'
              }}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
          <div>Loading moves...</div>
        </div>
      ) : (
        <>
          {/* Move Selectors */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '16px',
            marginBottom: '24px'
          }}>
            {renderMoveSelector('Primary Move', selectedMove, setSelectedMove)}
            {renderMoveSelector('Compare With', compareMove, setCompareMove)}
          </div>

          {/* Metrics Display */}
          {selectedMove && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: compareMove ? 'repeat(auto-fit, minmax(300px, 1fr))' : '1fr',
              gap: '16px',
              marginBottom: '24px'
            }}>
              {renderMetricsCard(selectedMove, calculateBalanceMetrics(selectedMove))}
              {compareMove && renderMetricsCard(compareMove, calculateBalanceMetrics(compareMove))}
            </div>
          )}

          {/* Comparison View */}
          {selectedMove && compareMove && renderComparison()}

          {/* Empty State */}
          {!selectedMove && (
            <div className="empty-state">
              <p>🎯 Select a move to view its balance metrics</p>
              <p style={{ fontSize: '14px', opacity: 0.7, marginTop: '8px' }}>
                Choose two moves to compare their power levels
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Content Overview Component
const ContentOverview = ({ lightMode = false }) => {
  const [loading, setLoading] = useState(false);
  const [contentStats, setContentStats] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('overview');
  const [npcs, setNpcs] = useState([]);
  const [locations, setLocations] = useState([]);
  const [stories, setStories] = useState([]);
  const [expandedItems, setExpandedItems] = useState(new Set());

  useEffect(() => {
    loadContentOverview();
  }, []);

  const loadContentOverview = async () => {
    setLoading(true);
    try {
      // Load NPCs
      const npcData = await fetchDirectoryContents('Dms Root/NPCs');
      setNpcs(npcData);

      // Load Locations
      const locationData = await fetchDirectoryContents('Dms Root/Locations');
      setLocations(locationData);

      // Load Story files
      const storyData = await fetchDirectoryContents('Dms Root/Story');
      setStories(storyData);

      // Calculate statistics
      const stats = {
        totalNPCs: countAllFiles(npcData),
        npcCategories: npcData.length,
        totalLocations: countAllFiles(locationData),
        locationCategories: locationData.length,
        totalStoryFiles: countAllFiles(storyData),
        storyCategories: storyData.length,
        totalContent: countAllFiles(npcData) + countAllFiles(locationData) + countAllFiles(storyData)
      };

      setContentStats(stats);
    } catch (error) {
      console.error('Error loading content overview:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDirectoryContents = async (path) => {
    try {
      const response = await fetch(`${API_BASE_URL}/list_directory?path=${encodeURIComponent(path)}`);
      if (!response.ok) return [];
      
      const data = await response.json();
      const items = data.items || [];
      
      // Separate folders and files
      const result = [];
      
      for (const item of items) {
        if (item.type === 'directory' && !item.name.startsWith('.')) {
          // Recursively fetch subdirectory contents
          const subPath = `${path}/${item.name}`;
          const subItems = await fetchDirectoryContents(subPath);
          result.push({
            name: item.name,
            type: 'directory',
            path: subPath,
            children: subItems
          });
        } else if (item.type === 'file' && item.name.endsWith('.md') && !item.name.startsWith('.')) {
          // Fetch file metadata
          const filePath = `${path}/${item.name}`;
          result.push({
            name: item.name.replace('.md', ''),
            type: 'file',
            path: filePath
          });
        }
      }
      
      return result;
    } catch (error) {
      console.error(`Error fetching directory ${path}:`, error);
      return [];
    }
  };

  const countAllFiles = (items) => {
    let count = 0;
    for (const item of items) {
      if (item.type === 'file') {
        count++;
      } else if (item.type === 'directory' && item.children) {
        count += countAllFiles(item.children);
      }
    }
    return count;
  };

  const toggleItemExpanded = (path) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const renderTreeItem = (item, depth = 0) => {
    const isExpanded = expandedItems.has(item.path);
    const hasChildren = item.children && item.children.length > 0;

    return (
      <div key={item.path} style={{ marginLeft: `${depth * 20}px` }}>
        <div
          onClick={() => hasChildren && toggleItemExpanded(item.path)}
          style={{
            padding: '10px 12px',
            marginBottom: '6px',
            background: lightMode ? '#f9f9f9' : '#2d2d30',
            borderRadius: '6px',
            cursor: hasChildren ? 'pointer' : 'default',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            border: `2px solid ${lightMode ? '#e0e0e0' : '#3e3e42'}`,
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => {
            if (hasChildren) {
              e.currentTarget.style.transform = 'translateX(4px)';
              e.currentTarget.style.borderColor = lightMode ? '#667eea' : '#4ec9b0';
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateX(0)';
            e.currentTarget.style.borderColor = lightMode ? '#e0e0e0' : '#3e3e42';
          }}
        >
          {hasChildren && (
            <span style={{ fontSize: '12px', opacity: 0.7, transition: 'transform 0.2s ease', display: 'inline-block', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>
              ▶
            </span>
          )}
          <span style={{ fontSize: '18px' }}>
            {item.type === 'directory' ? '📁' : '📄'}
          </span>
          <span style={{ flex: 1, fontWeight: item.type === 'directory' ? '600' : '400', fontSize: '14px' }}>
            {item.name}
          </span>
          {item.type === 'directory' && item.children && (
            <span style={{
              fontSize: '11px',
              padding: '3px 10px',
              background: lightMode ? '#e3f2fd' : 'rgba(78, 201, 176, 0.2)',
              borderRadius: '12px',
              color: lightMode ? '#1976d2' : '#4ec9b0',
              fontWeight: '600'
            }}>
              {countAllFiles(item.children)}
            </span>
          )}
        </div>
        {isExpanded && hasChildren && (
          <div style={{ marginTop: '4px', marginBottom: '8px' }}>
            {item.children.map(child => renderTreeItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const renderCategoryBreakdown = (title, items, icon, color) => (
    <div className="summary-section">
      <h3 style={{
        marginBottom: '16px',
        color: color,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        fontSize: '1.3rem'
      }}>
        <span style={{ fontSize: '24px' }}>{icon}</span>
        {title}
      </h3>
      <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '8px' }}>
        {items.length > 0 ? (
          items.map(item => renderTreeItem(item, 0))
        ) : (
          <div className="empty-state">
            No items found
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="content-panel">
      <div className="controls-section">
        <h2>📚 Content Overview</h2>
        <p style={{ marginBottom: '0', opacity: 0.8 }}>
          Comprehensive view of your campaign's NPCs, locations, story arcs, and statistics
        </p>
      </div>

      {loading ? (
        <div className="empty-state">
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏳</div>
          <div>Loading campaign content...</div>
        </div>
      ) : contentStats ? (
        <>
          {/* Overview Tab Navigation */}
          <div style={{
            display: 'flex',
            gap: '8px',
            marginBottom: '24px',
            flexWrap: 'wrap'
          }}>
            {[
              { id: 'overview', label: '📊 Overview' },
              { id: 'npcs', label: '👥 NPCs' },
              { id: 'locations', label: '🗺️ Locations' },
              { id: 'story', label: '📖 Story' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedCategory(tab.id)}
                className={`element-btn ${selectedCategory === tab.id ? 'active' : ''}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {selectedCategory === 'overview' && (
            <div>
              {/* Summary Statistics */}
              <div className="summary-section">
                <h2 style={{ marginBottom: '20px' }}>Campaign Statistics</h2>
                <div className="summary-grid">
                  <div className="summary-card" style={{ borderColor: '#667eea', background: lightMode ? '#f0f4ff' : 'rgba(102, 126, 234, 0.15)' }}>
                    <div className="summary-value" style={{ color: '#667eea' }}>{contentStats.totalContent}</div>
                    <div className="summary-label">Total Content Files</div>
                  </div>
                  <div className="summary-card success">
                    <div className="summary-value" style={{ color: '#4ec9b0' }}>{contentStats.totalNPCs}</div>
                    <div className="summary-label">NPCs</div>
                  </div>
                  <div className="summary-card warning">
                    <div className="summary-value" style={{ color: '#f39c12' }}>{contentStats.totalLocations}</div>
                    <div className="summary-label">Locations</div>
                  </div>
                  <div className="summary-card danger">
                    <div className="summary-value" style={{ color: '#e74c3c' }}>{contentStats.totalStoryFiles}</div>
                    <div className="summary-label">Story Files</div>
                  </div>
                </div>
              </div>

              {/* Category Breakdown */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: '16px',
                marginBottom: '24px'
              }}>
                <div className="summary-section">
                  <h4 style={{ marginBottom: '12px', color: '#4ec9b0', fontSize: '1.1rem' }}>👥 NPC Categories</h4>
                  <div style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '4px', color: '#4ec9b0' }}>
                    {contentStats.npcCategories}
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.8 }}>
                    {contentStats.totalNPCs} total NPCs
                  </div>
                </div>

                <div className="summary-section">
                  <h4 style={{ marginBottom: '12px', color: '#f39c12', fontSize: '1.1rem' }}>🗺️ Location Groups</h4>
                  <div style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '4px', color: '#f39c12' }}>
                    {contentStats.locationCategories}
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.8 }}>
                    {contentStats.totalLocations} total locations
                  </div>
                </div>

                <div className="summary-section">
                  <h4 style={{ marginBottom: '12px', color: '#e74c3c', fontSize: '1.1rem' }}>📖 Story Sections</h4>
                  <div style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '4px', color: '#e74c3c' }}>
                    {contentStats.storyCategories}
                  </div>
                  <div style={{ fontSize: '13px', opacity: 0.8 }}>
                    {contentStats.totalStoryFiles} story files
                  </div>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="summary-section">
                <h3 style={{ marginBottom: '12px', fontSize: '1.2rem' }}>
                  📊 Campaign Scope
                </h3>
                <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
                  <p>Your campaign contains <strong>{contentStats.totalContent} content files</strong> organized across multiple categories:</p>
                  <ul style={{ marginTop: '8px', marginLeft: '20px' }}>
                    <li><strong>{contentStats.totalNPCs}</strong> NPCs across {contentStats.npcCategories} categories (Lotus, Night Bloom, Combat NPCs, etc.)</li>
                    <li><strong>{contentStats.totalLocations}</strong> locations in {contentStats.locationCategories} groups (Cities, Villages, Oases, etc.)</li>
                    <li><strong>{contentStats.totalStoryFiles}</strong> story files spanning {contentStats.storyCategories} narrative sections</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* NPCs Tab */}
          {selectedCategory === 'npcs' && renderCategoryBreakdown(
            `NPCs (${contentStats.totalNPCs} total)`,
            npcs,
            '👥',
            '#4ec9b0'
          )}

          {/* Locations Tab */}
          {selectedCategory === 'locations' && renderCategoryBreakdown(
            `Locations (${contentStats.totalLocations} total)`,
            locations,
            '🗺️',
            '#f39c12'
          )}

          {/* Story Tab */}
          {selectedCategory === 'story' && renderCategoryBreakdown(
            `Story Arcs (${contentStats.totalStoryFiles} total)`,
            stories,
            '📖',
            '#e74c3c'
          )}
        </>
      ) : (
        <div className="empty-state">
          <p>Failed to load content overview</p>
          <button
            onClick={loadContentOverview}
            className="analyze-btn"
            style={{ marginTop: '12px', maxWidth: '200px' }}
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};

const GameMasterMode = ({ lightMode = false }) => {
  const [activeTab, setActiveTab] = useState('moveAnalysis');
  const [loading, setLoading] = useState(false);
  const [moveAnalysisData, setMoveAnalysisData] = useState(null);
  const [selectedElements, setSelectedElements] = useState(['air']);
  const [selectedLevels, setSelectedLevels] = useState([1, 2]);
  const [analysisMode, setAnalysisMode] = useState('uniqueness'); // 'uniqueness' or 'balance'
  const [sortBy, setSortBy] = useState('uniqueness');
  const [filterThreshold, setFilterThreshold] = useState(0);
  const [expandedMoves, setExpandedMoves] = useState(new Set());
  
  // Table sorting state
  const [tableSortBy, setTableSortBy] = useState('overall');
  const [tableSortDirection, setTableSortDirection] = useState('desc');
  const [expandedTableMove, setExpandedTableMove] = useState(null);

  // Analysis results
  const [analysisResults, setAnalysisResults] = useState(null);
  const [visualizationData, setVisualizationData] = useState(null);
  const [showVisualization, setShowVisualization] = useState(true);

  const elements = ['air', 'water', 'earth', 'fire', 'spirit'];
  const levels = [1, 2, 3, 4, 5];

  // Fetch moves for analysis
  const fetchMoves = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze-moves`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          elements: selectedElements,
          levels: selectedLevels,
          mode: analysisMode
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setMoveAnalysisData(data);
        analyzeMovesLocally(data);
        
        // Fetch visualization data for balance mode
        if (analysisMode === 'balance') {
          fetchVisualizationData(data.moves);
        }
      }
    } catch (error) {
      console.error('Error fetching moves:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch visualization data
  const fetchVisualizationData = async (moves) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/balance-visualization`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ moves })
      });
      
      if (response.ok) {
        const vizData = await response.json();
        setVisualizationData(vizData);
      }
    } catch (error) {
      console.error('Error fetching visualization data:', error);
    }
  };

  // Detect synergies between moves
  const detectSynergies = (move, allMoves) => {
    const synergies = [];
    const moveEffects = (move.effects || move.description || '').toLowerCase();
    
    allMoves.forEach(other => {
      if (other.name === move.name) return;
      
      const otherEffects = (other.effects || other.description || '').toLowerCase();
      let synergyScore = 0;
      let synergyReasons = [];
      
      // Movement synergies
      if (moveEffects.match(/movement|meters|move/i) && otherEffects.match(/movement|meters|move/i)) {
        // Check if one generates movement and the other benefits from it
        if ((moveEffects.match(/gain.*movement/i) && otherEffects.match(/moved|moving/i)) ||
            (otherEffects.match(/gain.*movement/i) && moveEffects.match(/moved|moving/i))) {
          synergyScore += 2;
          synergyReasons.push('Movement Generation + Movement Reward');
        }
      }
      
      // Temporary resource synergies
      if ((moveEffects.match(/temporary.*slot|bonus.*slot/i) && otherEffects.match(/spend|cost|slot/i)) ||
          (otherEffects.match(/temporary.*slot|bonus.*slot/i) && moveEffects.match(/spend|cost|slot/i))) {
        synergyScore += 2;
        synergyReasons.push('Resource Generation + Resource Consumption');
      }
      
      // Concentration + non-concentration synergy (can use both together)
      if ((moveEffects.includes('concentration') && !otherEffects.includes('concentration')) ||
          (!moveEffects.includes('concentration') && otherEffects.includes('concentration'))) {
        // Bonus actions that work with concentration actions
        if (move.actionType === 'Bonus Action' && other.actionType === 'Action') {
          synergyScore += 1;
          synergyReasons.push('Bonus Action + Concentration Action');
        } else if (move.actionType === 'Action' && other.actionType === 'Bonus Action') {
          synergyScore += 1;
          synergyReasons.push('Concentration Action + Bonus Action');
        }
      }
      
      // Support + Self-buff synergies
      if ((moveEffects.match(/ally|target.*gain/i) && otherEffects.match(/self|you gain/i)) ||
          (otherEffects.match(/ally|target.*gain/i) && moveEffects.match(/self|you gain/i))) {
        synergyScore += 1.5;
        synergyReasons.push('Team Support + Self Enhancement');
      }
      
      // Setup + Payoff synergies
      if ((moveEffects.match(/prone|dazed|stun/i) && otherEffects.match(/advantage|bonus.*attack/i)) ||
          (otherEffects.match(/prone|dazed|stun/i) && moveEffects.match(/advantage|bonus.*attack/i))) {
        synergyScore += 1.5;
        synergyReasons.push('Control Setup + Attack Payoff');
      }
      
      // Area control + forced movement
      if ((moveEffects.match(/lingering|terrain|area/i) && otherEffects.match(/push|pull|knock/i)) ||
          (otherEffects.match(/lingering|terrain|area/i) && moveEffects.match(/push|pull|knock/i))) {
        synergyScore += 1.5;
        synergyReasons.push('Area Control + Forced Movement');
      }
      
      // Different action types is a positive (can use in same turn)
      if (move.actionType !== other.actionType && 
          !move.actionType.includes('Reaction') && 
          !other.actionType.includes('Reaction')) {
        synergyScore += 0.5;
        synergyReasons.push('Different Action Types (Combo Potential)');
      }
      
      if (synergyScore > 1) {
        synergies.push({
          name: other.name,
          level: other.level,
          score: synergyScore,
          reasons: synergyReasons
        });
      }
    });
    
    return synergies;
  };

  // Calculate balance metrics for a move
  const calculateBalanceMetrics = (move) => {
    const metrics = {
      damagePerSlot: 0,
      damagePerAction: 0,
      utilityScore: 0,
      efficiencyScore: 0,
      powerLevel: 0,
      costEffectiveness: 0,
      balanceScore: 0,
      warnings: [],
      strengths: []
    };

    // Parse damage
    let totalDamage = 0;
    if (move.damage) {
      const dicePattern = /(\d+)d(\d+)/gi;
      let match;
      while ((match = dicePattern.exec(move.damage)) !== null) {
        const numDice = parseInt(match[1]);
        const diceSize = parseInt(match[2]);
        const avgRoll = (diceSize + 1) / 2;
        totalDamage += numDice * avgRoll;
      }
      // Add flat bonuses
      const flatBonus = move.damage.match(/[+-]\s*(\d+)(?!d)/);
      if (flatBonus) {
        totalDamage += parseInt(flatBonus[1]);
      }
    }

    // Parse cost
    let slotCost = 0;
    let waterCost = 0;
    if (move.cost) {
      const slotMatch = move.cost.match(/(\d+)\s*(?:bending\s*)?slot/i);
      if (slotMatch) slotCost = parseInt(slotMatch[1]);
      
      const waterMatch = move.cost.match(/(\d+)\s*water\s*charge/i);
      if (waterMatch) waterCost = parseInt(waterMatch[1]);
    }

    const totalCost = slotCost + (waterCost * 0.5); // Water charges worth half a slot

    // Damage efficiency
    if (totalDamage > 0 && totalCost > 0) {
      metrics.damagePerSlot = totalDamage / totalCost;
    }
    
    if (totalDamage > 0) {
      metrics.damagePerAction = totalDamage;
    }

    // Utility score based on effects
    const effectsText = ((move.effects || '') + (move.description || '')).toLowerCase();
    let utilityPoints = 0;
    
    if (effectsText.includes('push') || effectsText.includes('pull')) utilityPoints += 2;
    if (effectsText.includes('prone') || effectsText.includes('knock')) utilityPoints += 3;
    if (effectsText.includes('dazed') || effectsText.includes('stun')) utilityPoints += 4;
    if (effectsText.includes('immobilize') || effectsText.includes('restrain')) utilityPoints += 5;
    if (effectsText.includes('armor') && !effectsText.includes('reduce armor')) utilityPoints += 3;
    if (effectsText.includes('heal') || effectsText.includes('restore')) utilityPoints += 4;
    if (effectsText.includes('ally') || effectsText.includes('support')) utilityPoints += 2;
    if (effectsText.includes('lingering') || effectsText.includes('terrain')) utilityPoints += 3;
    if (effectsText.includes('aoe') || effectsText.includes('area')) utilityPoints += 2;
    if (effectsText.includes('movement') || effectsText.includes('dash')) utilityPoints += 1;
    
    metrics.utilityScore = utilityPoints;

    // Calculate power level (0-100 scale)
    const basePower = (move.level || 1) * 10;
    const damagePower = Math.min(totalDamage * 2, 30);
    const utilityPower = Math.min(utilityPoints * 3, 30);
    const costPenalty = totalCost * 3;
    
    metrics.powerLevel = Math.max(0, Math.min(100, basePower + damagePower + utilityPower - costPenalty));

    // Cost effectiveness (power per cost)
    if (totalCost > 0) {
      metrics.costEffectiveness = metrics.powerLevel / totalCost;
    } else {
      metrics.costEffectiveness = metrics.powerLevel;
    }

    // Balance score (0-10 scale combining multiple factors)
    // Good balance means appropriate power for level and cost
    const expectedPower = move.level * 15; // Expected power per level
    const powerDiff = Math.abs(metrics.powerLevel - expectedPower);
    const balanceDeduction = powerDiff / 10; // Penalize deviation from expected power
    
    metrics.balanceScore = Math.max(0, Math.min(10, 10 - balanceDeduction));

    // Generate warnings
    if (totalDamage === 0 && utilityPoints === 0) {
      metrics.warnings.push('⚠️ Move has no clear damage or utility value');
    }
    if (totalCost > move.level * 2) {
      metrics.warnings.push(`⚠️ Cost (${totalCost}) is high for level ${move.level}`);
    }
    if (totalDamage > 0 && totalCost > 0 && metrics.damagePerSlot < 3) {
      metrics.warnings.push(`⚠️ Low damage efficiency (${metrics.damagePerSlot.toFixed(1)} damage/slot)`);
    }
    if (totalDamage > move.level * 12) {
      metrics.warnings.push(`⚠️ Damage (${totalDamage.toFixed(1)}) may be too high for level ${move.level}`);
    }
    if (move.actionType === 'Bonus Action' && totalDamage > move.level * 8) {
      metrics.warnings.push('⚠️ High damage for a Bonus Action');
    }
    if (move.actionType === 'Reaction' && totalCost > 1) {
      metrics.warnings.push('⚠️ High cost for a Reaction');
    }

    // Generate strengths
    if (metrics.damagePerSlot >= 6) {
      metrics.strengths.push(`✨ Excellent damage efficiency (${metrics.damagePerSlot.toFixed(1)} damage/slot)`);
    }
    if (utilityPoints >= 6) {
      metrics.strengths.push('✨ High utility - provides strong tactical options');
    }
    if (totalDamage > 0 && utilityPoints >= 3) {
      metrics.strengths.push('✨ Good balance of damage and utility');
    }
    if (totalCost <= 1 && (totalDamage >= move.level * 4 || utilityPoints >= 3)) {
      metrics.strengths.push('✨ Excellent value for low cost');
    }
    if (metrics.balanceScore >= 8) {
      metrics.strengths.push('✨ Well-balanced for its level');
    }

    return metrics;
  };

  // Local analysis function (can be enhanced with backend analysis)
  const analyzeMovesLocally = (movesData) => {
    if (!movesData || !movesData.moves) return;

    // Calculate scores based on analysis mode
    const analyzed = movesData.moves.map(move => {
      const baseMove = {
        ...move,
        categories: determineCategories(move)
      };

      if (analysisMode === 'balance') {
        // Balance Analysis Mode
        // Use ML balance score if available from backend, otherwise calculate locally
        let balanceScore;
        let balanceMetrics;
        
        if (move.mlBalanceScore !== undefined && move.mlBalanceFeedback) {
          // Use ML-calculated balance score from backend
          balanceScore = move.mlBalanceScore;
          balanceMetrics = {
            balanceScore: move.mlBalanceScore,
            rating: move.mlBalanceFeedback.rating,
            warnings: move.mlBalanceFeedback.warnings || [],
            strengths: move.mlBalanceFeedback.strengths || [],
            recommendations: move.mlBalanceFeedback.recommendations || [],
            scoringMethod: move.mlBalanceScoringMethod || 'ml',
            // Keep calculated metrics for display
            ...calculateBalanceMetrics(move)
          };
        } else {
          // Fallback to local calculation
          balanceMetrics = calculateBalanceMetrics(move);
          balanceScore = balanceMetrics.balanceScore;
          balanceMetrics.scoringMethod = 'local';
        }
        
        return {
          ...baseMove,
          balanceMetrics,
          balanceScore: balanceScore,
          uniquenessScore: balanceScore, // Use balance score as primary score
          primaryScore: balanceMetrics.balanceScore
        };
      } else if (analysisMode === 'simplicity') {
        // Simplicity Analysis Mode
        // Use ML simplicity score from backend
        let simplicityScore = move.mlSimplicityScore || 5.0;
        let simplicityFeedback = move.mlSimplicityFeedback || {};
        
        return {
          ...baseMove,
          simplicityScore,
          simplicityFeedback,
          primaryScore: simplicityScore,
          uniquenessScore: simplicityScore // For filtering compatibility
        };
      } else if (analysisMode === 'full') {
        // Full Analysis Mode - combines all three scores
        let fullScore = move.mlFullScore || 5.0;
        let fullBreakdown = move.mlFullBreakdown || {
          balance: 5.0,
          uniqueness: 5.0,
          simplicity: 5.0
        };
        let fullFeedback = move.mlFullFeedback || {};
        
        return {
          ...baseMove,
          fullScore,
          fullBreakdown,
          fullFeedback,
          primaryScore: fullScore,
          uniquenessScore: fullScore, // For filtering compatibility
          // Keep individual scores accessible
          balanceScore: fullBreakdown.balance,
          simplicityScore: fullBreakdown.simplicity
        };
      } else {
        // Uniqueness Analysis Mode
        let score = 5; // Base score
        
        // Action type variety
        const actionTypes = ['Action', 'Bonus Action', 'Reaction', 'Danger Sense Reaction'];
        const actionTypeIndex = actionTypes.indexOf(move.actionType);
        if (actionTypeIndex >= 2) score += 1; // Reactions are more unique
        
        // Range creativity
        if (move.range && move.range.includes('Self')) score += 0.5;
        else if (move.range && move.range.includes('radius')) score += 1;
        else if (move.range && move.range.includes('Cone')) score += 1.5;
        
        // Effect complexity
        const effects = move.effects || move.description || '';
        if (effects.includes('concentration')) score += 1.5;
        if (effects.includes('lingering')) score += 2;
        if (effects.match(/prone|dazed|disadvantage/i)) score += 1;
        if (effects.match(/pull|push|knock/i)) score += 0.5;
        
        // Utility assessment
        if (effects.match(/move|dash|movement/i)) score += 0.5;
        if (effects.match(/wall|terrain|environmental/i)) score += 1.5;
        if (effects.match(/ally|willing|support/i)) score += 1;
        
        // Damage type variety
        if (effects.match(/slashing/i)) score += 0.5;
        if (effects.match(/piercing/i)) score += 0.5;
        if (effects.match(/multi.*hit|projectile/i)) score += 0.5;
        
        // Temporary resource generation
        if (effects.match(/temporary.*slot|bonus.*slot|gain.*slot/i)) score += 1.5;
        
        // Cap at 10 (before synergy adjustments)
        score = Math.min(10, score);
        
        return {
          ...baseMove,
          baseUniquenessScore: Math.round(score * 10) / 10,
          uniquenessScore: Math.round(score * 10) / 10,
          primaryScore: Math.round(score * 10) / 10
        };
      }
    });

    // Second pass: find similarities and synergies (only for uniqueness mode)
    const withRelationships = analyzed.map(move => {
      if (analysisMode !== 'uniqueness') {
        // In non-uniqueness modes, just return the move as-is
        return move;
      }

      // Uniqueness mode: calculate similarities and synergies
      const similar = analyzed.filter(other => 
        other.name !== move.name && 
        calculateSimilarity(move, other) > 0.6
      );
      
      const synergies = detectSynergies(move, analyzed);
      
      // Adjust score based on synergies
      let adjustedScore = move.uniquenessScore;
      
      // If the move has strong synergies, it's more valuable even if similar to others
      const totalSynergyScore = synergies.reduce((sum, syn) => sum + syn.score, 0);
      if (totalSynergyScore > 0) {
        adjustedScore += Math.min(2, totalSynergyScore * 0.5); // Cap synergy bonus at +2
      }
      
      adjustedScore = Math.min(10, adjustedScore);
      
      return {
        ...move,
        uniquenessScore: Math.round(adjustedScore * 10) / 10,
        primaryScore: Math.round(adjustedScore * 10) / 10,
        similarMoves: similar.map(s => ({ 
          name: s.name, 
          similarity: calculateSimilarity(move, s),
          hasSynergy: synergies.some(syn => syn.name === s.name)
        })),
        synergies: synergies,
        synergyBonus: adjustedScore - move.baseUniquenessScore
      };
    });

    setAnalysisResults({
      moves: withRelationships,
      summary: generateSummary(withRelationships)
    });
  };

  const determineCategories = (move) => {
    const cats = [];
    const text = ((move.effects || '') + (move.description || '')).toLowerCase();
    
    if (text.includes('damage') || text.includes('attack roll')) cats.push('Damage');
    if (text.includes('movement') || text.includes('dash') || text.includes('meters')) cats.push('Mobility');
    if (text.includes('push') || text.includes('pull') || text.includes('knock')) cats.push('Forced Movement');
    if (text.includes('armor') || text.includes('deflect') || text.includes('reduce')) cats.push('Defense');
    if (text.includes('prone') || text.includes('dazed') || text.includes('stun')) cats.push('Control');
    if (text.includes('lingering') || text.includes('concentration') || text.includes('terrain')) cats.push('Area Control');
    if (text.includes('ally') || text.includes('willing') || text.includes('support')) cats.push('Support');
    
    return cats.length > 0 ? cats : ['Utility'];
  };

  const calculateSimilarity = (move1, move2) => {
    let similarity = 0;
    let factors = 0;

    // Action type similarity
    factors++;
    if (move1.actionType === move2.actionType) similarity += 0.3;

    // Category overlap
    factors++;
    const cats1 = move1.categories || [];
    const cats2 = move2.categories || [];
    const overlap = cats1.filter(c => cats2.includes(c)).length;
    if (overlap > 0) similarity += (overlap / Math.max(cats1.length, cats2.length)) * 0.4;

    // Range similarity
    factors++;
    if (move1.range && move2.range) {
      if (move1.range === move2.range) similarity += 0.3;
      else if (move1.range.includes('Self') && move2.range.includes('Self')) similarity += 0.2;
    }

    return similarity;
  };

  const generateSummary = (moves) => {
    const total = moves.length;
    
    // Stats that work for both modes
    const categoryCount = {};
    moves.forEach(move => {
      (move.categories || []).forEach(cat => {
        categoryCount[cat] = (categoryCount[cat] || 0) + 1;
      });
    });

    const overrepresentedCategories = Object.entries(categoryCount)
      .filter(([_, count]) => count >= 3)
      .sort((a, b) => b[1] - a[1]);

    let summary = {
      total,
      categoryCount,
      overrepresentedCategories
    };

    if (analysisMode === 'uniqueness') {
      // Uniqueness mode stats
      const lowUniqueness = moves.filter(m => m.uniquenessScore <= 5).length;
      const mediumUniqueness = moves.filter(m => m.uniquenessScore > 5 && m.uniquenessScore <= 7).length;
      const highUniqueness = moves.filter(m => m.uniquenessScore > 7).length;

      // Count synergies
      const totalSynergies = moves.reduce((sum, m) => sum + (m.synergies?.length || 0), 0);
      const movesWithSynergies = moves.filter(m => m.synergies && m.synergies.length > 0).length;
      const avgSynergyBonus = moves.reduce((sum, m) => sum + (m.synergyBonus || 0), 0) / total;

      summary = {
        ...summary,
        lowUniqueness,
        mediumUniqueness,
        highUniqueness,
        totalSynergies,
        movesWithSynergies,
        avgSynergyBonus
      };
    } else if (analysisMode === 'balance') {
      // Balance mode stats
      const lowBalance = moves.filter(m => m.balanceScore <= 4).length;
      const mediumBalance = moves.filter(m => m.balanceScore > 4 && m.balanceScore <= 7).length;
      const highBalance = moves.filter(m => m.balanceScore > 7).length;

      summary = {
        ...summary,
        lowBalance,
        mediumBalance,
        highBalance
      };
    } else if (analysisMode === 'simplicity') {
      // Simplicity mode stats
      const lowSimplicity = moves.filter(m => m.simplicityScore <= 5).length;
      const mediumSimplicity = moves.filter(m => m.simplicityScore > 5 && m.simplicityScore <= 7).length;
      const highSimplicity = moves.filter(m => m.simplicityScore > 7).length;
      
      // Word count stats
      const wordCounts = moves.map(m => m.simplicityFeedback?.features?.word_count || 0);
      const avgWordCount = wordCounts.reduce((a, b) => a + b, 0) / total;
      const shortMoves = moves.filter(m => (m.simplicityFeedback?.features?.word_count || 0) <= 12).length;
      const longMoves = moves.filter(m => (m.simplicityFeedback?.features?.word_count || 0) > 25).length;

      summary = {
        ...summary,
        lowSimplicity,
        mediumSimplicity,
        highSimplicity,
        avgWordCount: avgWordCount.toFixed(1),
        shortMoves,
        longMoves
      };
    } else if (analysisMode === 'full') {
      // Full analysis mode stats
      const excellent = moves.filter(m => m.fullScore >= 8).length;
      const good = moves.filter(m => m.fullScore >= 6 && m.fullScore < 8).length;
      const needsWork = moves.filter(m => m.fullScore < 6).length;
      
      // Average breakdown
      const avgBalance = moves.reduce((sum, m) => sum + (m.fullBreakdown?.balance || 5), 0) / total;
      const avgUniqueness = moves.reduce((sum, m) => sum + (m.fullBreakdown?.uniqueness || 5), 0) / total;
      const avgSimplicity = moves.reduce((sum, m) => sum + (m.fullBreakdown?.simplicity || 5), 0) / total;

      summary = {
        ...summary,
        excellent,
        good,
        needsWork,
        avgBalance: avgBalance.toFixed(1),
        avgUniqueness: avgUniqueness.toFixed(1),
        avgSimplicity: avgSimplicity.toFixed(1)
      };
    } else {
      // Fallback for any unknown mode
      summary = {
        ...summary,
        lowBalance: 0,
        mediumBalance: 0,
        highBalance: 0
      };
    }

    summary.recommendations = generateRecommendations(moves, categoryCount);
    return summary;
  };

  const generateRecommendations = (moves, categoryCount) => {
    const recs = [];
    
    if (analysisMode === 'uniqueness') {
      // UNIQUENESS MODE RECOMMENDATIONS
      
      // Find moves to replace (low uniqueness)
      const toReplace = moves
        .filter(m => m.uniquenessScore <= 5)
        .sort((a, b) => a.uniquenessScore - b.uniquenessScore);
      
      if (toReplace.length > 0) {
        recs.push({
          type: 'replace',
          priority: 'high',
          moves: toReplace.slice(0, 3).map(m => m.name),
          reason: 'Low uniqueness scores and high similarity to other moves'
        });
      }

      // Identify overrepresented categories
      const overrep = Object.entries(categoryCount)
        .filter(([_, count]) => count >= 4)
        .map(([cat]) => cat);
      
      if (overrep.length > 0) {
        recs.push({
          type: 'diversify',
          priority: 'medium',
          categories: overrep,
          reason: `Too many moves in categories: ${overrep.join(', ')}`
        });
      }

      // Find missing mechanics
      const allCategories = ['Damage', 'Mobility', 'Forced Movement', 'Defense', 'Control', 'Area Control', 'Support', 'Utility'];
      const missing = allCategories.filter(cat => !categoryCount[cat] || categoryCount[cat] === 0);
      
      if (missing.length > 0) {
        recs.push({
          type: 'add',
          priority: 'low',
          categories: missing,
          reason: `Consider adding moves with: ${missing.join(', ')}`
        });
      }
    } else {
      // BALANCE MODE RECOMMENDATIONS
      
      // Find severely underpowered moves (≤3.5)
      const severelyUnderpowered = moves
        .filter(m => m.balanceScore <= 3.5)
        .sort((a, b) => a.balanceScore - b.balanceScore);
      
      if (severelyUnderpowered.length > 0) {
        recs.push({
          type: 'rebalance',
          priority: 'high',
          moves: severelyUnderpowered.slice(0, 5).map(m => m.name),
          reason: `${severelyUnderpowered.length} severely underpowered moves (score ≤3.5) - consider buffing damage, reducing cost, or adding utility`
        });
      }

      // Find overpowered moves (≥7.5)
      const overpowered = moves
        .filter(m => m.balanceScore >= 7.5)
        .sort((a, b) => b.balanceScore - a.balanceScore);
      
      if (overpowered.length > 0) {
        recs.push({
          type: 'nerf',
          priority: 'high',
          moves: overpowered.map(m => m.name),
          reason: `${overpowered.length} overpowered moves (score ≥7.5) - consider reducing damage, increasing cost, or limiting utility`
        });
      }

      // Find moves with poor damage efficiency
      const inefficient = moves
        .filter(m => m.balanceMetrics?.damagePerSlot < 5)
        .sort((a, b) => (a.balanceMetrics?.damagePerSlot || 0) - (b.balanceMetrics?.damagePerSlot || 0));
      
      if (inefficient.length >= 5) {
        recs.push({
          type: 'optimize',
          priority: 'medium',
          moves: inefficient.slice(0, 3).map(m => m.name),
          reason: `${inefficient.length} moves with low damage efficiency (<5 damage/slot) - consider adjusting damage or cost`
        });
      }

      // Check for level imbalances
      const byLevel = {};
      moves.forEach(m => {
        if (!byLevel[m.level]) byLevel[m.level] = [];
        byLevel[m.level].push(m.balanceScore);
      });
      
      const levelImbalances = Object.entries(byLevel)
        .filter(([lvl, scores]) => {
          const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
          return Math.abs(avg - 5.0) > 1.5; // More than 1.5 from target
        })
        .map(([lvl, scores]) => {
          const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
          return { level: lvl, avg: avg.toFixed(1) };
        });
      
      if (levelImbalances.length > 0) {
        recs.push({
          type: 'level-balance',
          priority: 'medium',
          levels: levelImbalances.map(l => `Level ${l.level} (avg: ${l.avg})`),
          reason: `Some levels have imbalanced average scores - target is 5.0`
        });
      }
    }

    return recs;
  };

  const getSortedMoves = () => {
    if (!analysisResults) return [];
    
    let filtered = analysisResults.moves.filter(m => (m.uniquenessScore || m.primaryScore || 0) >= filterThreshold);
    
    switch (sortBy) {
      case 'uniqueness':
      case 'balance':
      case 'simplicity':
      case 'full':
        return filtered.sort((a, b) => (b.primaryScore || b.uniquenessScore || 0) - (a.primaryScore || a.uniquenessScore || 0));
      case 'power':
        return filtered.sort((a, b) => (b.balanceMetrics?.powerLevel || 0) - (a.balanceMetrics?.powerLevel || 0));
      case 'efficiency':
        return filtered.sort((a, b) => (b.balanceMetrics?.damagePerSlot || 0) - (a.balanceMetrics?.damagePerSlot || 0));
      case 'wordCount':
        return filtered.sort((a, b) => {
          const aWords = (a.simplicityFeedback?.features?.word_count || 0);
          const bWords = (b.simplicityFeedback?.features?.word_count || 0);
          return aWords - bWords; // Ascending - fewer words is better
        });
      case 'name':
        return filtered.sort((a, b) => a.name.localeCompare(b.name));
      case 'level':
        return filtered.sort((a, b) => a.level - b.level);
      case 'actionType':
        return filtered.sort((a, b) => a.actionType.localeCompare(b.actionType));
      default:
        return filtered;
    }
  };

  const getUniquenessColor = (score) => {
    if (score <= 4) return '#e74c3c';
    if (score <= 6) return '#e67e22';
    if (score <= 8) return '#f39c12';
    return '#2ecc71';
  };

  const getRecommendationIcon = (type) => {
    switch (type) {
      // Uniqueness mode icons
      case 'replace': return '⚠️';
      case 'diversify': return '🔄';
      case 'add': return '💡';
      // Balance mode icons
      case 'rebalance': return '⚖️';
      case 'nerf': return '⬇️';
      case 'optimize': return '📈';
      case 'level-balance': return '📊';
      default: return '📋';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return '#e74c3c';
      case 'medium': return '#f39c12';
      case 'low': return '#3498db';
      default: return '#95a5a6';
    }
  };

  const toggleMoveExpanded = (moveName) => {
    setExpandedMoves(prev => {
      const newSet = new Set(prev);
      if (newSet.has(moveName)) {
        newSet.delete(moveName);
      } else {
        newSet.add(moveName);
      }
      return newSet;
    });
  };

  const getMoveColors = (move) => {
    const element = move.element || (selectedElements.length === 1 ? selectedElements[0] : 'air');
    return {
      elementColor: ELEMENT_COLORS[element] || '#3498db',
      actionColor: ACTION_COLORS[move.actionType] || '#3498db'
    };
  };

  // Group moves by level and action type for better organization
  const getGroupedMoves = () => {
    if (!analysisResults) return {};
    
    let filtered = analysisResults.moves.filter(m => m.uniquenessScore >= filterThreshold);
    
    // Sort based on selected option
    switch (sortBy) {
      case 'uniqueness':
        filtered = filtered.sort((a, b) => a.uniquenessScore - b.uniquenessScore);
        break;
      case 'name':
        filtered = filtered.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'level':
        filtered = filtered.sort((a, b) => a.level - b.level);
        break;
      case 'actionType':
        filtered = filtered.sort((a, b) => a.actionType.localeCompare(b.actionType));
        break;
    }

    // Group by level
    const grouped = {};
    filtered.forEach(move => {
      const levelKey = `Level ${move.level}`;
      if (!grouped[levelKey]) {
        grouped[levelKey] = [];
      }
      grouped[levelKey].push(move);
    });

    return grouped;
  };

  const renderMoveCard = (move) => {
    const colors = getMoveColors(move);
    const isExpanded = expandedMoves.has(move.name);
    const uniquenessColor = getUniquenessColor(move.uniquenessScore);

    return (
      <div 
        key={move.name}
        className="move-card-analysis"
        style={{
          background: lightMode ? '#fff' : '#2d2d30',
          border: `2px solid ${colors.elementColor}`,
          borderRadius: '8px',
          marginBottom: '12px',
          overflow: 'hidden',
          transition: 'all 0.3s ease'
        }}
      >
        {/* Move Header */}
        <div 
          className="move-card-header"
          onClick={() => toggleMoveExpanded(move.name)}
          style={{
            background: `linear-gradient(135deg, ${colors.actionColor}dd 0%, ${colors.elementColor}dd 100%)`,
            padding: '12px 16px',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            userSelect: 'none'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
            <span style={{ 
              fontSize: '16px', 
              fontWeight: '700',
              color: '#fff',
              textShadow: '0 1px 2px rgba(0,0,0,0.3)'
            }}>
              {move.name}
            </span>
            <span style={{
              padding: '3px 8px',
              background: 'rgba(255,255,255,0.2)',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: '600',
              color: '#fff'
            }}>
              L{move.level}
            </span>
            <span style={{
              padding: '3px 8px',
              background: colors.actionColor,
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: '600',
              color: '#fff'
            }}>
              {move.actionType}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div 
              style={{
                padding: '6px 12px',
                background: uniquenessColor,
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '700',
                color: '#fff',
                boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                lineHeight: '1.2'
              }}
            >
              <div style={{ fontSize: '10px', opacity: 0.8 }}>
                {analysisMode === 'balance' ? 'Balance' : 'Uniqueness'}
              </div>
              <div>{(move.primaryScore || move.uniquenessScore || 0).toFixed(1)}/10</div>
            </div>
            <span style={{ fontSize: '14px', color: '#fff' }}>
              {isExpanded ? '▲' : '▼'}
            </span>
          </div>
        </div>

        {/* Move Body - Collapsible */}
        {isExpanded && (
          <div style={{ padding: '16px' }}>
            
            {/* Balance Metrics (Balance Mode Only) */}
            {analysisMode === 'balance' && move.balanceMetrics && (
              <div style={{
                marginBottom: '16px',
                padding: '12px',
                background: lightMode ? '#f0f4ff' : 'rgba(102, 126, 234, 0.1)',
                borderRadius: '6px',
                border: `2px solid ${lightMode ? '#667eea' : '#4ec9b0'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <strong style={{ color: lightMode ? '#667eea' : '#4ec9b0' }}>
                    ⚖️ Balance Metrics
                  </strong>
                  {move.balanceMetrics.scoringMethod && (
                    <span style={{ 
                      fontSize: '10px', 
                      padding: '2px 8px', 
                      background: move.balanceMetrics.scoringMethod === 'ml' ? '#4ec9b0' : 
                                  move.balanceMetrics.scoringMethod === 'tuned' ? '#9b59b6' : '#f39c12',
                      borderRadius: '10px',
                      color: '#000',
                      fontWeight: '600'
                    }}>
                      {move.balanceMetrics.scoringMethod === 'ml' ? '🤖 ML-Powered' : 
                       move.balanceMetrics.scoringMethod === 'tuned' ? '🎯 ML-Tuned' : '📊 Rule-Based'}
                    </span>
                  )}
                </div>
                
                {move.balanceMetrics.rating && (
                  <div style={{ 
                    marginBottom: '12px', 
                    padding: '8px', 
                    background: lightMode ? '#e7f3ff' : 'rgba(78, 201, 176, 0.15)',
                    borderRadius: '4px',
                    fontSize: '13px',
                    fontWeight: '600',
                    color: lightMode ? '#667eea' : '#4ec9b0'
                  }}>
                    Rating: {move.balanceMetrics.rating}
                  </div>
                )}
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', fontSize: '13px' }}>
                  {move.balanceMetrics.damagePerSlot > 0 && (
                    <div>
                      <div style={{ opacity: 0.7, fontSize: '11px' }}>Damage/Slot</div>
                      <div style={{ fontWeight: '600', color: '#3498db' }}>{move.balanceMetrics.damagePerSlot.toFixed(1)}</div>
                    </div>
                  )}
                  <div>
                    <div style={{ opacity: 0.7, fontSize: '11px' }}>Utility</div>
                    <div style={{ fontWeight: '600', color: '#2ecc71' }}>{move.balanceMetrics.utilityScore}</div>
                  </div>
                  <div>
                    <div style={{ opacity: 0.7, fontSize: '11px' }}>Power</div>
                    <div style={{ fontWeight: '600', color: '#e67e22' }}>{move.balanceMetrics.powerLevel.toFixed(0)}/100</div>
                  </div>
                  <div>
                    <div style={{ opacity: 0.7, fontSize: '11px' }}>Cost Effectiveness</div>
                    <div style={{ fontWeight: '600', color: '#9b59b6' }}>{move.balanceMetrics.costEffectiveness.toFixed(1)}</div>
                  </div>
                </div>
                
                {/* Balance warnings/strengths */}
                {move.balanceMetrics.warnings && move.balanceMetrics.warnings.length > 0 && (
                  <div style={{ marginTop: '12px', padding: '8px', background: lightMode ? '#fff3cd' : 'rgba(241, 196, 15, 0.1)', borderRadius: '4px', border: '1px solid #f1c40f' }}>
                    {move.balanceMetrics.warnings.map((warning, idx) => (
                      <div key={idx} style={{ fontSize: '12px', color: lightMode ? '#856404' : '#f39c12', marginBottom: '2px' }}>
                        {warning}
                      </div>
                    ))}
                  </div>
                )}
                {move.balanceMetrics.strengths && move.balanceMetrics.strengths.length > 0 && (
                  <div style={{ marginTop: '8px', padding: '8px', background: lightMode ? '#d4edda' : 'rgba(46, 204, 113, 0.1)', borderRadius: '4px', border: '1px solid #2ecc71' }}>
                    {move.balanceMetrics.strengths.map((strength, idx) => (
                      <div key={idx} style={{ fontSize: '12px', color: lightMode ? '#155724' : '#27ae60', marginBottom: '2px' }}>
                        {strength}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Range */}
            {move.range && (
              <div style={{ 
                marginBottom: '12px',
                padding: '8px 12px',
                background: lightMode ? '#f0f0f0' : 'rgba(255,255,255,0.05)',
                borderRadius: '6px',
                borderLeft: `3px solid ${colors.elementColor}`
              }}>
                <strong style={{ color: colors.elementColor, marginRight: '8px' }}>Range:</strong>
                <span>{move.range}</span>
              </div>
            )}

            {/* Damage */}
            {move.damage && (
              <div style={{ 
                marginBottom: '12px',
                padding: '8px 12px',
                background: lightMode ? '#fff5f5' : 'rgba(231,76,60,0.1)',
                borderRadius: '6px',
                borderLeft: '3px solid #e74c3c'
              }}>
                <strong style={{ color: '#e74c3c', marginRight: '8px' }}>Damage:</strong>
                <span>{move.damage}</span>
              </div>
            )}

            {/* Duration */}
            {move.duration && (
              <div style={{ 
                marginBottom: '12px',
                padding: '8px 12px',
                background: lightMode ? '#f0f0f0' : 'rgba(255,255,255,0.05)',
                borderRadius: '6px',
                borderLeft: `3px solid ${colors.actionColor}`
              }}>
                <strong style={{ color: colors.actionColor, marginRight: '8px' }}>Duration:</strong>
                <span>{move.duration}</span>
              </div>
            )}

            {/* Cost */}
            {move.cost && (
              <div style={{ 
                marginBottom: '12px',
                padding: '8px 12px',
                background: lightMode ? '#fffbf0' : 'rgba(243,156,18,0.1)',
                borderRadius: '6px',
                borderLeft: '3px solid #f39c12'
              }}>
                <strong style={{ color: '#f39c12', marginRight: '8px' }}>Cost:</strong>
                <span>{move.cost}</span>
              </div>
            )}

            {/* Effects */}
            <div style={{ 
              marginBottom: '12px',
              padding: '12px',
              background: lightMode ? '#f8f9fa' : 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: `1px solid ${lightMode ? '#e0e0e0' : '#3e3e42'}`
            }}>
              <strong style={{ display: 'block', marginBottom: '8px', color: colors.elementColor }}>
                Effect:
              </strong>
              <div style={{ lineHeight: '1.6', fontSize: '14px' }}>
                {move.effects || move.description || 'No description available'}
              </div>
            </div>

            {/* Categories */}
            {move.categories && move.categories.length > 0 && (
              <div style={{ marginBottom: '12px' }}>
                <strong style={{ display: 'block', marginBottom: '6px', fontSize: '13px' }}>
                  Categories:
                </strong>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {move.categories.map(cat => (
                    <span
                      key={cat}
                      style={{
                        padding: '4px 10px',
                        background: `${colors.elementColor}33`,
                        border: `1px solid ${colors.elementColor}`,
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600',
                        color: lightMode ? colors.elementColor : '#fff'
                      }}
                    >
                      {cat}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Similar Moves Warning (Uniqueness Mode Only) */}
            {analysisMode === 'uniqueness' && move.similarMoves && move.similarMoves.length > 0 && (
              <div style={{ 
                marginTop: '12px',
                padding: '12px',
                background: lightMode ? '#fff5f5' : 'rgba(231,76,60,0.1)',
                borderRadius: '6px',
                border: '2px solid #e74c3c'
              }}>
                <strong style={{ color: '#e74c3c', display: 'block', marginBottom: '8px' }}>
                  ⚠️ Similar Moves Detected:
                </strong>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {move.similarMoves.map((sim, i) => (
                    <span
                      key={i}
                      style={{
                        padding: '4px 10px',
                        background: sim.hasSynergy ? 'rgba(46,204,113,0.2)' : 'rgba(231,76,60,0.2)',
                        border: `1px solid ${sim.hasSynergy ? '#2ecc71' : '#e74c3c'}`,
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600',
                        color: sim.hasSynergy ? '#2ecc71' : '#e74c3c',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      {sim.hasSynergy && '✨ '}
                      {sim.name} ({Math.round(sim.similarity * 100)}%)
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Synergies Display (Uniqueness Mode Only) */}
            {analysisMode === 'uniqueness' && move.synergies && move.synergies.length > 0 && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                background: lightMode ? '#d4edda' : 'rgba(46, 204, 113, 0.15)',
                borderRadius: '6px',
                border: '2px solid #2ecc71'
              }}>
                <div style={{ 
                  fontWeight: '600', 
                  color: lightMode ? '#155724' : '#2ecc71',
                  marginBottom: '8px',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <span>✨ Synergies Found</span>
                  {move.synergyBonus > 0 && (
                    <span style={{
                      fontSize: '11px',
                      backgroundColor: lightMode ? '#c3e6cb' : 'rgba(46, 204, 113, 0.3)',
                      padding: '3px 10px',
                      borderRadius: '10px',
                      fontWeight: '700'
                    }}>
                      +{move.synergyBonus.toFixed(1)} uniqueness bonus
                    </span>
                  )}
                </div>
                {move.synergies.map((syn, idx) => (
                  <div key={idx} style={{
                    marginBottom: '8px',
                    paddingBottom: '8px',
                    borderBottom: idx < move.synergies.length - 1 ? `1px solid ${lightMode ? '#c3e6cb' : 'rgba(46, 204, 113, 0.3)'}` : 'none'
                  }}>
                    <div style={{
                      fontSize: '13px',
                      fontWeight: '700',
                      color: lightMode ? '#155724' : '#2ecc71',
                      marginBottom: '4px'
                    }}>
                      → {syn.name} (Level {syn.level}) - Synergy Score: {syn.score.toFixed(1)}
                    </div>
                    <div style={{
                      fontSize: '12px',
                      marginLeft: '12px',
                      color: lightMode ? '#155724' : '#27ae60',
                      opacity: 0.9,
                      lineHeight: '1.4'
                    }}>
                      {syn.reasons.map((reason, ridx) => (
                        <div key={ridx}>• {reason}</div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* File Path */}
            <div style={{ 
              marginTop: '12px',
              padding: '8px',
              background: lightMode ? '#f0f0f0' : 'rgba(255,255,255,0.03)',
              borderRadius: '4px',
              fontSize: '11px',
              opacity: 0.7,
              fontFamily: 'monospace'
            }}>
              {move.filePath}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`gm-mode ${lightMode ? 'light-mode' : ''}`}>
      <div className="gm-header">
        <h1>🎲 Game Master Tools</h1>
        <p className="gm-subtitle">Analysis and management tools for campaign content</p>
      </div>

      <div className="gm-tabs">
        <button 
          className={`gm-tab ${activeTab === 'moveAnalysis' ? 'active' : ''}`}
          onClick={() => setActiveTab('moveAnalysis')}
        >
          🎯 Move Analysis
        </button>
        <button 
          className={`gm-tab ${activeTab === 'content' ? 'active' : ''}`}
          onClick={() => setActiveTab('content')}
        >
          📚 Content Overview
        </button>
        <button 
          className={`gm-tab ${activeTab === 'sessions' ? 'active' : ''}`}
          onClick={() => setActiveTab('sessions')}
        >
          👥 Active Sessions
        </button>
      </div>

      <div className="gm-content">
        {activeTab === 'moveAnalysis' && (
          <div className="analysis-panel">
            <div className="controls-section">
              <h2>Analysis Configuration</h2>
              
              <div className="control-group">
                <label>Analysis Mode:</label>
                <div className="element-selector" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                  <button
                    className={`element-btn ${analysisMode === 'uniqueness' ? 'active' : ''}`}
                    onClick={() => {
                      setAnalysisMode('uniqueness');
                      setSortBy('uniqueness');
                    }}
                  >
                    🎯 Uniqueness
                  </button>
                  <button
                    className={`element-btn ${analysisMode === 'balance' ? 'active' : ''}`}
                    onClick={() => {
                      setAnalysisMode('balance');
                      setSortBy('balance');
                    }}
                  >
                    ⚖️ Balance
                  </button>
                  <button
                    className={`element-btn ${analysisMode === 'simplicity' ? 'active' : ''}`}
                    onClick={() => {
                      setAnalysisMode('simplicity');
                      setSortBy('simplicity');
                    }}
                  >
                    📝 Simplicity
                  </button>
                  <button
                    className={`element-btn ${analysisMode === 'full' ? 'active' : ''}`}
                    onClick={() => {
                      setAnalysisMode('full');
                      setSortBy('full');
                    }}
                  >
                    🔮 Full Analysis
                  </button>
                </div>
                <p style={{ fontSize: '12px', opacity: 0.7, marginTop: '8px', marginBottom: 0 }}>
                  {analysisMode === 'uniqueness' && 'Analyzes move creativity, originality, and synergies'}
                  {analysisMode === 'balance' && 'Analyzes damage efficiency, cost effectiveness, and power balance'}
                  {analysisMode === 'simplicity' && 'Rewards clear wording, brevity, and simple structure'}
                  {analysisMode === 'full' && 'ML-powered combination of all three analysis types'}
                </p>
              </div>

              <div className="control-group">
                <label>Element:</label>
                <div className="element-selector">
                  {elements.map(el => (
                    <button
                      key={el}
                      className={`element-btn ${selectedElements.includes(el) ? 'active' : ''}`}
                      onClick={() => {
                        if (selectedElements.includes(el)) {
                          // Remove if already selected (but keep at least one)
                          if (selectedElements.length > 1) {
                            setSelectedElements(selectedElements.filter(e => e !== el));
                          }
                        } else {
                          // Add to selection
                          setSelectedElements([...selectedElements, el]);
                        }
                      }}
                    >
                      {el.charAt(0).toUpperCase() + el.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div className="control-group">
                <label>Levels to Compare:</label>
                <div className="level-selector">
                  {levels.map(lvl => (
                    <button
                      key={lvl}
                      className={`level-btn ${selectedLevels.includes(lvl) ? 'active' : ''}`}
                      onClick={() => {
                        if (selectedLevels.includes(lvl)) {
                          setSelectedLevels(selectedLevels.filter(l => l !== lvl));
                        } else {
                          setSelectedLevels([...selectedLevels, lvl].sort());
                        }
                      }}
                    >
                      Level {lvl}
                    </button>
                  ))}
                </div>
              </div>

              <div className="control-group">
                <label>Sort By:</label>
                <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                  {analysisMode === 'uniqueness' && (
                    <>
                      <option value="uniqueness">Uniqueness Score</option>
                      <option value="name">Name</option>
                      <option value="level">Level</option>
                      <option value="actionType">Action Type</option>
                    </>
                  )}
                  {analysisMode === 'balance' && (
                    <>
                      <option value="balance">Balance Score</option>
                      <option value="power">Power Level</option>
                      <option value="efficiency">Damage Efficiency</option>
                      <option value="name">Name</option>
                      <option value="level">Level</option>
                      <option value="actionType">Action Type</option>
                    </>
                  )}
                  {analysisMode === 'simplicity' && (
                    <>
                      <option value="simplicity">Simplicity Score</option>
                      <option value="wordCount">Word Count</option>
                      <option value="name">Name</option>
                      <option value="level">Level</option>
                      <option value="actionType">Action Type</option>
                    </>
                  )}
                  {analysisMode === 'full' && (
                    <>
                      <option value="full">Overall Score</option>
                      <option value="balance">Balance Component</option>
                      <option value="uniqueness">Uniqueness Component</option>
                      <option value="simplicity">Simplicity Component</option>
                      <option value="name">Name</option>
                      <option value="level">Level</option>
                      <option value="actionType">Action Type</option>
                    </>
                  )}
                </select>
              </div>

              <div className="control-group">
                <label>
                  Filter: Min {analysisMode === 'uniqueness' ? 'Uniqueness' : 'Balance'} Score ({filterThreshold})
                </label>
                <input 
                  type="range" 
                  min="0" 
                  max="10" 
                  step="0.5"
                  value={filterThreshold}
                  onChange={(e) => setFilterThreshold(parseFloat(e.target.value))}
                />
              </div>

              <button 
                className="analyze-btn"
                onClick={fetchMoves}
                disabled={loading || selectedLevels.length === 0}
              >
                {loading ? '⏳ Analyzing...' : '🔍 Run Analysis'}
              </button>
            </div>

            {analysisResults && (
              <>
                <div className="summary-section">
                  <h2>📊 Analysis Summary</h2>
                  <div className="summary-grid">
                    <div className="summary-card">
                      <div className="summary-value">{analysisResults.summary.total}</div>
                      <div className="summary-label">Total Moves</div>
                    </div>
                    
                    {analysisMode === 'uniqueness' ? (
                      <>
                        <div className="summary-card danger">
                          <div className="summary-value">{analysisResults.summary.lowUniqueness}</div>
                          <div className="summary-label">Low Uniqueness (≤5)</div>
                        </div>
                        <div className="summary-card warning">
                          <div className="summary-value">{analysisResults.summary.mediumUniqueness}</div>
                          <div className="summary-label">Medium (6-7)</div>
                        </div>
                        <div className="summary-card success">
                          <div className="summary-value">{analysisResults.summary.highUniqueness}</div>
                          <div className="summary-label">High Uniqueness (&gt;7)</div>
                        </div>
                      </>
                    ) : analysisMode === 'balance' ? (
                      <>
                        <div className="summary-card danger">
                          <div className="summary-value">{analysisResults.summary.lowBalance || 0}</div>
                          <div className="summary-label">Underpowered (≤4)</div>
                        </div>
                        <div className="summary-card warning">
                          <div className="summary-value">{analysisResults.summary.mediumBalance || 0}</div>
                          <div className="summary-label">Balanced (5-7)</div>
                        </div>
                        <div className="summary-card success">
                          <div className="summary-value">{analysisResults.summary.highBalance || 0}</div>
                          <div className="summary-label">Overpowered (&gt;7)</div>
                        </div>
                      </>
                    ) : analysisMode === 'simplicity' ? (
                      <>
                        <div className="summary-card danger">
                          <div className="summary-value">{analysisResults.summary.lowSimplicity || 0}</div>
                          <div className="summary-label">Complex (≤5)</div>
                        </div>
                        <div className="summary-card warning">
                          <div className="summary-value">{analysisResults.summary.mediumSimplicity || 0}</div>
                          <div className="summary-label">Moderate (6-7)</div>
                        </div>
                        <div className="summary-card success">
                          <div className="summary-value">{analysisResults.summary.highSimplicity || 0}</div>
                          <div className="summary-label">Simple (&gt;7)</div>
                        </div>
                        <div className="summary-card info">
                          <div className="summary-value">{analysisResults.summary.avgWordCount || '0'}</div>
                          <div className="summary-label">Avg Words</div>
                        </div>
                      </>
                    ) : analysisMode === 'full' ? (
                      <>
                        <div className="summary-card success">
                          <div className="summary-value">{analysisResults.summary.excellent || 0}</div>
                          <div className="summary-label">Excellent (≥8)</div>
                        </div>
                        <div className="summary-card warning">
                          <div className="summary-value">{analysisResults.summary.good || 0}</div>
                          <div className="summary-label">Good (6-8)</div>
                        </div>
                        <div className="summary-card danger">
                          <div className="summary-value">{analysisResults.summary.needsWork || 0}</div>
                          <div className="summary-label">Needs Work (&lt;6)</div>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="summary-card danger">
                          <div className="summary-value">{analysisResults.summary.lowBalance || 0}</div>
                          <div className="summary-label">Low Score (≤4)</div>
                        </div>
                        <div className="summary-card warning">
                          <div className="summary-value">{analysisResults.summary.mediumBalance || 0}</div>
                          <div className="summary-label">Medium (5-7)</div>
                        </div>
                        <div className="summary-card success">
                          <div className="summary-value">{analysisResults.summary.highBalance || 0}</div>
                          <div className="summary-label">High Score (&gt;7)</div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Component Scores Breakdown (Full Analysis Mode Only) */}
                  {analysisMode === 'full' && (
                    <div style={{
                      marginTop: '20px',
                      padding: '16px',
                      background: lightMode ? '#e8f4f8' : 'rgba(66, 133, 244, 0.15)',
                      borderRadius: '8px',
                      border: '2px solid #4285f4'
                    }}>
                      <h3 style={{ 
                        color: lightMode ? '#1976d2' : '#4285f4',
                        marginBottom: '16px',
                        fontSize: '16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        <span>🔮</span>
                        <span>ML-Powered Component Analysis</span>
                        <span style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          background: '#4285f4',
                          color: '#fff',
                          borderRadius: '12px',
                          fontWeight: '600'
                        }}>
                          {analysisResults.moves[0]?.fullFeedback?.method_badge || '🤖 ML-Powered'}
                        </span>
                      </h3>
                      <div style={{ 
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '12px'
                      }}>
                        <div style={{
                          padding: '12px',
                          background: lightMode ? 'rgba(52, 152, 219, 0.1)' : 'rgba(52, 152, 219, 0.2)',
                          borderRadius: '6px',
                          border: '1px solid #3498db'
                        }}>
                          <div style={{ 
                            fontSize: '11px',
                            color: lightMode ? '#2980b9' : '#3498db',
                            marginBottom: '4px',
                            fontWeight: '600'
                          }}>
                            ⚖️ BALANCE
                          </div>
                          <div style={{ 
                            fontSize: '28px',
                            fontWeight: '700',
                            color: lightMode ? '#2980b9' : '#3498db'
                          }}>
                            {analysisResults.summary.avgBalance || '5.0'}
                          </div>
                          <div style={{ 
                            fontSize: '11px',
                            color: lightMode ? '#2980b9' : '#3498db',
                            opacity: 0.8
                          }}>
                            Target: 5.0 (balanced power)
                          </div>
                        </div>
                        
                        <div style={{
                          padding: '12px',
                          background: lightMode ? 'rgba(155, 89, 182, 0.1)' : 'rgba(155, 89, 182, 0.2)',
                          borderRadius: '6px',
                          border: '1px solid #9b59b6'
                        }}>
                          <div style={{ 
                            fontSize: '11px',
                            color: lightMode ? '#8e44ad' : '#9b59b6',
                            marginBottom: '4px',
                            fontWeight: '600'
                          }}>
                            🎯 UNIQUENESS
                          </div>
                          <div style={{ 
                            fontSize: '28px',
                            fontWeight: '700',
                            color: lightMode ? '#8e44ad' : '#9b59b6'
                          }}>
                            {analysisResults.summary.avgUniqueness || '5.0'}
                          </div>
                          <div style={{ 
                            fontSize: '11px',
                            color: lightMode ? '#8e44ad' : '#9b59b6',
                            opacity: 0.8
                          }}>
                            Target: 7.0 (highly creative)
                          </div>
                        </div>
                        
                        <div style={{
                          padding: '12px',
                          background: lightMode ? 'rgba(46, 204, 113, 0.1)' : 'rgba(46, 204, 113, 0.2)',
                          borderRadius: '6px',
                          border: '1px solid #2ecc71'
                        }}>
                          <div style={{ 
                            fontSize: '11px',
                            color: lightMode ? '#27ae60' : '#2ecc71',
                            marginBottom: '4px',
                            fontWeight: '600'
                          }}>
                            📝 SIMPLICITY
                          </div>
                          <div style={{ 
                            fontSize: '28px',
                            fontWeight: '700',
                            color: lightMode ? '#27ae60' : '#2ecc71'
                          }}>
                            {analysisResults.summary.avgSimplicity || '5.0'}
                          </div>
                          <div style={{ 
                            fontSize: '11px',
                            color: lightMode ? '#27ae60' : '#2ecc71',
                            opacity: 0.8
                          }}>
                            Target: 7.0 (clear & concise)
                          </div>
                        </div>
                      </div>
                      <div style={{
                        marginTop: '12px',
                        padding: '10px',
                        background: lightMode ? 'rgba(255, 255, 255, 0.5)' : 'rgba(0, 0, 0, 0.3)',
                        borderRadius: '4px',
                        fontSize: '12px',
                        lineHeight: '1.5',
                        color: lightMode ? '#1976d2' : '#64b5f6'
                      }}>
                        <strong>💡 Interpretation:</strong> The ML model combines these three dimensions using weighted analysis. 
                        Moves closer to the ideal point (5, 7, 7) receive higher overall scores. The system automatically 
                        penalizes extreme imbalances and rewards consistency across all three dimensions.
                      </div>
                    </div>
                  )}

                  {/* Synergy Stats (Uniqueness Mode Only) */}
                  {analysisMode === 'uniqueness' && analysisResults.summary.totalSynergies > 0 && (
                    <div style={{
                      marginTop: '20px',
                      padding: '16px',
                      background: lightMode ? '#d4edda' : 'rgba(46, 204, 113, 0.15)',
                      borderRadius: '8px',
                      border: '2px solid #2ecc71'
                    }}>
                      <h3 style={{ 
                        color: lightMode ? '#155724' : '#2ecc71',
                        marginBottom: '12px',
                        fontSize: '16px'
                      }}>
                        ✨ Synergy Analysis
                      </h3>
                      <div style={{ 
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '12px'
                      }}>
                        <div style={{
                          padding: '12px',
                          background: lightMode ? '#c3e6cb' : 'rgba(46, 204, 113, 0.2)',
                          borderRadius: '6px'
                        }}>
                          <div style={{ 
                            fontSize: '24px',
                            fontWeight: '700',
                            color: lightMode ? '#155724' : '#2ecc71'
                          }}>
                            {analysisResults.summary.totalSynergies}
                          </div>
                          <div style={{ 
                            fontSize: '12px',
                            color: lightMode ? '#155724' : '#27ae60',
                            opacity: 0.9
                          }}>
                            Total Synergies
                          </div>
                        </div>
                        <div style={{
                          padding: '12px',
                          background: lightMode ? '#c3e6cb' : 'rgba(46, 204, 113, 0.2)',
                          borderRadius: '6px'
                        }}>
                          <div style={{ 
                            fontSize: '24px',
                            fontWeight: '700',
                            color: lightMode ? '#155724' : '#2ecc71'
                          }}>
                            {analysisResults.summary.movesWithSynergies}
                          </div>
                          <div style={{ 
                            fontSize: '12px',
                            color: lightMode ? '#155724' : '#27ae60',
                            opacity: 0.9
                          }}>
                            Moves with Synergies
                          </div>
                        </div>
                        <div style={{
                          padding: '12px',
                          background: lightMode ? '#c3e6cb' : 'rgba(46, 204, 113, 0.2)',
                          borderRadius: '6px'
                        }}>
                          <div style={{ 
                            fontSize: '24px',
                            fontWeight: '700',
                            color: lightMode ? '#155724' : '#2ecc71'
                          }}>
                            +{analysisResults.summary.avgSynergyBonus.toFixed(2)}
                          </div>
                          <div style={{ 
                            fontSize: '12px',
                            color: lightMode ? '#155724' : '#27ae60',
                            opacity: 0.9
                          }}>
                            Avg. Synergy Bonus
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {analysisResults.summary.overrepresentedCategories.length > 0 && (
                    <div className="category-distribution">
                      <h3>Category Distribution</h3>
                      <div className="category-bars">
                        {analysisResults.summary.overrepresentedCategories.map(([cat, count]) => (
                          <div key={cat} className="category-bar-row">
                            <span className="category-name">{cat}</span>
                            <div className="category-bar-container">
                              <div 
                                className="category-bar-fill"
                                style={{ 
                                  width: `${(count / analysisResults.summary.total) * 100}%`,
                                  backgroundColor: count >= 4 ? '#e67e22' : '#3498db'
                                }}
                              />
                              <span className="category-count">{count}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 3D Visualization Section (Full Analysis Mode Only) */}
                {analysisMode === 'full' && analysisResults.moves.length > 0 && (
                  <div className="visualization-section" style={{
                    marginTop: '20px',
                    background: lightMode ? '#fff' : '#1e1e1e',
                    borderRadius: '12px',
                    padding: '24px',
                    boxShadow: lightMode ? '0 2px 8px rgba(0,0,0,0.1)' : '0 2px 8px rgba(0,0,0,0.3)'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '20px'
                    }}>
                      <h2 style={{ margin: 0 }}>🔮 Full Analysis - 3D Score Space</h2>
                      <button
                        onClick={() => setShowVisualization(!showVisualization)}
                        style={{
                          padding: '8px 16px',
                          background: showVisualization ? '#e74c3c' : '#2ecc71',
                          color: '#fff',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontWeight: '600'
                        }}
                      >
                        {showVisualization ? '👁️ Hide' : '👁️ Show'}
                      </button>
                    </div>

                    {showVisualization && (
                      <div>
                        {/* 3D Scatter Plot */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px',
                          marginBottom: '20px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>
                            3D Coordinate System: Balance × Uniqueness × Simplicity
                          </h3>
                          <Plot
                            data={[
                              {
                                x: analysisResults.moves.map(m => m.fullBreakdown?.balance || 5),
                                y: analysisResults.moves.map(m => m.fullBreakdown?.uniqueness || 5),
                                z: analysisResults.moves.map(m => m.fullBreakdown?.simplicity || 5),
                                text: analysisResults.moves.map(m => 
                                  `${m.name}<br>Overall: ${m.fullScore?.toFixed(1) || 'N/A'}<br>` +
                                  `Balance: ${m.fullBreakdown?.balance?.toFixed(1) || 'N/A'}<br>` +
                                  `Uniqueness: ${m.fullBreakdown?.uniqueness?.toFixed(1) || 'N/A'}<br>` +
                                  `Simplicity: ${m.fullBreakdown?.simplicity?.toFixed(1) || 'N/A'}<br>` +
                                  `Level: ${m.level} | Element: ${m.element}`
                                ),
                                mode: 'markers',
                                type: 'scatter3d',
                                marker: {
                                  size: analysisResults.moves.map(m => 5 + (m.fullScore || 5) * 0.8),
                                  color: analysisResults.moves.map(m => m.fullScore || 5),
                                  colorscale: [
                                    [0, '#e74c3c'],      // Red for low scores
                                    [0.25, '#e67e22'],   // Orange
                                    [0.5, '#f39c12'],    // Yellow
                                    [0.75, '#2ecc71'],   // Green
                                    [1, '#4ec9b0']       // Teal for high scores
                                  ],
                                  colorbar: {
                                    title: 'Overall<br>Score',
                                    titleside: 'right',
                                    tickmode: 'linear',
                                    tick0: 0,
                                    dtick: 2,
                                    len: 0.7,
                                    thickness: 15,
                                    tickfont: { color: lightMode ? '#000' : '#fff' },
                                    titlefont: { color: lightMode ? '#000' : '#fff' }
                                  },
                                  line: {
                                    color: lightMode ? '#000' : '#fff',
                                    width: 0.5
                                  },
                                  opacity: 0.8
                                },
                                hovertemplate: '<b>%{text}</b><extra></extra>'
                              },
                              // Add ideal point indicator
                              {
                                x: [5],
                                y: [7],
                                z: [7],
                                text: ['Ideal Target<br>Balance: 5.0<br>Uniqueness: 7.0<br>Simplicity: 7.0'],
                                mode: 'markers',
                                type: 'scatter3d',
                                marker: {
                                  size: 15,
                                  color: '#667eea',
                                  symbol: 'diamond',
                                  line: {
                                    color: '#fff',
                                    width: 2
                                  }
                                },
                                name: 'Ideal Target',
                                hovertemplate: '<b>%{text}</b><extra></extra>'
                              }
                            ]}
                            layout={{
                              scene: {
                                xaxis: {
                                  title: {
                                    text: 'Balance (Power Level)',
                                    font: { size: 12, color: lightMode ? '#000' : '#fff' }
                                  },
                                  range: [0, 10],
                                  gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                  color: lightMode ? '#000' : '#fff',
                                  backgroundcolor: lightMode ? '#fff' : '#1e1e1e'
                                },
                                yaxis: {
                                  title: {
                                    text: 'Uniqueness (Creativity)',
                                    font: { size: 12, color: lightMode ? '#000' : '#fff' }
                                  },
                                  range: [0, 10],
                                  gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                  color: lightMode ? '#000' : '#fff',
                                  backgroundcolor: lightMode ? '#fff' : '#1e1e1e'
                                },
                                zaxis: {
                                  title: {
                                    text: 'Simplicity (Clarity)',
                                    font: { size: 12, color: lightMode ? '#000' : '#fff' }
                                  },
                                  range: [0, 10],
                                  gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                  color: lightMode ? '#000' : '#fff',
                                  backgroundcolor: lightMode ? '#fff' : '#1e1e1e'
                                },
                                camera: {
                                  eye: { x: 1.5, y: 1.5, z: 1.3 },
                                  center: { x: 0, y: 0, z: 0 }
                                },
                                bgcolor: lightMode ? '#fff' : '#1e1e1e'
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff', size: 11 },
                              hovermode: 'closest',
                              margin: { t: 20, b: 20, l: 20, r: 20 },
                              height: 600,
                              showlegend: true,
                              legend: {
                                x: 0.02,
                                y: 0.98,
                                bgcolor: lightMode ? 'rgba(255,255,255,0.9)' : 'rgba(30,30,30,0.9)',
                                bordercolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                borderwidth: 1
                              }
                            }}
                            config={{ 
                              displayModeBar: true, 
                              responsive: true,
                              displaylogo: false,
                              modeBarButtonsToRemove: ['select2d', 'lasso2d']
                            }}
                            style={{ width: '100%' }}
                          />
                          <div style={{
                            marginTop: '16px',
                            padding: '12px',
                            background: lightMode ? '#e3f2fd' : 'rgba(66, 133, 244, 0.1)',
                            borderRadius: '6px',
                            fontSize: '13px',
                            lineHeight: '1.6'
                          }}>
                            <strong>💡 How to interpret:</strong>
                            <ul style={{ marginTop: '8px', marginBottom: 0, paddingLeft: '20px' }}>
                              <li><strong>X-axis (Balance):</strong> Power level - target is 5.0 (balanced)</li>
                              <li><strong>Y-axis (Uniqueness):</strong> Creativity - higher is better (target: 7.0)</li>
                              <li><strong>Z-axis (Simplicity):</strong> Clarity - higher is better (target: 7.0)</li>
                              <li><strong>Color:</strong> Overall ML-generated score (warmer = better)</li>
                              <li><strong>Size:</strong> Larger markers indicate higher overall scores</li>
                              <li><strong>💎 Diamond:</strong> Ideal target point (5.0, 7.0, 7.0)</li>
                            </ul>
                          </div>
                        </div>

                        {/* Component Breakdown Charts */}
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                          gap: '16px',
                          marginBottom: '20px'
                        }}>
                          {/* Balance Component Distribution */}
                          <div style={{
                            background: lightMode ? '#f8f9fa' : '#2a2a2a',
                            borderRadius: '8px',
                            padding: '16px'
                          }}>
                            <h4 style={{ marginTop: 0, marginBottom: '12px' }}>⚖️ Balance Component</h4>
                            <Plot
                              data={[
                                {
                                  x: analysisResults.moves.map(m => m.fullBreakdown?.balance || 5),
                                  type: 'histogram',
                                  nbinsx: 20,
                                  marker: {
                                    color: '#3498db',
                                    line: { color: lightMode ? '#fff' : '#000', width: 1 }
                                  },
                                  name: 'Balance'
                                }
                              ]}
                              layout={{
                                xaxis: { title: 'Balance Score', range: [0, 10], color: lightMode ? '#000' : '#fff' },
                                yaxis: { title: 'Count', color: lightMode ? '#000' : '#fff' },
                                plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                                paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                                font: { color: lightMode ? '#000' : '#fff', size: 10 },
                                margin: { t: 10, b: 40, l: 40, r: 10 },
                                height: 200,
                                showlegend: false,
                                shapes: [{
                                  type: 'line',
                                  x0: 5, x1: 5, y0: 0, yref: 'paper', y1: 1,
                                  line: { color: '#667eea', width: 2, dash: 'dot' }
                                }]
                              }}
                              config={{ displayModeBar: false, responsive: true }}
                              style={{ width: '100%' }}
                            />
                          </div>

                          {/* Uniqueness Component Distribution */}
                          <div style={{
                            background: lightMode ? '#f8f9fa' : '#2a2a2a',
                            borderRadius: '8px',
                            padding: '16px'
                          }}>
                            <h4 style={{ marginTop: 0, marginBottom: '12px' }}>🎯 Uniqueness Component</h4>
                            <Plot
                              data={[
                                {
                                  x: analysisResults.moves.map(m => m.fullBreakdown?.uniqueness || 5),
                                  type: 'histogram',
                                  nbinsx: 20,
                                  marker: {
                                    color: '#9b59b6',
                                    line: { color: lightMode ? '#fff' : '#000', width: 1 }
                                  },
                                  name: 'Uniqueness'
                                }
                              ]}
                              layout={{
                                xaxis: { title: 'Uniqueness Score', range: [0, 10], color: lightMode ? '#000' : '#fff' },
                                yaxis: { title: 'Count', color: lightMode ? '#000' : '#fff' },
                                plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                                paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                                font: { color: lightMode ? '#000' : '#fff', size: 10 },
                                margin: { t: 10, b: 40, l: 40, r: 10 },
                                height: 200,
                                showlegend: false,
                                shapes: [{
                                  type: 'line',
                                  x0: 7, x1: 7, y0: 0, yref: 'paper', y1: 1,
                                  line: { color: '#667eea', width: 2, dash: 'dot' }
                                }]
                              }}
                              config={{ displayModeBar: false, responsive: true }}
                              style={{ width: '100%' }}
                            />
                          </div>

                          {/* Simplicity Component Distribution */}
                          <div style={{
                            background: lightMode ? '#f8f9fa' : '#2a2a2a',
                            borderRadius: '8px',
                            padding: '16px'
                          }}>
                            <h4 style={{ marginTop: 0, marginBottom: '12px' }}>📝 Simplicity Component</h4>
                            <Plot
                              data={[
                                {
                                  x: analysisResults.moves.map(m => m.fullBreakdown?.simplicity || 5),
                                  type: 'histogram',
                                  nbinsx: 20,
                                  marker: {
                                    color: '#2ecc71',
                                    line: { color: lightMode ? '#fff' : '#000', width: 1 }
                                  },
                                  name: 'Simplicity'
                                }
                              ]}
                              layout={{
                                xaxis: { title: 'Simplicity Score', range: [0, 10], color: lightMode ? '#000' : '#fff' },
                                yaxis: { title: 'Count', color: lightMode ? '#000' : '#fff' },
                                plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                                paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                                font: { color: lightMode ? '#000' : '#fff', size: 10 },
                                margin: { t: 10, b: 40, l: 40, r: 10 },
                                height: 200,
                                showlegend: false,
                                shapes: [{
                                  type: 'line',
                                  x0: 7, x1: 7, y0: 0, yref: 'paper', y1: 1,
                                  line: { color: '#667eea', width: 2, dash: 'dot' }
                                }]
                              }}
                              config={{ displayModeBar: false, responsive: true }}
                              style={{ width: '100%' }}
                            />
                          </div>
                        </div>

                        {/* Overall Score Distribution */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>🔮 Overall Score Distribution</h3>
                          <Plot
                            data={[
                              {
                                x: analysisResults.moves.map(m => m.fullScore || 5),
                                type: 'histogram',
                                nbinsx: 20,
                                marker: {
                                  color: analysisResults.moves.map(m => m.fullScore || 5),
                                  colorscale: [
                                    [0, '#e74c3c'],
                                    [0.5, '#f39c12'],
                                    [1, '#4ec9b0']
                                  ],
                                  line: { color: lightMode ? '#fff' : '#000', width: 1 }
                                },
                                name: 'Overall Score'
                              }
                            ]}
                            layout={{
                              xaxis: { 
                                title: 'Overall Score', 
                                range: [0, 10],
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              yaxis: { 
                                title: 'Number of Moves',
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff' },
                              showlegend: false,
                              margin: { t: 20, b: 50, l: 60, r: 20 },
                              height: 300,
                              shapes: [
                                {
                                  type: 'line',
                                  x0: analysisResults.summary.avgBalance || 5,
                                  x1: analysisResults.summary.avgBalance || 5,
                                  y0: 0,
                                  yref: 'paper',
                                  y1: 1,
                                  line: { color: '#4ec9b0', width: 3, dash: 'dash' }
                                }
                              ],
                              annotations: [
                                {
                                  x: analysisResults.summary.avgBalance || 5,
                                  y: 1,
                                  yref: 'paper',
                                  text: `Mean: ${(analysisResults.summary.avgBalance || 5)}`,
                                  showarrow: false,
                                  yshift: 10,
                                  font: { color: '#4ec9b0', size: 12, weight: 'bold' }
                                }
                              ]
                            }}
                            config={{ displayModeBar: true, responsive: true }}
                            style={{ width: '100%' }}
                          />
                        </div>

                        {/* Data Table */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px',
                          marginTop: '20px',
                          overflowX: 'auto'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>📊 Detailed Move Data</h3>
                          <table style={{
                            width: '100%',
                            borderCollapse: 'collapse',
                            fontSize: '13px'
                          }}>
                            <thead>
                              <tr style={{
                                background: lightMode ? '#e9ecef' : '#1e1e1e',
                                borderBottom: `2px solid ${lightMode ? '#dee2e6' : '#3e3e42'}`
                              }}>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'name') {
                                      setabbleSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('name');
                                      setTableSortDirection('asc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'left', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Move Name {tableSortBy === 'name' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'element') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('element');
                                      setTableSortDirection('asc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Element {tableSortBy === 'element' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'level') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('level');
                                      setTableSortDirection('desc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Level {tableSortBy === 'level' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'balance') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('balance');
                                      setTableSortDirection('desc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Balance {tableSortBy === 'balance' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'uniqueness') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('uniqueness');
                                      setTableSortDirection('desc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Uniqueness {tableSortBy === 'uniqueness' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'simplicity') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('simplicity');
                                      setTableSortDirection('desc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Simplicity {tableSortBy === 'simplicity' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'overall') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('overall');
                                      setTableSortDirection('desc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Overall {tableSortBy === 'overall' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                                <th 
                                  onClick={() => {
                                    if (tableSortBy === 'rating') {
                                      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
                                    } else {
                                      setTableSortBy('rating');
                                      setTableSortDirection('desc');
                                    }
                                  }}
                                  style={{ 
                                    padding: '12px 8px', 
                                    textAlign: 'center', 
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    userSelect: 'none',
                                    transition: 'background 0.2s'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.background = lightMode ? '#dee2e6' : '#2a2a2a'}
                                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                                >
                                  Rating {tableSortBy === 'rating' ? (tableSortDirection === 'asc' ? '↑' : '↓') : ''}
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {analysisResults.moves
                                .sort((a, b) => {
                                  let comparison = 0;
                                  switch (tableSortBy) {
                                    case 'name':
                                      comparison = (a.name || '').localeCompare(b.name || '');
                                      break;
                                    case 'element':
                                      comparison = (a.element || '').localeCompare(b.element || '');
                                      break;
                                    case 'level':
                                      comparison = (a.level || 0) - (b.level || 0);
                                      break;
                                    case 'balance':
                                      comparison = (a.fullBreakdown?.balance || 0) - (b.fullBreakdown?.balance || 0);
                                      break;
                                    case 'uniqueness':
                                      comparison = (a.fullBreakdown?.uniqueness || 0) - (b.fullBreakdown?.uniqueness || 0);
                                      break;
                                    case 'simplicity':
                                      comparison = (a.fullBreakdown?.simplicity || 0) - (b.fullBreakdown?.simplicity || 0);
                                      break;
                                    case 'overall':
                                      comparison = (a.fullScore || 0) - (b.fullScore || 0);
                                      break;
                                    case 'rating':
                                      comparison = (a.fullScore || 0) - (b.fullScore || 0);
                                      break;
                                    default:
                                      comparison = (b.fullScore || 0) - (a.fullScore || 0);
                                  }
                                  return tableSortDirection === 'asc' ? comparison : -comparison;
                                })
                                .map((move, idx) => {
                                  const overallScore = move.fullScore || 0;
                                  const rating = overallScore >= 8 ? 'Excellent' : 
                                               overallScore >= 6 ? 'Good' : 'Needs Work';
                                  const ratingColor = overallScore >= 8 ? '#4ec9b0' : 
                                                    overallScore >= 6 ? '#f39c12' : '#e74c3c';
                                  const isExpanded = expandedTableMove === move.name;
                                  
                                  return (
                                    <React.Fragment key={idx}>
                                      <tr 
                                        onClick={() => setExpandedTableMove(isExpanded ? null : move.name)}
                                        style={{
                                          borderBottom: `1px solid ${lightMode ? '#dee2e6' : '#3e3e42'}`,
                                          background: idx % 2 === 0 ? 
                                            (lightMode ? '#ffffff' : '#252526') : 
                                            (lightMode ? '#f8f9fa' : '#2a2a2a'),
                                          transition: 'background 0.2s',
                                          cursor: 'pointer'
                                        }}
                                        onMouseEnter={(e) => {
                                          e.currentTarget.style.background = lightMode ? '#e9ecef' : '#1e1e1e';
                                        }}
                                        onMouseLeave={(e) => {
                                          e.currentTarget.style.background = idx % 2 === 0 ? 
                                            (lightMode ? '#ffffff' : '#252526') : 
                                            (lightMode ? '#f8f9fa' : '#2a2a2a');
                                        }}>
                                        <td style={{ padding: '10px 8px', fontWeight: 500 }}>
                                          {isExpanded ? '▼ ' : '▶ '}{move.name}
                                        </td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center' }}>
                                          <span style={{
                                            background: move.element === 'fire' ? '#e74c3c20' :
                                                      move.element === 'water' ? '#3498db20' :
                                                      move.element === 'earth' ? '#2ecc7120' :
                                                      move.element === 'air' ? '#95a5a620' : '#95a5a620',
                                            color: move.element === 'fire' ? '#e74c3c' :
                                                 move.element === 'water' ? '#3498db' :
                                                 move.element === 'earth' ? '#2ecc71' :
                                                 move.element === 'air' ? '#95a5a6' : '#95a5a6',
                                            padding: '4px 8px',
                                            borderRadius: '4px',
                                            fontSize: '12px',
                                            fontWeight: 600,
                                            textTransform: 'capitalize'
                                          }}>
                                            {move.element}
                                          </span>
                                        </td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center' }}>{move.level}</td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center', fontWeight: 600 }}>
                                          <span style={{
                                            color: (move.fullBreakdown?.balance || 0) >= 7 ? '#4ec9b0' :
                                                  (move.fullBreakdown?.balance || 0) >= 4 ? '#f39c12' : '#e74c3c'
                                          }}>
                                            {(move.fullBreakdown?.balance || 0).toFixed(1)}
                                          </span>
                                        </td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center', fontWeight: 600 }}>
                                          <span style={{
                                            color: (move.fullBreakdown?.uniqueness || 0) >= 7 ? '#4ec9b0' :
                                                  (move.fullBreakdown?.uniqueness || 0) >= 5 ? '#f39c12' : '#e74c3c'
                                          }}>
                                            {(move.fullBreakdown?.uniqueness || 0).toFixed(1)}
                                          </span>
                                        </td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center', fontWeight: 600 }}>
                                          <span style={{
                                            color: (move.fullBreakdown?.simplicity || 0) >= 7 ? '#4ec9b0' :
                                                  (move.fullBreakdown?.simplicity || 0) >= 5 ? '#f39c12' : '#e74c3c'
                                          }}>
                                            {(move.fullBreakdown?.simplicity || 0).toFixed(1)}
                                          </span>
                                        </td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center', fontWeight: 700, fontSize: '14px' }}>
                                          <span style={{ color: ratingColor }}>
                                            {overallScore.toFixed(1)}
                                          </span>
                                        </td>
                                        <td style={{ padding: '10px 8px', textAlign: 'center' }}>
                                          <span style={{
                                            background: ratingColor + '20',
                                            color: ratingColor,
                                            padding: '4px 8px',
                                            borderRadius: '4px',
                                            fontSize: '11px',
                                            fontWeight: 600,
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px'
                                          }}>
                                            {rating}
                                          </span>
                                        </td>
                                      </tr>
                                      
                                      {/* Detailed Analysis Row */}
                                      {isExpanded && (
                                        <tr>
                                          <td colSpan="8" style={{
                                            padding: '20px',
                                            background: lightMode ? '#f8f9fa' : '#1e1e1e',
                                            borderBottom: `2px solid ${lightMode ? '#dee2e6' : '#3e3e42'}`
                                          }}>
                                            <div style={{
                                              display: 'grid',
                                              gridTemplateColumns: '1fr 1fr',
                                              gap: '20px'
                                            }}>
                                              {/* Left Column - Basic Info & Scores */}
                                              <div>
                                                <h4 style={{ marginTop: 0, marginBottom: '16px', color: ratingColor }}>
                                                  📋 Move Details
                                                </h4>
                                                
                                                <div style={{ marginBottom: '16px' }}>
                                                  <div style={{ fontSize: '12px', color: lightMode ? '#6c757d' : '#8e8e93', marginBottom: '4px' }}>
                                                    <strong>Action Type:</strong> {move.actionType || 'Unknown'}
                                                  </div>
                                                  <div style={{ fontSize: '12px', color: lightMode ? '#6c757d' : '#8e8e93', marginBottom: '4px' }}>
                                                    <strong>Range:</strong> {move.range || 'Not specified'}
                                                  </div>
                                                  <div style={{ fontSize: '12px', color: lightMode ? '#6c757d' : '#8e8e93', marginBottom: '4px' }}>
                                                    <strong>Duration:</strong> {move.duration || 'Not specified'}
                                                  </div>
                                                  <div style={{ fontSize: '12px', color: lightMode ? '#6c757d' : '#8e8e93', marginBottom: '4px' }}>
                                                    <strong>Damage:</strong> {move.damage || 'None'}
                                                  </div>
                                                  {move.cost && (
                                                    <div style={{ fontSize: '12px', color: lightMode ? '#6c757d' : '#8e8e93', marginBottom: '4px' }}>
                                                      <strong>Cost:</strong> {move.cost}
                                                    </div>
                                                  )}
                                                </div>

                                                <h5 style={{ marginTop: '16px', marginBottom: '8px' }}>📊 Score Breakdown</h5>
                                                <div style={{
                                                  background: lightMode ? '#fff' : '#252526',
                                                  padding: '12px',
                                                  borderRadius: '6px',
                                                  fontSize: '13px'
                                                }}>
                                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                                    <span>⚖️ Balance (Power Level):</span>
                                                    <strong style={{ color: (move.fullBreakdown?.balance || 0) >= 7 ? '#4ec9b0' : (move.fullBreakdown?.balance || 0) >= 4 ? '#f39c12' : '#e74c3c' }}>
                                                      {(move.fullBreakdown?.balance || 0).toFixed(1)}/10
                                                    </strong>
                                                  </div>
                                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                                    <span>🎯 Uniqueness (Creativity):</span>
                                                    <strong style={{ color: (move.fullBreakdown?.uniqueness || 0) >= 7 ? '#4ec9b0' : (move.fullBreakdown?.uniqueness || 0) >= 5 ? '#f39c12' : '#e74c3c' }}>
                                                      {(move.fullBreakdown?.uniqueness || 0).toFixed(1)}/10
                                                    </strong>
                                                  </div>
                                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                                    <span>📝 Simplicity (Clarity):</span>
                                                    <strong style={{ color: (move.fullBreakdown?.simplicity || 0) >= 7 ? '#4ec9b0' : (move.fullBreakdown?.simplicity || 0) >= 5 ? '#f39c12' : '#e74c3c' }}>
                                                      {(move.fullBreakdown?.simplicity || 0).toFixed(1)}/10
                                                    </strong>
                                                  </div>
                                                  <div style={{ 
                                                    display: 'flex', 
                                                    justifyContent: 'space-between', 
                                                    marginTop: '12px', 
                                                    paddingTop: '12px',
                                                    borderTop: `1px solid ${lightMode ? '#dee2e6' : '#3e3e42'}`
                                                  }}>
                                                    <span style={{ fontWeight: 600 }}>🔮 Overall Score:</span>
                                                    <strong style={{ color: ratingColor, fontSize: '16px' }}>
                                                      {overallScore.toFixed(1)}/10
                                                    </strong>
                                                  </div>
                                                </div>
                                              </div>

                                              {/* Right Column - Description & Feedback */}
                                              <div>
                                                <h4 style={{ marginTop: 0, marginBottom: '12px' }}>📖 Description</h4>
                                                <div style={{
                                                  background: lightMode ? '#fff' : '#252526',
                                                  padding: '12px',
                                                  borderRadius: '6px',
                                                  fontSize: '13px',
                                                  lineHeight: '1.6',
                                                  marginBottom: '16px',
                                                  maxHeight: '150px',
                                                  overflowY: 'auto'
                                                }}>
                                                  {move.effects || move.description || 'No description available'}
                                                </div>

                                                {/* AI Feedback */}
                                                {move.mlFullFeedback && (
                                                  <>
                                                    <h5 style={{ marginTop: '16px', marginBottom: '8px' }}>🤖 AI Analysis</h5>
                                                    
                                                    {move.mlFullFeedback.strengths && move.mlFullFeedback.strengths.length > 0 && (
                                                      <div style={{ marginBottom: '12px' }}>
                                                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#4ec9b0', marginBottom: '4px' }}>
                                                          ✅ Strengths:
                                                        </div>
                                                        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px' }}>
                                                          {move.mlFullFeedback.strengths.map((s, i) => (
                                                            <li key={i} style={{ marginBottom: '2px' }}>{s}</li>
                                                          ))}
                                                        </ul>
                                                      </div>
                                                    )}
                                                    
                                                    {move.mlFullFeedback.warnings && move.mlFullFeedback.warnings.length > 0 && (
                                                      <div style={{ marginBottom: '12px' }}>
                                                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#f39c12', marginBottom: '4px' }}>
                                                          ⚠️ Areas for Improvement:
                                                        </div>
                                                        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px' }}>
                                                          {move.mlFullFeedback.warnings.map((w, i) => (
                                                            <li key={i} style={{ marginBottom: '2px' }}>{w}</li>
                                                          ))}
                                                        </ul>
                                                      </div>
                                                    )}
                                                    
                                                    {move.mlFullFeedback.recommendations && move.mlFullFeedback.recommendations.length > 0 && (
                                                      <div>
                                                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#667eea', marginBottom: '4px' }}>
                                                          💡 Recommendations:
                                                        </div>
                                                        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px' }}>
                                                          {move.mlFullFeedback.recommendations.map((r, i) => (
                                                            <li key={i} style={{ marginBottom: '2px' }}>{r}</li>
                                                          ))}
                                                        </ul>
                                                      </div>
                                                    )}
                                                  </>
                                                )}

                                                {/* File Path */}
                                                {move.filePath && (
                                                  <div style={{
                                                    marginTop: '16px',
                                                    padding: '8px',
                                                    background: lightMode ? '#e9ecef' : '#2a2a2a',
                                                    borderRadius: '4px',
                                                    fontSize: '11px',
                                                    color: lightMode ? '#6c757d' : '#8e8e93',
                                                    fontFamily: 'monospace'
                                                  }}>
                                                    📁 {move.filePath}
                                                  </div>
                                                )}
                                              </div>
                                            </div>
                                          </td>
                                        </tr>
                                      )}
                                    </React.Fragment>
                                  );
                                })}
                            </tbody>
                          </table>
                          <div style={{
                            marginTop: '12px',
                            fontSize: '12px',
                            color: lightMode ? '#6c757d' : '#8e8e93',
                            textAlign: 'right'
                          }}>
                            Total: {analysisResults.moves.length} moves
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Visualization Section (Balance Mode Only) */}
                {analysisMode === 'balance' && visualizationData && (
                  <div className="visualization-section" style={{
                    marginTop: '20px',
                    padding: '20px',
                    background: lightMode ? '#fff' : '#1e1e1e',
                    borderRadius: '8px',
                    border: `1px solid ${lightMode ? '#e0e0e0' : '#3e3e42'}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h2 style={{ margin: 0 }}>📈 Balance Distribution Visualizations</h2>
                      <button 
                        onClick={() => setShowVisualization(!showVisualization)}
                        style={{
                          padding: '8px 16px',
                          background: '#667eea',
                          color: '#fff',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontWeight: '600'
                        }}
                      >
                        {showVisualization ? '📊 Hide Charts' : '📊 Show Charts'}
                      </button>
                    </div>

                    {showVisualization && (
                      <div style={{ display: 'grid', gap: '24px' }}>
                        {/* Histogram */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Score Distribution</h3>
                          <Plot
                            data={[
                              {
                                x: visualizationData.histogram.bin_centers,
                                y: visualizationData.histogram.counts,
                                type: 'bar',
                                marker: {
                                  color: visualizationData.histogram.bin_centers.map(score => {
                                    if (score <= 3.5) return '#e74c3c';
                                    if (score <= 4.5) return '#e67e22';
                                    if (score <= 5.5) return '#f39c12';
                                    if (score <= 7.0) return '#2ecc71';
                                    if (score <= 8.0) return '#3498db';
                                    if (score <= 9.0) return '#9b59b6';
                                    return '#c0392b';
                                  }),
                                  line: { color: lightMode ? '#000' : '#fff', width: 1 }
                                },
                                name: 'Frequency'
                              }
                            ]}
                            layout={{
                              title: '',
                              xaxis: { 
                                title: 'Balance Score',
                                range: [0, 10],
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              yaxis: { 
                                title: 'Number of Moves',
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff' },
                              shapes: [
                                {
                                  type: 'line',
                                  x0: visualizationData.statistics.mean,
                                  x1: visualizationData.statistics.mean,
                                  y0: 0,
                                  yref: 'paper',
                                  y1: 1,
                                  line: {
                                    color: '#4ec9b0',
                                    width: 3,
                                    dash: 'dash'
                                  }
                                },
                                {
                                  type: 'line',
                                  x0: 5.0,
                                  x1: 5.0,
                                  y0: 0,
                                  yref: 'paper',
                                  y1: 1,
                                  line: {
                                    color: '#667eea',
                                    width: 2,
                                    dash: 'dot'
                                  }
                                }
                              ],
                              annotations: [
                                {
                                  x: visualizationData.statistics.mean,
                                  y: 1,
                                  yref: 'paper',
                                  text: `Mean: ${visualizationData.statistics.mean.toFixed(2)}`,
                                  showarrow: false,
                                  yshift: 10,
                                  font: { color: '#4ec9b0', size: 12, weight: 'bold' }
                                },
                                {
                                  x: 5.0,
                                  y: 0.9,
                                  yref: 'paper',
                                  text: 'Target: 5.0',
                                  showarrow: false,
                                  yshift: 10,
                                  font: { color: '#667eea', size: 11 }
                                }
                              ],
                              margin: { t: 20, b: 50, l: 60, r: 20 },
                              height: 350
                            }}
                            config={{ displayModeBar: true, responsive: true }}
                            style={{ width: '100%' }}
                          />
                        </div>

                        {/* Pie Chart - Category Distribution */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Category Distribution</h3>
                          <Plot
                            data={[
                              {
                                values: Object.values(visualizationData.categories),
                                labels: Object.keys(visualizationData.categories),
                                type: 'pie',
                                marker: {
                                  colors: ['#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#3498db', '#9b59b6', '#c0392b']
                                },
                                textinfo: 'label+percent',
                                textposition: 'outside',
                                automargin: true
                              }
                            ]}
                            layout={{
                              showlegend: true,
                              legend: {
                                orientation: 'h',
                                y: -0.2,
                                font: { color: lightMode ? '#000' : '#fff' }
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff' },
                              margin: { t: 20, b: 80, l: 20, r: 20 },
                              height: 400
                            }}
                            config={{ displayModeBar: true, responsive: true }}
                            style={{ width: '100%' }}
                          />
                        </div>

                        {/* Box Plot by Element */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Balance by Element</h3>
                          <Plot
                            data={Object.entries(visualizationData.boxplot_by_element).map(([element, data]) => ({
                              y: data.scores,
                              type: 'box',
                              name: element.charAt(0).toUpperCase() + element.slice(1),
                              marker: { color: ELEMENT_COLORS[element] || '#3498db' },
                              boxmean: 'sd'
                            }))}
                            layout={{
                              yaxis: { 
                                title: 'Balance Score',
                                range: [0, 10],
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              xaxis: {
                                color: lightMode ? '#000' : '#fff'
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff' },
                              showlegend: false,
                              margin: { t: 20, b: 50, l: 60, r: 20 },
                              height: 350
                            }}
                            config={{ displayModeBar: true, responsive: true }}
                            style={{ width: '100%' }}
                          />
                        </div>

                        {/* Box Plot by Level */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Balance by Level</h3>
                          <Plot
                            data={Object.entries(visualizationData.boxplot_by_level).sort((a, b) => a[0] - b[0]).map(([level, data]) => ({
                              y: data.scores,
                              type: 'box',
                              name: `Level ${level}`,
                              marker: { color: '#667eea' },
                              boxmean: 'sd'
                            }))}
                            layout={{
                              yaxis: { 
                                title: 'Balance Score',
                                range: [0, 10],
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              xaxis: {
                                color: lightMode ? '#000' : '#fff'
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff' },
                              showlegend: false,
                              margin: { t: 20, b: 50, l: 60, r: 20 },
                              height: 350
                            }}
                            config={{ displayModeBar: true, responsive: true }}
                            style={{ width: '100%' }}
                          />
                        </div>

                        {/* Scatter Plot - Score vs Level */}
                        <div style={{
                          background: lightMode ? '#f8f9fa' : '#2a2a2a',
                          borderRadius: '8px',
                          padding: '16px'
                        }}>
                          <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Score vs Level (by Element)</h3>
                          <Plot
                            data={Object.keys(ELEMENT_COLORS).map(element => {
                              const indices = visualizationData.scatterplot.elements
                                .map((el, i) => el === element ? i : -1)
                                .filter(i => i !== -1);
                              
                              return {
                                x: indices.map(i => visualizationData.scatterplot.levels[i]),
                                y: indices.map(i => visualizationData.scatterplot.scores[i]),
                                text: indices.map(i => visualizationData.scatterplot.names[i]),
                                type: 'scatter',
                                mode: 'markers',
                                name: element.charAt(0).toUpperCase() + element.slice(1),
                                marker: {
                                  size: 10,
                                  color: ELEMENT_COLORS[element],
                                  line: { color: lightMode ? '#000' : '#fff', width: 1 }
                                }
                              };
                            })}
                            layout={{
                              xaxis: { 
                                title: 'Level',
                                dtick: 1,
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              yaxis: { 
                                title: 'Balance Score',
                                range: [0, 10],
                                gridcolor: lightMode ? '#e0e0e0' : '#3e3e42',
                                color: lightMode ? '#000' : '#fff'
                              },
                              plot_bgcolor: lightMode ? '#fff' : '#1e1e1e',
                              paper_bgcolor: lightMode ? '#f8f9fa' : '#2a2a2a',
                              font: { color: lightMode ? '#000' : '#fff' },
                              hovermode: 'closest',
                              margin: { t: 20, b: 50, l: 60, r: 20 },
                              height: 400,
                              legend: {
                                orientation: 'h',
                                y: -0.2
                              }
                            }}
                            config={{ displayModeBar: true, responsive: true }}
                            style={{ width: '100%' }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {analysisResults.summary.recommendations.length > 0 && (
                  <div className="recommendations-section">
                    <h2>💡 Recommendations</h2>
                    {analysisResults.summary.recommendations.map((rec, idx) => (
                      <div 
                        key={idx} 
                        className="recommendation-card"
                        style={{ borderLeftColor: getPriorityColor(rec.priority) }}
                      >
                        <div className="rec-header">
                          <span className="rec-icon">{getRecommendationIcon(rec.type)}</span>
                          <span className="rec-type">{rec.type.toUpperCase()}</span>
                          <span 
                            className="rec-priority"
                            style={{ backgroundColor: getPriorityColor(rec.priority) }}
                          >
                            {rec.priority}
                          </span>
                        </div>
                        <div className="rec-body">
                          <p>{rec.reason}</p>
                          {rec.moves && (
                            <div className="rec-moves">
                              <strong>Affected moves:</strong> {rec.moves.join(', ')}
                            </div>
                          )}
                          {rec.categories && (
                            <div className="rec-categories">
                              <strong>Categories:</strong> {rec.categories.join(', ')}
                            </div>
                          )}
                          {rec.levels && (
                            <div className="rec-levels">
                              <strong>Levels:</strong> {rec.levels.join(', ')}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="moves-section">
                  <h2>📋 Move Details</h2>
                  {Object.keys(getGroupedMoves()).length === 0 ? (
                    <div className="empty-state">
                      <p>No moves match the current filter criteria</p>
                    </div>
                  ) : (
                    Object.entries(getGroupedMoves()).map(([levelLabel, moves]) => (
                      <div key={levelLabel} style={{ marginBottom: '30px' }}>
                        <h3 style={{
                          fontSize: '18px',
                          fontWeight: '700',
                          color: lightMode ? '#667eea' : '#4ec9b0',
                          marginBottom: '16px',
                          paddingBottom: '8px',
                          borderBottom: `2px solid ${lightMode ? '#667eea' : '#4ec9b0'}`
                        }}>
                          {levelLabel} ({moves.length} {moves.length === 1 ? 'move' : 'moves'})
                        </h3>
                        <div>
                          {moves.map(move => renderMoveCard(move))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}

            {!analysisResults && !loading && (
              <div className="empty-state">
                <p>🎯 Select an element and levels, then click "Run Analysis" to begin</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'content' && (
          <ContentOverview lightMode={lightMode} />
        )}

        {activeTab === 'sessions' && (
          <div className="sessions-panel">
            <h2>👥 Active Sessions</h2>
            <p className="coming-soon">Coming soon: View active player sessions and server logs</p>
            <a href="http://localhost:9002/api/log_viewer" target="_blank" rel="noopener noreferrer">
              Open Log Viewer →
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default GameMasterMode;
