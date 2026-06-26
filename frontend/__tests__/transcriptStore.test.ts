import { describe, it, expect } from "vitest";
import type { Bubble } from "../src/transcript";
import { restoredState } from "../src/transcript";
import {
  MAX_BUBBLES,
  clearBubbles,
  loadBubbles,
  saveBubbles,
} from "../src/transcriptStore";

// Minimal in-memory Storage stand-in (vitest runs in node — no real localStorage).
function fakeStore(): Storage {
  const m = new Map<string, string>();
  return {
    get length() {
      return m.size;
    },
    clear: () => m.clear(),
    getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
    key: (i: number) => Array.from(m.keys())[i] ?? null,
    removeItem: (k: string) => void m.delete(k),
    setItem: (k: string, v: string) => void m.set(k, v),
  } as Storage;
}

const bubble = (id: string, text: string): Bubble => ({
  id,
  speaker: "user",
  lang: "en",
  text,
});

describe("transcriptStore — localStorage persistence", () => {
  it("round-trips bubbles keyed by client id", () => {
    const s = fakeStore();
    const bubbles = [bubble("user:1", "hello"), bubble("user:2", "world")];
    saveBubbles("c1", bubbles, s);
    expect(loadBubbles("c1", s)).toEqual(bubbles);
  });

  it("isolates by client id", () => {
    const s = fakeStore();
    saveBubbles("c1", [bubble("user:1", "a")], s);
    expect(loadBubbles("c2", s)).toEqual([]);
  });

  it("returns [] for absent / corrupt / non-bubble data", () => {
    const s = fakeStore();
    expect(loadBubbles("missing", s)).toEqual([]);
    s.setItem("tutor.transcript.bad", "not json");
    expect(loadBubbles("bad", s)).toEqual([]);
    s.setItem("tutor.transcript.obj", JSON.stringify({ not: "array" }));
    expect(loadBubbles("obj", s)).toEqual([]);
    // array with junk entries → junk filtered out
    s.setItem(
      "tutor.transcript.mixed",
      JSON.stringify([bubble("user:1", "ok"), { id: 5 }, null]),
    );
    expect(loadBubbles("mixed", s)).toEqual([bubble("user:1", "ok")]);
  });

  it("bounds stored bubbles to the last MAX_BUBBLES", () => {
    const s = fakeStore();
    const many = Array.from({ length: MAX_BUBBLES + 50 }, (_, i) =>
      bubble(`user:${i}`, `m${i}`),
    );
    saveBubbles("c1", many, s);
    const loaded = loadBubbles("c1", s);
    expect(loaded).toHaveLength(MAX_BUBBLES);
    expect(loaded[0].text).toBe(`m50`); // oldest 50 dropped
    expect(loaded[loaded.length - 1].text).toBe(`m${MAX_BUBBLES + 49}`);
  });

  it("clears persisted bubbles", () => {
    const s = fakeStore();
    saveBubbles("c1", [bubble("user:1", "a")], s);
    clearBubbles("c1", s);
    expect(loadBubbles("c1", s)).toEqual([]);
  });
});

describe("restoredState — seed reducer from persisted bubbles", () => {
  it("seeds the render list and advances _seq, resets turn memory", () => {
    const bubbles = [bubble("user:1", "hi"), bubble("user:2", "there")];
    const st = restoredState(bubbles);
    expect(st.bubbles).toEqual(bubbles);
    expect(st._seq).toBe(2);
    expect(st.lastUserText).toBe("");
    expect(st.activeUserBubbleId).toBeNull();
    expect(st.tutorSeg).toEqual({});
  });

  it("empty restore equals a fresh state", () => {
    const st = restoredState([]);
    expect(st.bubbles).toEqual([]);
    expect(st._seq).toBe(0);
  });
});
