"""
API endpoint tests.

Uses a standalone test app that mirrors app.py routes without mounting the
../frontend static directory, which does not exist in the test environment.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Model definitions — mirror app.py exactly
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class Source(BaseModel):
    label: str
    link: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------

def _build_test_app(rag_system) -> FastAPI:
    """Create a minimal FastAPI app wired to *rag_system* (no static-file mount)."""
    app = FastAPI()

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        rag_system.session_manager.clear_session(session_id)
        return {"status": "cleared", "session_id": session_id}

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_rag_system):
    """TestClient backed by the standalone test app."""
    with TestClient(_build_test_app(mock_rag_system)) as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_200_for_valid_payload(self, client):
        response = client.post("/api/query", json={"query": "What is Claude?"})
        assert response.status_code == 200

    def test_response_contains_answer_sources_session_id(self, client):
        data = client.post("/api/query", json={"query": "What is Claude?"}).json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_answer_is_non_empty_string(self, client):
        data = client.post("/api/query", json={"query": "What is Claude?"}).json()
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

    def test_creates_new_session_when_none_provided(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Hello"})
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_reuses_existing_session_id(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Hello", "session_id": "existing-session"})
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_session_id_from_request_forwarded_to_rag_query(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Q", "session_id": "sess-42"})
        mock_rag_system.query.assert_called_once_with("Q", "sess-42")

    def test_sources_contain_label_field(self, client):
        data = client.post("/api/query", json={"query": "What is Claude?"}).json()
        assert data["sources"][0]["label"] == "Introduction to Claude API - Lesson 1"

    def test_returns_422_when_query_field_missing(self, client):
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_returns_500_on_rag_failure(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("vector store error")
        response = client.post("/api/query", json={"query": "test"})
        assert response.status_code == 500

    def test_500_detail_contains_error_message(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("db unavailable")
        data = client.post("/api/query", json={"query": "test"}).json()
        assert "db unavailable" in data["detail"]


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/courses").status_code == 200

    def test_response_contains_total_courses_and_titles(self, client):
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 2
        assert "Introduction to Claude API" in data["course_titles"]

    def test_course_titles_is_list(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["course_titles"], list)

    def test_returns_500_on_analytics_failure(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("analytics error")
        response = client.get("/api/courses")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestSessionEndpoint:

    def test_returns_200(self, client):
        assert client.delete("/api/session/sess-001").status_code == 200

    def test_response_has_cleared_status(self, client):
        data = client.delete("/api/session/sess-001").json()
        assert data["status"] == "cleared"

    def test_response_echoes_session_id(self, client):
        data = client.delete("/api/session/my-session").json()
        assert data["session_id"] == "my-session"

    def test_delegates_to_session_manager_clear_session(self, client, mock_rag_system):
        client.delete("/api/session/target-session")
        mock_rag_system.session_manager.clear_session.assert_called_once_with("target-session")
