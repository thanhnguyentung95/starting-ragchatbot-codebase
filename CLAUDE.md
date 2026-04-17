# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the backend server (serves both API and frontend)
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at `http://localhost:8000` | Swagger docs at `http://localhost:8000/docs`

No test or lint commands are configured in this project.

## Environment

Copy `.env.example` to `.env` and set:
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials stored in `/docs`.

**Request flow:**
1. User query → `POST /api/query` (FastAPI in `backend/app.py`)
2. `rag_system.py` orchestrates the pipeline
3. `vector_store.py` (ChromaDB) performs semantic similarity search over chunked course content
4. `search_tools.py` exposes a `search_course_content` tool definition for Claude's tool-use API
5. `ai_generator.py` calls Claude with conversation history + tool; Claude may call the search tool, then generates a final answer
6. Response with sources returned to frontend (`frontend/script.js`)

**Storage:** ChromaDB persists locally at `./chroma_db/` with two collections:
- `course_catalog` — course metadata and lesson info
- `course_content` — chunked lesson text with embeddings (model: `all-MiniLM-L6-v2`)

**Session memory:** `session_manager.py` keeps the last `MAX_HISTORY` (default: 2) conversation turns in memory per `session_id`.

## Key Backend Modules

| File | Responsibility |
|---|---|
| `backend/app.py` | FastAPI routes, CORS, static file serving |
| `backend/config.py` | All tuneable constants (model, chunk size, etc.) |
| `backend/rag_system.py` | Top-level pipeline coordinator |
| `backend/vector_store.py` | ChromaDB wrapper — indexing and search |
| `backend/ai_generator.py` | Claude API calls, tool execution loop |
| `backend/document_processor.py` | Parses `.txt` course files into `Course`/`Lesson`/`CourseChunk` objects |
| `backend/search_tools.py` | Tool schema definitions (`CourseSearchTool`, `ToolManager`) |
| `backend/session_manager.py` | In-memory conversation history per session |
| `backend/models.py` | Pydantic models shared across modules |

## Course Document Format

Documents in `/docs` must follow this structure for the parser to extract metadata:

```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[Content...]

Lesson 1: [Next Lesson Title]
...
```

## Configuration Defaults (`backend/config.py`)

- `ANTHROPIC_MODEL`: `claude-sonnet-4-20250514`
- `EMBEDDING_MODEL`: `all-MiniLM-L6-v2`
- `CHUNK_SIZE`: 800 chars | `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 search results per query
- `MAX_HISTORY`: 2 conversation turns
