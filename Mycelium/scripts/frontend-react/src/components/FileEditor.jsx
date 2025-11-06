import React, { useState, useEffect, useRef } from "react";
import { fetchFile, saveFile, moveFile, findFileByName } from "../utils/api";
import {
  renderMarkdown,
  nodeColorForKey,
  stylePreviewTables,
  ensurePlayerRoot,
  rollDiceExpression,
} from "../utils/helpers";

const FileEditor = ({
  file,
  onClose,
  onLog,
  onRefresh,
  onDiceRoll,
  onOpen,
  onNavigate,
}) => {
  const [content, setContent] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [status, setStatus] = useState("");
  const previewRef = useRef(null);
  const backgroundColor = nodeColorForKey(file.path || file.name);

  useEffect(() => {
    loadContent();
  }, [file.path]);

  useEffect(() => {
    if (previewRef.current && content) {
      stylePreviewTables(previewRef.current, backgroundColor);

      // Resolve embedded image sources
      const imageElements = previewRef.current.querySelectorAll(
        "img[data-image-src]"
      );
      imageElements.forEach(async (img) => {
        const imageName = img.getAttribute("data-image-src");
        if (imageName) {
          try {
            // Find the image file
            const result = await findFileByName(imageName);
            if (result.found && result.path && result.type === "file") {
              // Set the actual image source
              img.src = `/player_root/${result.path
                .split("/")
                .map((s) => encodeURIComponent(s))
                .join("/")}`;
              img.style.cursor = "pointer";

              // Make image clickable to open in new tab
              img.onclick = () => {
                window.open(img.src, "_blank");
              };
            } else {
              // Image not found - show placeholder
              img.alt = `Image not found: ${imageName}`;
              img.src =
                "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='100'%3E%3Crect fill='%23f0f0f0' width='200' height='100'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23999'%3EImage not found%3C/text%3E%3C/svg%3E";
            }
          } catch (error) {
            console.error(`Failed to resolve image: ${imageName}`, error);
            img.alt = `Error loading: ${imageName}`;
          }
        }
      });

      // Add click handlers to dice expressions in preview
      const diceElements =
        previewRef.current.querySelectorAll(".dice-expression");
      diceElements.forEach((el) => {
        el.onclick = (e) => {
          e.preventDefault();
          const expression = el.getAttribute("data-dice-expression");
          if (expression && onDiceRoll) {
            const result = rollDiceExpression(expression);
            onDiceRoll(result, expression);
          }
        };
      });

      // Add click handlers to wikilinks in preview
      if (onOpen) {
        const wikilinkElements =
          previewRef.current.querySelectorAll(".wikilink");
        console.log('Found wikilink elements:', wikilinkElements.length);
        
        wikilinkElements.forEach((el) => {
          console.log('Attaching handler to:', el.getAttribute('data-wikilink'));
          
          const clickHandler = async (e) => {
            // For command/ctrl-click on anchor tags, the browser will handle it naturally
            // We just need to set the href properly
            const isCommandClick = e.metaKey || e.ctrlKey;
            
            console.log('Wikilink clicked:', {
              metaKey: e.metaKey,
              ctrlKey: e.ctrlKey,
              isCommandClick,
              target: el.getAttribute("data-wikilink"),
              tagName: el.tagName
            });
            
            // Always prevent default navigation since href="#"
            e.preventDefault();
            
            const target = el.getAttribute("data-wikilink");
            if (!target) return;
            
            try {
              // Find the file or folder by name
              const result = await findFileByName(target);
              if (!result.found || !result.path) {
                console.warn(`Wikilink target not found: ${target}`);
                if (onLog) {
                  onLog("warning", "Link Not Found", `File or folder not found: ${target}`);
                }
                return;
              }
              
            const fileData = {
              name: target.endsWith(".md") ? target : `${target}.md`,
              path: `Player Root/${result.path}`,
              type: result.type,
            };
            
            // For command/ctrl-click, open in new tab
            if (isCommandClick) {
              // For folders, encode the path to navigate to; for files, encode the file data
              if (result.type === "folder") {
                // Navigate to the folder in a new tab
                const folderPath = result.path.replace(/^Player Root\//i, '');
                const url = `${window.location.origin}${window.location.pathname}?path=${encodeURIComponent(folderPath)}`;
                console.log('Opening folder in new tab:', {
                  url,
                  folderPath
                });
                window.open(url, '_blank', 'noopener,noreferrer');
              } else {
                // Open file in new tab
                const params = new URLSearchParams({
                  file: JSON.stringify(fileData)
                });
                const url = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
                console.log('Opening file in new tab:', {
                  url,
                  fileData,
                  serialized: JSON.stringify(fileData)
                });
                window.open(url, '_blank', 'noopener,noreferrer');
              }
              return;
            }              // Normal click: open in current editor or navigate to folder
              if (result.type === "file") {
                onOpen(fileData);
              } else if (result.type === "folder" && onNavigate) {
                onNavigate(fileData);
                onClose(); // Close the editor when navigating to a folder
              }
            } catch (error) {
              console.error("Failed to resolve wikilink:", error);
              if (onLog) {
                onLog("error", "Link Error", error.message);
              }
            }
          };
          
          // Use addEventListener for better event handling
          el.addEventListener('click', clickHandler);
          
          // Store handler reference for potential cleanup (optional)
          el._clickHandler = clickHandler;
        });
      }
    }
  }, [
    content,
    backgroundColor,
    onDiceRoll,
    onOpen,
    onLog,
    onNavigate,
    onClose,
  ]);

  const loadContent = async () => {
    setIsLoading(true);
    setStatus("loading...");
    try {
      const data = await fetchFile(file.path.replace(/^Player Root\//i, ""));
      setContent(data.content || "");
      setStatus("");
    } catch (error) {
      console.error("Failed to load file:", error);
      setContent("// Failed to load content\n// Error: " + error.message);
      setStatus("error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setStatus("saving...");
    try {
      await saveFile(file.path.replace(/^Player Root\//i, ""), content);
      setStatus("saved");
      onLog("info", "File Saved", `${file.name} saved successfully`);
      setTimeout(() => setStatus(""), 2000);
    } catch (error) {
      console.error("Failed to save file:", error);
      setStatus("save failed");
      onLog("error", "Save Failed", error.message);
    }
  };

  const handleDelete = async () => {
    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${file.name}? This will move it to Player Root/deleted/deleted_${file.name}.`
    );
    if (!confirmDelete) return;

    try {
      const srcFull = ensurePlayerRoot(file.path);
      const dstFull = ensurePlayerRoot(`deleted/deleted_${file.name}`);

      await moveFile(srcFull, dstFull);
      onLog("info", "File Deleted", `${file.name} moved to deleted folder`);
      onClose();
      onRefresh();
    } catch (error) {
      console.error("Failed to delete file:", error);
      onLog("error", "Delete Failed", error.message);
    }
  };

  const handleRefresh = async () => {
    setStatus("refreshing...");
    await loadContent();
    onLog("info", "Refreshed", file.path.replace(/^Player Root\//i, ""));
  };

  return (
    <div
      className={`markdown-file ${isFullscreen ? "is-fullscreen" : ""}`}
      style={{ background: backgroundColor }}
    >
      <div className="file-title">
        <div>
          <strong id="file-title-name">{file.name}</strong>
          <div className="file-meta">
            /{file.path.replace(/^Player Root\//i, "")}
          </div>
        </div>
        <div>
          <button onClick={() => setIsFullscreen(!isFullscreen)}>
            {isFullscreen ? "Close" : "Full screen"}
          </button>
          <button onClick={handleRefresh} style={{ marginLeft: "8px" }}>
            Refresh
          </button>
        </div>
      </div>

      <div style={{ marginTop: "8px", position: "relative" }}>
        <textarea
          id="file-ta"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={isLoading ? "Loading..." : "Enter content..."}
          style={{
            width: "100%",
            minHeight: "320px",
            paddingRight: "140px",
            fontFamily: "monospace",
            fontSize: "14px",
            padding: "8px",
          }}
        />
        <div
          id="file-controls"
          style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            alignItems: "flex-end",
          }}
        >
          <button onClick={handleSave}>Save</button>
          <button
            onClick={handleDelete}
            style={{ background: "#ffefef", border: "1px solid #cc9999" }}
          >
            Delete
          </button>
          <span
            className="muted"
            style={{ display: "block", whiteSpace: "nowrap" }}
          >
            {status}
          </span>
        </div>
      </div>

      {!isFullscreen && (
        <>
          <h3>Preview</h3>
          <div
            id="preview"
            ref={previewRef}
            style={{
              background: "#fff",
              padding: "8px",
              borderRadius: "6px",
              minHeight: "120px",
            }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        </>
      )}
    </div>
  );
};

export default FileEditor;
