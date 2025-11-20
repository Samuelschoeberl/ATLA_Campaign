import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import Navigation from "./components/Navigation";
import FileList from "./components/FileList";
import MarkdownPreview from "./components/MarkdownPreview";
import FileEditor from "./components/FileEditor";
import DiceRoller from "./components/DiceRoller";
import EventLog from "./components/EventLog";
import {
  fetchDirectory,
  moveFile,
  generateGraphs,
  searchFiles,
  fetchFileColors,
} from "./utils/api";
import { ensurePlayerRoot } from "./utils/helpers";
import "./styles/App.css";

// Patterns from .gitignore to filter out
const GITIGNORE_PATTERNS = [
  /\.DS_Store/i,
  /\.bak$/i,
  /\.zip$/i,
  /__pycache__/i,
  /\.obsidian\/workspace\.json$/i,
  /^logs$/i,
  /\.log$/i,
  /^backups$/i,
  /^DMs Root/i,
];

const shouldIgnoreFile = (name) => {
  return GITIGNORE_PATTERNS.some((pattern) => pattern.test(name));
};

function App() {
  const [currentPath, setCurrentPath] = useState("");
  const [pathStack, setPathStack] = useState([""]);
  const [entries, setEntries] = useState([]);
  const [openedFile, setOpenedFile] = useState(null);
  const [pinnedPaths, setPinnedPaths] = useState([]);
  const [events, setEvents] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [fileFromUrl, setFileFromUrl] = useState(false); // Track if file came from URL
  const [fileColors, setFileColors] = useState({}); // Color mapping for files/folders

  // Helper function to build path stack from a path string
  const buildPathStack = (path) => {
    if (!path) {
      return [''];
    }
    const segments = path.split('/').filter(p => p); // Filter out empty segments
    const stack = [''];
    let current = '';
    for (const segment of segments) {
      current = current ? `${current}/${segment}` : segment;
      stack.push(current);
    }
    return stack;
  };

  // Check for file parameter in URL (for opening in new tab)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fileParam = params.get('file');
    const pathParam = params.get('path');
    
    console.log('App.jsx useEffect - URL params:', {
      search: window.location.search,
      fileParam,
      pathParam,
      allParams: Object.fromEntries(params.entries())
    });
    
    // Handle folder navigation via path parameter
    if (pathParam) {
      console.log('Navigating to folder:', pathParam);
      setCurrentPath(pathParam);
      setPathStack(buildPathStack(pathParam));
      return; // Don't process file parameter if path parameter exists
    }
    
    // Handle file opening via file parameter
    if (fileParam) {
      try {
        const fileData = JSON.parse(fileParam);
        console.log('Parsed file data:', fileData);
        setFileFromUrl(true); // Mark that we have a file from URL
        setOpenedFile(fileData);
        // Extract the path to navigate to the correct directory
        const filePath = fileData.path?.replace(/^Player Root\//i, '') || '';
        const pathParts = filePath.split('/').filter(p => p);
        pathParts.pop(); // Remove filename to get directory
        const dirPath = pathParts.join('/');
        console.log('Setting path:', { filePath, pathParts, dirPath });
        setCurrentPath(dirPath);
        setPathStack(buildPathStack(dirPath));
      } catch (error) {
        console.error('Failed to parse file parameter:', error);
      }
    }
  }, []);

  // Fetch file colors on mount
  useEffect(() => {
    const loadColors = async () => {
      try {
        const data = await fetchFileColors();
        setFileColors(data.colors || {});
      } catch (error) {
        console.error('Failed to fetch file colors:', error);
        // Continue without colors if fetch fails
      }
    };
    loadColors();
  }, []);

  useEffect(() => {
    loadDirectory(currentPath);
  }, [currentPath]);

  const loadDirectory = async (path) => {
    try {
      const data = await fetchDirectory(path);
      const filteredEntries = (data.entries || []).filter(
        (entry) => !shouldIgnoreFile(entry.name)
      );
      setEntries(filteredEntries);
      // Don't clear the opened file if it came from a URL parameter
      if (!fileFromUrl) {
        setOpenedFile(null);
      } else {
        // Clear the flag after the first directory load
        setFileFromUrl(false);
      }
    } catch (error) {
      console.error("Failed to load directory:", error);
      logEvent("error", "Directory Error", error.message);
    }
  };

  const logEvent = (severity, title, text) => {
    const newEvent = {
      severity,
      title,
      text: String(text),
      timestamp: new Date().toLocaleString(),
    };
    setEvents((prev) => [...prev, newEvent]);
  };

  const handleNavigate = (entry) => {
    const rel = (entry.path || "").replace(/^Player Root\//i, "");
    setPathStack(buildPathStack(rel));
    setCurrentPath(rel);
  };

  const handleNavigateUp = () => {
    // If a file is opened, close it first (go back to directory view)
    if (openedFile) {
      setOpenedFile(null);
      return;
    }
    
    // Otherwise, navigate up in the directory structure
    if (pathStack.length > 1) {
      const newStack = pathStack.slice(0, -1);
      setPathStack(newStack);
      setCurrentPath(newStack[newStack.length - 1]);
    }
  };

  const handleNavigateDeleted = () => {
    setPathStack((prev) => [...prev, "deleted"]);
    setCurrentPath("deleted");
  };

  const handleOpenFile = (file) => {
    const fileName = file.name.toLowerCase();

    // Open HTML files in new tab
    if (fileName.endsWith(".html")) {
      let rel = file.path || "";
      if (/^Player Root\//i.test(rel)) {
        rel = rel.replace(/^Player Root\//i, "");
      }
      const url =
        "/" +
        rel
          .split("/")
          .map((s) => encodeURIComponent(s))
          .join("/");
      window.open(url, "_blank");
      return;
    }

    // Open image files in new tab
    if (
      fileName.endsWith(".jpg") ||
      fileName.endsWith(".jpeg") ||
      fileName.endsWith(".png") ||
      fileName.endsWith(".gif") ||
      fileName.endsWith(".webp") ||
      fileName.endsWith(".svg")
    ) {
      let rel = file.path || "";
      if (/^Player Root\//i.test(rel)) {
        rel = rel.replace(/^Player Root\//i, "");
      }
      const url =
        "/player_root/" +
        rel
          .split("/")
          .map((s) => encodeURIComponent(s))
          .join("/");
      window.open(url, "_blank");
      logEvent("info", "Image Opened", `Opened ${file.name} in new tab`);
      return;
    }

    // Update currentPath to the file's directory
    let filePath = file.path || "";
    if (/^Player Root\//i.test(filePath)) {
      filePath = filePath.replace(/^Player Root\//i, "");
    }
    
    // Extract the directory path (everything except the filename)
    const pathParts = filePath.split("/").filter(p => p);
    pathParts.pop(); // Remove the filename
    const dirPath = pathParts.join("/");
    
    // Update currentPath and pathStack if the file is in a different directory
    if (dirPath !== currentPath) {
      setCurrentPath(dirPath);
      setPathStack(buildPathStack(dirPath));
    }

    setOpenedFile(file);
  };

  const handlePin = () => {
    if (!pinnedPaths.includes(currentPath)) {
      setPinnedPaths((prev) => [...prev, currentPath]);
      logEvent("info", "Pinned", `Pinned: ${currentPath || "Root"}`);
    }
  };

  const handleUnpin = (path) => {
    setPinnedPaths((prev) => prev.filter((p) => p !== path));
    logEvent("info", "Unpinned", `Unpinned: ${path || "Root"}`);
  };

  const handleNavigateToPinned = (path) => {
    // Build proper pathStack from the path segments
    setCurrentPath(path || "");
    setPathStack(buildPathStack(path));
  };

  const handleGenerateGraphs = async () => {
    try {
      logEvent("info", "Graphs", "Running Wikigraphs...");
      const folder = currentPath ? `Player Root/${currentPath}` : "Player Root";
      const result = await generateGraphs(folder);

      if (result.success) {
        logEvent(
          "info",
          "Graphs Finished",
          `Wikigraphs completed for /${currentPath || ""}`
        );
        // Refresh current directory
        await loadDirectory(currentPath);
      } else {
        logEvent("error", "Graphs Error", result.error || "Unknown error");
      }
    } catch (error) {
      console.error("Failed to generate graphs:", error);
      logEvent("error", "Graphs Error", error.message);
    }
  };

  const handleRestore = async (entry) => {
    const defaultDst = prompt(
      "Restore to (path under Player Root, e.g. PCs/Anju):",
      "PCs/"
    );
    if (!defaultDst) return;

    try {
      const dstFolder = defaultDst.replace(/^\/+|\/+$/g, "");
      const dstFull = ensurePlayerRoot(dstFolder + "/" + entry.name);
      const srcFull = ensurePlayerRoot("deleted/" + entry.name);

      await moveFile(srcFull, dstFull);
      logEvent("info", "Restored", entry.name);
      loadDirectory("deleted");
    } catch (error) {
      console.error("Failed to restore file:", error);
      logEvent("error", "Restore Failed", error.message);
    }
  };

  const handleSearch = async (query) => {
    if (!query.trim() || query.trim().length < 3) {
      setSearchResults(null);
      return;
    }

    try {
      const data = await searchFiles(query);
      setSearchResults(data.results || []);
    } catch (error) {
      console.error("Search failed:", error);
      logEvent("error", "Search Failed", error.message);
    }
  };

  const handleClearEvent = (index) => {
    setEvents((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleDiceRoll = (result, expression) => {
    if (result.error) {
      logEvent("error", "Dice Roll Error", result.error);
    } else {
      const diceValues = result.rolls.join("+");
      const modifierText =
        result.modifier !== 0
          ? result.modifier > 0
            ? ` + ${result.modifier}`
            : ` - ${Math.abs(result.modifier)}`
          : "";

      const rollsText = `[${result.rolls.join(", ")}]`;

      logEvent(
        "info",
        "Dice Roll",
        `${result.numDice}d${result.sides}(${diceValues})${modifierText} = ${
          result.total
        }\nRolls: ${rollsText}${expression ? `\n(from: ${expression})` : ""}`
      );
    }
  };

  const markdownFiles = entries.filter(
    (e) => e.type === "file" && e.name.toLowerCase().endsWith(".md")
  );

  const isDeletedFolder = currentPath === "deleted";

  return (
    <div className="app">
      <Header />

      <Navigation
        currentPath={currentPath}
        onNavigateUp={handleNavigateUp}
        onNavigateDeleted={handleNavigateDeleted}
        onGenerateGraphs={handleGenerateGraphs}
        pinnedPaths={pinnedPaths}
        onPin={handlePin}
        onUnpin={handleUnpin}
        onNavigateToPinned={handleNavigateToPinned}
        openedFileName={openedFile?.name}
      />

      <div className="workspace">
        <div className="workspace-sidebar">
          <FileList
            entries={entries}
            currentPath={currentPath}
            onNavigate={handleNavigate}
            onOpenFile={handleOpenFile}
            onRestore={handleRestore}
            onRefresh={() => loadDirectory(currentPath)}
            isDeletedFolder={isDeletedFolder}
            fileColors={fileColors}
          />
        </div>
        <div className="workspace-main">
          <div className="search-bar">
            <input
              id="search-input"
              placeholder="Search files and contents... (type to search)"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                handleSearch(e.target.value);
              }}
              style={{
                flex: 1,
                padding: "8px 10px",
                borderRadius: "6px",
                border: "1px solid #ccc",
              }}
            />
            <button
              onClick={() => {
                setSearchQuery("");
                setSearchResults(null);
              }}
            >
              Clear
            </button>
          </div>

          {searchResults && searchResults.length > 0 && (
            <section style={{ marginTop: "12px" }}>
              <h3>Search Results ({searchResults.length})</h3>
              <ul className="entries">
                {searchResults.map((result, idx) => {
                  // Extract filename from path
                  const filename = result.path.split("/").pop();
                  return (
                    <li key={idx}>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          // Clear search when opening a result
                          setSearchQuery("");
                          setSearchResults([]);
                          // Convert to the format handleOpenFile expects
                          handleOpenFile({
                            name: filename,
                            path: result.path,
                            type: "file",
                          });
                        }}
                      >
                        {filename}
                        {result.score && (
                          <span
                            style={{
                              marginLeft: "8px",
                              fontSize: "0.85em",
                              color: "#888",
                            }}
                          >
                            (score: {result.score})
                          </span>
                        )}
                      </a>
                      <div className="muted">
                        {result.path}
                        {result.match_count > 0 &&
                          ` • ${result.match_count} matches`}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <div className="md-container">
            {openedFile ? (
              <FileEditor
                file={openedFile}
                onClose={() => setOpenedFile(null)}
                onLog={logEvent}
                onRefresh={() => loadDirectory(currentPath)}
                onDiceRoll={handleDiceRoll}
                onOpen={handleOpenFile}
                onNavigate={handleNavigate}
              />
            ) : (
              markdownFiles.map((file, idx) => (
                <MarkdownPreview
                  key={idx}
                  file={file}
                  onOpen={handleOpenFile}
                  onNavigate={handleNavigate}
                  onDiceRoll={handleDiceRoll}
                  fileColors={fileColors}
                />
              ))
            )}
          </div>
        </div>
      </div>

      <DiceRoller onLog={logEvent} />
      <EventLog events={events} onClearEvent={handleClearEvent} />

      <div id="notif-area"></div>
    </div>
  );
}

export default App;
