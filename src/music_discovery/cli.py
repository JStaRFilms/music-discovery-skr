from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config, db as dbmod
from .embed import embed_texts, load_clap, run_index
from .evaluate import make_blind_pack, scorecard
from .health import check_model
from .inventory import run_inventory
from .queries import QUERIES, write_queries
from .sample import select_sample, write_sample
from .search import load_matrix, rank_tracks


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="music-discovery")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("inventory")
    p.add_argument("--root", type=Path, default=config.DEFAULT_MUSIC_ROOT)
    p.add_argument("--db", type=Path, default=config.DB_PATH)

    p = sub.add_parser("select-sample")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--out", type=Path, default=Path("experiments/sample.json"))

    p = sub.add_parser("index")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--limit-tracks", type=int, default=None)
    p.add_argument("--batch", type=int, default=4)

    p = sub.add_parser("index-dense")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--batch", type=int, default=4)

    p = sub.add_parser("index-all")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--batch", type=int, default=4)

    p = sub.add_parser("compare-dense")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)

    p = sub.add_parser("search")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--query", required=True)
    p.add_argument("--top", type=int, default=20)

    p = sub.add_parser("blind-pack")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--out", type=Path, default=Path("experiments/blind_pack"))

    p = sub.add_parser("scorecard")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--judgements", type=Path, default=Path("experiments/blind_pack/judgements.csv"))

    p = sub.add_parser("tier4-pack")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--out", type=Path, default=Path("experiments/blind_pack_tier4v2"))

    p = sub.add_parser("lyrics-review")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--out", type=Path, default=Path("experiments/lyrics_review"))

    p = sub.add_parser("lyrics-detect")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--all", action="store_true", help="score every track, not just the sample")

    p = sub.add_parser("lyrics-transcribe")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--all", action="store_true", help="transcribe every track, not just the sample")

    p = sub.add_parser("duplicates")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)
    p.add_argument("--threshold", type=float, default=0.995)

    p = sub.add_parser("lyrics-themes")
    p.add_argument("--db", type=Path, default=config.DB_PATH)
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)

    p = sub.add_parser("check-model")
    p.add_argument("--model", default=config.PRIMARY_MODEL_ID)
    p.add_argument("--revision", default=config.PRIMARY_MODEL_REVISION)

    p = sub.add_parser("queries")
    p.add_argument("--out", type=Path, default=Path("experiments/queries.json"))

    args = parser.parse_args(argv)
    config.ensure_dirs()

    if args.cmd == "inventory":
        print(json.dumps(run_inventory(args.db, args.root), indent=2))
    elif args.cmd == "select-sample":
        conn = dbmod.connect(args.db)
        sample = select_sample(conn)
        conn.close()
        write_sample(sample, args.out)
        print(json.dumps({"selected": len(sample), "out": str(args.out)}, indent=2))
    elif args.cmd == "index":
        print(json.dumps(run_index(args.db, args.model, args.revision, args.limit_tracks, args.batch), indent=2))
    elif args.cmd == "index-dense":
        print(json.dumps(run_index(args.db, args.model, args.revision, batch=args.batch, kind="dense"), indent=2))
    elif args.cmd == "index-all":
        print(json.dumps(run_index(args.db, args.model, args.revision, batch=args.batch, all_tracks=True), indent=2))
    elif args.cmd == "compare-dense":
        from .compare import compare_dense

        print(json.dumps(compare_dense(args.db, args.model, args.revision), indent=2))
    elif args.cmd in ("search", "blind-pack"):
        matrix, meta = load_matrix(args.db, args.model, args.revision)
        model, processor, device = load_clap(args.model, args.revision)
        if args.cmd == "search":
            vec = embed_texts(model, processor, device, [args.query])[0]
            print(json.dumps(rank_tracks(matrix, meta, vec, args.top), indent=2, default=str))
        else:
            texts = [q["text"] for q in QUERIES]
            vecs = embed_texts(model, processor, device, texts)
            by_query = {q["id"]: rank_tracks(matrix, meta, vecs[i], 5) for i, q in enumerate(QUERIES)}
            print(json.dumps(make_blind_pack(args.db, by_query, args.out), indent=2))
    elif args.cmd == "scorecard":
        print(json.dumps(scorecard(args.db, args.judgements), indent=2))
    elif args.cmd == "tier4-pack":
        from .lyric_search import make_tier4_pack

        print(json.dumps(make_tier4_pack(args.db, args.out), indent=2))
    elif args.cmd == "lyrics-review":
        from .review import make_lyrics_review

        print(json.dumps(make_lyrics_review(args.db, args.out), indent=2))
    elif args.cmd == "lyrics-detect":
        from .lyrics import detect_vocals

        print(json.dumps(detect_vocals(args.db, args.model, args.revision, selected_only=not args.all), indent=2))
    elif args.cmd == "lyrics-transcribe":
        from .lyrics import transcribe_vocals

        print(json.dumps(transcribe_vocals(args.db, args.threshold, selected_only=not args.all, limit=args.limit), indent=2))
    elif args.cmd == "duplicates":
        from .search import duplicate_groups as find_groups

        matrix, meta = load_matrix(args.db, args.model, args.revision)
        groups = find_groups(matrix, meta, args.threshold)
        by_canonical: dict[int, list[str]] = {}
        path_of = {}
        for row in meta:
            path_of.setdefault(row["track_id"], row["rel_path"])
        for tid, canon in groups.items():
            by_canonical.setdefault(canon, []).append(path_of.get(tid, str(tid)))
        dup_groups = {str(c): sorted(ps) for c, ps in by_canonical.items() if len(ps) > 1}
        print(json.dumps({"groups": len(dup_groups), "duplicate_groups": dup_groups}, indent=2))
    elif args.cmd == "lyrics-themes":
        from .lyrics import classify_lyric_themes

        print(json.dumps(classify_lyric_themes(args.db, args.model, args.revision), indent=2))
    elif args.cmd == "check-model":
        result = check_model(args.model, args.revision)
        print(json.dumps(result, indent=2))
        if not result["healthy"]:
            raise SystemExit(f"model failed text-distinctness health check: {result}")
    elif args.cmd == "queries":
        write_queries(args.out)
        print(json.dumps({"queries": len(QUERIES), "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
