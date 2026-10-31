# Hackathon packaging plan and roadmap audit

Date: 31 October 2026. Status: packaging started. Result limit raised from 5 to 20 in the same pass.

## 1. What changed today

- Search no longer caps at five songs. The app defaults to 20 results, with a
  Results selector for 5, 10, 20, or 50. The API accepts `top` from 1 to 50
  (`src/music_discovery/server.py`, `SearchIn`). There is no model-side limit:
  CLAP cosine search over the local index can rank every indexed track, and
  duplicate collapsing happens before the count, so 20 means 20 distinct songs.
  Blind packs still use top-5 on purpose, because Precision@5 is the metric.
- A first-run setup panel now exists in the app. On an empty index it asks for
  a music folder and indexes it in the background (`POST /api/setup/index`,
  progress via `GET /api/setup/status`). Before this, indexing was CLI-only
  and a fresh install opened on an empty library.
- The index location can move out of the install folder with the
  `MUSIC_DISCOVERY_DATA` environment variable (`src/music_discovery/config.py`).
  Default is unchanged, so the existing 1,548-track index is untouched.

## 2. How a judge installs it: the plan

Target: one file, double-click, no terminal, no dev server, no Node, no `uv run`.

### Phase 1: portable zip (buildable now, script in `packaging/`)

`packaging/build-release.ps1` builds the frontend once, then assembles
`release/MusicDiscovery-win64.zip`:

- Prebuilt `web/dist`. FastAPI serves it directly. No Vite dev server at runtime.
- `MusicDiscovery.bat` launcher: on first run it creates the app environment
  with the bundled `uv.exe`, installs pinned dependencies from `uv.lock`,
  and starts the local server on 127.0.0.1:8765, then opens the browser.
  Later runs skip straight to launch.
- The CLAP model is not in the zip. First search or first indexing downloads
  the pinned checkpoint `laion/larger_clap_music_and_speech` at revision
  `195c3a3e…` from Hugging Face into the normal HF cache. Measured on this
  machine: about 1.6 GB for that checkpoint family. The app already does this
  download through Transformers; packaging only needs to say so on screen.
- FFmpeg must travel with the app. Today `ffmpeg` and `ffprobe` are assumed
  to be on PATH (`src/music_discovery/embed.py`, `inventory.py`). The release
  script copies them in when it finds them; a release built without them is
  not shippable, and the script warns instead of staying silent.
- No music and no index ship in the zip. Judges point the setup panel at
  their own folder. John's library and index stay on this machine.

Measured sizes on this machine, 31 October 2026: Python environment with
CUDA torch 2.14.1 is 4.44 GB. That is the honest weight of the current stack
and the main packaging problem. See the Phase 2 decision.

### Phase 2: real installer (the one-click `.exe`)

- PyInstaller `--onedir` build producing `MusicDiscovery.exe`: Python server,
  prebuilt frontend, and FFmpeg in one folder. The exe starts the server and
  opens the browser. No console window to babysit.
- Inno Setup wraps that folder into `MusicDiscovery-Setup.exe` with a Start
  menu shortcut. Neither Inno Setup nor NSIS is installed on this machine
  yet, so this phase starts with installing Inno Setup.
- User data (index database, embeddings, votes) lives in
  `%LOCALAPPDATA%\MusicDiscovery` via `MUSIC_DISCOVERY_DATA`, set by the
  launcher, so reinstalling never wipes a judge's index.
- Model download stays on first run, with the setup panel showing progress.
  Bundling the model would add roughly 1.6 GB to the installer and freeze
  the checkpoint into the download; first-run download keeps the installer
  smaller and the checkpoint updatable. Tradeoff: first run needs internet.

Open decision for Phase 2, not made silently: torch build.

| Build | Installer size | Indexing speed | Risk |
|---|---|---|---|
| CUDA torch (current) | About 4 to 5 GB | Fast on NVIDIA GPUs, about 5.5 windows/s measured here | Useless weight on machines without NVIDIA |
| CPU torch | Roughly 1 GB class | Slower; fine for a small demo folder, slow for a full library | Works everywhere |

Recommendation: ship the CPU build as the public installer for reliability,
and keep the CUDA build as the power-user download. Decide before the
PyInstaller spec is written, because it changes what gets bundled.

### Phase 3: demo shape for the hackathon

- Demo on this machine against the existing 1,548-track index for the main
  story: describe a feeling, hear the passage, play the full track, vote.
- For judges installing it themselves: they pick a folder, watch it index,
  then search. A small folder indexes in minutes; the full-library rate
  measured here is about 25 minutes for 1,548 tracks on a GTX 1650.
- Still John's call from the stack decision, Section 10: which music may
  appear in a public demo. No library audio ships in any package. This repo
  already had one history rewrite for exactly that mistake.

## 3. Original roadmap: what is actually left

Done, for reference: CLAP retrieval with the checkpoint health check, sparse
full-library index (1,548 tracks, 7,524 windows), dense best-passage refine,
lyrics transcription with trust filtering and themes, personal reranking from
votes, duplicate collapsing, full-track playback, and the thin local UI.

Not done, in the order it matters for the hackathon:

1. Comparator pack judging. `experiments/blind_pack_comparator` (75 clips,
   `clap-htsat-fused`) is generated and sealed but unjudged. Without marks
   there is no Precision@5 for the second model and no evidence-based call
   on whether it ships or is cut. John confirmed on 31 October that he has
   not judged it yet. This does not block packaging; it blocks the model
   story in the submission.
2. Meta Spark live test. `MetaSparkProvider.interpret` still raises
   `NotImplementedError` even with a key
   (`src/music_discovery/provider.py`). The plumbing, caching table, and UI
   selector exist; the live call and the A/B against verbatim do not. The
   kill rule from the stack decision is untested: expansion must beat
   verbatim on held-out queries or it is cut and the submission says so.
3. True one-click installer. Phase 2 above. Today the launcher is a `.bat`
   that needs `uv` on first run. No `.exe` exists yet.
4. Temporal transition scoring. "Starts reflective and becomes determined"
   needs ordered early-versus-late window scoring (stack decision, Section
   4). Tier 3 scored 0.93 on single passages, which does not prove ordered
   change works. Not built.
5. Timestamp hit rate. Never scored in any run; every scorecard row says
   "not scored". The UI's passage-versus-track judgement was meant to feed
   this and has not been tallied.
6. CLaMP 3 comparator. Never indexed or judged. It is experiment-only on
   license grounds (MERT is CC-BY-NC-4.0), so this is a research gap, not a
   shipping gap.
7. Dense-versus-sparse judged quality. Overlap measured at 3.4 of 5; never
   blind-judged. The "Find best passage" button ships the dense path without
   a judged quality number behind it.
8. Local transcription path. The stack decision promised local
   faster-whisper; the shipped path uses Groq's cloud Whisper at John's
   instruction. A packaged app for judges therefore has no working lyrics
   transcription without a Groq key. Vocal isolation, singing-specific
   transcription, and manual `.lrc` import from the roadmap are also undone.
9. SFX collection. `E:\Assets\Audio\SFX` (6,052 files) was never indexed,
   and the app has no collection switcher. Stack decision, Section 7.
10. Scene-to-music stretch. A scene clip in, dramatic intent out, search.
    Roadmap stretch goal, never built. Hackathon story value only after the
    items above.

## 4. Next three actions

1. Run `packaging/build-release.ps1` and test the zip on a clean folder:
   unzip, double-click, index a small folder, search, get 20 results.
2. Install Inno Setup, decide CPU versus CUDA, write the PyInstaller spec.
3. Judge the comparator pack so the submission can state, with numbers,
   whether the second model earned its place.
