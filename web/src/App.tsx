import { useEffect, useState } from "react";

type Result = {
  track_id: number;
  window_id: number;
  file_name: string;
  rel_path: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number | null;
  score: number;
  lyric_text: string | null;
  vocal_prob: number | null;
  excerpt_url: string;
};

type Status = {
  model: string;
  device: string;
  tracks_indexed: number;
  tracks_total: number;
  sparse_windows: number;
  feedback_marks: number;
};

const MARKS = ["usable", "close", "wrong"] as const;
type Mark = (typeof MARKS)[number];

function fmt(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [searchedQuery, setSearchedQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [marks, setMarks] = useState<Record<number, Mark>>({});

  useEffect(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setError("Backend not reachable. Start the app with the launcher."));
  }, []);

  async function onSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top: 5 }),
      });
      if (!response.ok) throw new Error(`search failed (${response.status})`);
      const data = await response.json();
      setResults(data.results);
      setSearchedQuery(data.query);
    } catch {
      setError("Search failed. The first search loads the model and can take a few seconds — try again.");
    } finally {
      setBusy(false);
    }
  }

  async function onMark(result: Result, mark: Mark) {
    setMarks((prev) => ({ ...prev, [result.window_id]: mark }));
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query_text: searchedQuery,
        track_id: result.track_id,
        window_id: result.window_id,
        mark,
      }),
    }).catch(() => undefined);
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">Music Discovery</div>
        <div className="status">
          {status
            ? `${status.tracks_indexed.toLocaleString()} tracks · ${status.sparse_windows.toLocaleString()} passages · ${status.device} · audio stays on this machine`
            : "checking index…"}
        </div>
      </header>

      <main className="main">
        <h1 className="headline">Describe the feeling. Hear the passage.</h1>
        <form className="search" onSubmit={onSearch}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try "happy with a twist of fate"'
            aria-label="Describe the music you need"
          />
          <button type="submit" disabled={busy}>
            {busy ? "Listening…" : "Search"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        {busy && <p className="hint">First search warms up the model on your GPU. Later ones are quick.</p>}

        {searchedQuery && !busy && (
          <p className="searched">
            Results for <strong>{searchedQuery}</strong> — judged by sound, not filenames.
          </p>
        )}

        <ol className="results">
          {results.map((result, index) => (
            <li key={result.window_id} className="row">
              <div className="rank">{index + 1}</div>
              <div className="body">
                <div className="file">{result.file_name}</div>
                <div className="meta">
                  <span>{result.rel_path}</span>
                  <span>
                    passage {fmt(result.start_seconds)}–{fmt(result.end_seconds)}
                    {result.duration_seconds ? ` of ${fmt(result.duration_seconds)}` : ""}
                  </span>
                  <span>match {result.score.toFixed(2)}</span>
                </div>
                <audio
                  controls
                  preload="none"
                  src={result.excerpt_url}
                  onPlay={(event) => {
                    document.querySelectorAll("audio").forEach((other) => {
                      if (other !== event.currentTarget) other.pause();
                    });
                  }}
                />
                <div className="words">
                  {result.lyric_text
                    ? `Words: ${result.lyric_text}`
                    : "Words: not transcribed yet — judged on sound alone."}
                </div>
              </div>
              <div className="marks" role="group" aria-label="Your mark">
                {MARKS.map((mark) => (
                  <button
                    key={mark}
                    className={marks[result.window_id] === mark ? `mark active ${mark}` : "mark"}
                    onClick={() => onMark(result, mark)}
                  >
                    {mark}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ol>

        {!busy && searchedQuery && results.length === 0 && (
          <p className="hint">No passages yet. Try a plainer description of the sound.</p>
        )}
      </main>

      <footer className="footer">
        Marks are saved to your local scorecard. Closing this tab loses nothing.
      </footer>
    </div>
  );
}
