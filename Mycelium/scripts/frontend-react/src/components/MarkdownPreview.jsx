import React, { useState, useEffect, useRef } from "react";
import {
  renderMarkdown,
  stylePreviewTables,
  rollDiceExpression,
} from "../utils/helpers";
import { findFileByName } from "../utils/api";

const MarkdownPreview = ({ file, onOpen, onNavigate, onDiceRoll, fileColors = {} }) => {
  const [content, setContent] = useState("Loading...");
  const previewRef = useRef(null);
  
  // Get background color from fileColors prop
  const getBackgroundColor = () => {
    // Normalize the path to match color keys
    let filePath = (file.path || "").replace(/^Player Root\//i, "");
    
    // Try exact match first
    if (fileColors[filePath]) {
      return fileColors[filePath];
    }
    
    // Default to white if no color found
    return '#ffffff';
  };
  
  const backgroundColor = getBackgroundColor();

  useEffect(() => {
    const loadContent = async () => {
      try {
        const segments = (file.path || "")
          .replace(/^Player Root\//i, "")
          .split("/")
          .map((s) => encodeURIComponent(s))
          .join("/");
        const response = await fetch(`/player_root/${segments}`);
        if (!response.ok) {
          setContent("Error loading preview");
          return;
        }
        const json = await response.json();
        setContent(json.content || "");
      } catch (error) {
        console.error("Failed to load markdown preview:", error);
        setContent("Error loading preview");
      }
    };

    loadContent();
  }, [file.path]);

  useEffect(() => {
    if (
      previewRef.current &&
      content !== "Loading..." &&
      content !== "Error loading preview"
    ) {
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

      // Add click handlers to dice expressions
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

      // Add click handlers to wikilinks
      const wikilinkElements = previewRef.current.querySelectorAll(".wikilink");
      wikilinkElements.forEach((el) => {
        const clickHandler = async (e) => {
          // For command/ctrl-click on anchor tags, the browser handles it naturally
          const isCommandClick = e.metaKey || e.ctrlKey;
          
          // Always prevent default navigation since href="#"
          e.preventDefault();
          
          const target = el.getAttribute("data-wikilink");
          if (!target) return;
          
          try {
            // Find the file or folder by name
            const result = await findFileByName(target);
            if (!result.found || !result.path) {
              console.warn(`Wikilink target not found: ${target}`);
              // Show error message in event log
              if (onDiceRoll) {
                onDiceRoll(
                  { error: `File or folder not found: ${target}` },
                  `[[${target}]]`
                );
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
                console.log('MarkdownPreview - Opening folder in new tab:', {
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
                console.log('MarkdownPreview - Opening file in new tab:', {
                  url,
                  fileData,
                  serialized: JSON.stringify(fileData)
                });
                window.open(url, '_blank', 'noopener,noreferrer');
              }
              return;
            }
            
            // Normal click: open in current view or navigate to folder
            if (result.type === "file") {
              onOpen(fileData);
            } else if (result.type === "folder") {
              onNavigate(fileData);
            }
          } catch (error) {
            console.error("Failed to resolve wikilink:", error);
            if (onDiceRoll) {
              onDiceRoll(
                { error: `Error resolving link: ${error.message}` },
                `[[${target}]]`
              );
            }
          }
        };
        
        el.addEventListener('click', clickHandler);
      });
    }
  }, [content, backgroundColor, onDiceRoll, onOpen, onNavigate]);

  return (
    <div className="markdown-file" style={{ background: backgroundColor }}>
      <div className="file-title">
        <div>
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              onOpen(file);
            }}
            style={{ textDecoration: "none", color: "inherit" }}
          >
            {file.name}
          </a>
          <div className="file-meta">
            /{file.path.replace(/^Player Root\//i, "")}
          </div>
        </div>
        <button onClick={() => onOpen(file)}>Open</button>
      </div>
      <div
        ref={previewRef}
        dangerouslySetInnerHTML={{
          __html:
            content === "Loading..." || content === "Error loading preview"
              ? content
              : renderMarkdown(content),
        }}
      />
    </div>
  );
};

export default MarkdownPreview;
