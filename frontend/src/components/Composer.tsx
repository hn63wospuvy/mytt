// Composer docked at the bottom of the session: mic toggle + chat input + Gửi.
// Disabled until connected.

import { useState } from "react";
import type { Mode } from "../hooks/useRoom";

export function Composer({
  connected,
  mode,
  micOn,
  onToggleMic,
  onSend,
}: {
  connected: boolean;
  mode: Mode;
  micOn: boolean;
  onToggleMic: () => void;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");

  function submit() {
    const t = text.trim();
    if (!t) return;
    setText("");
    onSend(t);
  }

  // Chat input is the active input path in chat mode; usable any time the room
  // is connected (tutor speaks in chat mode too).
  return (
    <div className="composer">
      <button
        type="button"
        className={micOn ? "btn btn-mic on" : "btn btn-mic"}
        onClick={onToggleMic}
        disabled={!connected}
        title={micOn ? "Tắt micro (chuyển sang chat)" : "Bật micro (luyện nói)"}
      >
        {micOn ? "🎙 Tắt mic" : "🎙 Bật mic"}
      </button>
      <input
        type="text"
        className="input composer-input"
        placeholder={
          mode === "chat" ? "Nhập tin nhắn…" : "Tắt mic để nhập tin nhắn…"
        }
        value={text}
        disabled={!connected}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          // Ignore Enter while an IME composition is in progress (Vietnamese
          // input commits via Enter) so we don't send a half-composed word.
          if (e.nativeEvent.isComposing) return;
          if (e.key === "Enter") submit();
        }}
      />
      <button
        type="button"
        className="btn btn-primary"
        onClick={submit}
        disabled={!connected}
      >
        Gửi
      </button>
    </div>
  );
}
