// Pure transcript dedup reducer — ported from backend/web/index.html
// (renderUserText / endUserTurn / onTranscription, ~lines 217-252).
//
// The DOM version mutated live <div> nodes and called Date.now() internally.
// This port replaces nodes with stable ids and INJECTS the clock (ev.now), so
// the 15s-window behaviour is deterministically unit-testable.

export type Speaker = "user" | "tutor";
export type Lang = "vi" | "en";

export interface Bubble {
  id: string;
  speaker: Speaker;
  lang: Lang;
  text: string;
}

export interface TranscriptState {
  bubbles: Bubble[]; // ordered render list (replaces DOM child order)
  lastUserText: string; // last user text seen (turn memory)
  lastUserAt: number; // ms timestamp of lastUserText (injected clock)
  activeUserBubbleId: string | null; // current open user turn; null after a tutor line
  tutorSeg: Record<string, string>; // tutor segment id → bubble id (replaces streamEls)
  _seq: number; // monotonic counter for stable bubble ids
}

export type Event =
  | { kind: "user"; text: string; now: number }
  | { kind: "tutor"; segId: string; text: string; lang?: Lang; now: number }
  | { kind: "tutor-clear"; now: number };

export const initialState: TranscriptState = {
  bubbles: [],
  lastUserText: "",
  lastUserAt: 0,
  activeUserBubbleId: null,
  tutorSeg: {},
  _seq: 0,
};

// Seed a fresh state from persisted bubbles (restored from localStorage on
// load). Turn memory is intentionally reset so dedup never compares new input
// against stale prior-session text; tutorSeg is left empty because segment ids
// belong to a finished room and won't recur. _seq starts past the restored
// count so new user-bubble ids stay unique.
export function restoredState(bubbles: Bubble[]): TranscriptState {
  return { ...initialState, bubbles: [...bubbles], _seq: bubbles.length };
}

// The existing VI_CHARS regex (index.html:180-181).
const VI_CHARS =
  /[ăâđêôơưàáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]/i;

export function guessLang(text: string): Lang {
  return VI_CHARS.test(text || "") ? "vi" : "en";
}

const WINDOW_MS = 15000;

export function reduce(state: TranscriptState, ev: Event): TranscriptState {
  switch (ev.kind) {
    case "tutor-clear":
      // matches clearTranscript(): reset bubbles + turn memory.
      return { ...initialState };

    case "tutor": {
      // upsert by segId (streamEls behavior); explicit lang wins, else guessLang.
      const lang = ev.lang ?? guessLang(ev.text);
      const existingId = state.tutorSeg[ev.segId];

      let bubbles: Bubble[];
      const tutorSeg = state.tutorSeg;
      let nextTutorSeg = tutorSeg;
      let seq = state._seq;

      if (existingId) {
        // replace that bubble's text/lang in place (new array, no mutation)
        bubbles = state.bubbles.map((b) =>
          b.id === existingId ? { ...b, text: ev.text, lang } : b,
        );
      } else {
        const id = `seg:${ev.segId}`;
        bubbles = [...state.bubbles, { id, speaker: "tutor", lang, text: ev.text }];
        nextTutorSeg = { ...tutorSeg, [ev.segId]: id };
        seq = state._seq; // tutor ids are seg-derived; counter untouched
      }

      // A tutor event ends the active user turn (turn memory preserved).
      return {
        ...state,
        bubbles,
        tutorSeg: nextTutorSeg,
        activeUserBubbleId: null,
        _seq: seq,
      };
    }

    case "user": {
      const text = (ev.text || "").trim();
      if (!text) return state; // empty → no-op

      const now = ev.now;

      // In-window dedup branch (index.html:231-239): same turn — a late
      // echo-back / growing fragment ("go" for "ok let's go").
      if (
        state.lastUserText &&
        now - state.lastUserAt < WINDOW_MS &&
        (state.lastUserText.includes(text) || text.includes(state.lastUserText))
      ) {
        // Always bump turn memory to the longer text, sliding the window.
        const longer =
          text.length > state.lastUserText.length ? text : state.lastUserText;

        if (state.activeUserBubbleId !== null) {
          // Bubble open → grow it to the longer text (index.html:233-235).
          const activeId = state.activeUserBubbleId;
          const active = state.bubbles.find((b) => b.id === activeId);
          let bubbles = state.bubbles;
          if (active && text.length > active.text.length) {
            bubbles = state.bubbles.map((b) =>
              b.id === activeId
                ? { ...b, text, lang: guessLang(text) }
                : b,
            );
          }
          return { ...state, bubbles, lastUserText: longer, lastUserAt: now };
        }

        // No active bubble (a tutor line closed the turn): SUPPRESS a new
        // bubble and do NOT mutate the prior one — only turn memory updates.
        return { ...state, lastUserText: longer, lastUserAt: now };
      }

      // No in-window match → start a new user turn.
      const seq = state._seq + 1;
      const id = `user:${seq}`;
      const bubbles: Bubble[] = [
        ...state.bubbles,
        { id, speaker: "user", lang: guessLang(text), text },
      ];
      return {
        ...state,
        bubbles,
        activeUserBubbleId: id,
        lastUserText: text,
        lastUserAt: now,
        _seq: seq,
      };
    }
  }
}
