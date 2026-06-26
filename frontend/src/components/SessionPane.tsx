// Right session pane: scrollable Transcript + Composer docked at the bottom.

import { Transcript } from "./Transcript";
import { Composer } from "./Composer";
import type { Bubble } from "../transcript";
import type { Mode } from "../hooks/useRoom";

export function SessionPane({
  bubbles,
  connected,
  mode,
  micOn,
  onToggleMic,
  onSend,
}: {
  bubbles: Bubble[];
  connected: boolean;
  mode: Mode;
  micOn: boolean;
  onToggleMic: () => void;
  onSend: (text: string) => void;
}) {
  return (
    <section className="session-pane">
      <h2 className="pane-title">Phiên học</h2>
      <Transcript bubbles={bubbles} />
      <Composer
        connected={connected}
        mode={mode}
        micOn={micOn}
        onToggleMic={onToggleMic}
        onSend={onSend}
      />
    </section>
  );
}
