import React, { useState, useEffect } from 'react';
import './StatOverview.css';
import { getLighterColor, hexToRgba } from '../utils/colorUtils';
import { API_BASE_URL } from '../config/api';

const StatOverview = ({ onFileSelect }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const [fileColors, setFileColors] = useState({});

  const fetchStatOverview = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/stat_overview`);
      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadFileColors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/file-colors`);
      if (response.ok) {
        const data = await response.json();
        setFileColors(data.colors || {});
      }
    } catch (error) {
      console.error('Error loading file colors:', error);
    }
  };

  const regenerateStats = async () => {
    try {
      setRegenerating(true);
      const response = await fetch(`${API_BASE_URL}/api/stat_overview/regenerate`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Failed to regenerate: ${response.statusText}`);
      }
      // Fetch fresh data after regeneration
      await fetchStatOverview();
    } catch (err) {
      setError(err.message);
    } finally {
      setRegenerating(false);
    }
  };

  const updateEnvironmentalVariable = async (name, current, max) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/environmental_variable`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          current,
          max,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update environmental variable: ${response.statusText}`);
      }
      
      // Update local state immediately for responsive UI
      setData(prevData => {
        if (!prevData) return prevData;
        
        const updatedEnvironmental = prevData.environmental.map(env => {
          if (env.name === name) {
            return { ...env, value: `${current}/${max}` };
          }
          return env;
        });
        
        return {
          ...prevData,
          environmental: updatedEnvironmental,
        };
      });
    } catch (err) {
      console.error('Error updating environmental variable:', err);
      setError(err.message);
    }
  };

  const refreshEnvironmentalVariable = async (name) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/environmental_variable/${name}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch environmental variable: ${response.statusText}`);
      }
      
      const envData = await response.json();
      
      // Update local state with fresh data
      setData(prevData => {
        if (!prevData) return prevData;
        
        const updatedEnvironmental = prevData.environmental.map(env => {
          if (env.name === name) {
            return { ...env, value: `${envData.current}/${envData.max}` };
          }
          return env;
        });
        
        return {
          ...prevData,
          environmental: updatedEnvironmental,
        };
      });
    } catch (err) {
      console.error('Error refreshing environmental variable:', err);
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchStatOverview();
    loadFileColors();
  }, []);

  if (loading) {
    return (
      <div className="stat-overview-container">
        <div className="stat-overview-loading">Loading stat overview...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stat-overview-container">
        <div className="stat-overview-error">Error: {error}</div>
        <button onClick={fetchStatOverview} className="stat-overview-retry">
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { environmental, pcs, last_generated } = data;

  return (
    <div className="stat-overview-container">
      <div className="stat-overview-header">
        <h1>Stat Overview</h1>
        <button
          onClick={regenerateStats}
          disabled={regenerating}
          className="stat-overview-regenerate"
        >
          {regenerating ? '🔄 Regenerating...' : '🔄 Regenerate'}
        </button>
      </div>

      {/* Global Environmental Variables */}
      <section className="stat-overview-section">
        <h2>Global Environmental Variables</h2>
        {environmental && environmental.length > 0 ? (
          <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
            {environmental.map((env, idx) => {
              // Parse current/max if in format "9" or "9/10"
              let current = 0;
              let max = 0;
              
              if (env.value) {
                const slashMatch = String(env.value).match(/^(\d+)\s*\/\s*(\d+)$/);
                if (slashMatch) {
                  current = parseInt(slashMatch[1]) || 0;
                  max = parseInt(slashMatch[2]) || 0;
                } else {
                  const numValue = parseInt(env.value);
                  if (!isNaN(numValue)) {
                    current = numValue;
                    max = numValue;
                  }
                }
              }
              
              const elementColor = '#91bbff'; // Water blue color
              
              return (
                <div key={idx} style={{
                  backgroundColor: 'var(--bg-secondary, #252526)',
                  border: `2px solid ${elementColor}`,
                  borderRadius: '10px',
                  padding: '15px',
                  transition: 'all 0.2s ease'
                }}>
                  <h3 style={{
                    margin: '0 0 12px 0',
                    fontSize: '1.2rem',
                    color: elementColor,
                    fontWeight: '600',
                    borderBottom: `2px solid ${elementColor}`,
                    paddingBottom: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <span>{env.name}</span>
                    <button
                      onClick={() => refreshEnvironmentalVariable(env.name)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '14px',
                        backgroundColor: elementColor,
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontWeight: '600',
                        transition: 'opacity 0.2s',
                        flexShrink: 0
                      }}
                      onMouseEnter={(e) => e.target.style.opacity = '0.8'}
                      onMouseLeave={(e) => e.target.style.opacity = '1'}
                      title="Refresh from source file"
                    >
                      ↻
                    </button>
                  </h3>
                  
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '8px'
                    }}>
                      <span style={{
                        backgroundColor: hexToRgba(elementColor, 0.15),
                        color: elementColor,
                        padding: '4px 12px',
                        borderRadius: '4px',
                        fontWeight: '600',
                        fontSize: '14px'
                      }}>
                        {current} / 
                      </span>
                      <input
                        type="number"
                        min="0"
                        value={max}
                        onChange={(e) => {
                          const newMax = parseInt(e.target.value) || 0;
                          const newCurrent = Math.min(current, newMax);
                          updateEnvironmentalVariable(env.name, newCurrent, newMax);
                        }}
                        style={{
                          width: '60px',
                          padding: '4px 8px',
                          fontSize: '14px',
                          border: `1px solid ${elementColor}`,
                          borderRadius: '4px',
                          backgroundColor: 'rgba(255, 255, 255, 0.9)',
                          color: '#2c3e50',
                          textAlign: 'center'
                        }}
                      />
                    </div>
                  </div>
                  
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(20px, 1fr))',
                    gap: '6px'
                  }}>
                    {Array.from({ length: max }, (_, i) => (
                      <label key={i} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer'
                      }}>
                        <input
                          type="checkbox"
                          checked={i < current}
                          onChange={(e) => {
                            const newCurrent = e.target.checked 
                              ? Math.max(current, i + 1)
                              : Math.min(current, i);
                            updateEnvironmentalVariable(env.name, newCurrent, max);
                          }}
                          style={{ display: 'none' }}
                        />
                        <span style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '3px',
                          border: `2px solid ${i < current ? elementColor : '#bdc3c7'}`,
                          backgroundColor: i < current ? elementColor : '#ecf0f1',
                          transition: 'all 0.2s ease',
                          display: 'block'
                        }}></span>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="stat-overview-empty">No environmental variables found</p>
        )}
      </section>

      {/* Per-PC Stats */}
      <section className="stat-overview-section">
        <h2>Per-PC Extracted Stats</h2>
        <p className="stat-overview-note">
          (Only shows variables tagged with #vitality or #defensive)
        </p>

        {pcs && Object.keys(pcs).length > 0 ? (
          <div className="stat-overview-pcs">
            {Object.entries(pcs).map(([pcName, stats]) => {
              // Get color for this PC's folder (PCs/pcName/)
              const pcFolderPath = `PCs/${pcName}/`;
              const pcColor = fileColors[pcFolderPath] || '#e6e6e6';
              const isUncolored = pcColor === '#e6e6e6';
              const backgroundColor = isUncolored ? 'transparent' : hexToRgba(pcColor, 0.15);
              const borderColor = isUncolored ? 'var(--border-color, #3e3e42)' : pcColor;
              const headerColor = isUncolored ? 'var(--accent-color, #4ec9b0)' : getLighterColor(pcColor);
              
              // Calculate HP percentage for life bar
              const currentHpStat = stats.vitality?.find(s => s.key === 'current_hp');
              const maxHpStat = stats.vitality?.find(s => s.key === 'max_hp');
              const currentHp = currentHpStat ? parseFloat(currentHpStat.value) : 0;
              const maxHp = maxHpStat ? parseFloat(maxHpStat.value) : 0;
              const hpPercentage = maxHp > 0 ? Math.max(0, Math.min(100, (currentHp / maxHp) * 100)) : 0;
              
              // Determine life bar color based on HP percentage
              const getHpColor = (percent) => {
                if (percent > 75) return '#4ec9b0'; // Healthy green-cyan
                if (percent > 50) return '#dcdcaa'; // Yellow
                if (percent > 25) return '#ce9178'; // Orange
                return '#f48771'; // Critical red
              };
              const hpColor = getHpColor(hpPercentage);
              
              return (
                <div 
                  key={pcName} 
                  className="stat-overview-pc"
                  style={{
                    backgroundColor: backgroundColor,
                    borderColor: borderColor,
                  }}
                >
                  <h3 
                    style={{ 
                      color: headerColor, 
                      borderBottomColor: borderColor,
                      cursor: onFileSelect ? 'pointer' : 'default',
                      transition: 'opacity 0.2s'
                    }}
                    onClick={() => {
                      if (onFileSelect) {
                        // Use the same method as [[]] links - just pass the character name
                        onFileSelect(pcName);
                      }
                    }}
                    onMouseEnter={(e) => {
                      if (onFileSelect) {
                        e.currentTarget.style.opacity = '0.7';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (onFileSelect) {
                        e.currentTarget.style.opacity = '1';
                      }
                    }}
                    title={onFileSelect ? `Open ${pcName}` : pcName}
                  >
                    {pcName}
                  </h3>
                  
                  {/* Large Life Bar Display */}
                  {maxHp > 0 && (
                    <div style={{
                      marginBottom: '15px',
                      padding: '8px',
                      backgroundColor: 'rgba(0, 0, 0, 0.2)',
                      borderRadius: '8px',
                      border: `1px solid ${borderColor}`
                    }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '6px',
                        fontSize: '12px',
                        fontWeight: '600',
                        color: headerColor
                      }}>
                        <span>HP</span>
                        <span>{currentHp} / {maxHp}</span>
                      </div>
                      <div style={{
                        width: '100%',
                        height: '20px',
                        backgroundColor: '#2d2d30',
                        borderRadius: '10px',
                        overflow: 'hidden',
                        border: '2px solid #444',
                        position: 'relative',
                        boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)'
                      }}>
                        <div style={{
                          width: `${hpPercentage}%`,
                          height: '100%',
                          backgroundColor: hpColor,
                          transition: 'width 0.5s ease, background-color 0.5s ease',
                          boxShadow: `0 0 10px ${hpColor}, inset 0 1px 2px rgba(255, 255, 255, 0.3)`,
                          borderRadius: '8px'
                        }} />
                        <span style={{
                          position: 'absolute',
                          top: '50%',
                          left: '50%',
                          transform: 'translate(-50%, -50%)',
                          fontSize: '11px',
                          fontWeight: 'bold',
                          color: '#fff',
                          textShadow: '0 1px 3px rgba(0, 0, 0, 0.8)',
                          pointerEvents: 'none',
                          letterSpacing: '0.5px'
                        }}>
                          {Math.round(hpPercentage)}%
                        </span>
                      </div>
                    </div>
                  )}

                {/* Defensive Stats */}
                {stats.defensive && stats.defensive.length > 0 && (
                  <div className="stat-overview-category">
                    <h4>Defensive</h4>
                    <div className="stat-overview-table-wrapper">
                      <table className="stat-overview-table stat-overview-table-compact">
                        <thead>
                          <tr>
                            <th>Key</th>
                            <th>Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stats.defensive.map((stat, idx) => (
                            <tr key={idx}>
                              <td className="stat-overview-key">{stat.key}</td>
                              <td className="stat-overview-value">{stat.value || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Bending Slots */}
                {stats.bending_slots && stats.bending_slots.length > 0 && (
                  <div className="stat-overview-category">
                    <h4>Bending Slots</h4>
                    <div className="stat-overview-slots-grid">
                      {stats.bending_slots.map((slot, idx) => {
                        // Parse current/max from value like "9/15"
                        const slotMatch = String(slot.value).match(/^(\d+)\s*\/\s*(\d+)$/);
                        const current = slotMatch ? parseInt(slotMatch[1]) : 0;
                        const max = slotMatch ? parseInt(slotMatch[2]) : 0;
                        const percentage = max > 0 ? (current / max) * 100 : 0;
                        
                        // Determine element color from slot name
                        const getElementColor = (name) => {
                          const lowerName = name.toLowerCase();
                          if (lowerName.includes('air')) return '#fdffd1';
                          if (lowerName.includes('water')) return '#91bbff';
                          if (lowerName.includes('earth')) return '#c8f0a6';
                          if (lowerName.includes('fire')) return '#ffb3b3';
                          if (lowerName.includes('spirit')) return '#ffcaf4';
                          return '#4ec9b0'; // default
                        };
                        
                        const slotColor = getElementColor(slot.key);
                        
                        return (
                          <div key={idx} style={{
                            backgroundColor: hexToRgba(slotColor, 0.1),
                            border: `2px solid ${slotColor}`,
                            borderRadius: '8px',
                            padding: '10px',
                            minWidth: '140px'
                          }}>
                            <div style={{
                              fontSize: '11px',
                              fontWeight: '600',
                              color: slotColor,
                              marginBottom: '6px',
                              textTransform: 'capitalize'
                            }}>
                              {slot.key.replace(/_/g, ' ')}
                            </div>
                            <div style={{
                              fontSize: '14px',
                              fontWeight: 'bold',
                              color: '#fff',
                              marginBottom: '4px'
                            }}>
                              {current} / {max}
                            </div>
                            <div style={{
                              width: '100%',
                              height: '8px',
                              backgroundColor: '#2d2d30',
                              borderRadius: '4px',
                              overflow: 'hidden',
                              border: '1px solid #444'
                            }}>
                              <div style={{
                                width: `${percentage}%`,
                                height: '100%',
                                backgroundColor: slotColor,
                                transition: 'width 0.3s ease',
                                boxShadow: `0 0 6px ${slotColor}`
                              }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
              );
            })}
          </div>
        ) : (
          <p className="stat-overview-empty">No PC stats found</p>
        )}
      </section>

      {last_generated && (
        <footer className="stat-overview-footer">
          Last generated: {new Date(last_generated * 1000).toLocaleString()}
        </footer>
      )}
    </div>
  );
};

export default StatOverview;
