import React, { createContext, useState, useContext, useCallback, useMemo } from 'react';

const ReadyStateContext = createContext();

export const ReadyStateProvider = ({ children }) => {
  // Store ready state per character name
  const [readyStates, setReadyStates] = useState({});

  const setReady = useCallback((characterName, isReady) => {
    setReadyStates(prev => ({
      ...prev,
      [characterName]: isReady
    }));
  }, []);

  const isReady = useCallback((characterName) => {
    const ready = readyStates[characterName] || false;
    return ready;
  }, [readyStates]);

  const clearReady = useCallback((characterName) => {
    setReadyStates(prev => ({
      ...prev,
      [characterName]: false
    }));
  }, []);

  const value = useMemo(() => ({
    setReady,
    isReady,
    clearReady,
    readyStates
  }), [setReady, isReady, clearReady, readyStates]);

  return (
    <ReadyStateContext.Provider value={value}>
      {children}
    </ReadyStateContext.Provider>
  );
};

export const useReadyState = () => {
  const context = useContext(ReadyStateContext);
  if (!context) {
    throw new Error('useReadyState must be used within a ReadyStateProvider');
  }
  return context;
};
