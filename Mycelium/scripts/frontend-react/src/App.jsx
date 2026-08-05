import React, { useState, useEffect } from 'react';
import FileExplorer from './components/FileExplorer';
import DiceRoller from './components/DiceRoller';
import GameMasterMode from './components/GameMasterMode';
import BattlemapViewer from './components/BattlemapViewer';
import { ReadyStateProvider } from './context/ReadyStateContext';
import { API_BASE_URL } from './config/api';
import { initEventStream } from './data/vaultResource';
import './styles/App.css';

function App() {
  const [lightMode, setLightMode] = useState(false);
  const [gmMode, setGmMode] = useState(false);
  const [watcherFilePath, setWatcherFilePath] = useState(null);
  const [watcherContent, setWatcherContent] = useState(null);

  // Open the single shared SSE stream once for the whole app. Components
  // that used to poll their own file(s) on independent timers now subscribe
  // to vaultResource instead, which invalidates/refetches on the
  // `file_changed` events this stream delivers.
  useEffect(() => {
    initEventStream();
  }, []);

  // Check URL for GM mode or watcher mode
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('gm') === 'true') {
      setGmMode(true);
    }
    const watcher = params.get('watcher');
    if (watcher) {
      setWatcherFilePath(watcher);
    }
  }, []);

  // Fetch initial content for watcher mode
  useEffect(() => {
    if (!watcherFilePath) return;
    fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(watcherFilePath)}`)
      .then(r => r.json())
      .then(data => setWatcherContent(data.content || JSON.stringify(data)))
      .catch(() => setWatcherContent(''));
  }, [watcherFilePath]);

  // Watcher mode: full-screen battlemap with fast sync, no other UI
  if (watcherFilePath) {
    if (watcherContent === null) {
      return (
        <div style={{ height: '100dvh', width: '100dvw', background: '#1a1a1a', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888', fontSize: '18px' }}>
          Loading battlemap...
        </div>
      );
    }
    return (
      <ReadyStateProvider>
        <div style={{ height: '100dvh', width: '100dvw', background: '#1a1a1a', overflow: 'hidden' }}>
          <BattlemapViewer
            filePath={watcherFilePath}
            content={watcherContent}
            initialWatcherMode={true}
            syncIntervalMs={1500}
          />
        </div>
      </ReadyStateProvider>
    );
  }

  return (
    <ReadyStateProvider>
      <div className={`app ${lightMode ? 'light-mode' : ''}`} style={{
        height: '100dvh',
        width: '100dvw',
        background: lightMode ? '#f5f5f5' : '#1e1e1e',
        margin: 0,
        padding: 0,
        overflow: gmMode ? 'auto' : 'hidden',
        position: 'fixed',
        top: 0,
        left: 0,
        zIndex: 10000,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {gmMode ? (
          <GameMasterMode lightMode={lightMode} />
        ) : (
          <>
            <div style={{ 
              flex: 1, 
              overflow: 'hidden',
              minHeight: 0  // Critical for flex children to respect parent constraints
            }}>
              <FileExplorer 
                lightMode={lightMode} 
                onToggleTheme={() => setLightMode(!lightMode)}
                gmMode={gmMode}
                onToggleGmMode={() => setGmMode(!gmMode)}
              />
            </div>
            <div style={{
              padding: '12px',
              borderTop: lightMode ? '1px solid #ddd' : '1px solid #333',
              flexShrink: 0  // Prevent dice roller from being compressed
            }}>
              <DiceRoller lightMode={lightMode} />
            </div>
          </>
        )}
      </div>
    </ReadyStateProvider>
  );
}

export default App;
