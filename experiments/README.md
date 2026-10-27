# Feasibility experiment

Goal: answer whether local audio-text retrieval finds usable passages in
John's library before any app UI is built. See
`docs/music-discovery-stack-decision.md` Sections 4 and 9 for the full design.

## Run order (from the project root, with the project `.venv`)

```powershell
uv venv --python 3.11
uv sync --extra embed --extra dev
uv run music-discovery inventory
uv run music-discovery select-sample
uv run music-discovery queries
uv run music-discovery index --limit-tracks 5
uv run music-discovery search --query "happy with a twist of fate"
uv run music-discovery index
uv run music-discovery blind-pack
uv run music-discovery scorecard
```

Originals in `E:\Assets\Audio` are read only. The database, embeddings,
and blind-pack excerpts live under `data/` and `experiments/blind_pack/`
on C: and are not committed. `sample.json` and `queries.json` are
committed so the experiment can be reproduced.

## Rules fixed before listening

- 40 tracks by the quota rule in `src/music_discovery/sample.py`, seed 20261027.
- 15 queries in `src/music_discovery/queries.py`. A third are held out.
  John's verbatim words are never replaced by sharpened variants.
- Blind judging only. No filenames until every row in
  `blind_pack/judgements.csv` is marked.
- Kill rules and the model scorecard live in the stack decision, Section 9.
