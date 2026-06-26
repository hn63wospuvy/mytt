// Browser-local profile: name + Gemini key + a stable client_id, all in
// localStorage. No network, no GIS, no /me — replaces the old useAuth hook.
//
// - name + key are what the user types on the setup card.
// - client_id is minted once (api.getClientId) and reused as the LiveKit
//   identity / room seed so each browser gets its own isolated session.

import { useCallback, useMemo, useState } from "react";
import { KEY_KEY, NAME_KEY, getClientId } from "../api";

export interface ProfileState {
  name: string;
  apiKey: string;
  clientId: string;
  /** Setup complete: both a name and a key are present. */
  hasProfile: boolean;
  /** A Gemini key is stored. */
  hasKey: boolean;
  /** Save the full profile (setup card). */
  saveProfile: (name: string, key: string) => void;
  /** Update just the key (config pane). */
  saveKey: (key: string) => void;
  /** Forget name + key (return to setup). client_id is kept. */
  clear: () => void;
}

export function useLocalProfile(): ProfileState {
  const [name, setName] = useState<string>(
    () => localStorage.getItem(NAME_KEY) ?? "",
  );
  const [apiKey, setApiKey] = useState<string>(
    () => localStorage.getItem(KEY_KEY) ?? "",
  );
  // Stable for the life of the browser; minted on first read.
  const clientId = useMemo(() => getClientId(), []);

  const saveProfile = useCallback((n: string, k: string) => {
    const name = n.trim();
    const key = k.trim();
    localStorage.setItem(NAME_KEY, name);
    localStorage.setItem(KEY_KEY, key);
    setName(name);
    setApiKey(key);
  }, []);

  const saveKey = useCallback((k: string) => {
    const key = k.trim();
    localStorage.setItem(KEY_KEY, key);
    setApiKey(key);
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem(NAME_KEY);
    localStorage.removeItem(KEY_KEY);
    setName("");
    setApiKey("");
  }, []);

  return {
    name,
    apiKey,
    clientId,
    hasProfile: !!name && !!apiKey,
    hasKey: !!apiKey,
    saveProfile,
    saveKey,
    clear,
  };
}
