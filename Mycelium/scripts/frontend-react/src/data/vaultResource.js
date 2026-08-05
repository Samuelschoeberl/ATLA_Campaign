// Shared vault data/sync layer.
//
// Before this, every component (CharacterSheet, InitiativeTracker,
// BattlemapViewer) did its own raw `fetch()`, kept its own copy of "current
// file state", and polled on its own timer -- the same underlying file could
// be independently re-fetched by 3+ components on 3+ different schedules,
// and saves were whole-document overwrites with little or no conflict
// detection (see the rework plan for the specific races this caused).
//
// This module is the one place that:
//   - Talks to the backend's SSE stream (/api/events) and turns
//     `file_changed` events into cache invalidation + subscriber
//     notification, replacing per-component polling.
//   - Caches each vault path's {content, version} so multiple components
//     asking for the same path share one fetch instead of each doing their
//     own.
//   - Wraps the version-checked save/patch endpoints added on the backend,
//     surfacing conflicts (`{conflict: true, ...}`) instead of silently
//     overwriting newer server state.
//
// Intentionally NOT introducing a new dependency (no react-query/SWR/
// zustand) -- this app's scale (a handful of players on a LAN) doesn't need
// one, and every other part of the codebase talks to the backend with plain
// fetch already.

import { API_BASE_URL } from '../config/api';

// ---------------------------------------------------------------------------
// Path normalization -- components in this app have historically passed
// paths both with and without a leading "Player Root/" prefix. Normalize to
// "no prefix" internally (matching what most /player_root/<path> callers
// already send) so the same file is always one cache entry, not two.
// ---------------------------------------------------------------------------
const PLAYER_ROOT_PREFIX = 'Player Root/';

function normalizePath(path) {
  if (!path) return path;
  return path.startsWith(PLAYER_ROOT_PREFIX) ? path.slice(PLAYER_ROOT_PREFIX.length) : path;
}

function buildPlayerRootUrl(path) {
  const rel = normalizePath(path);
  const encoded = rel.split('/').map(encodeURIComponent).join('/');
  return `${API_BASE_URL}/player_root/${encoded}`;
}

// ---------------------------------------------------------------------------
// Cache: Map<normalizedPath, { content, version, subscribers: Set<fn>, inflight: Promise|null }>
// ---------------------------------------------------------------------------
const cache = new Map();

function getEntry(path) {
  const key = normalizePath(path);
  let entry = cache.get(key);
  if (!entry) {
    entry = { content: null, version: null, subscribers: new Set(), inflight: null };
    cache.set(key, entry);
  }
  return entry;
}

function notify(path) {
  const entry = cache.get(normalizePath(path));
  if (!entry) return;
  const snapshot = { content: entry.content, version: entry.version };
  entry.subscribers.forEach((cb) => {
    try {
      cb(snapshot);
    } catch (e) {
      console.error('[vaultResource] subscriber callback threw', e);
    }
  });
}

/**
 * Subscribe to changes for a vault path. `callback` fires with
 * `{content, version}` whenever this module refetches that path (either
 * because an SSE file_changed event arrived, or because another caller
 * force-refreshed it). Returns an unsubscribe function.
 */
export function subscribe(path, callback) {
  const entry = getEntry(path);
  entry.subscribers.add(callback);
  return () => {
    entry.subscribers.delete(callback);
  };
}

/**
 * Get a vault file's {content, version}, from cache unless `force` is set
 * or nothing has been fetched yet.
 */
export async function getResource(path, { force = false } = {}) {
  const entry = getEntry(path);
  if (!force && entry.content !== null) {
    return { content: entry.content, version: entry.version };
  }
  if (entry.inflight) {
    return entry.inflight;
  }
  entry.inflight = (async () => {
    const resp = await fetch(buildPlayerRootUrl(path), { cache: 'no-store' });
    if (!resp.ok) {
      throw new Error(`Failed to fetch ${path}: ${resp.status}`);
    }
    const data = await resp.json();
    entry.content = data.content;
    entry.version = data.version || data.hash;
    entry.inflight = null;
    return { content: entry.content, version: entry.version };
  })();
  try {
    return await entry.inflight;
  } finally {
    entry.inflight = null;
  }
}

/**
 * Save a vault file's full content under optimistic concurrency.
 *
 * If `expectedVersion` is provided and the server's current version has
 * moved on, this resolves to `{conflict: true, serverContent, serverVersion}`
 * instead of throwing or silently overwriting -- callers decide how to
 * reconcile (reload + reapply the user's specific edit, prompt them, etc.)
 * Pass expectedVersion=null to force-write unconditionally (matches the old
 * behavior, for call sites not yet migrated to conflict-aware saves).
 */
export async function saveResource(path, newContent, expectedVersion = null) {
  const resp = await fetch(buildPlayerRootUrl(path), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: newContent,
      ...(expectedVersion != null ? { expected_version: expectedVersion } : {}),
    }),
  });
  const data = await resp.json().catch(() => ({}));
  if (resp.status === 409) {
    return { conflict: true, serverContent: data.current_content, serverVersion: data.current_version };
  }
  if (!resp.ok) {
    throw new Error(data.error || `Failed to save ${path}: ${resp.status}`);
  }
  const entry = getEntry(path);
  entry.content = newContent;
  entry.version = data.version || data.hash;
  notify(path);
  return { conflict: false, version: entry.version };
}

/**
 * Thin wrapper for the hot-spot PATCH endpoints (sheet vitals, initiative
 * turn, battlemap tokens). `endpoint` is a path relative to API_BASE_URL,
 * e.g. `/api/sheets/Anju/fields`. Same conflict contract as saveResource.
 */
export async function patchField(endpoint, body) {
  const resp = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (resp.status === 409) {
    return { conflict: true, current: data.current };
  }
  if (!resp.ok) {
    throw new Error(data.error || `PATCH ${endpoint} failed: ${resp.status}`);
  }
  return { conflict: false, ...data };
}

// Convenience wrappers for the 3 hot-spot domains -----------------------------

export function patchSheetFields(pcName, fields, expectedVersion = null) {
  return patchField(`/api/sheets/${encodeURIComponent(pcName)}/fields`, {
    ...(expectedVersion != null ? { expected_version: expectedVersion } : {}),
    fields,
  });
}

export function patchInitiativeTurn(fields, expectedVersion = null) {
  return patchField('/api/initiative/turn', {
    ...(expectedVersion != null ? { expected_version: expectedVersion } : {}),
    ...fields,
  });
}

export function patchBattlemapToken(mapFile, tokenId, changes, expectedVersion = null) {
  const encodedMap = normalizePath(mapFile).split('/').map(encodeURIComponent).join('/');
  return patchField(`/api/battlemap/${encodedMap}/tokens/${encodeURIComponent(tokenId)}`, {
    ...(expectedVersion != null ? { expected_version: expectedVersion } : {}),
    changes,
  });
}

// ---------------------------------------------------------------------------
// SSE event stream -- one shared EventSource for the whole app.
// ---------------------------------------------------------------------------
let eventSource = null;
let reconnectTimer = null;
let reconnectDelayMs = 1000;
const MAX_RECONNECT_DELAY_MS = 15000;

function handleFileChanged(event) {
  let payload;
  try {
    payload = JSON.parse(event.data);
  } catch (e) {
    return;
  }
  const path = payload.path;
  if (!path) return;
  const key = normalizePath(path);
  const entry = cache.get(key);
  if (!entry) return; // nobody's interested in this path right now

  // Proactively refetch and notify -- these are exactly the hot-spot/
  // frequently-open resources (sheets, initiative tracker, battlemap) where
  // an immediate UI update matters. Force-bypasses the cache.
  getResource(key, { force: true })
    .then(() => notify(key))
    .catch((e) => console.error('[vaultResource] refetch after file_changed failed', e));
}

/**
 * Open the shared SSE connection. Call once from App.jsx. Safe to call more
 * than once (no-ops if already connected/connecting).
 */
export function initEventStream() {
  if (eventSource) return;
  if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') return;

  const connect = () => {
    eventSource = new window.EventSource(`${API_BASE_URL}/api/events`);
    eventSource.addEventListener('file_changed', handleFileChanged);
    eventSource.onopen = () => {
      reconnectDelayMs = 1000;
    };
    eventSource.onerror = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      if (!reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connect();
        }, reconnectDelayMs);
        reconnectDelayMs = Math.min(reconnectDelayMs * 2, MAX_RECONNECT_DELAY_MS);
      }
    };
  };

  connect();
}

export function closeEventStream() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

// Exposed for tests / advanced callers that want to inspect cache state
// without going through React.
export const _internal = { cache, normalizePath };
