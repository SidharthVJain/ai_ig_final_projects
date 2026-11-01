# DevDigest

**DevDigest** is an AI-powered open-source and research intelligence workspace. It combines live GitHub repository information, semantic search over uploaded research papers, grounded question answering, and multi-agent technical briefings.

The application is split into a **Streamlit frontend** and a **FastAPI backend**. The backend integrates GitHub, Groq, ChromaDB, sentence-transformers, and CrewAI.

## Current capabilities

### 1. GitHub Repository Explorer

- Search public GitHub repositories by keyword and optional programming language.
- Discover recently updated, popular repositories over day, week, or month windows.
- Inspect repository metadata, latest releases, and recent commits.
- Uses the GitHub REST API; an optional personal access token increases available API rate limits.

### 2. Research Assistant (PDF RAG)

- Upload text-based PDF research papers (15 MB maximum by default).
- Extract text and page information with PyMuPDF.
- Split extracted text into overlapping chunks.
- Generate embeddings with `sentence-transformers/all-MiniLM-L6-v2` by default.
- Persist embeddings, chunk text, and metadata in ChromaDB.
- Ask questions against all indexed documents or selected documents.
- Retrieve relevant passages and generate answers through Groq.
- Return source references with filenames, page numbers, and excerpts.
- Detect duplicate uploads using SHA-256 hashes.

**Limitations:** OCR is not included, so scanned/image-only PDFs are not supported unless they contain an embedded text layer. The uploaded original PDF files are not retained by the current RAG implementation; extracted chunks, embeddings, and metadata are stored in ChromaDB.

### 3. AI Briefings (CrewAI)

- Generate a technical briefing through a sequential **Researcher → Writer → Editor** CrewAI workflow.
- Use Groq as the LLM provider (`openai/gpt-oss-120b` by default; configurable with `GROQ_MODEL`).
- Include compact, live GitHub repository metadata, recent release information, and commit summaries.
- Optionally include relevant passages retrieved from indexed research papers.
- Add concise research notes.
- Produce a Markdown briefing with an executive summary, findings, implications, metrics where available, limitations, and source links.
- Download the generated briefing as a Markdown file.
- Includes custom CrewAI tools for Python package-version compatibility checks and benchmark comparisons.

**Current scope and testing note:** The briefing UI and API currently accept at most one GitHub repository per briefing. The current Researcher task is in tool-calling diagnostic mode: it is instructed to invoke the Python library compatibility checker once. The benchmark comparison tool is implemented and registered, but is not part of that diagnostic instruction. Once tool-calling behavior is validated across deployment, the diagnostic instruction can be replaced with normal evidence-led research instructions.

**Other limitations:** Briefing history is not persisted. The workflow is sequential, not hierarchical. The application has no user accounts or per-user document isolation.

## Architecture

```text
Streamlit frontend
    |
    | HTTP (BACKEND_URL)
    v
FastAPI backend
    ├── GitHub REST API client
    ├── PDF processing (PyMuPDF)
    ├── Embeddings (sentence-transformers)
    ├── Persistent vector store (ChromaDB)
    ├── Grounded Q&A (Groq)
    └── CrewAI briefing crew
          ├── Researcher
          ├── Writer
          └── Editor
```

## Technology stack

| Area | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI, Pydantic |
| HTTP client | HTTPX |
| GitHub data | GitHub REST API |
| PDF extraction | PyMuPDF |
| Embeddings | sentence-transformers |
| Vector database | ChromaDB |
| LLM provider | Groq |
| Agent orchestration | CrewAI |
| Custom agent tools | Python package compatibility and benchmark comparison |

## Requirements

- Python **3.12** is the tested project runtime. The repository includes `.python-version` set to `3.12` for platforms that honor it; also select Python 3.12 explicitly in Streamlit Community Cloud's deployment settings.
- A Groq API key for research Q&A and AI briefings.
- A GitHub token is optional, but recommended for higher GitHub API rate limits.
- Internet access is required for GitHub/Groq calls and the initial download of the embedding model.

The dependency files are separated for the two deployment services:

- `requirements.txt` — complete **backend** runtime dependencies; use this on Render.
- `frontend/requirements.txt` — minimal **Streamlit frontend** dependencies; Streamlit Community Cloud should install this file alongside `frontend/app.py`.
- `requirements-dev.txt` — test/development dependencies.

The CrewAI/LiteLLM/MCP versions are deliberately pinned because this project encountered provider compatibility problems with other combinations:

```text
crewai==1.15.33
litellm==1.105.1
mcp==1.30.0
```

These pins are intentional. Do not casually upgrade them without re-running the CrewAI + Groq tool-calling test.

## Local setup

### 1. Create a Python 3.12 environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install backend and frontend dependencies

For local development, install the complete backend dependencies and frontend dependencies into the same environment:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r frontend/requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configure environment variables

Copy the example file:

```bash
cp .env.example .env
```

Configure at least:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
BACKEND_URL=http://127.0.0.1:8000
```

Optional GitHub authentication:

```env
GITHUB_TOKEN=your_github_token
```

RAG configuration defaults:

```env
CHROMA_PERSIST_DIR=./data/chroma
CHROMA_COLLECTION_NAME=devdigest_research
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
RAG_TOP_K=5
MAX_PDF_SIZE_MB=15
```

Never commit `.env` or put real credentials in `.env.example`.

### 4. Start the backend

From the repository root:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation: <http://127.0.0.1:8000/docs>

Health check: <http://127.0.0.1:8000/health>

### 5. Start the frontend

In a second terminal, from the repository root:

```bash
streamlit run frontend/app.py
```

Open the local URL printed by Streamlit.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API welcome message |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/repositories/trending` | Recently pushed popular repositories |
| `GET` | `/api/v1/repositories/search` | Search public repositories |
| `GET` | `/api/v1/repositories/{owner}/{repo}` | Repository metadata |
| `GET` | `/api/v1/repositories/{owner}/{repo}/releases` | Repository releases |
| `GET` | `/api/v1/repositories/{owner}/{repo}/commits` | Recent commits |
| `GET` | `/api/v1/repositories/{owner}/{repo}/activity` | Releases and commits |
| `POST` | `/api/v1/research/documents/upload` | Upload and index a PDF |
| `GET` | `/api/v1/research/documents` | List indexed PDFs |
| `POST` | `/api/v1/research/ask` | Ask a grounded question about PDFs |
| `POST` | `/api/v1/briefings/generate` | Generate a CrewAI briefing |

## Deployment

The recommended deployment is **two services from the same GitHub repository**:

- FastAPI backend on Render.
- Streamlit frontend on Streamlit Community Cloud.

### A. Deploy the backend to Render

Create a new Render **Web Service** connected to this repository.

| Setting | Value |
|---|---|
| Root directory | Repository root (leave blank) |
| Runtime | Python |
| Python version | 3.12 (also enforced by the root `.python-version` file) |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Set these environment variables in Render:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
GITHUB_TOKEN=your_github_token
CHROMA_PERSIST_DIR=/var/data/chroma
CHROMA_COLLECTION_NAME=devdigest_research
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
RAG_TOP_K=5
MAX_PDF_SIZE_MB=15
```

`GITHUB_TOKEN` can be omitted if unauthenticated public GitHub API limits are sufficient.

**Persistent storage is required for ChromaDB.** Attach a Render persistent disk to the backend service, mount it at `/var/data`, and use `CHROMA_PERSIST_DIR=/var/data/chroma`. Without a persistent disk, indexed vectors may be lost on redeploy/restart. The embedding model is downloaded/cached at runtime; plan for the initial model download and memory requirements.

### B. Deploy the frontend to Streamlit Community Cloud

1. Create a new Streamlit app and connect the same GitHub repository.
2. Set the app's main file path to `frontend/app.py`.
3. Ensure the frontend dependency file is `frontend/requirements.txt` (in the same directory as the app entry point).
4. In Streamlit app settings, add the backend URL as a secret or environment variable:

```toml
BACKEND_URL = "https://YOUR-RENDER-SERVICE.onrender.com"
```

The frontend reads `BACKEND_URL` from the environment. If using Streamlit secrets, expose it as an environment variable in the app configuration, or update `frontend/api_client.py` to read `st.secrets` as a fallback.

The frontend does not need the Groq API key or GitHub token; those belong on the backend only.

### C. Verify the deployment

1. Open `https://YOUR-RENDER-SERVICE.onrender.com/health`.
2. Open the Streamlit app and confirm the Repository Explorer can search.
3. Upload a small text-based PDF and confirm it appears in the Research Assistant library.
4. Ask a question and verify that the answer includes source references.
5. Generate a briefing with one repository and no PDF first; then test with an indexed paper.
6. Confirm the ChromaDB index survives a backend redeploy.

## Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite from the repository root:

```bash
pytest -q
```

The tests cover API contracts and core GitHub, PDF-processing, RAG, and briefing behavior. External service calls and model-dependent paths should be tested separately with configured credentials.

## Security and operational limitations

- This MVP has no user authentication or per-user data isolation.
- Indexed research documents are shared by the deployed backend. Do not upload confidential or sensitive papers to a public instance.
- Protect the API before exposing it to untrusted users. Add authentication/authorization, rate limiting, upload controls, and abuse protections.
- Keep Groq and GitHub credentials in Render environment variables, not in GitHub or frontend code.
- ChromaDB must use persistent storage in production.
- The original PDF files are not stored by the current implementation; the extracted chunks, embeddings, and metadata are stored in ChromaDB.
- Groq model availability and rate limits depend on the account and selected model. Keep prompts concise and monitor provider limits.

## Project layout

```text
devdigest/
├── backend/
│   └── app/
│       ├── api/
│       │   └── routes/
│       ├── core/
│       ├── rag/
│       ├── schemas/
│       ├── services/
│       └── tools/
├── frontend/
│   ├── pages/
│   ├── app.py
│   ├── api_client.py
│   └── requirements.txt
├── tests/
├── data/                  # Local ChromaDB data; do not commit
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt       # Render backend dependencies
└── requirements-dev.txt
```

## License

Add a license file before publishing if you intend to permit reuse or contributions. Until then, all rights remain with the repository owner.
