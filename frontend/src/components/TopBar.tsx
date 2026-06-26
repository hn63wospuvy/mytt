// Top bar: app title · "Xin chào, <tên>" · ☰ collapse toggle · Đổi tên/key.

export function TopBar({
  name,
  collapsed,
  onToggleCollapse,
  onLogout,
}: {
  name: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onLogout: () => void;
}) {
  return (
    <header className="topbar">
      <span className="topbar-title">🎓 Gia sư</span>
      <span className="topbar-greeting">Xin chào, {name}</span>
      <div className="topbar-actions">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={onToggleCollapse}
          title={collapsed ? "Hiện cấu hình" : "Ẩn cấu hình"}
          aria-label={collapsed ? "Hiện cấu hình" : "Ẩn cấu hình"}
        >
          ☰ {collapsed ? "Hiện cấu hình" : "Ẩn cấu hình"}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={onLogout}
          title="Quên tên + key trên trình duyệt này"
        >
          Đổi tên/key
        </button>
      </div>
    </header>
  );
}
