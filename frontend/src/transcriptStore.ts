// Persist the transcript to localStorage so history survives a reload. Keyed by
// client_id; the server stores nothing. Bounded to the last MAX_BUBBLES lines so
// a long-running tab can't grow storage without limit.
//
// The Storage is injectable (defaults to window.localStorage) so the helpers are
// unit-testable in a plain node environment with a fake store.

import type { Bubble } from "./transcript";

const PREFIX = "tutor.transcript.";
export const MAX_BUBBLES = 200;

function keyFor(clientId: string): string {
  return PREFIX + clientId;
}

function isBubble(x: unknown): x is Bubble {
  if (!x || typeof x !== "object") return false;
  const b = x as Record<string, unknown>;
  return (
    typeof b.id === "string" &&
    (b.speaker === "user" || b.speaker === "tutor") &&
    (b.lang === "vi" || b.lang === "en") &&
    typeof b.text === "string"
  );
}

export function loadBubbles(
  clientId: string,
  store: Storage = localStorage,
): Bubble[] {
  try {
    const raw = store.getItem(keyFor(clientId));
    if (!raw) return [];
    const arr: unknown = JSON.parse(raw);
    return Array.isArray(arr) ? arr.filter(isBubble) : [];
  } catch {
    return [];
  }
}

export function saveBubbles(
  clientId: string,
  bubbles: Bubble[],
  store: Storage = localStorage,
): void {
  try {
    const trimmed =
      bubbles.length > MAX_BUBBLES ? bubbles.slice(-MAX_BUBBLES) : bubbles;
    store.setItem(keyFor(clientId), JSON.stringify(trimmed));
  } catch {
    /* quota / serialization failure → drop persistence, keep the session live */
  }
}

export function clearBubbles(
  clientId: string,
  store: Storage = localStorage,
): void {
  try {
    store.removeItem(keyFor(clientId));
  } catch {
    /* ignore */
  }
}
