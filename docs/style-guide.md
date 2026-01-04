# PyPNM-CMTS documentation style guide

Follow the PyPNM documentation conventions so the docs remain consistent across repos.

## Headings

- Use sentence case (for example, `## System configuration`).
- Keep heading hierarchy shallow and avoid skipping levels.
 - Capitalize proper nouns and product names (for example, `PyPNM-CMTS`).

## Voice and tone

- Default to second-person imperative for task guides.
- Use concise, reference-style language for APIs and schemas.
- Use GitHub-style notes (`> **Note:** ...`) for critical context.
 - When appropriate, include a one-line summary at the top of each page to help readers orient quickly.

## Linking and navigation

- Start each page with a one-sentence summary.
- Use short “Next steps” or “See also” lists instead of long tables of contents.
- Prefer relative links so GitHub and MkDocs share the same paths.

## Lists and code

- Use unordered lists for concepts and ordered lists for procedures.
- Add fenced code blocks with language hints (` ```bash `).
- Keep code samples copy-paste ready.
 - Wrap short CLI commands in fenced `bash` blocks and keep examples minimal and runnable.
