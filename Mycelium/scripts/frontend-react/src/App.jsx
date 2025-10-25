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
      setOpenedFile(null);
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
    setPathStack((prev) => [...prev, rel]);
    setCurrentPath(rel);
  };

  const handleNavigateUp = () => {
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
    if (!path) {
      setPathStack([""]);
      setCurrentPath("");
    } else {
      const segments = path.split("/");
      const stack = [""];
      let current = "";
      for (const segment of segments) {
        current = current ? `${current}/${segment}` : segment;
        stack.push(current);
      }
      setPathStack(stack);
      setCurrentPath(path);
    }
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
      />

      <div
        style={{
          marginTop: "12px",
          display: "flex",
          gap: "8px",
          alignItems: "center",
        }}
      >
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

      <section id="entries-wrap">
        <FileList
          entries={entries}
          currentPath={currentPath}
          onNavigate={handleNavigate}
          onOpenFile={handleOpenFile}
          onRestore={handleRestore}
          onRefresh={() => loadDirectory(currentPath)}
          isDeletedFolder={isDeletedFolder}
        />
      </section>

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
            />
          ))
        )}
      </div>

      <DiceRoller onLog={logEvent} />
      <EventLog events={events} onClearEvent={handleClearEvent} />

      <div id="notif-area"></div>
    </div>
  );
}

export default App;
