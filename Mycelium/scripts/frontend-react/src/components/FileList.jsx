import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createFile, fetchDirectory } from "../utils/api";

const IGNORED_PATTERNS = [
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

const shouldIgnoreFile = (name = "") =>
  IGNORED_PATTERNS.some((pattern) => pattern.test(name));

const sanitizePath = (path = "") => {
  const withoutPrefix = (path || "").replace(/^Player Root\//i, "");
  return withoutPrefix.replace(/^\/+|\/+$/g, "");
};

const getParentPath = (path = "") => {
  const sanitized = sanitizePath(path);
  if (!sanitized) return "";
  const segments = sanitized.split("/").filter(Boolean);
  segments.pop();
  return segments.join("/");
};

const getAncestorPaths = (path = "") => {
  const sanitized = sanitizePath(path);
  const ancestors = [""];
  if (!sanitized) {
    return ancestors;
  }
  const segments = sanitized.split("/").filter(Boolean);
  let current = "";
  for (const segment of segments) {
    current = current ? `${current}/${segment}` : segment;
    ancestors.push(current);
  }
  return ancestors;
};

const isImageFile = (fileName = "") => {
  const lower = fileName.toLowerCase();
  return (
    lower.endsWith(".jpg") ||
    lower.endsWith(".jpeg") ||
    lower.endsWith(".png") ||
    lower.endsWith(".gif") ||
    lower.endsWith(".webp") ||
    lower.endsWith(".svg")
  );
};

const getFileUrl = (path = "") => {
  const rel = sanitizePath(path);
  return (
    "/player_root/" +
    rel
      .split("/")
      .filter(Boolean)
      .map((s) => encodeURIComponent(s))
      .join("/")
  );
};

const getHtmlUrl = (path = "") => {
  const rel = sanitizePath(path);
  return (
    "/player_root/" +
    rel
      .split("/")
      .filter(Boolean)
      .map((s) => encodeURIComponent(s))
      .join("/")
  );
};

const getEntryColor = (entry, fileColors = {}) => {
  let rel = sanitizePath(entry?.path || "");
  if (fileColors[rel]) {
    return fileColors[rel];
  }
  if (entry?.type === "dir") {
    const dirKey = rel.endsWith("/") ? rel : `${rel}/`;
    if (fileColors[dirKey]) {
      return fileColors[dirKey];
    }
  }
  return "transparent";
};

const FileList = ({
  entries,
  currentPath,
  onNavigate,
  onOpenFile,
  onRestore,
  onRefresh,
  isDeletedFolder,
  fileColors = {},
}) => {
  const normalizedCurrentPath = sanitizePath(currentPath);
  const [newFileName, setNewFileName] = useState("");
  const [treeData, setTreeData] = useState({});
  const [expandedPaths, setExpandedPaths] = useState(() => new Set([""]));

  const sanitizedEntries = useMemo(
    () => (entries || []).filter((entry) => !shouldIgnoreFile(entry.name)),
    [entries]
  );

  useEffect(() => {
    const key = normalizedCurrentPath;
    setTreeData((prev) => {
      const prevNode = prev[key] || {};
      return {
        ...prev,
        [key]: {
          ...prevNode,
          entries: sanitizedEntries,
          loading: false,
          error: null,
        },
      };
    });
  }, [sanitizedEntries, normalizedCurrentPath]);

  const loadChildren = useCallback(async (path) => {
    const key = sanitizePath(path);
    setTreeData((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        loading: true,
        error: null,
      },
    }));
    try {
      const data = await fetchDirectory(key);
      const filtered = (data.entries || []).filter(
        (entry) => !shouldIgnoreFile(entry.name)
      );
      setTreeData((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          entries: filtered,
          loading: false,
          error: null,
        },
      }));
    } catch (error) {
      setTreeData((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          loading: false,
          error: error.message || "Failed to load folder",
        },
      }));
    }
  }, []);

  const hasRootData = Boolean(treeData[""]?.entries || treeData[""]?.loading);

  useEffect(() => {
    if (!hasRootData && normalizedCurrentPath !== "") {
      loadChildren("");
    }
  }, [hasRootData, normalizedCurrentPath, loadChildren]);

  useEffect(() => {
    const parents = getAncestorPaths(normalizedCurrentPath)
      .slice(0, -1)
      .filter(Boolean);
    parents.forEach((path) => {
      const node = treeData[path];
      if (!node?.entries && !node?.loading) {
        loadChildren(path);
      }
    });
  }, [normalizedCurrentPath, treeData, loadChildren]);

  useEffect(() => {
    const ancestors = getAncestorPaths(normalizedCurrentPath);
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      ancestors.forEach((path) => next.add(path));
      return next;
    });
  }, [normalizedCurrentPath]);

  const handleCreateFile = async () => {
    const name = newFileName.trim() || "new-file.md";
    try {
      await createFile(normalizedCurrentPath, name);
      setNewFileName("");
      onRefresh();
    } catch (error) {
      console.error("Failed to create file:", error);
      alert(`Failed to create file: ${error.message}`);
    }
  };

  const openFolderInNewTab = (entry) => {
    const folderPath = sanitizePath(entry?.path || "");
    const url = `${window.location.origin}${window.location.pathname}?path=${encodeURIComponent(
      folderPath
    )}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const openFileInNewTab = (entry) => {
    const fileData = {
      name: entry.name,
      path: entry.path,
      type: "file",
    };
    const params = new URLSearchParams({ file: JSON.stringify(fileData) });
    const url = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleFileClick = (e, entry) => {
    const isCommandClick = e.metaKey || e.ctrlKey;
    const isModified = e.shiftKey || e.altKey || e.button === 1;
    const fileName = entry.name.toLowerCase();
    const isHtmlFile = fileName.endsWith(".html");
    const image = isImageFile(entry.name);

    if (isCommandClick) {
      if (isHtmlFile) {
        return;
      }
      if (image) {
        return;
      }
      e.preventDefault();
      openFileInNewTab(entry);
      return;
    }

    if (isHtmlFile || image) {
      return;
    }

    if (!isModified) {
      e.preventDefault();
      onOpenFile(entry);
    }
  };

  const handleDirectorySelect = (e, entry, entryPath) => {
    const isCommandClick = e.metaKey || e.ctrlKey;
    const isModified = e.shiftKey || e.altKey || e.button === 1;

    if (isCommandClick) {
      e.preventDefault();
      openFolderInNewTab(entry);
      return;
    }

    if (!isModified) {
      e.preventDefault();
      if (!expandedPaths.has(entryPath)) {
        setExpandedPaths((prev) => {
          const next = new Set(prev);
          next.add(entryPath);
          return next;
        });
        const node = treeData[entryPath];
        if (!node?.entries && !node?.loading) {
          loadChildren(entryPath);
        }
      }
      onNavigate(entry);
    }
  };

  const TreeNode = ({ entry, depth }) => {
    const entryPath = sanitizePath(entry.path || "");
    const isDirectory = entry.type === "dir";
    const isExpanded = expandedPaths.has(entryPath);
    const node = treeData[entryPath] || {};
    const childEntries = node.entries || [];
    const isLoading = Boolean(node.loading);
    const nodeError = node.error;
    const entryColor = getEntryColor(entry, fileColors);
    const parentPath = getParentPath(entryPath);
    const highlight =
      isDirectory && entryPath === normalizedCurrentPath
        ? "#dfe8ff"
        : "transparent";

    const isHtmlFile =
      entry.type === "file" && entry.name.toLowerCase().endsWith(".html");
    const isImage = entry.type === "file" && isImageFile(entry.name);
    const href = isHtmlFile ? getHtmlUrl(entry.path) : isImage ? getFileUrl(entry.path) : "#";
    const opensExternally = isHtmlFile || isImage;
    const showRestore =
      isDeletedFolder &&
      entry.type === "file" &&
      parentPath === normalizedCurrentPath;

    const handleToggle = (e) => {
      e.stopPropagation();
      if (isExpanded) {
        setExpandedPaths((prev) => {
          const next = new Set(prev);
          next.delete(entryPath);
          return next;
        });
      } else {
        setExpandedPaths((prev) => {
          const next = new Set(prev);
          next.add(entryPath);
          return next;
        });
        const needsChildren = !node.entries && !node.loading;
        if (needsChildren) {
          loadChildren(entryPath);
        }
      }
    };

    return (
      <div
        style={{
          paddingLeft: depth * 3,
          paddingTop: 4,
          paddingBottom: 4,
          backgroundColor:
            entryColor !== "transparent" ? entryColor : highlight,
          borderRadius: 4,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          {isDirectory ? (
            <button
              type="button"
              onClick={handleToggle}
              style={{
                border: "none",
                background: "transparent",
                cursor: "pointer",
                width: 18,
                padding: 0,
                fontSize: "0.85rem",
              }}
              aria-label={isExpanded ? "Collapse folder" : "Expand folder"}
            >
              {isExpanded ? "▾" : "▸"}
            </button>
          ) : (
            <span style={{ width: 18 }} />
          )}

          {isDirectory ? (
            <button
              type="button"
              onClick={(e) => handleDirectorySelect(e, entry, entryPath)}
              style={{
                flex: 1,
                textAlign: "left",
                border: "none",
                background: "transparent",
                cursor: "pointer",
                fontWeight:
                  entryPath === normalizedCurrentPath ? 600 : undefined,
              }}
            >
              📁 {entry.name}
            </button>
          ) : (
            <a
              href={href}
              onClick={(e) => handleFileClick(e, entry)}
              className={opensExternally ? "external-link" : ""}
              title={
                opensExternally ? "Opens in new tab" : "Open in editor (Enter)"
              }
              target={opensExternally ? "_blank" : undefined}
              rel={opensExternally ? "noopener noreferrer" : undefined}
              style={{
                flex: 1,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                textDecoration: "none",
                color: "#222",
              }}
            >
              {isImage && "🖼️"}
              {isHtmlFile && "🌐"}
              {!isImage && !isHtmlFile && "📄"}
              <span>{entry.name}</span>
            </a>
          )}

          {showRestore && (
            <button onClick={() => onRestore(entry)}>Restore</button>
          )}
        </div>

        {isDirectory && isExpanded && (
          <div style={{ marginTop: 2 }}>
            {isLoading && (
              <div className="muted" style={{ paddingLeft: 24 }}>
                Loading...
              </div>
            )}
            {nodeError && (
              <div
                style={{
                  paddingLeft: 24,
                  color: "#a10000",
                  fontSize: "0.85rem",
                }}
              >
                {nodeError}
              </div>
            )}
            {!isLoading && !nodeError && childEntries.length === 0 && (
              <div className="muted" style={{ paddingLeft: 24 }}>
                Empty folder
              </div>
            )}
            {childEntries.map((child) => (
              <TreeNode key={child.path} entry={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  const rootNode = treeData[""] || {};
  const rootEntries = rootNode.entries || [];
  const rootLoading = Boolean(rootNode.loading);
  const rootError = rootNode.error;

  return (
    <aside
      style={{
        background: "#f7f7f7",
        border: "1px solid #c6c6c6",
        borderRadius: 8,
        padding: 12,
        minHeight: 300,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ fontWeight: 600 }}>Explorer</div>
      <div style={{ flex: 1, overflowY: "auto", paddingRight: 6, maxHeight: "70vh" }}>
        {rootError && (
          <div style={{ color: "#a10000", marginBottom: 8 }}>{rootError}</div>
        )}
        {rootLoading && rootEntries.length === 0 ? (
          <div className="muted">Loading files…</div>
        ) : rootEntries.length === 0 ? (
          <div className="muted">No files found.</div>
        ) : (
          rootEntries.map((entry) => (
            <TreeNode key={entry.path} entry={entry} depth={0} />
          ))
        )}
      </div>

      {!isDeletedFolder && (
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <input
            type="text"
            placeholder="new-file.md"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleCreateFile();
              }
            }}
            style={{
              flex: 1,
              padding: "6px",
              borderRadius: "4px",
              border: "1px solid #ddd",
            }}
          />
          <button onClick={handleCreateFile}>Create</button>
        </div>
      )}
    </aside>
  );
};

export default FileList;
