// Left config pane: profile + mode badges, Gemini key field + Lưu, thinking
// number, Kết nối / Ngắt. Each labelled control is wrapped in a Tooltip with a
// Vietnamese hint.

import { useState } from "react";
import { Tooltip } from "./Tooltip";
import { Badge } from "./Badge";
import type { ConnState, Mode, Profile } from "../hooks/useRoom";

export function ConfigPane({
  profile,
  mode,
  conn,
  status,
  isError,
  hasKey,
  thinking,
  onThinkingChange,
  onSaveKey,
  onConnect,
  onDisconnect,
  onNewSession,
}: {
  profile: Profile;
  mode: Mode;
  conn: ConnState;
  status: string;
  isError: boolean;
  hasKey: boolean;
  thinking: string;
  onThinkingChange: (v: string) => void;
  onSaveKey: (key: string) => Promise<void>;
  onConnect: () => void;
  onDisconnect: () => void;
  onNewSession: () => void;
}) {
  const [keyInput, setKeyInput] = useState("");
  const [keyStatus, setKeyStatus] = useState("");
  const [saving, setSaving] = useState(false);

  const connected = conn === "connected";
  const connecting = conn === "connecting";

  async function handleSave() {
    const key = keyInput.trim();
    if (!key) {
      setKeyStatus("Nhập key trước.");
      return;
    }
    setSaving(true);
    setKeyStatus("Đang lưu…");
    try {
      await onSaveKey(key);
      setKeyInput("");
      setKeyStatus("Đã lưu ✓");
    } catch (e) {
      setKeyStatus("Lỗi: " + (e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const profileBadge =
    profile === "cloud" ? (
      <Badge tone="cloud" title="Gemini Live trên cloud">
        ☁️ cloud
      </Badge>
    ) : profile === "local" ? (
      <Badge tone="local" title="Mô hình chạy trên máy">
        💻 local
      </Badge>
    ) : (
      <Badge title="cloud (Gemini Live) hay local">chế độ —</Badge>
    );

  const modeBadge =
    mode === "voice" ? (
      <Badge tone="voice">🎙 voice</Badge>
    ) : (
      <Badge tone="chat">💬 chat</Badge>
    );

  return (
    <aside className="config-pane">
      <h2 className="pane-title">Cấu hình</h2>

      <div className="config-badges">
        {profileBadge}
        {modeBadge}
      </div>

      <div className="field">
        <Tooltip hint="Dán Gemini API key của bạn. Key chỉ lưu trên trình duyệt của bạn (localStorage) — máy chủ không lưu. Lấy miễn phí tại aistudio.google.com/apikey.">
          <label htmlFor="apikey">
            Gemini API key {hasKey ? "(đã có — cập nhật)" : "(bắt buộc)"}
          </label>
        </Tooltip>
        <div className="field-row">
          <input
            id="apikey"
            type="text"
            placeholder="AIza…"
            autoComplete="off"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            className={!hasKey ? "input required" : "input"}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            Lưu
          </button>
        </div>
        <p className="field-hint">
          Lấy key miễn phí tại{" "}
          <a
            href="https://aistudio.google.com/apikey"
            target="_blank"
            rel="noopener noreferrer"
          >
            aistudio.google.com/apikey
          </a>
        </p>
        {keyStatus && <p className="field-hint">{keyStatus}</p>}
      </div>

      <div className="field">
        <Tooltip hint="0 = nhanh nhất · số dương = suy nghĩ kỹ hơn · -1 = mặc định (chỉ áp dụng cho cloud).">
          <label htmlFor="thinking">Thinking (cloud)</label>
        </Tooltip>
        <input
          id="thinking"
          type="number"
          step={1}
          min={-1}
          value={thinking}
          disabled={connected || connecting}
          onChange={(e) => onThinkingChange(e.target.value)}
          className="input thinking-input"
        />
      </div>

      <div className="config-actions">
        <Tooltip hint="Kết nối vào phiên học (cần có Gemini key).">
          <button
            type="button"
            className="btn btn-primary"
            onClick={onConnect}
            disabled={!hasKey || connected || connecting}
          >
            {connecting ? "Đang kết nối…" : "Kết nối"}
          </button>
        </Tooltip>
        <Tooltip hint="Ngắt kết nối và kết thúc phiên học.">
          <button
            type="button"
            className="btn btn-danger"
            onClick={onDisconnect}
            disabled={!connected}
          >
            Ngắt
          </button>
        </Tooltip>
        <Tooltip hint="Xoá lịch sử hội thoại đang hiển thị (và bản lưu trên trình duyệt).">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onNewSession}
            disabled={connecting}
          >
            Phiên mới
          </button>
        </Tooltip>
      </div>

      <p className={isError ? "config-status err" : "config-status"}>{status}</p>
    </aside>
  );
}
