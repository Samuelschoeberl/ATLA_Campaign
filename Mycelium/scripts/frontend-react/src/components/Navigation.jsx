import React from "react";

const Navigation = ({
  currentPath,
  onNavigateUp,
  onNavigateDeleted,
  onGenerateGraphs,
  pinnedPaths,
  onPin,
  onUnpin,
  onNavigateToPinned,
}) => {
  return (
    <nav>
      <div className="back">
        <button id="up-btn" disabled={!currentPath} onClick={onNavigateUp}>
          Up
        </button>
      </div>
      <div>
        <button id="deleted-btn" onClick={onNavigateDeleted}>
          Deleted
        </button>
      </div>
      <div>
        <button
          id="graphs-btn"
          title="Create or update wikigraph visualizations for this folder"
          onClick={onGenerateGraphs}
        >
          Create/Update graphs
        </button>
      </div>
      <div>
        <button
          id="pin-btn"
          onClick={() =>
            (pinnedPaths || []).includes(currentPath)
              ? onUnpin(currentPath)
              : onPin()
          }
        >
          {(pinnedPaths || []).includes(currentPath) ? "Unpin" : "Pin"}
        </button>
      </div>
      <div
        id="pinned-list"
        style={{ display: "flex", gap: "6px", alignItems: "center" }}
      >
        {pinnedPaths.map((path, idx) => (
          <span
            key={idx}
            style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}
          >
            <button onClick={() => onNavigateToPinned(path)}>
              📌 {path || "Root"}
            </button>
          </span>
        ))}
      </div>
      <div className="muted">
        Current: /<span id="curpath">{currentPath}</span>
      </div>
    </nav>
  );
};

export default Navigation;
