# PaperAI — AI Academic Reading Workspace

Upload an English academic paper, read it side by side with a Traditional Chinese translation, and ask questions that are answered from the paper itself — every answer carries clickable citations that jump to the source paragraph.

Built from [SPEC.md](./SPEC.md).

```
Upload PDF → Parse structure → Translate → Bilingual reading → Ask AI (RAG) → Click citation → Jump to paragraph
```

## Stack

| Layer     | Tech                                                        |
| --------- | ----------------------------------------------------------- |
| Frontend  | Next.js 16 · React 19 · TypeScript · Tailwind v4 · shadcn/ui · KaTeX |
| Backend   | Python 3.12 · FastAPI · SQLAlchemy 2 · PyMuPDF · NumPy       |
| Database  | SQLite (default, zero setup) **or** PostgreSQL + pgvector    |
| Storage   | Local disk (dev) **or** S3-compatible (AWS S3 / R2 / Supabase) |
| AI        | Provider abstraction — OpenAI, Anthropic, or a fully offline **mock** |

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env          # optional — defaults run fully offline
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000, drop a PDF — or click **Try demo paper** to run the whole pipeline on a bundled sample paper.

### 3. Real AI (optional)

Edit `backend/.env`:

```env
LLM_PROVIDER=openai          # or anthropic
EMBEDDING_PROVIDER=openai
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

Without keys the `mock` providers still run the complete flow: the translation column shows the glossary-annotated source text and the assistant answers extractively (real sentences from the paper with citations), so the UI, citation navigation, search, notes and highlights all work.

### 4. PostgreSQL + pgvector (optional)

```bash
docker compose up -d db
# backend/.env
DATABASE_URL=postgresql+psycopg://paperai:paperai@localhost:5432/paperai
```

Tables and the `vector` extension are created on startup. On SQLite, embeddings are stored as JSON and scored in NumPy; on PostgreSQL the query runs in pgvector.

## Features (MVP scope, SPEC §69)

- Drag-and-drop PDF upload with file info and live processing progress
- Text extraction (PyMuPDF) with two-column reading order and paragraph merging
- Heading detection + semantic section classification (Abstract, Introduction, Method, Results, …)
- Stable paragraph IDs (`…__paragraph_0042`), page mapping, figure / table / caption detection
- Traditional Chinese translation with terminology memory and a translation cache
- Reading modes: English · 中文 · 中英對照 (default), linked paragraph hover highlighting
- AI assistant with context modes (Entire Paper / Current Section / Current Page / Selected Text), explanation levels (Beginner → Researcher), quick actions
- RAG over paragraph chunks; answers cite `[Page · Section · Paragraph]`; citations are validated against the document and clicking one scrolls to and flashes the paragraph
- Selection toolbar: Explain · Translate · Summary · Ask AI · Highlight · Add Note
- Exact and semantic search (⌘K), notes & highlights, structured summaries, Markdown export
- Light / dark / system theme; desktop three-column layout, tablet panel collapse, mobile tabs

## Project structure

```
frontend/src
  app/                 upload page, /papers/[id] workspace
  components/
    workspace/         header, three-column layout, shared workspace context
    paper-sidebar/     outline, figures, tables
    paper-reader/      bilingual reader, KaTeX, selection toolbar
    ai-chat/           assistant panel, citations, quick actions
    notes/ search/ ui/
  hooks/ lib/ types/
backend/app
  api/                 documents, chat, search, annotations, summary
  models/ schemas/     SQLAlchemy models, camelCase Pydantic schemas
  services/
    pdf/               PyMuPDF extraction
    parsing/           structure detection
    translation/       provider abstraction + terminology
    embeddings/ rag/   embedding providers, chunking, retrieval
    llm/ chat/         LLM providers, grounded prompting, citation validation
    pipeline.py        background processing with progress
    storage.py         local / S3 storage abstraction
```

## API (SPEC §51–55)

| Method | Path |
| ------ | ---- |
| POST | `/api/documents/upload` · `/api/documents/demo` |
| GET / PATCH / DELETE | `/api/documents/{id}` |
| GET | `/api/documents/{id}/sections` · `/paragraphs` · `/figures` · `/tables` · `/file` |
| POST | `/api/documents/{id}/translate` |
| POST | `/api/documents/{id}/chat` |
| POST | `/api/documents/{id}/search` |
| GET / POST | `/api/documents/{id}/notes` · `DELETE /api/notes/{id}` |
| GET / POST | `/api/documents/{id}/highlights` · `DELETE /api/highlights/{id}` |
| GET / POST | `/api/documents/{id}/summary?length=one_sentence|short|detailed` |

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest
cd frontend && npm run lint && npm run build
```
