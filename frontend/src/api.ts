// Stateless token-server client. No auth, no /me, no /apikey.
//
// The browser owns identity: a name + Gemini key + a random client_id all live
// in localStorage. /token is the only call — it mints a LiveKit join token and
// carries the key (per connect) in the room metadata. Nothing is stored server
// side.

export const NAME_KEY = "tutor.name";
export const KEY_KEY = "tutor.key";
export const CLIENT_ID_KEY = "tutor.clientId";

export interface TokenInfo {
  url: string;
  token: string;
  room: string;
  identity: string;
}

/** Thrown on 400 {error:"no_key"} from /token (no Gemini key supplied). */
export class NoKeyError extends Error {
  constructor() {
    super("no_key");
    this.name = "NoKeyError";
  }
}

/** The browser's stable client id; minted once and persisted in localStorage. */
export function getClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

/**
 * POST /token {client_id, key, thinking?}. The key rides to the agent in the
 * room metadata and is never persisted server-side. 400 no_key → NoKeyError.
 */
export async function getToken(
  key: string,
  clientId: string,
  thinking: string,
): Promise<TokenInfo> {
  const body: Record<string, string> = { client_id: clientId, key };
  if (thinking !== "") body.thinking = thinking;
  const r = await fetch("/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 400) {
    const e = (await r.json().catch(() => ({}))) as { error?: string };
    if (e.error === "no_key") throw new NoKeyError();
    throw new Error("token server trả 400: " + (e.error ?? "bad_request"));
  }
  if (!r.ok) throw new Error("token server trả " + r.status);
  return r.json();
}
