# Music discovery — stack decision

Date: 27 October 2026. Status: decided for the feasibility experiment. Not yet built.
Inputs: `music-discovery-idea.md`, `music-discovery-exploration-brief.md`, two sub-agent
reports (Muse Wonder 1.0 and GPT-6.1 Terra via Takomi), an external research report
copied to `music-discovery-research-report-external.md`, and John's inline comments
on the first synthesis.

## 1. What was decided from John's comments

- Audio stays local. Only query text may leave the machine, and only to Meta.
- Library source is `E:\Assets\Audio`. John will give the full folder, not a
  hand-picked sample. The agent selects the experiment sample.
- Query text may go to Meta. Use `muse-spark-1.3` for the hackathon.
  Do not burn API calls for no gain. Interpretation must be cached and optional.
- The model layer must be swappable later, in the spirit of the Vercel AI SDK:
  a provider interface so Meta Spark can be replaced by a local model on
  John's laptop without rewriting search.
- Mostly instrumental was the first brief, but lyrics must be catered for now.
  See Section 6. Do not retrofit later.
- The end product is a local app John double-clicks open. It must look good.
  Gradio, Electron, and Tauri are means, not the goal.
- Scanning is normally once. Rescan only when John adds or changes music.
  No watcher, no constant reindexing.
- Seed queries in John's words: "happy", "sad", "rather dramatic",
  "slow-paced with a bit of ginger", "groove", "demure".
  Agents may sharpen these into test prompts, but the originals stay.
- Keep a running scorecard of the candidate models as work proceeds.
  John wants to see which model earns its place over time.

## 2. Measured facts, not assumptions

Hardware probed on this machine, 27 October 2026:

- AMD Ryzen 5 4600H, 6 cores / 12 threads.
- 31.4 GB RAM.
- NVIDIA GeForce GTX 1650, 4096 MiB VRAM, driver 616.92, plus AMD integrated GPU.
- Windows 11 Pro Insider Preview, build 10.0.28120.
- FFmpeg 8.0 (gyan.dev full build). Node v24.16.0. uv 0.11.8.
- Python 3.14.5 is the default. Python 3.11 is also installed.
  The project will use Python 3.11 in its own `.venv`. Python 3.12 is not
  installed; the earlier 3.12 recommendation is dropped for that reason.
- Disk: C: 137.3 GB free. E: 25.7 GB free. The index lives on C: with the
  project. Original audio on E: is read only and never written.

Library census of `E:\Assets\Audio`, read only:

- 7,849 files, 92.34 GB total. Two top folders: `Music` and `SFX`.
- `Music`: 1,797 files, 45.24 GB. Of these, 1,510 are audio files
  (1,301 `.wav`, 208 `.mp3`, plus `.aif`, `.m4a`, and `.mp4` containers
  whose audio stream must be extracted).
- Estimated music duration is about 62.6 hours. Estimate method: 30 randomly
  sampled audio files averaged 149.3 seconds. One sampled file probed at
  zero duration, so corrupt or empty files exist and must be logged, not hidden.
- `Music\Stream Beats` dominates with 1,413 files (1,256 `.wav`), in genre
  subfolders such as Ambient, Lofi, Hiphop, EDM, Synthwave, Chiptune.
  Pixabay has 200 files. The rest is a long tail of small folders and singles.
- `SFX`: 6,052 files, including 3,466 `.wav`. Sound effects are a separate
  collection. They must never be mixed into music ranking by default.
- Some files have no real extension. Their names start with
  " Harris Heller - ". File type must be sniffed with ffprobe, not guessed
  from the extension alone.
- Non-audio clutter (`.pek`, `.png`, `.mov`, `.ds_store`, licenses) must be
  ignored by the indexer by content type, not by a blocklist of names.

Consequence of 4 GB VRAM: CLAP fits. A 7B to 9B caption model does not fit
comfortably. Caption-first architectures are roadmap items, not v1.

## 3. Chosen stack

| Layer | Pick | Version / status |
|---|---|---|
| Runtime | Python 3.11 venv, local process | Installed; pin with uv lockfile |
| Decode | FFmpeg 8.0, mono 48 kHz | Installed; log `ffmpeg -version` |
| Embedding A | `laion/larger_clap_music` | HF rev `a0b4534a…`, Apache-2.0, 512-d |
| Embedding B | `laion/clap-htsat-fused` | HF rev `365dea6e…`, comparator only |
| Embedding C | CLaMP 3, `sander-wood/clamp3` | Comparator only, see license note |
| Search, experiment | NumPy exact cosine | No vector DB |
| Search, app | sqlite-vec `vec0`, cosine | 0.1.x pre-1.0, pin exact wheel |
| Metadata | SQLite, single file on C: | Tracks, windows, lyrics, feedback |
| Features | librosa | Filters and evidence only |
| Lyrics | faster-whisper, local | Model size TBD by VRAM test |
| Query interpretation | Provider interface | Meta Spark 1.3 first provider |
| Frontend, experiment | CLI, then thin localhost page | No polish until retrieval passes |
| Frontend, app | React + Vite + TypeScript | Served from 127.0.0.1 |
| Packaging | Double-click launcher first | Electron or Tauri decided later |

PyTorch is unpinned until a clean install on this machine is logged.
GPT-6.1 Terra reported torch 2.14.1 as the current PyPI version. That is a
candidate, not a verified compatible pin. The lockfile from the first
successful install becomes the truth, and its versions go in the index manifest.

License notes that affect shipping, not experimenting:

- `laion/larger_clap_music` is Apache-2.0. Safe primary.
- CLaMP 3 code is MIT, but its recommended MERT feature extractor
  (`m-a-p/MERT-v1-95M`) is CC-BY-NC-4.0. The full CLaMP 3 pipeline is
  therefore experiment-only until that dependency is replaced or licensed.
- MuQ-MuLan Large is CC-BY-NC-4.0. Experiment-only for the same reason.
- Essentia is AGPLv3 with separately licensed mood models, and its Python
  bindings are not supported on native Windows. Out.

## 4. Window sampling: scattered first, dense on demand

John's point stands. Ten seconds from one place can lie about a track.
A track can start slow and switch entirely in the middle. Searching every
second of 62 hours up front is also wasteful. Two stages solve both:

Stage 1, sparse scan for every track. Five 10-second windows per track at
roughly 10%, 30%, 50%, 70%, and 90% of its duration. Skip the first and
last five seconds where fades and silence are common. For 1,510 tracks
that is about 7,550 windows. At 512 float32 dimensions the raw vectors
are about 15 MB. This buys whole-library coverage on day one.

Stage 2, dense scan only where it earns compute. The top candidate tracks
from a search, or any track John opens, get contiguous 10-second windows
with a 5-second hop. That finds the exact passage and exposes changes
over time. Dense results replace sparse results for that track in the index.

The experiment must compare the two directly. Same tracks, same queries:
sparse-only ranking against contiguous ranking. If sparse misses the
passage John would have picked, the sampling changes before any UI work.

Temporal queries need ordered evidence. "Starts reflective and becomes
determined" is scored as an early window matching the first description
and a later window matching the second, with a minimum time gap.
"Happy with sadness underneath" is different. It needs two properties in
the same window, scored independently. One averaged vector proves neither.

## 5. Meta role and the swappable provider

Meta cannot be the retriever. No Meta embedding endpoint was found in the
Model API model list, and no music retrieval evaluation was found for
Spark or Wonder audio input. Audio grounding comes from local CLAP.

Meta Spark 1.3 may do one job: turn a phrase such as "happy with a twist
of fate" into two to four concrete acoustic descriptions, plus explicit
exclusions, plus a note on whether the request sounds simultaneous or
temporal. The original query is always searched too. Expansion ships only
if it beats verbatim search on held-out queries.

Cost control, per John's comment:

- Verbatim local search is free and always available offline.
- Interpretation is opt-in per query, cached by query text hash.
  The same phrase never bills twice.
- Standard mode only. Contributor mode allows training on submitted
  content and is not used.

Swappable provider interface, after the Vercel AI SDK pattern John named:

```text
InterpretationProvider
  interpret(query) -> [acoustic descriptions], [exclusions], mode
Providers:
  MetaSparkProvider    muse-spark-1.3, first, hackathon
  LocalProvider        later, a local model on John's laptop, stubbed now
  NoOpProvider         verbatim only, the offline default fallback
```

The interface lives in one module. Search never imports a vendor SDK
directly. In the Python backend that means a thin internal abstraction,
not the Vercel AI SDK itself, which is TypeScript. If the app later moves
its interpretation call into a TypeScript layer, the same interface maps
onto the Vercel AI SDK's model switching directly. Spark 1.2 is noted
only because Meta documents that Spark 1.3 audio understanding is not
fully supported and directs audio work to 1.2. No audio is sent in v1,
so 1.3 stands for text.

## 6. Lyrics: catered for now

Lyrics are a separate evidence track from day one. They are not blended
into the CLAP score, because a lyric embedding and an audio embedding do
not share a vector space, and because sound and words can disagree.
That disagreement is a feature John asked for, not noise.

In the first build:

- The schema reserves, per window and per track: vocal probability,
  lyric text, lyric language, transcription confidence, and lyric source.
  No reindex is needed when this improves.
- Vocal detection per window uses CLAP zero-shot scoring against a small
  fixed set including singing voice and instrumental. Windows with no
  vocal signal skip transcription at zero cost. On a mostly instrumental
  library, most windows skip it.
- Transcription is local with faster-whisper. Model size is set by a
  VRAM test on the GTX 1650, starting from a small int8 model. Audio
  never leaves the machine. Meta Voice Transcribe is not used. It is
  speech-to-text, it needs an upload, and this library is sung or
  instrumental, not spoken.
- Lyric search starts lexical, with SQLite FTS5 over transcribed lines,
  kept apart from audio ranking. Results show Sound and Words as two
  labelled signals. A flag marks likely disagreement, such as upbeat
  sound with sad words, and links the passage that proves each side.
- The experiment sample must include vocal tracks and at least one
  lyric-versus-sound query, even though StreamBeats is instrumental.
  The long tail of the library, including Yoruba and church material,
  is exactly where lyrics will matter.

Stated limits: Whisper transcribes speech far better than singing.
Dense mixes, reverb, and backing vocals will produce errors, so
confidence is stored and shown, never hidden. If direct transcription
fails its test, the roadmap order is: isolate vocals first, then retry
transcription; then a singing-specific model; then manual import of
lyric files John already has. Each step is a schema-compatible upgrade,
not a redesign.

## 7. Collections, scanning, and the local app

Two collections, never silently merged:

- Music, from `E:\Assets\Audio\Music`. The default search target.
- SFX, from `E:\Assets\Audio\SFX`. Searchable only when John selects it.
  A door slam must not answer a query about a sad piano cue.

Scanning behaviour:

- First scan indexes everything in the chosen collection. It is resumable
  and logs every failure with a reason.
- Every file gets a fingerprint from path, size, and modification time,
  with a content hash for files whose fingerprint changed.
- Rescan skips unchanged files. Only new, changed, or moved music is
  decoded and embedded. Deleted files are marked missing, not forgotten,
  so feedback history survives.
- The index, decoded cache, and manifests live on C: with the project.
  E: is read only. Nothing writes into `E:\Assets\Audio`.

App shape: a localhost React interface bound to 127.0.0.1, opened by a
double-click launcher. Search box, editable interpreted intent, three to
five results with seekable passage playback, Sound and Words evidence,
indexing status, and directional feedback such as too cheerful, too
dark, or wrong passage. Electron versus Tauri is deferred until the
launcher version works. John opens an app, not a terminal, either way.
No accounts, no hosting, no public sharing toggle in v1.

## 8. What the external report changed

Taken from `music-discovery-research-report-external.md`:

- CLaMP 3 added as Baseline C, a genuinely music-specific comparator
  rather than a second CLAP checkpoint. Its MERT license restricts it
  to experiments, which the report itself flags.
- The simultaneous versus temporal distinction is adopted as a scoring
  rule in Section 4, not left as prose.
- Scene-to-music is adopted as a roadmap stretch. A filmmaker drops in a
  scene clip, Meta describes the dramatic intent in text, and the local
  engine searches. It is meaningful for the hackathon story only after
  plain text search works.

Ignored or rejected, with reasons:

- MOSS-Music-8B and NVIDIA Music Flamingo as local caption rerankers.
  Both are too heavy for 4 GB VRAM, and Music Flamingo is non-commercial
  research only. They return as roadmap options on bigger hardware.
- MuQ-MuLan Large as a primary. CC-BY-NC-4.0 blocks the shipping path.
- Qdrant, FAISS server modes, and a Next.js stack. Unneeded at 7,550
  sparse windows, and FAISS Windows wheels add friction for no gain yet.
- Its suggestion to cut lyric transcription. Superseded by John, see
  Section 6. The report was written before that instruction.
- Its FastAPI plus React shape is kept, but its framing of a hosted demo
  is not. John's priority is his real local library.

## 9. The experiment and the model scorecard

Sample: 40 tracks chosen by rule, not by taste. Mostly StreamBeats
instrumental across its genre folders, plus Pixabay and long-tail vocal
tracks, plus mood-changing tracks and hard near-neighbours. Selection
rules are written down before any listening.

Queries: three tiers plus lyrics. Tier 1 concrete sound. Tier 2 John's
words, sharpened: "happy" becomes happy against "happy with a twist of
fate"; "demure" and "slow-paced with a bit of ginger" stay verbatim as
adversarial cases, because vague language is the real workload. Tier 3
temporal and exclusion. Tier 4 lyric versus sound. A third of the
queries are held out and never used for tuning.

Scorecard, updated every run, one row per model per tier:

- Precision at 5 from John's blind marks: usable, close, or wrong.
- Timestamp hit rate. Did the returned passage contain the fit?
- Indexing throughput in windows per second, CPU and GPU separately.
- Failure class: wrong instrument, right sound wrong mood, right mood
  wrong passage, duplicates flooding, lyrics misheard.

Kill and pivot rules, fixed in advance:

- If Tier 1 Precision at 5 is under 0.4 for every audio-text model,
  text-to-audio v1 stops. The fallback is audio-example search, and
  that change of product needs John's explicit say-so.
- If Meta expansion does not improve held-out Tier 2 and 3 results,
  it is cut and the submission says so.
- If sparse sampling misses passages that dense sampling finds,
  Stage 1 sampling is redesigned before any bulk indexing.
- If indexing the sparse pass over the full Music collection projects
  beyond a day of compute on this machine, that is reported plainly
  instead of silently shrinking the library.

## 10. Still open, and who owns it

Researchable without John: whether Transformers loads both CLAP
checkpoints cleanly under Python 3.11 on this GPU; faster-whisper model
size against 4 GB VRAM; exact sparse indexing time over 40, then 300,
then all 1,510 music files; whether the $150 credit is actually applied
in Meta Billing; the final hackathon rules as accepted.

Only John can decide: which music may appear in a public demo; whether
a useful single passage is enough or ordered emotional change must work
in v1; what Precision at 5 makes this better than browsing by hand;
whether the scene-to-music stretch is worth hackathon time.

## 11. Bottom line

The stack is CLAP locally, sparse then dense, SQLite underneath, React
on loopback, Meta Spark 1.3 behind a swappable provider for query
interpretation only, and lyrics as a separate local evidence track from
the first schema. The external report earned CLaMP 3 a place in the
experiment and lost its caption models to your 4 GB GPU. The next step
is the 40-track blind experiment. Its scorecard, not any agent's
preference, picks the shipping model.
