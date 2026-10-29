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
  sound_score?: number | null;
  word_score?: number | null;
  personal_adjustment?: number | null;
  lyric_themes?: string[];
  lyric_text: string | null;
  lyric_trusted?: boolean | null;
  lyric_confidence?: number | null;
  vocal_prob: number | null;
  excerpt_url: string;
  track_url?: string;
};

type Status = {
  model: string;
  device: string;
  tracks_indexed: number;
  tracks_total: number;
  sparse_windows: number;
  feedback_marks: number;
  lyric_windows_trusted?: number;
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
  const [includeLyrics, setIncludeLyrics] = useState(false);
  const [searchedWithLyrics, setSearchedWithLyrics] = useState(false);

  useEffect(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setError("Backend not reachable. Start the app with the launcher."));
  }, []);

  async function runSearch(text: string, withLyrics: boolean) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, top: 5, include_lyrics: withLyrics }),
      });
      if (!response.ok) throw new Error(`search failed (${response.status})`);
      const data = await response.json();
      setResults(data.results);
      setSearchedQuery(data.query);
      setSearchedWithLyrics(Boolean(data.include_lyrics));
    } catch {
      setError("Search failed. The first search loads the model and can take a few seconds — try again.");
    } finally {
      setBusy(false);
    }
  }

  async function onSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    await runSearch(query, includeLyrics);
  }

  function onToggleLyrics(event: React.ChangeEvent<HTMLInputElement>) {
    const next = event.target.checked;
    setIncludeLyrics(next);
    if (searchedQuery) void runSearch(searchedQuery, next);
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
        <label className="lyrics-toggle">
          <input type="checkbox" checked={includeLyrics} onChange={onToggleLyrics} disabled={busy} />
          <span>
            Include lyrics in search
            <span className="toggle-note">
              {typeof status?.lyric_windows_trusted === "number"
                ? ` — matches sung words too, over ${status.lyric_windows_trusted.toLocaleString()} trusted passages only`
                : " — matches sung words too, trusted passages only"}
            </span>
          </span>
        </label>
        {status && typeof status.lyric_windows_trusted !== "number" && (
          <p className="error">
            This page is talking to an older server build, so the lyrics toggle cannot work yet.
            Close the Music Discovery launcher window, start it again, then refresh this page.
          </p>
        )}
        {error && <p className="error">{error}</p>}
        {busy && <p className="hint">First search warms up the model on your GPU. Later ones are quick.</p>}

        {searchedQuery && !busy && (
          <p className="searched">
            Results for <strong>{searchedQuery}</strong> —{" "}
            {searchedWithLyrics
              ? "ranked by sound and sung words together, trusted lyrics only."
              : "judged by sound, not filenames."}
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
                  {typeof result.sound_score === "number" && typeof result.word_score === "number" && (
                    <span>
                      sound {result.sound_score.toFixed(2)} · words {result.word_score.toFixed(2)}
                    </span>
                  )}
                  {typeof result.personal_adjustment === "number" && Math.abs(result.personal_adjustment) >= 0.01 && (
                    <span className={result.personal_adjustment > 0 ? "taste up" : "taste down"}>
                      your taste {result.personal_adjustment > 0 ? "+" : ""}
                      {result.personal_adjustment.toFixed(2)}
                    </span>
                  )}
                </div>
                <audio
                  controls
                  preload="none"
                  src={result.track_url ?? result.excerpt_url}
                  onLoadedMetadata={(event) => {
                    // Start at the matched passage; the whole track stays scrubbable.
                    if (event.currentTarget.currentTime < result.start_seconds) {
                      event.currentTarget.currentTime = result.start_seconds;
                    }
                  }}
                  onError={(event) => {
                    // Formats the browser cannot decode fall back to the passage excerpt.
                    const el = event.currentTarget;
                    if (!el.dataset.fallback) {
                      el.dataset.fallback = "1";
                      el.src = result.excerpt_url;
                      el.load();
                    }
                  }}
                  onPlay={(event) => {
                    document.querySelectorAll("audio").forEach((other) => {
                      if (other !== event.currentTarget) other.pause();
                    });
                  }}
                />
                <div className="player-note">
                  <span>Full track — starts at the matched passage. Scrub to hear the rest.</span>
                  <button
                    type="button"
                    className="from-start"
                    onClick={(event) => {
                      const audio = event.currentTarget.closest(".row")?.querySelector("audio");
                      if (!audio) return;
                      audio.currentTime = 0;
                      void audio.play();
                    }}
                  >
                    Play from start
                  </button>
                </div>
                <div className="words">
                  {result.lyric_text ? (
                    <>
                      {result.lyric_trusted === true ? (
                        <span className="badge trusted">
                          trusted words
                          {typeof result.lyric_confidence === "number" ? ` · ${Math.round(result.lyric_confidence * 100)}%` : ""}
                        </span>
                      ) : result.lyric_trusted === false ? (
                        <span className="badge low">
                          low-trust words
                          {typeof result.lyric_confidence === "number" ? ` · ${Math.round(result.lyric_confidence * 100)}%` : ""}
                        </span>
                      ) : (
                        <span className="badge">words</span>
                      )}
                      <span className="lyric-text">“{result.lyric_text}”</span>
                      {result.lyric_themes && result.lyric_themes.length > 0 && (
                        <span className="themes">likely themes: {result.lyric_themes.join(" · ")}</span>
                      )}
                    </>
                  ) : (
                    "Words: none transcribed for this passage — sound only."
                  )}
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
