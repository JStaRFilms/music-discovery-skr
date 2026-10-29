# Model scorecard

One row per model per tier per run. Updated after every blind judging round.
Precision@5 and timestamp hit rate come from John's marks in
`blind_pack/judgements.csv`. Throughput is measured, never estimated.

| Date | Model (revision) | Tier | P@5 | Timestamp hit | Win/s | Device | Notes |
|---|---|---|---|---|---|---|---|
| 2026-10-27 run 1 | `laion/larger_clap_music` (`a0b4534a…`) | 1–4 | INVALID | INVALID | 5.5 | GTX 1650 CUDA | Text tower collapsed (0.999). Pack withdrawn after 21 marks. |
| 2026-10-29 run 2 judged | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 1 concrete | 0.73 (11/15) | not scored | 6.15 | GTX 1650 CUDA | Piano 5/5, strings 2/5. Passes 0.4 kill bar |
| 2026-10-29 run 2 judged | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 2 emotional | 0.85 (34/40) | not scored | 6.15 | GTX 1650 CUDA | Demure weakest at 2/5 |
| 2026-10-29 run 2 judged | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 3 temporal | 0.93 (14/15) | not scored | 6.15 | GTX 1650 CUDA | Single passages judged, transition unverified |
| 2026-10-29 run 2 judged | `laion/larger_clap_music_and_speech` (`195c3a3e…`) | 4 lyric vs sound | 0.20 (1/5) | not scored | 6.15 | GTX 1650 CUDA | No transcription yet; lyrics track must earn this |
| 2026-10-29 | `laion/clap-htsat-fused` (`365dea6e…`) | 1–4 | sealed, unjudged | sealed | 6.68 | GTX 1650 CUDA | comparator pack generated, 31 distinct tracks |
| 2026-10-29 | primary, dense vs sparse | 1–4 | unjudged | unjudged | 6.08 dense | GTX 1650 CUDA | mean top-5 overlap 3.4/5 |
| 2026-10-29 | primary, full library | all | n/a | n/a | 5.50 | GTX 1650 CUDA | 1,548 tracks, 7,524 sparse windows |
| 2026-10-29 | primary + Groq Whisper lyrics | 4 v2 | pack generated, unjudged | not scored | n/a | GTX 1650 + Groq | 807/807 vocal windows transcribed, 424 trusted (195 tracks); 15 clips, 13 distinct tracks; baseline to beat: 0.20 |
| | `laion/clap-htsat-fused` (`365dea6e…`) | 1–4 | | | | | comparator |
| | CLaMP 3 (`sander-wood/clamp3`) | 1–4 | | | | | experiment-only license |

Failure classes to tally per run: wrong instrument; right sound, wrong mood;
right mood, wrong passage; duplicates flooding; lyrics misheard.

Kill rules (fixed in advance, stack decision Section 9): Tier 1 P@5 under
0.4 for every audio-text model stops text-to-audio v1. Meta expansion must
beat verbatim search on held-out queries or it is cut.
