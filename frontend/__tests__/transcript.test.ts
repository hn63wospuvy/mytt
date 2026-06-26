import { describe, it, expect } from "vitest";
import { reduce, initialState, type Event, type TranscriptState } from "../src/transcript";

function run(events: Event[]): TranscriptState {
  return events.reduce((s, ev) => reduce(s, ev), initialState);
}

function userTexts(state: TranscriptState): string[] {
  return state.bubbles.filter((b) => b.speaker === "user").map((b) => b.text);
}

function tutorTexts(state: TranscriptState): string[] {
  return state.bubbles.filter((b) => b.speaker === "tutor").map((b) => b.text);
}

describe("transcript dedup reducer — 7 spec cases", () => {
  // 1: trailing-fragment collapse (bubble still open)
  it("case 1: trailing fragment within window collapses into one bubble", () => {
    const s = run([
      { kind: "user", text: "ok let's go", now: 0 },
      { kind: "user", text: "go", now: 1000 },
    ]);
    expect(userTexts(s)).toEqual(["ok let's go"]);
  });

  // 2: tutor between → turn closed → fragment suppressed (no new, no mutate)
  it("case 2: fragment after tutor reply is suppressed", () => {
    const s = run([
      { kind: "user", text: "ok let's go", now: 0 },
      { kind: "tutor", segId: "t1", text: "Sure", now: 1000 },
      { kind: "user", text: "go", now: 2000 },
    ]);
    expect(userTexts(s)).toEqual(["ok let's go"]);
  });

  // 3: growing segments collapse into one bubble holding the longest
  it("case 3: growing segments collapse to the longest", () => {
    const s = run([
      { kind: "user", text: "ok", now: 0 },
      { kind: "user", text: "ok let's", now: 200 },
      { kind: "user", text: "ok let's go", now: 400 },
      { kind: "user", text: "go", now: 600 },
    ]);
    expect(userTexts(s)).toEqual(["ok let's go"]);
  });

  // 4: distinct (non-substring) → two turns
  it("case 4: distinct messages produce two bubbles", () => {
    const s = run([
      { kind: "user", text: "hello", now: 0 },
      { kind: "user", text: "how are you", now: 1000 },
    ]);
    expect(userTexts(s)).toEqual(["hello", "how are you"]);
  });

  // 5: echo-back within window, no tutor → one bubble
  it("case 5: identical echo within window stays one bubble", () => {
    const s = run([
      { kind: "user", text: "hi", now: 0 },
      { kind: "user", text: "hi", now: 1000 },
    ]);
    expect(userTexts(s)).toEqual(["hi"]);
  });

  // 6: echo-back within window WITH tutor between → still one bubble
  it("case 6: identical echo after tutor reply stays one bubble", () => {
    const s = run([
      { kind: "user", text: "hi", now: 0 },
      { kind: "tutor", segId: "t1", text: "Hello!", now: 1000 },
      { kind: "user", text: "hi", now: 2000 },
    ]);
    expect(userTexts(s)).toEqual(["hi"]);
  });

  // 7: window expiry re-opens a new turn
  it("case 7: identical text past the 15s window opens a new bubble", () => {
    const s = run([
      { kind: "user", text: "hi", now: 0 },
      { kind: "user", text: "hi", now: 16000 },
    ]);
    expect(userTexts(s)).toEqual(["hi", "hi"]);
  });
});

// LOCAL backend profile: tutor lines arrive item-level over the data channel
// with NO native segment id. useRoom synthesizes a UNIQUE segId per line
// (`dc-${n++}`), so each whole line must become its own bubble — never merged.
describe("data-channel tutor path (LOCAL profile)", () => {
  it("distinct synthetic segIds keep each tutor line as its own bubble", () => {
    const s = run([
      { kind: "tutor", segId: "dc-0", text: "Xin chào!", lang: "vi", now: 0 },
      { kind: "tutor", segId: "dc-1", text: "How are you?", lang: "en", now: 100 },
    ]);
    expect(tutorTexts(s)).toEqual(["Xin chào!", "How are you?"]);
    expect(s.bubbles.find((b) => b.id === "seg:dc-0")?.lang).toBe("vi");
    expect(s.bubbles.find((b) => b.id === "seg:dc-1")?.lang).toBe("en");
  });

  it("explicit lang from the data channel overrides guessLang", () => {
    // "hello" has no Vietnamese chars → guessLang would say "en"; explicit wins.
    const s = run([
      { kind: "tutor", segId: "dc-0", text: "hello", lang: "vi", now: 0 },
    ]);
    expect(s.bubbles[0].lang).toBe("vi");
  });
});
