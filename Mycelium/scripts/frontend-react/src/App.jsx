import React, { useState } from 'react';
import FileExplorer from './components/FileExplorer';
import DiceRoller from './components/DiceRoller';
import './styles/App.css';

function App() {
  const [lightMode, setLightMode] = useState(false);

  return (
    <div className={`app ${lightMode ? 'light-mode' : ''}`} style={{ 
      height: '100vh', 
      width: '100vw', 
      background: lightMode ? '#f5f5f5' : '#1e1e1e',
      margin: 0,
      padding: 0,
      overflow: 'hidden',
      position: 'fixed',
      top: 0,
      left: 0,
      zIndex: 10000,
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{ 
        flex: 1, 
        overflow: 'hidden',
        minHeight: 0  // Critical for flex children to respect parent constraints
      }}>
        <FileExplorer lightMode={lightMode} onToggleTheme={() => setLightMode(!lightMode)} />
      </div>
      <div style={{
        padding: '12px',
        borderTop: lightMode ? '1px solid #ddd' : '1px solid #333',
        flexShrink: 0  // Prevent dice roller from being compressed
      }}>
        <DiceRoller lightMode={lightMode} />
      </div>
    </div>
  );
}

export default App;
