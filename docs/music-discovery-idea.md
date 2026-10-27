# Natural-language music discovery

## User's preferred hackathon direction

On October 15, 2026, John described wanting an application that searches his own large indexed music library using natural-language descriptions of how the music should feel. Example: "happy with a twist of fate."

Hard requirement: recommendations must be grounded in the audio, not merely filenames, song titles or tags. A track that sounds happy superficially might have sad underlying emotion. Preserve emotional complexity rather than forcing a single happy/sad label.

John confirmed this as the hackathon project, personally submitted the application, and later reported acceptance and claiming the API credits. On October 27, he requested an exploratory Markdown brief to share with other agents before creating a repository and building. The brief is `music-discovery-exploration-brief.md`; it discusses possible approaches without selecting an architecture. Implementation has not yet been requested. Library size, file formats, instrumental/vocal mix, hardware and licensing/access remain unknown.

## Proposed feasibility scope, not an approved architecture

- Local library, initially a few hundred tracks rather than the entire collection.
- Index excerpts from multiple parts of each track, retaining timestamps.
- Evaluate a pretrained joint audio/text embedding model for candidate retrieval.
- Use a Meta model for query interpretation and evidence-based reranking or explanations, contingent on verified model capabilities. Do not assume its API directly embeds or understands music.
- Show a few recommended tracks with playable evidence excerpts and honest uncertainty.
- Validate ambiguous mood queries against John's own choices before scaling indexing.

Risks: music emotion is subjective; generic audio embeddings may miss narrative mood, irony or emotional changes. Lyrics and musical sound can disagree. Excerpt selection can miss relevant moments. Copyrighted audio must not be uploaded to a provider without appropriate rights and user approval.

Application framing entered: search a filmmaker's own music library by emotional intent rather than remembering track names. The project is chosen; technical methods and final implementation scope remain open.
