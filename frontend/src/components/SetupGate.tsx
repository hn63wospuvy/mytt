// Full-screen setup card: the user types a name + Gemini API key, both saved to
// localStorage. No login — the app is fully stateless.

import { useState } from "react";

export function SetupGate({
  onSave,
}: {
  onSave: (name: string, key: string) => void;
}) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [err, setErr] = useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const n = name.trim();
    const k = key.trim();
    if (!n) {
      setErr("Nhập tên trước.");
      return;
    }
    if (!k) {
      setErr("Nhập Gemini API key trước.");
      return;
    }
    onSave(n, k);
  }

  return (
    <div className="login-gate">
      <form className="card login-card" onSubmit={submit}>
        <h1 className="login-title">🎓 Gia sư</h1>
        <p className="login-sub">
          Nhập tên và Gemini API key của bạn để bắt đầu luyện nói và chat. Mọi
          thứ lưu trên trình duyệt của bạn — máy chủ không lưu gì.
        </p>

        <div className="field">
          <label htmlFor="setup-name">Tên</label>
          <input
            id="setup-name"
            type="text"
            className="input"
            placeholder="Tên của bạn"
            autoComplete="off"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="setup-key">Gemini API key</label>
          <input
            id="setup-key"
            type="password"
            className="input"
            placeholder="AIza…"
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
          <p className="field-hint">
            Lấy miễn phí tại{" "}
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noopener noreferrer"
            >
              aistudio.google.com/apikey
            </a>
          </p>
        </div>

        <button type="submit" className="btn btn-primary">
          Bắt đầu
        </button>

        {err && <p className="login-error">{err}</p>}
      </form>
    </div>
  );
}
