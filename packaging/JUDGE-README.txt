Music Discovery - hackathon build (portable)

WHAT IT DOES
Describe the music you need ("happy with a twist of fate", "sparse solo
piano") and it finds matching passages in YOUR music folder, plays the full
track from the matched moment, and learns from your usable / close / wrong
votes. Audio never leaves your machine. Only optional query-wording help
(Meta Spark, off by default) would send query text, never audio.

HOW TO RUN
1. Unzip this folder anywhere.
2. Double-click MusicDiscovery.bat and keep the window open.
3. Your browser opens http://127.0.0.1:8765
4. First run only: paste the path of a music folder and choose
   "Index this folder". Small folders take minutes. The search model
   (about 1.6 GB) downloads once from Hugging Face, so first run needs
   internet.
5. Search. You get 20 songs by default; use the Results selector for
   5, 10, 20, or 50.

NOTES
- Windows only in this build. An NVIDIA GPU makes indexing much faster;
  CPU works for small folders.
- Everything you index and vote on stays in the data folder next to the
  app. Delete it to start over. No account, no uploads.
- Lyrics search covers passages already transcribed in a library. Fresh
  folders index sound first; lyric transcription is not automatic in
  this build.
