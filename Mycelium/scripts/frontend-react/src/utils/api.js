// Base URL for API calls
const BASE =
  window.MYCELIUM_BACKEND_BASE ||
  `${window.location.protocol}//${window.location.host}`;

export const API_BASE = BASE.replace(/\/$/, "");

// Fetch directory listing
export async function fetchDirectory(path) {
  const normalizedPath = (path || "").replace(/^Player Root\//i, "");
  const segments = normalizedPath
    ? "/" +
      normalizedPath
        .split("/")
        .map((s) => encodeURIComponent(s))
        .join("/")
    : "";
  const url = `${API_BASE}/player_root${segments}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch directory: ${response.status}`);
  }
  return response.json();
}

// Fetch file content
export async function fetchFile(path) {
  const normalizedPath = (path || "").replace(/^Player Root\//i, "");
  const segments = normalizedPath
    .split("/")
    .map((s) => encodeURIComponent(s))
    .join("/");
  const url = `${API_BASE}/player_root/${segments}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch file: ${response.status}`);
  }
  return response.json();
}

// Save file content
export async function saveFile(path, content) {
  const normalizedPath = (path || "").replace(/^Player Root\//i, "");
  const segments = normalizedPath
    .split("/")
    .map((s) => encodeURIComponent(s))
    .join("/");
  const url = `${API_BASE}/player_root/${segments}`;
  const response = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    throw new Error(`Failed to save file: ${response.status}`);
  }
  return response.json();
}

// Delete/move file
export async function moveFile(src, dst) {
  const url = `${API_BASE}/player_root/move`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ src, dst }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Failed to move file: ${response.status}`);
  }
  return response.json();
}

// Create new file
export async function createFile(folderPath, fileName, content = "") {
  const url = `${API_BASE}/api/create-md-file`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      folderPath: folderPath || "",
      filename: fileName,
    }),
  });
  if (!response.ok) {
    let errorText;
    try {
      const json = await response.json();
      errorText = json.error || JSON.stringify(json);
    } catch (e) {
      errorText = await response.text();
    }
    throw new Error(errorText || `Failed to create file: ${response.status}`);
  }
  return response.json();
}

// Generate graphs
export async function generateGraphs(folder) {
  const url = `${API_BASE}/api/generate-graphs`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder }),
  });
  if (!response.ok) {
    throw new Error(`Failed to generate graphs: ${response.status}`);
  }
  return response.json();
}

// Search files
export async function searchFiles(query) {
  const url = `${API_BASE}/player_root/search?q=${encodeURIComponent(query)}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`);
  }
  return response.json();
}

// Find file by name
export async function findFileByName(filename) {
  const url = `${API_BASE}/api/find-file/${encodeURIComponent(filename)}`;
  const response = await fetch(url);
  if (!response.ok) {
    if (response.status === 404) {
      return { found: false };
    }
    throw new Error(`File lookup failed: ${response.status}`);
  }
  return response.json();
}

// Fetch file/folder colors for the explorer
export async function fetchFileColors() {
  const url = `${API_BASE}/api/file-colors`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to fetch file colors: ${response.status}`);
  }
  return response.json();
}
