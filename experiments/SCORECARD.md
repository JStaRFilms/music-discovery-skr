# Model scorecard

One row per model per tier per run. Updated after every blind judging round.
Precision@5 and timestamp hit rate come from John's marks in
`blind_pack/judgements.csv`. Throughput is measured, never estimated.

| Date | Model (revision) | Tier | P@5 | Timestamp hit | Win/s | Device | Notes |
|---|---|---|---|---|---|---|---|
| | `laion/larger_clap_music` (`a0b4534a…`) | 1 concrete | | | | | |
| | `laion/larger_clap_music` (`a0b4534a…`) | 2 emotional | | | | | |
| | `laion/larger_clap_music` (`a0b4534a…`) | 3 temporal | | | | | |
| | `laion/larger_clap_music` (`a0b4534a…`) | 4 lyric vs sound | | | | | |
| | `laion/clap-htsat-fused` (`365dea6e…`) | 1–4 | | | | | comparator |
| | CLaMP 3 (`sander-wood/clamp3`) | 1–4 | | | | | experiment-only license |

Failure classes to tally per run: wrong instrument; right sound, wrong mood;
right mood, wrong passage; duplicates flooding; lyrics misheard.

Kill rules (fixed in advance, stack decision Section 9): Tier 1 P@5 under
0.4 for every audio-text model stops text-to-audio v1. Meta expansion must
beat verbatim search on held-out queries or it is cut.
