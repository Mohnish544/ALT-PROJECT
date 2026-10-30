# Retrieval-Based Intelligent QA System for Healthcare Documents

> Context-aware question answering for healthcare documents

Retrieval-Based Intelligent QA System for Healthcare Documents is a full-stack retrieval-augmented generation (RAG) application for asking questions across clinical notes, medical guidelines, reports, and other healthcare documents. It combines semantic search, optional BM25 ranking, a MedQuAD general medical knowledge base, and configurable large-language-model (LLM) providers to produce answers with source citations and retrieval metadata.

> **Important:** This system is an educational and research tool. It is not a medical device and does not replace a qualified healthcare professional, diagnosis, or treatment plan.

## What it does

- Uploads and indexes `.pdf`, `.docx`, `.txt`, and other supported text documents.
- Extracts and cleans document text, then splits it into overlapping chunks.
- Builds persistent FAISS indexes for uploaded documents.
- Retrieves relevant passages with dense embeddings and lexical BM25 ranking.
- Falls back to the general MedQuAD knowledge base when uploaded-document matches are weak.
- Generates grounded answers through Groq, OpenAI, Anthropic, Ollama, or a deterministic mock provider.
- Displays source passages, scores, source type, retrieval strategy, and fallback details.
- Keeps short-lived conversation history for follow-up questions.
- Includes document management, system settings, evaluation, and architecture views.
- Serves the compiled frontend directly from FastAPI in production.

## Architecture

```text
                         ┌──────────────────────────────┐
                         │ React + TypeScript + Vite     │
                         │ Chat · Documents · Evaluation │
                         │ Architecture · Settings      │
                         └──────────────┬───────────────┘
                                        │ /api
                         ┌──────────────▼───────────────┐
                         │ FastAPI                       │
                         │ Upload · Chat · Status        │
                         │ Documents · Settings          │
                         │ Evaluation                    │
                         └───────┬───────────┬──────────┘
                                 │            │
                    ┌────────────▼───┐  ┌────▼─────────────┐
                    │ Preprocessing  │  │ Retrieval         │
                    │ Extract        │  │ Dense + BM25      │
                    │ Clean          │  │ Document / KB     │
                    │ Chunk          │  │ FAISS indexes     │
                    └────────────────┘  └────┬─────────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │ LLM provider      │
                                   │ Groq · OpenAI     │
                                   │ Anthropic · Ollama│
                                   │ Mock              │
                                   └───────────────────┘
```

### Main technologies

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, React Router, Zustand, React Markdown |
| API | FastAPI, Uvicorn, Pydantic |
| Retrieval | Sentence Transformers, FAISS, BM25, scikit-learn |
| Document processing | pypdf, pdfplumber, python-docx, chardet |
| LLM integrations | Groq, OpenAI, Anthropic, Ollama |
| Knowledge base | MedQuAD JSONL + persistent FAISS index |
| Testing | pytest, pytest-asyncio, FastAPI test client |

## Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer and npm
- At least 4 GB of free disk space for Python packages and the default embedding model
- An LLM provider:
  - **Groq** is the quickest cloud setup.
  - **Ollama** runs locally and needs no API key.
  - **Mock** requires no provider and is useful for UI/API smoke tests.

The first backend startup downloads the configured sentence-transformer model (about 400 MB with the default configuration) if it is not already cached.

## Quick start

### 1. Clone and configure

```powershell
git clone https://github.com/Mohnish544/ALT-PROJECT.git
cd ALT-PROJECT
Copy-Item .env.example .env
```

Open `.env` and choose a provider. For a Groq setup:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

For a local Ollama setup:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
```

For a provider-free smoke test:

```dotenv
LLM_PROVIDER=mock
```

Never commit `.env` or provider API keys.

### 2. Install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

If PowerShell blocks activation, run the commands from an activated terminal or use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 3. Prepare the general knowledge base

The repository includes the `scripts\download_medquad.py` helper for obtaining MedQuAD. Run it when the knowledge-base JSONL is not already present:

```powershell
python scripts\download_medquad.py
python scripts\build_kb_index.py --max-entries 2000
```

Use the complete dataset for a fuller index:

```powershell
python scripts\build_kb_index.py
```

The `--max-entries 2000` option is useful for a fast local demo. Add `--force` to rebuild an existing index.

### 4. Start the API

From the repository root:

```powershell
python -m backend.api.main
```

The API starts at <http://localhost:8000>. Interactive API documentation is available at:

- Swagger UI: <http://localhost:8000/api/docs>
- ReDoc: <http://localhost:8000/api/redoc>
- OpenAPI JSON: <http://localhost:8000/api/openapi.json>

The first startup may take a few minutes while the embedding model and indexes load.

### 5. Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to the FastAPI server at `http://localhost:8000`.

## Production-style serving

Build the frontend and then start FastAPI from the repository root:

```powershell
cd frontend
npm run build
cd ..
$env:APP_ENV = "production"
python -m backend.api.main
```

When `frontend\dist` exists, FastAPI serves the compiled client at <http://localhost:8000>.

## Using the QA system

1. Open **Documents** and upload a clinical note, guideline, report, or supported text file.
2. Wait for processing to complete. The system extracts text, chunks it, creates embeddings, and persists the document index.
3. Open **Chat**, select the document scope if needed, and ask a focused question.
4. Review the answer alongside its cited source chunks and retrieval details.
5. Continue the conversation with follow-up questions; the current session retains up to 20 turns.
6. Use **Evaluation** to run the bundled question-answer evaluation and **Settings** to inspect or update retrieval/provider settings.

## Configuration reference

All settings can be placed in `.env`. The complete starter configuration is in [.env.example](./.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` in code / `groq` in `.env.example` | `groq`, `openai`, `anthropic`, `ollama`, or `mock` |
| `GROQ_API_KEY` | — | API key when using Groq |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq model name |
| `OPENAI_API_KEY` | — | API key when using OpenAI |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `ANTHROPIC_API_KEY` | — | API key when using Anthropic |
| `ANTHROPIC_MODEL` | `claude-3-haiku-20240307` | Anthropic model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `mistral` | Local Ollama model |
| `EMBEDDING_MODEL` | `pritamdeka/S-PubMedBert-MS-MARCO` | Sentence-transformer model |
| `CHUNK_SIZE` | `400` | Approximate chunk size |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K` | `5` | Number of chunks retrieved |
| `DOC_FALLBACK_THRESHOLD` | `0.35` | Minimum document score before KB fallback |
| `UPLOAD_DIR` | `data/uploads` | Uploaded source files |
| `FAISS_INDEX_DIR` | `data/indexes` | Per-document FAISS indexes |
| `KB_INDEX_PATH` | `data/kb_index/medquad.faiss` | Knowledge-base vector index |
| `KB_METADATA_PATH` | `data/kb_index/medquad_meta.pkl` | Knowledge-base metadata |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated CORS origins |
| `APP_ENV` | `development` | Enables reload in development |
| `LOG_LEVEL` | `INFO` | Backend log level |

## API overview

All application endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/upload` | Upload and index a document |
| `GET` | `/api/documents` | List indexed documents |
| `GET` | `/api/documents/{doc_id}` | Get document details |
| `DELETE` | `/api/documents/{doc_id}` | Delete a document and its index |
| `POST` | `/api/chat` | Ask a grounded question |
| `GET` | `/api/chat/history/{session_id}` | Read conversation history |
| `DELETE` | `/api/chat/history/{session_id}` | Clear conversation history |
| `GET` | `/api/status` | Check system and provider status |
| `GET` | `/api/evaluate` | Run the bundled evaluation |
| `GET` | `/api/settings` | Read active settings |
| `PUT` | `/api/settings` | Update supported runtime settings |

See the generated Swagger UI at `/api/docs` for request and response schemas.

## Development commands

### Backend

```powershell
# Run all backend tests
pytest backend\tests -q

# Run a focused test module
pytest backend\tests\test_retrieval.py -q
```

### Frontend

```powershell
cd frontend
npm run lint
npm run build
npm run preview
```

## Repository layout

```text
.
├── backend/
│   ├── api/                 FastAPI app, models, and route handlers
│   ├── embeddings/          Embedding model and FAISS indexing
│   ├── evaluation/          Evaluation dataset, runner, and metrics
│   ├── knowledge_base/      MedQuAD index loading/building
│   ├── llm/                 Provider adapters and prompts
│   ├── preprocessing/       Extraction, cleaning, and chunking
│   ├── retrieval/           Dense/lexical retrieval and fallback logic
│   ├── storage/             Persistent document metadata and files
│   └── tests/               Backend test suite
├── frontend/
│   ├── src/components/      Shared UI components
│   ├── src/pages/           Application screens
│   ├── src/services/        Backend API client
│   └── src/store/           Client state
├── data/
│   ├── sample_docs/         Small example documents
│   ├── medquad/             Downloaded MedQuAD JSONL (ignored)
│   ├── uploads/             User uploads (ignored)
│   └── indexes/             Generated FAISS indexes (ignored)
├── scripts/                 Dataset and index preparation helpers
├── .env.example             Environment configuration template
└── README.md
```

## Data, privacy, and limitations

- Uploaded files and generated indexes are stored locally under `data\` by default.
- If a cloud provider is selected, retrieved context and questions are sent to that provider for answer generation. Review the provider's data policy before using sensitive information.
- Chat history is held in an in-memory process-local store and is lost when the API restarts.
- There is no authentication or authorization layer in the development setup. Do not expose the service directly to the public internet without adding access control, TLS, rate limiting, and production storage.
- Retrieval quality depends on document quality, chunking settings, embedding model, and the selected provider.
- Answers can be incomplete or incorrect even when citations are present. Always verify clinically significant information against authoritative sources and qualified professionals.

## Troubleshooting

### The API fails during startup

Check that the virtual environment is active, dependencies installed successfully, and the configured embedding model can be downloaded. If using a cloud LLM, confirm the provider key and model name.

### Chat reports that no provider is available

Set `LLM_PROVIDER=mock` for a provider-free smoke test, or configure the matching API key/model variables in `.env`. For Ollama, make sure the Ollama service is running and the configured model has been pulled.

### The frontend cannot reach the API

Run both servers, verify that FastAPI is listening on port 8000, and keep the Vite development server on port 5173. For a different API port, update the proxy target in [frontend/vite.config.ts](./frontend/vite.config.ts).

### Retrieval always falls back to the knowledge base

Make sure the document finished processing and appears as `ready` in **Documents**. Try a question using terminology present in the document, then adjust `TOP_K`, `CHUNK_SIZE`, or `DOC_FALLBACK_THRESHOLD` if needed.

### The knowledge base is unavailable

Run the download and index commands in the knowledge-base section. A document-only workflow can still be tested once an uploaded document has been indexed, but general-knowledge fallback requires the MedQuAD index.

## License

No license file is currently included. Treat this repository as a course/research project and check with the project maintainers before redistributing or deploying it.
