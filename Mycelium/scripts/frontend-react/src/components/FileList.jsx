import React, { useState } from "react";
import { createFile } from "../utils/api";

const FileList = ({
  entries,
  currentPath,
  onNavigate,
  onOpenFile,
  onRestore,
  onRefresh,
  isDeletedFolder,
}) => {
  const [newFileName, setNewFileName] = useState("");

  const handleCreateFile = async () => {
    const name = newFileName.trim() || "new-file.md";
    try {
      await createFile(currentPath, name);
      setNewFileName("");
      onRefresh();
    } catch (error) {
      console.error("Failed to create file:", error);
      alert(`Failed to create file: ${error.message}`);
    }
  };

  const handleEntryClick = (e, entry) => {
    const isModified =
      e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button === 1;

    if (entry.type === "dir") {
      e.preventDefault();
      onNavigate(entry);
    } else if (entry.name.toLowerCase().endsWith(".html")) {
      // Let default behavior open HTML files in new tab
      return;
    } else if (isImageFile(entry.name)) {
      // Let default behavior open image files in new tab
      return;
    } else {
      if (!isModified) {
        e.preventDefault();
        onOpenFile(entry);
      }
    }
  };

  const isImageFile = (fileName) => {
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

  const getFileUrl = (path) => {
    let rel = path || "";
    if (/^Player Root\//i.test(rel)) {
      rel = rel.replace(/^Player Root\//i, "");
    }

    // Use player_root endpoint for proper file serving
    return (
      "/player_root/" +
      rel
        .split("/")
        .map((s) => encodeURIComponent(s))
        .join("/")
    );
  };

  const getHtmlUrl = (path) => {
    let rel = path || "";
    if (/^Player Root\//i.test(rel)) {
      rel = rel.replace(/^Player Root\//i, "");
    }
    return (
      "/" +
      rel
        .split("/")
        .map((s) => encodeURIComponent(s))
        .join("/")
    );
  };

  return (
    <>
      <ul className="entries">
        {entries.map((entry, idx) => {
          const isHtmlFile =
            entry.type === "file" && entry.name.toLowerCase().endsWith(".html");
          const isImage = entry.type === "file" && isImageFile(entry.name);
          const href = isHtmlFile
            ? getHtmlUrl(entry.path)
            : isImage
            ? getFileUrl(entry.path)
            : "#";
          const opensExternally = isHtmlFile || isImage;

          return (
            <li key={idx}>
              <a
                href={href}
                className={opensExternally ? "external-link" : ""}
                title={opensExternally ? "Opens in new tab" : ""}
                target={opensExternally ? "_blank" : undefined}
                rel={opensExternally ? "noopener" : undefined}
                onClick={(e) => handleEntryClick(e, entry)}
              >
                {isImage && "🖼️ "}
                {entry.name}
              </a>
              <div className="muted">{entry.type}</div>
              {isDeletedFolder && entry.type === "file" && (
                <button
                  style={{ marginLeft: "8px" }}
                  onClick={() => onRestore(entry)}
                >
                  Restore
                </button>
              )}
            </li>
          );
        })}
      </ul>

      {!isDeletedFolder && (
        <div
          style={{
            margin: "12px 0",
            display: "flex",
            gap: "8px",
            alignItems: "center",
          }}
        >
          <input
            type="text"
            placeholder="new-file.md"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyPress={(e) => {
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
    </>
  );
};

export default FileList;
