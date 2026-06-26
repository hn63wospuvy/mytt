# Tutor backend — Phase 1 (LOCAL)

LiveKit voice agent: Vietnamese-English tutor with **giảng / luyện / hỏi-đáp**
modes (spec §1, §7). STT (Nemotron) · LLM (Qwen3-8B) · TTS (VieNeu) on the Mac,
plus a web-search tool, learning store (SQLite) and a token server.

See `../docs/spec_tro_ly_tieng_anh (1).md` and
`../docs/superpowers/specs/2026-06-17-tutor-phase1-local-design.md`.

## Layout

```
src/tutor_agent/
  config.py            env → typed Settings (§13)
  bilingual.py         <vi>/<en> tag parse, strip, mode (§7.1/§7.2)
  text_pipeline.py     clean tags/markers before TTS
  tutor.py             Agent + system prompt (§7.3), tts cleaning
  agent.py             AgentServer entrypoint (wires everything)
  wiring.py            session events → persist + data channel
  data_channel.py      transcript/mode/profile to the app (§9.4)
  tools.py             web_search function tool (§8)
  stt/ tts/ llm/       real adapters + deterministic mocks
  search/              tavily / brave / searxng + mock + grounding
  storage/             SQLite schema, repository, marker extract, recorder (§12)
  history.py           read API for past sessions (§9.2) — aiohttp on :8090
  token_server/        short-lived LiveKit tokens — secret only here (§11)
  eval/wer.py          word error rate for the STT benchmark (§15.1)
tests/                 pure-logic + integration (mock loop, no models)
scripts/               on-device benchmarks: bench_wer.py, bench_latency.py
```

## Setup

```bash
uv venv --python 3.12
uv pip install -e '.[livekit,http,dev]'   # add 'models' on the Mac that serves models
# add 'cloud' for the Phase-3 Gemini Live profile: '.[livekit,http,cloud,dev]'
cp .env.example .env                       # then edit
```

## Test (no models, no network)

```bash
.venv/bin/python -m pytest -q
```

The whole suite runs on mock adapters — no model downloads, no LiveKit room.

## Run

```bash
MOCK_ADAPTERS=1 ./start.sh    # loop with mocks (smoke the transport end-to-end)
./start.sh                    # LOCAL: needs STT:8000, LLM:8080, TTS:8001 up
PROFILE=cloud GEMINI_API_KEY=... ./start.sh   # CLOUD (Phase 3): Gemini Live realtime
```

### Profiles (spec §2/§3 hybrid)

- **LOCAL** (`PROFILE=local`) — Nemotron + Qwen3 + VieNeu pipeline, tag-based
  bilingual transcript + learning data, self-assembled web_search.
- **CLOUD** (`PROFILE=cloud`, Phase 3) — Gemini Live realtime block
  (STT+LLM+TTS + Google Search grounding). Tag-free natural speech (the model
  speaks server-side, so inline tags can't be stripped); the framework forwards
  transcripts. Learning-data extraction is reduced (no `<fix>`/`<vocab>` markers)
  — a documented Phase-3 trade-off. `session_factory.build_session` picks the
  profile; the rest of the agent is shared.

`start.sh` boots livekit-server (dev) → token server → probes model servers →
starts the agent. The app fetches a token from `:8080/token?identity=<id>&room=<room>`.

## On-device verification (the user's part, design §"testing")

The live voice loop, latency tuning, and Vietnamese WER (spec §15.1–15.3) are
verified on real hardware once the model servers run. Mocks prove the wiring;
they don't prove audio quality. Tooling:

```bash
# §15.1 — STT WER over a folder of <name>.wav + <name>.txt pairs
python scripts/bench_wer.py audio_dir/ --stt-base-url http://localhost:8000/v1
# §15.2 — component latencies (LLM first token, TTS first byte, STT round-trip)
python scripts/bench_latency.py --wav sample.wav
```
