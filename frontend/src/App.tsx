// Setup-gate (name + key) vs MainApp routing + left-pane collapse state. Wires
// useLocalProfile and useRoom together. No login, no network auth.

import { useCallback, useState } from "react";
import { KEY_KEY } from "./api";
import { useLocalProfile } from "./hooks/useLocalProfile";
import { useRoom } from "./hooks/useRoom";
import { SetupGate } from "./components/SetupGate";
import { TopBar } from "./components/TopBar";
import { ConfigPane } from "./components/ConfigPane";
import { SessionPane } from "./components/SessionPane";

export function App() {
  const profile = useLocalProfile();

  if (!profile.hasProfile) {
    return <SetupGate onSave={profile.saveProfile} />;
  }

  return <MainApp profile={profile} />;
}

function MainApp({ profile }: { profile: ReturnType<typeof useLocalProfile> }) {
  const [collapsed, setCollapsed] = useState(false);
  const [thinking, setThinking] = useState("1");
  // Revealed when the key is rejected mid-session (no_key); the config pane
  // gates Connect until a fresh key is saved.
  const [keyRevealed, setKeyRevealed] = useState(false);

  // Read the key fresh from localStorage so connect never closes over a stale
  // value; useLocalProfile.saveKey keeps localStorage in sync.
  const getKey = useCallback(() => localStorage.getItem(KEY_KEY) ?? "", []);

  const room = useRoom(
    { clientId: profile.clientId, getKey },
    { onNoKey: () => setKeyRevealed(true) },
  );

  const handleSaveKey = useCallback(
    async (key: string) => {
      profile.saveKey(key);
      setKeyRevealed(false);
    },
    [profile],
  );

  const hasKey = profile.hasKey && !keyRevealed;

  return (
    <div className="app">
      <TopBar
        name={profile.name || "Bạn"}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        onLogout={profile.clear}
      />
      <main className={collapsed ? "panes collapsed" : "panes"}>
        {!collapsed && (
          <ConfigPane
            profile={room.profile}
            mode={room.mode}
            conn={room.conn}
            status={room.status}
            isError={room.isError}
            hasKey={hasKey}
            thinking={thinking}
            onThinkingChange={setThinking}
            onSaveKey={handleSaveKey}
            onConnect={() => void room.connect(thinking)}
            onDisconnect={() => void room.disconnect()}
            onNewSession={room.clearTranscript}
          />
        )}
        <SessionPane
          bubbles={room.transcript.bubbles}
          connected={room.conn === "connected"}
          mode={room.mode}
          micOn={room.micOn}
          onToggleMic={() => void room.toggleMic()}
          onSend={(t) => void room.sendChat(t)}
        />
      </main>
    </div>
  );
}
