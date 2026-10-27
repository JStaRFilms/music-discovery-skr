# Model scorecard

One row per model per tier per run. Updated after every blind judging round.
Precision@5 and timestamp hit rate come from John's marks in
`blind_pack/judgements.csv`. Throughput is measured, never estimated.

| Date | Model (revision) | Tier | P@5 | Timestamp hit | Win/s | Device | Notes |
|---|---|---|---|---|---|---|---|
| 2026-10-27 run 1 | `laion/larger_clap_music` (`a0b4534a…`) | 1–4 | INVALID | INVALID | 5.5 | GTX 1650 CUDA | Text tower collapsed (0.999). Pack withdrawn after 21 marks. |
| 2026-10-27 run 2 | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 1 concrete | pending judging | pending | 6.15 | GTX 1650 CUDA | 30 distinct tracks in pack |
| 2026-10-27 run 2 | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 2 emotional | pending judging | pending | 6.15 | GTX 1650 CUDA | blind_pack_run2, 75 excerpts |
| 2026-10-27 run 2 | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 3 temporal | pending judging | pending | 6.15 | GTX 1650 CUDA | sparse windows only |
| 2026-10-27 run 2 | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 4 lyric vs sound | pending judging | pending | 6.15 | GTX 1650 CUDA | lyrics not yet transcribed |
| | `laion/clap-htsat-fused` (`365dea6e…`) | 1–4 | | | | | comparator |
| | CLaMP 3 (`sander-wood/clamp3`) | 1–4 | | | | | experiment-only license |

Failure classes to tally per run: wrong instrument; right sound, wrong mood;
right mood, wrong passage; duplicates flooding; lyrics misheard.

Kill rules (fixed in advance, stack decision Section 9): Tier 1 P@5 under
0.4 for every audio-text model stops text-to-audio v1. Meta expansion must
beat verbatim search on held-out queries or it is cut.
