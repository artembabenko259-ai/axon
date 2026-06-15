# AXON Bible — Content Source

Human-authored chapter files for the 150-page Knowledge Base.

## Layout

```
.axon/docs/content/
├── en/          # English (full depth)
│   ├── 01_introduction.json
│   ├── 02_skills_masterclass.json
│   ├── ...
│   └── 15_reference_appendix.json
├── ru/          # Russian
└── ua/          # Ukrainian
```

Each chapter file = **10 pages** (subsections).  
15 chapters × 10 pages = **150 pages** per language.

## Subsection schema

Every page includes:

- `eli5` — beginner analogy
- `theoreticalFoundation` — why this exists
- `markdown` — practical deep-dive
- `examples` — 5+ complex examples (command/skill chapters)
- `failureMode` — what goes wrong and how to fix
- `animations` — `[ANIMATION: ...]` UI placeholders
- Optional: `stepsTable`, `sandbox`, `beforeAfter`

## Merge into web portal

```bash
python scripts/merge_docs_content.py
```

Writes merged JSON to `zenith-web/locales/{en,ru,ua}.json`.

## Regenerate seed content

```bash
python scripts/seed_axon_bible.py
python scripts/merge_docs_content.py
```

## Full docs pipeline (AST + Bible)

```bash
python scripts/docs_gen.py
```

Runs AST index generation **and** Bible merge.

View in Zenith: `npm run dev` → http://localhost:3000/docs
