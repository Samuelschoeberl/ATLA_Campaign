import React, { useState, useEffect, useRef } from 'react';
import './SearchBar.css';
import { API_BASE_URL } from '../config/api';

const SearchBar = ({ onFileSelect, lightMode }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef(null);

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }

    const timeoutId = setTimeout(() => {
      performSearch(query);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query]);

  const performSearch = async (searchQuery) => {
    setIsSearching(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/player_root/search?q=${encodeURIComponent(searchQuery)}`
      );
      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
        setShowResults(true);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleResultClick = (result) => {
    // Convert the path format from backend to match the file structure
    // Remove 'Player Root/' prefix if present
    const cleanPath = result.path.replace(/^Player Root\//, '');
    
    onFileSelect({
      name: result.path.split('/').pop(),
      path: cleanPath
    });
    
    setShowResults(false);
    setQuery('');
  };

  const highlightMatch = (text, query) => {
    if (!query) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} className="search-highlight">{part}</mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className={`search-bar-container ${lightMode ? 'light-mode' : ''}`} ref={searchRef}>
      <div className="search-input-wrapper">
        <input
          type="text"
          className="search-input"
          placeholder="Search files..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.trim().length >= 2 && setShowResults(true)}
        />
        {isSearching && <div className="search-spinner"></div>}
      </div>

      {showResults && results.length > 0 && (
        <div className="search-results">
          {results.map((result, index) => (
            <div
              key={index}
              className="search-result-item"
              onClick={() => handleResultClick(result)}
            >
              <div className="result-path">
                {highlightMatch(result.path, query)}
              </div>
              {result.matches && result.matches.length > 0 && (
                <div className="result-preview">
                  {highlightMatch(result.matches[0].excerpt, query)}
                </div>
              )}
              <div className="result-meta">
                {result.match_count} match{result.match_count !== 1 ? 'es' : ''}
              </div>
            </div>
          ))}
        </div>
      )}

      {showResults && query.trim().length >= 2 && results.length === 0 && !isSearching && (
        <div className="search-results">
          <div className="search-no-results">No results found</div>
        </div>
      )}
    </div>
  );
};

export default SearchBar;
