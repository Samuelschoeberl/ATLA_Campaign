import { API_BASE_URL } from '../config/api';
import { gridToGraphData, graphDataToGrid } from './hexUtils';

/**
 * Sync utilities for battlemap state management.
 *
 * NOTE (rework, Phase 2): `saveBattlemapState`/`syncFromServer` below are NOT
 * actually what BattlemapViewer.jsx's main save/sync loop calls -- that
 * component has its own inline reimplementation of full-document save
 * (`saveBattlemapState`, now via vaultResource.subscribe for incoming
 * changes) and per-token hot-spot PATCH calls (see `patchBattlemapToken` in
 * `src/data/vaultResource.js`). This file's exports are still used for the
 * per-background-image hex-grid save/load path
 * (`saveHexGridForImage`/`loadHexGridForImage`). Reconciling this duplication
 * properly is Phase 3 work (component decomposition), once BattlemapViewer
 * is being split up anyway -- not attempted here to avoid a risky partial
 * merge this late in the Phase 1/2 rework. See the rework plan.
 */

/**
 * Get hex grid filename for a specific background image
 */
export const getHexGridFilename = (imageName, dirPath) => {
  if (!imageName || !dirPath) {
    console.log('⚠️ getHexGridFilename: missing imageName or dirPath', { imageName, dirPath });
    return null;
  }
  const baseName = imageName.replace(/\.[^/.]+$/, '');
  const fullPath = `${dirPath}/${baseName}_hexgrid.json`;
  console.log('📝 Hex grid path:', fullPath);
  return fullPath;
};

/**
 * Save hex grid data for current background image
 */
export const saveHexGridForImage = async (imageName, dirPath, gridSize, hexGrid, tokens, hexSize) => {
  if (!imageName) return;
  
  const hexGridPath = getHexGridFilename(imageName, dirPath);
  if (!hexGridPath) return;

  const hexGridData = {
    format: 'graph',
    version: '2.0',
    gridSize,
    hexGraph: gridToGraphData(hexGrid, gridSize),
    tokens,
    hexSize,
    lastModified: Date.now()
  };

  console.log('💾 Saving hex grid for image:', imageName, 'to:', hexGridPath);

  try {
    const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(hexGridPath)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: JSON.stringify(hexGridData, null, 2)
      })
    });

    if (response.ok) {
      console.log('✅ Hex grid saved successfully for:', imageName);
    } else {
      console.error('❌ Failed to save hex grid:', response.status);
    }
  } catch (err) {
    console.error('❌ Error saving hex grid:', err);
  }
};

/**
 * Load hex grid data for a specific background image
 */
export const loadHexGridForImage = async (imageName, dirPath) => {
  if (!imageName) return null;

  const hexGridPath = getHexGridFilename(imageName, dirPath);
  if (!hexGridPath) return null;

  console.log('📂 Loading hex grid for image:', imageName, 'from:', hexGridPath);

  try {
    const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(hexGridPath)}`);
    
    if (response.ok) {
      const contentType = response.headers.get('content-type');
      let data;

      if (contentType && contentType.includes('application/json')) {
        const jsonData = await response.json();
        if (jsonData.content) {
          data = JSON.parse(jsonData.content);
        } else {
          data = jsonData;
        }
      } else {
        const text = await response.text();
        if (text && text.trim() !== '') {
          data = JSON.parse(text);
        }
      }

      if (data) {
        console.log('✅ Hex grid loaded for:', imageName);
        return data;
      }
    } else if (response.status === 404) {
      console.log('ℹ️ No existing hex grid found for:', imageName);
    } else {
      console.error('❌ Failed to load hex grid:', response.status);
    }
  } catch (err) {
    console.error('❌ Error loading hex grid:', err);
  }

  return null;
};

/**
 * Save battlemap state to server
 */
export const saveBattlemapState = async (filePath, gridSize, hexGrid, tokens, selectedImage, hexSize, lastSavedStateRef, setLastSyncTime, setIsSyncing, useGraphFormat = true) => {
  if (!filePath) {
    console.warn('BattlemapViewer: No filePath provided, cannot save');
    return;
  }
  
  const now = Date.now();
  
  let state;
  if (useGraphFormat) {
    state = {
      format: 'graph',
      version: '2.0',
      gridSize,
      hexGraph: gridToGraphData(hexGrid, gridSize),
      tokens,
      backgroundImage: selectedImage,
      hexSize,
      lastModified: now
    };
  } else {
    state = {
      format: 'array',
      version: '1.0',
      gridSize,
      hexGrid,
      tokens,
      backgroundImage: selectedImage,
      hexSize,
      lastModified: now
    };
  }
  
  const stateString = JSON.stringify(state, null, 2);
  if (stateString === lastSavedStateRef.current) {
    console.log('BattlemapViewer: State unchanged, skipping save');
    return;
  }
  
  console.log('💾 BattlemapViewer: Saving to path:', filePath);
  console.log('BattlemapViewer: lastModified timestamp:', now);
  
  try {
    setIsSyncing(true);
    const response = await fetch(`${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: stateString
      })
    });
    
    if (response.ok) {
      lastSavedStateRef.current = stateString;
      setLastSyncTime(now);
      console.log('✅ BattlemapViewer: Save successful, lastSyncTime updated to:', now);
    } else {
      const errorText = await response.text();
      console.error('❌ BattlemapViewer: Save failed with status:', response.status, errorText);
    }
  } catch (err) {
    console.error('❌ Failed to save battlemap:', err);
  } finally {
    setIsSyncing(false);
  }
};

/**
 * Sync from server - fetches latest state
 */
export const syncFromServer = async (filePath, lastSyncTimeRef, gridSizeRef, hexGridRef, tokensRef, selectedImageRef, hexSizeRef, callbacks) => {
  if (!filePath) return;
  
  const { setGridSize, setHexGrid, setTokens, setSelectedImage, setHexSize, setLastSyncTime, isUpdatingFromSyncRef } = callbacks;
  
  try {
    const syncUrl = `${API_BASE_URL}/player_root/${encodeURIComponent(filePath)}`;
    const response = await fetch(syncUrl);
    
    if (response.ok) {
      const contentType = response.headers.get('content-type');
      let newState;
      
      if (contentType && contentType.includes('application/json')) {
        const jsonResponse = await response.json();
        if (jsonResponse.content) {
          newState = JSON.parse(jsonResponse.content);
        } else {
          newState = jsonResponse;
        }
      } else {
        const textContent = await response.text();
        if (!textContent || textContent.trim() === '') {
          return;
        }
        newState = JSON.parse(textContent);
      }
      
      // Convert graph format to grid if needed
      if (newState.format === 'graph' && newState.hexGraph) {
        newState.hexGrid = graphDataToGrid(newState.hexGraph, newState.gridSize);
      }
      
      // Only update if remote state is newer and different
      if (newState.lastModified && newState.lastModified > lastSyncTimeRef.current) {
        const currentStateString = JSON.stringify({
          gridSize: gridSizeRef.current,
          hexGrid: hexGridRef.current,
          tokens: tokensRef.current,
          backgroundImage: selectedImageRef.current,
          hexSize: hexSizeRef.current
        });
        const newStateString = JSON.stringify({
          gridSize: newState.gridSize,
          hexGrid: newState.hexGrid,
          tokens: newState.tokens,
          backgroundImage: newState.backgroundImage,
          hexSize: newState.hexSize
        });
        
        if (currentStateString !== newStateString) {
          console.log('✅ BattlemapViewer: Applying remote changes');
          
          isUpdatingFromSyncRef.current = true;
          
          if (newState.gridSize) setGridSize(newState.gridSize);
          if (newState.hexGrid) setHexGrid(newState.hexGrid);
          if (newState.tokens) setTokens(newState.tokens);
          if (newState.backgroundImage) setSelectedImage(newState.backgroundImage);
          if (newState.hexSize) setHexSize(newState.hexSize);
          setLastSyncTime(newState.lastModified);
        }
      }
    }
  } catch (err) {
    console.error('❌ Failed to sync battlemap:', err);
  }
};
