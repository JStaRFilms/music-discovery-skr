# Audio-grounded music discovery — feasibility and architecture research

**Research date:** 27 October 2026  
**Status:** Evidence-backed desk research; no model inference or listening evaluation has been performed.  
**Inputs:** `music-discovery-idea.md` and `music-discovery-exploration-brief.md`. No repository, deployment, paid API calls, model training, or audio uploads were performed.

## Executive recommendation

**Build a passage-level music search engine around a pretrained audio–text retrieval model, and add Meta-assisted query interpretation only after comparing it against direct search.** Do not train a foundation model. Reserve a larger music-understanding model for selective captions/verification of the top retrieved passages. Measure emotional retrieval quality with John's own blind listening labels before building out UI or running bulk indexing.

The question is not simply whether AI can detect cheerful music. It is whether it can distinguish **simultaneous emotional conflict** (bright arrangement with melancholy underneath) from **temporal changes** (happy opening followed by a darker transition) and reliably find an auditionable excerpt. No reviewed checkpoint has been empirically validated against John's music or queries yet.

## Problem and boundaries

- Search an authorized collection of existing music using descriptions such as **“happy with a twist of fate.”**
- Rank by the **actual audio**, not filename/title/artist-derived mood or preexisting genre labels.
- Return a small shortlist of whole tracks *with* relevant passage timestamps, explanations limited to observed evidence, and playable excerpts.
- Keep decisions such as vocal vs instrumental preference, local/cloud processing, and what music may legally be demoed open until tested.
- This is retrieval, not music generation, identification, scraping, or full recommender-system training.

## Approaches: what code can and cannot solve

| Approach | Can it answer the original problem? | Strengths | Weaknesses | Verdict |
|---|---|---|---|---|
| Deterministic signal processing / rules (tempo, RMS loudness, onset rate, spectral descriptors, key) | Only partially | Cheap, local, measurable, good for tempo/dynamic/filter constraints | Fast/major ≠ happy; features do not establish irony, grief, regret, scene meaning | Essential supporting baseline; not the core retrieval engine |
| Pretrained joint audio–text embeddings (CLAP, CLaMP 3, MuQ-MuLan) | Plausible, requires a test | Audio-grounded, efficient precomputed indexing, flexible language queries | Broad/instrument matches can dominate; fine-grained clauses may be lost; temporal shifts need section-level logic | **First experiment** |
| Music audio → detailed captions → text retrieval | Plausible for nuance | Interpretable descriptors for genre/texture/affect/structure; natural fit to reranking | Expensive to caption entire library; hallucination and loss of nuance; separate embedding space | Try only after baseline, on top candidates |
| Hybrid: embeddings + DSP features + explicit query decomposition + optional caption-based rerank | Strong candidate | Can combine acoustic evidence, exclusions, dynamics, time and scene intent | Engineering complexity and scoring calibration; can explain wrong hits persuasively | **Potential shipping architecture if experiments support it** |
| Train a music model or fine-tune | Theoretically | Can adapt toward subjective emotional fit | Data, rights, evaluation and GPU constraints; not justified before baseline | **No** for hackathon; possibly later reranker using preference labels |

**Important semantics:** “happy with sadness underneath” should be evaluated on overlapping acoustic/harmonic or lyric signals; “happy then tragic” requires an **ordered sequence across passages**. A single global vector cannot reliably prove either. Prompt decomposition and time-aware logic are hypotheses to test, not certified fixes.

## Real candidate models (current model cards and repos)

| Candidate | Verified availability / input role | License and constraints | Practical recommendation |
|---|---|---|---|
| **LAION CLAP** — `laion/larger_clap_music_and_speech` | Open HF checkpoint; audio and text vectors; Transformers and LAION Python package; music-trained checkpoints also in LAION repo | HF model card states **Apache-2.0**; specific checkpoint, code, and dependency terms should still be reviewed | **Baseline A**. Cache excerpt vectors, embed original queries in same joint space. [Model](https://huggingface.co/laion/larger_clap_music_and_speech), [repo](https://github.com/LAION-AI/CLAP) |
| **CLaMP 3 SAAS** — `sander-wood/clamp3` | Open checkpoint and Python scripts for text-to-audio retrieval; audio feature extraction uses **MERT** before CLaMP; model accepts longer music representations | CLaMP 3 HF card states **MIT**; but recommended `m-a-p/MERT-v1-95M` dependency HF card currently states **CC BY-NC 4.0**. The complete pipeline is **not safely assumed commercially unrestricted** | **Baseline B**, particularly music-oriented retrieval. More setup. [Repo](https://github.com/sanderwood/clamp3), [model](https://huggingface.co/sander-wood/clamp3), [MERT dependency](https://huggingface.co/m-a-p/MERT-v1-95M) |
| **MuQ-MuLan Large** — `OpenMuQ/MuQ-MuLan-large` | Joint music–text model, around 700M params, with official Python package | **CC BY-NC 4.0** weights; official authors caution released models differ from the larger paper configurations | **Baseline C** if A/B are inadequate or useful for ablation. [Model](https://huggingface.co/OpenMuQ/MuQ-MuLan-large), [repo](https://github.com/tencent-ailab/muq) |
| **MOSS-Music-8B-Instruct** | Music-focused generative audio understanding/captioning and structural/lyrical QA; approximate 9.1B total model parameters | HF model card **Apache-2.0**. Much heavier inference; verify dependencies, data rights, and deployment resources | **Selective descriptor/rerank experiment** for perhaps five candidate snippets, not a mandatory per-window first-pass index. [Model](https://huggingface.co/OpenMOSS-Team/MOSS-Music-8B-Instruct), [repo](https://github.com/OpenMOSS/MOSS-Music) |
| **NVIDIA Music Flamingo** — `nvidia/music-flamingo-2601-hf` | Released music-audio language model for richer captioning and long-form reasoning; Transformers integration | **Non-commercial research only**; heavier runtime | Alternative caption benchmark if hardware/hosting/rights allow. [Model](https://huggingface.co/nvidia/music-flamingo-2601-hf) |
| **FIGMA (ACL 2026)** | Peer-reviewed approach for fine-grained music retrieval; documents contrastive CLAP models' difficulty with detailed clauses | Official paper confirmed; **no working weights/maintained code verified in this research** | **Research inspiration, not foundation of deadline-critical demo**. [Paper](https://aclanthology.org/2026.acl-long.2197/) |
| **Microsoft CLAP** | `msclap` package and official checkpoints, including caption model | HF model card **MS-PL**; evaluate terms before distribution | Optional control baseline. [Model](https://huggingface.co/microsoft/msclap), [repo](https://github.com/microsoft/CLAP) |

These models were **researched**, not run or benchmarked on John's collection. Papers' reported metrics are not measured hackathon performance.

## Libraries and engineering choices

| Task | Recommended tooling | Notes |
|---|---|---|
| Audio ingest, format decode, resampling, clips | **FFmpeg** + Python (`soundfile`, `torchaudio` as needed) | Decode originals read-only; avoid storing full decoded copies; FFmpeg licensing varies by build. [Legal](https://www.ffmpeg.org/legal.html) |
| Measured music features | **librosa** | BPM/beat/onset/RMS/spectral descriptors support real filter constraints but not emotional truth. Permissively licensed ISC. [Docs](https://librosa.org/doc/latest/index.html) |
| Extensive MIR and pretrained mood taggers | **Essentia** | Mood models exist, including “bittersweet” cluster; library is AGPLv3 and models carry separate noncommercial license terms. **Not default for future commercial use.** Linux/WSL preferred for Python bindings. [Models](https://essentia.upf.edu/models.html), [licensing](https://essentia.upf.edu/licensing_information.html), [install](https://essentia.upf.edu/installing.html) |
| Local similarity search | **NumPy cosine/dot-product first**, optionally **FAISS** | Thousands of clips need no server; FAISS is from Meta FAIR and supports efficient vector search. [FAISS](https://faiss.ai/) |
| Metadata / caching | **SQLite** | Track fingerprints, excerpt start/end, embeddings references, model/version, user labels, run state. |
| Browser UI and playback | **FastAPI** local backend + lightweight React/Next.js frontend | Local service can index permitted directories and serve timestamped audio. A remotely hosted web app cannot read a local drive unless files are explicitly uploaded. |
| Optional vector DB later | **Qdrant local** | Has persistent local mode if filters/index management outgrow a simple matrix. [Repo](https://github.com/qdrant/qdrant-client) |

Avoid using an unrelated generic **text embedding model** to compare against audio embeddings: vectors must be produced within a compatible audio–text model space. Text embeddings can be appropriate for searching **captions**, but that is a different index.

## Meta integration: strong, weak, and unverified

- **Strong near-term role: scene/query interpretation.** Given “happy with a twist of fate,” Muse Spark could produce (1) positive sonic traits, (2) negative constraints, (3) alternate readings, and (4) whether to search for simultaneous emotional layers or a temporal progression. Search the original query **as a control**; the LLM can degrade nuance by over-expanding.
- **Strong stretch feature: scene-to-music.** Meta's video understanding can describe an authorized clip/scene, from which the user can specify desired dramatic intent; the audio retrieval engine then finds appropriate passages. This is a meaningful addition for filmmakers **if** text retrieval already works.
- **Potential use: evidence-grounded reranking.** Muse may compare user intent to *real audio-derived descriptions* and reject contradictory candidates. If it never receives actual audio or descriptions, it cannot hear the music and must not claim acoustic evidence.
- **Audio input caveat:** Meta docs list audio input for Muse Spark/Wonder. But **Muse Spark 1.3 audio understanding is expressly not fully supported; Meta's own audio examples use 1.2.** API support does not prove music understanding. Test only permitted excerpts. [Audio guide](https://dev.meta.ai/docs/video-understanding), [models](https://dev.meta.ai/docs/models).
- **Meta-made FAISS** is useful infrastructure, but should not be the only reason to claim substantive Meta AI integration.
- **Cost:** Published Standard pricing is Muse Spark $1.25 input / $4.25 output per million tokens and Muse Wonder $4 / $20. Audio/video processing cost needs live per-request validation. Claimed $150 hackathon credits are not the same as confirmed usable billing balance. [Pricing](https://dev.meta.ai/docs/pricing-rate-limits).
- **Privacy:** Standard mode is stated not to train Meta models on submitted content; Contributor mode permits training and prohibits sensitive/confidential/personal submissions. Do not default to Contributor for clients' or private audio. [Pricing](https://dev.meta.ai/docs/pricing-rate-limits), [Contributor policy](https://dev.meta.ai/help/policies-and-privacy/contributor-tier).

## A minimal architecture worth *testing*, not yet committing to

```text
Authorized local tracks
  → inventory / read-only decode
  → excerpts with start/end timestamps
  → CLAP or CLaMP3 audio embeddings
  → local vector matrix + SQLite metadata

User description
  → direct audio-text query vector (baseline)
  → optional Meta query decomposition (A/B alternative)
  → candidate passages
  → group/diversify by track
  → optional cheap filters / caption rerank
  → top 3–5 tracks, clickable excerpt timestamp and explanation
  → user's relevance labels for evaluation
```

Store model ID, exact checkpoint revision, audio preprocessing and embedding dimensions. Don't mix vectors from incompatible model versions. Keep original track audio unchanged and off remote services by default.

### Temporal contrast matters

- **Single-passage match**: extract short audio windows and rank each independently; identify usable moments.
- **Ordered transition**: represent a track as a sequence of timestamped windows and score whether it *first* fits “bright” and *later* fits “uneasy,” using minimum gap/duration rules if justified.
- **Simultaneous bittersweetness**: requires multi-property representation/independent evidence for brightness and melancholy within the same window; do **not** infer it from positive BPM alone.
- Compare strategies on songs that change moods. Do not let duplicate overlapping windows dominate top results.

## First decisive experiment (before UI polish)

1. **Create a 30–50-track authorized evaluation set** the creator knows, deliberately including confusable bright-but-sad music, a mood-changing track, instrumental dialogue underscore, etc. Hide title/artist during *judgment*. Set aside a few tracks/prompts for held-out testing.
2. **Prepare 8–12 prompts** with simple (“low-energy piano”), nuanced (“happy with a twist of fate”), exclusion (“quiet tension, no dramatic drums”), and progression (“starts reflective, becomes determined”). Make personal labels of which songs/passages really fit; expect some subjectivity.
3. **Model A baseline**: fixed model-supported excerpt windows, CLAP vectors, normalized cosine retrieval, top-five unique tracks with timestamps. Measure decoding/index throughput and RAM/VRAM; don't extrapolate without measurements.
4. **Model B comparison**: same inputs and labels using CLaMP3. Respect the MERT dependency's noncommercial restrictions. Optionally add MuQ-MuLan.
5. **Meta ablation**: same audio index, compare **original query only** against **original + Muse-assisted interpretations**. Use structured positive/excluded criteria but do not manufacture false evidence.
6. **Optional caption study**: run MOSS-Music on top few candidates, independently fact-check its claims by listening and compare reranking utility. Hold off if hardware cost is high.
7. **Report**: Recall/useful@5, number of queries with any usable result in top five, timestamp precision, time-to-first-acceptable excerpt, query time, indexing throughput/cost, failure cases, and which method actually won. An experimental goal could be useful matches for most test queries; the acceptable cutoff must be set before observing results.

**Pivot condition:** If nuanced text retrieval is mediocre, first test short decomposed descriptions, passage windows, and feedback—not a larger generic LLM. If baseline audio search itself fails on easy material, narrow the product to explicit instrumentation/energy/tempo and consider tagged audio-caption search. If no method beats manual browsing, do not claim emotional intelligence and don't hide it behind UI polish.

### Back-of-envelope storage only, not runtime measurement

For an illustrative **200 tracks × 4 minutes × one 10-second non-overlapping passage**, the index contains **4,800 vectors**. If each happens to be **512 float32 dimensions**, the raw vectors occupy about **9.8 MB** before metadata and indexing overhead. The model weights, audio decoding and inference compute are much more significant constraints. Window length/hop and dimension must follow whichever checkpoint is actually selected.

## Time, legal and deployment considerations

- Public Meta hackathon page states **Nov 4, 2026, 9 PM ET** project submission deadline (on that date, **Nov 5, 3 AM WAT**). Recheck current official participant details before submission. [Event](https://dev.meta.ai/events/global-hackathon).
- Public demos must use owned or appropriately licensed recordings; owning a downloaded music file does not itself authorize public redistribution, third-party model upload, or training. A royalty-free production license may permit video synchronization without permitting public music streaming.
- If private local tracks are used for development, demo judges can use a **different cleared sample collection**. Don't use private filenames/paths as prompt sources or let public users open arbitrary server files.
- Local Windows development: test CLAP and audio decoding on small batches first, using CPU or available CUDA. **A 4 GB GPU should not be presumed adequate for a 9.1B-parameter caption model.** Consider a larger GPU host only after checking quality/cost and approvals. Essentia Python support is easier via Linux/WSL than native Windows.
- The MVP should cut login, payments, Spotify/YouTube catalogs, bulk cloud ingestion, desktop packaging, model fine-tuning, lyric transcription (unless vital), and fancy animated waveforms.
- No hidden authorizations: this research does not authorize deploying code, purchasing compute, spending API credits, or uploading audio.

## Best realistic demonstration

A filmmaker types **“happy with a twist of fate.”** The app shows the raw request, optionally interprets it as *surface optimism + uneasy undertone* or *positive-to-dark transition*, and returns **3–5 passages from verified indexed tracks**, with seekable playback at the relevant timestamp and a restrained description (e.g., “bright piano over restrained low strings, 01:32–01:48”). The creator marks “good fit / too cheerful / wrong transition”; the interface demonstrates how discovery improves *if evidence supports it*. One optional scene clip feeding the same search pipeline could illustrate a meaningful Meta integration.

## Decisions vs verified research

**Verified from documentation:** actual model repositories/checkpoints; CLaMP3 MERT preprocessing; Meta API audio input and Spark 1.3 caution; FAISS/librosa/Essentia capabilities; important noncommercial model dependencies; current public hackathon deadline.

**Unverified hypotheses:** which model retrieves subtle emotions best; whether Muse improves nuanced retrieval; whether audio captions tell the emotional truth; which model runs quickly enough on the available machine; whether a useful full-track mood curve can be extracted reliably.

**Future user decisions:** permitted music, available machine/data volume, instrumental-vocal distribution, whether audio can leave the machine, what counts as success, public demo license, whether clip- or track-level selection comes first.

## Primary sources

1. LAION CLAP repo / model: https://github.com/LAION-AI/CLAP ; https://huggingface.co/laion/larger_clap_music_and_speech
2. CLaMP3 code and model: https://github.com/sanderwood/clamp3 ; https://huggingface.co/sander-wood/clamp3
3. MERT-v1-95M dependency license: https://huggingface.co/m-a-p/MERT-v1-95M
4. MuQ-MuLan repo and model: https://github.com/tencent-ailab/muq ; https://huggingface.co/OpenMuQ/MuQ-MuLan-large
5. MOSS-Music repo and checkpoint: https://github.com/OpenMOSS/MOSS-Music ; https://huggingface.co/OpenMOSS-Team/MOSS-Music-8B-Instruct
6. Music Flamingo: https://huggingface.co/nvidia/music-flamingo-2601-hf
7. FIGMA paper: https://aclanthology.org/2026.acl-long.2197/
8. Essentia models/licensing/install: https://essentia.upf.edu/models.html ; https://essentia.upf.edu/licensing_information.html ; https://essentia.upf.edu/installing.html
9. FAISS documentation: https://faiss.ai/
10. Meta Model API: https://dev.meta.ai/docs/models ; https://dev.meta.ai/docs/video-understanding ; https://dev.meta.ai/docs/pricing-rate-limits
11. Meta hackathon: https://dev.meta.ai/events/global-hackathon
