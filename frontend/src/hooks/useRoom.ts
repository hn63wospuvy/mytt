// LiveKit session hook. Sole owner of connection lifecycle, mic/mode, chat
// send, and event wiring → transcript reducer. Ports connect/toggleMic/
// sendChat/teardown/onData/onTranscription (backend/web/index.html:334-445).
//
// Locked behaviours:
// - Status progression (Vietnamese): "Đang lấy token…" → "Đang kết nối…" → connected.
// - 412 no_key → reveal key requirement (onNoKey).
// - mic permission denied at connect → fall back to chat mode (still connected).
// - Disconnected → teardown, reset mic/mode to chat, NO auto-reconnect.
// - mid-session {error,no_key} over data channel → teardown + reveal key.

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import {
  Room,
  RoomEvent,
  type RemoteTrack,
  type RemoteParticipant,
  type Participant,
  type TranscriptionSegment,
  type DataPacket_Kind,
} from "livekit-client";
import { getToken, NoKeyError, type TokenInfo } from "../api";
import {
  reduce,
  restoredState,
  type Lang,
  type TranscriptState,
} from "../transcript";
import { clearBubbles, loadBubbles, saveBubbles } from "../transcriptStore";

export type Mode = "voice" | "chat";
export type Profile = "cloud" | "local" | null;
export type ConnState = "idle" | "connecting" | "connected";

export interface RoomCallbacks {
  /** 400 no_key on /token, or mid-session no_key → caller reveals key field. */
  onNoKey: () => void;
}

export interface RoomOpts {
  /** Browser identity / room seed (stable per browser). */
  clientId: string;
  /** Reads the current Gemini key (fresh, from localStorage-backed state). */
  getKey: () => string;
}

export interface RoomApi {
  conn: ConnState;
  mode: Mode;
  profile: Profile;
  status: string;
  isError: boolean;
  transcript: TranscriptState;
  micOn: boolean;
  connect: (thinking: string) => Promise<void>;
  disconnect: () => Promise<void>;
  toggleMic: () => Promise<void>;
  sendChat: (text: string) => Promise<void>;
  /** Clear the on-screen transcript + its persisted history ("phiên mới"). */
  clearTranscript: () => void;
}

const transcriptReducer = (
  s: TranscriptState,
  ev: Parameters<typeof reduce>[1],
) => reduce(s, ev);

export function useRoom(opts: RoomOpts, cb: RoomCallbacks): RoomApi {
  const { clientId, getKey } = opts;
  const [conn, setConn] = useState<ConnState>("idle");
  const [mode, setMode] = useState<Mode>("chat");
  const [profile, setProfile] = useState<Profile>(null);
  const [status, setStatus] = useState("Chưa kết nối.");
  const [isError, setIsError] = useState(false);
  const [micOn, setMicOn] = useState(false);
  // Restore prior-session transcript from localStorage (history survives reload).
  const [transcript, dispatch] = useReducer(transcriptReducer, clientId, (cid) =>
    restoredState(loadBubbles(cid)),
  );

  // Mirror the transcript to localStorage on every change (bounded in the store).
  useEffect(() => {
    saveBubbles(clientId, transcript.bubbles);
  }, [clientId, transcript.bubbles]);

  const roomRef = useRef<Room | null>(null);
  const audioRef = useRef<HTMLDivElement | null>(null);
  // Monotonic counter → unique synthetic segId per data-channel transcript line
  // (local profile lines have no segment id; each must be its own bubble, never
  // upsert-merged). See onData transcript handling.
  const dcSegRef = useRef(0);
  // Single-owner teardown: a caller can stash an intended status here BEFORE the
  // room disconnects; the RoomEvent.Disconnected handler (sole teardown owner)
  // uses it instead of the generic disconnect string, then clears it.
  const teardownMsgRef = useRef<string | null>(null);
  // Keep callbacks fresh without re-subscribing room events.
  const cbRef = useRef(cb);
  cbRef.current = cb;

  const say = useCallback((msg: string, err = false) => {
    setStatus(msg);
    setIsError(err);
  }, []);

  // Unmount cleanup (e.g. logout mid-session): drop the LiveKit connection and
  // remove the hidden audio container appended to document.body.
  useEffect(() => {
    return () => {
      void roomRef.current?.disconnect();
      const c = audioRef.current;
      if (c && c.parentNode) c.parentNode.removeChild(c);
      audioRef.current = null;
    };
  }, []);

  // Lazily-created hidden container for attached audio tracks.
  const audioContainer = useCallback((): HTMLDivElement => {
    if (!audioRef.current) {
      const el = document.createElement("div");
      el.hidden = true;
      document.body.appendChild(el);
      audioRef.current = el;
    }
    return audioRef.current;
  }, []);

  const teardown = useCallback(
    (msg: string) => {
      const c = audioRef.current;
      if (c) c.innerHTML = "";
      roomRef.current = null;
      setConn("idle");
      setMode("chat");
      setProfile(null);
      setMicOn(false);
      // An intended status stashed by the caller (e.g. mid-session no_key) wins
      // over the generic disconnect string so its message + key requirement stay
      // visible instead of being clobbered.
      if (teardownMsgRef.current !== null) {
        const intended = teardownMsgRef.current;
        teardownMsgRef.current = null;
        say(intended, true);
      } else {
        say(msg);
      }
    },
    [say],
  );

  const onTrackSubscribed = useCallback(
    (track: RemoteTrack) => {
      if (track.kind !== "audio") return;
      const el = track.attach() as HTMLAudioElement;
      el.autoplay = true;
      audioContainer().appendChild(el);
    },
    [audioContainer],
  );

  const onTranscription = useCallback(
    (segments: TranscriptionSegment[], participant?: Participant) => {
      const isUser = !!participant && participant.isLocal;
      const now = Date.now();
      for (const seg of segments) {
        if (isUser) {
          dispatch({ kind: "user", text: seg.text, now });
        } else {
          dispatch({
            kind: "tutor",
            segId: seg.id,
            text: seg.text,
            lang: (seg.language as Lang) || undefined,
            now,
          });
        }
      }
    },
    [],
  );

  const onData = useCallback(
    (
      payload: Uint8Array,
      _participant?: RemoteParticipant,
      _kind?: DataPacket_Kind,
      topic?: string,
    ) => {
      if (topic !== "tutor") return;
      let msg: {
        type?: string;
        value?: string;
        code?: string;
        lang?: string;
        text?: string;
        speaker?: string;
      };
      try {
        msg = JSON.parse(new TextDecoder().decode(payload));
      } catch {
        return;
      }
      if (msg.type === "transcript") {
        // LOCAL backend profile path: transcription_enabled=False, so the agent
        // publishes each whole line here (cloud uses native TranscriptionReceived
        // instead). Item-level lines have NO segment id, so synthesize a unique
        // segId per line → each tutor line is its own bubble (never merged).
        const text = msg.text ?? "";
        const now = Date.now();
        if (msg.speaker === "user") {
          dispatch({ kind: "user", text, now });
        } else if (msg.speaker === "tutor") {
          const segId = `dc-${dcSegRef.current++}`;
          dispatch({
            kind: "tutor",
            segId,
            text,
            lang: (msg.lang as Lang) || undefined,
            now,
          });
        }
      } else if (msg.type === "profile") {
        setProfile((msg.value as Profile) ?? null);
      } else if (msg.type === "mode") {
        if (msg.value === "voice" || msg.value === "chat") setMode(msg.value);
      } else if (msg.type === "error" && msg.code === "no_key") {
        // mid-session no_key: the agent rejected the key (missing/invalid).
        // Stash the intended status, then disconnect and let the
        // RoomEvent.Disconnected handler (single teardown owner) apply it — this
        // avoids the generic "Đã ngắt kết nối." clobbering our message.
        teardownMsgRef.current = "Key Gemini không hợp lệ — kiểm tra lại key.";
        cbRef.current.onNoKey();
        void roomRef.current?.disconnect();
      }
    },
    [],
  );

  const connect = useCallback(
    async (thinking: string) => {
      const key = getKey().trim();
      if (!key) {
        say("Chưa có Gemini key — thêm key trước.", true);
        cbRef.current.onNoKey();
        return;
      }
      // Starting a new session clears the chat (on-screen + persisted). The
      // localStorage copy still lets a mid-session reload restore the transcript;
      // a fresh connect is a new session, so it resets.
      dispatch({ kind: "tutor-clear", now: Date.now() });
      clearBubbles(clientId);
      setConn("connecting");
      say("Đang lấy token…");

      let info: TokenInfo;
      try {
        info = await getToken(key, clientId, thinking.trim());
      } catch (e) {
        setConn("idle");
        if (e instanceof NoKeyError) {
          say("Chưa có Gemini key — thêm key trước.", true);
          cbRef.current.onNoKey();
        } else {
          say("Lấy token lỗi: " + (e as Error).message, true);
        }
        return;
      }

      const room = new Room({ adaptiveStream: true, dynacast: true });
      room
        .on(RoomEvent.TrackSubscribed, onTrackSubscribed)
        .on(RoomEvent.DataReceived, onData)
        .on(RoomEvent.TranscriptionReceived, onTranscription)
        .on(RoomEvent.Disconnected, () => teardown("Đã ngắt kết nối."));

      say("Đang kết nối…");
      try {
        await room.connect(info.url, info.token);
      } catch (e) {
        // Connect threw before the room was wired into roomRef → no Disconnected
        // event will fire to clean it up. Drop our listeners and the half-open
        // connection here so the Room can't leak.
        room.removeAllListeners();
        await room.disconnect().catch(() => {});
        setConn("idle");
        say("Kết nối lỗi: " + (e as Error).message, true);
        return;
      }

      roomRef.current = room;
      setConn("connected");
      say(`Đã kết nối room "${info.room}".`);

      // Enable mic → voice; deny → chat fallback (room stays connected).
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
        setMicOn(true);
        setMode("voice");
      } catch (e) {
        setMicOn(false);
        setMode("chat");
        say("Không có mic — chuyển sang chat: " + (e as Error).message);
      }
    },
    [clientId, getKey, say, onTrackSubscribed, onData, onTranscription, teardown],
  );

  const clearTranscript = useCallback(() => {
    dispatch({ kind: "tutor-clear", now: Date.now() });
    clearBubbles(clientId);
  }, [clientId]);

  const disconnect = useCallback(async () => {
    // The RoomEvent.Disconnected handler is the SINGLE owner of teardown; just
    // disconnect and let that event fire teardown (avoids double-teardown +
    // racing the status string).
    const room = roomRef.current;
    if (room) await room.disconnect();
  }, []);

  const toggleMic = useCallback(async () => {
    const room = roomRef.current;
    if (!room) return;
    const next = !micOn;
    try {
      await room.localParticipant.setMicrophoneEnabled(next);
      setMicOn(next);
      setMode(next ? "voice" : "chat"); // muted → chat mode
    } catch (e) {
      say("Đổi mic lỗi: " + (e as Error).message, true);
    }
  }, [micOn, say]);

  const sendChat = useCallback(async (text: string) => {
    const room = roomRef.current;
    if (!room) return;
    const t = text.trim();
    if (!t) return;
    // Local echo through the dedup reducer: a distinct typed message starts its
    // own bubble; a substring/superset within the 15s window is absorbed (so a
    // later spoken echo-back fragment does not double-render). Mirrors the
    // vanilla client's endUserTurn()+renderUserText() path.
    dispatch({ kind: "user", text: t, now: Date.now() });
    try {
      await room.localParticipant.sendText(t, { topic: "lk.chat" });
    } catch (e) {
      say("Gửi chat lỗi: " + (e as Error).message, true);
    }
  }, [say]);

  return {
    conn,
    mode,
    profile,
    status,
    isError,
    transcript,
    micOn,
    connect,
    disconnect,
    toggleMic,
    sendChat,
    clearTranscript,
  };
}
