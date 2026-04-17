from unittest.mock import MagicMock

import pytest
from response_builders import make_direct_response, make_tool_use_response


def _make_rag(tmp_path, suffix="rag_chroma"):
    """Create a RAGSystem with a throwaway ChromaDB path (embedding patch must already be active)"""
    from config import Config
    from rag_system import RAGSystem

    return RAGSystem(
        Config(ANTHROPIC_API_KEY="test-key", CHROMA_PATH=str(tmp_path / suffix))
    )


def _inject_store(rag, store):
    """Swap the RAGSystem's VectorStore and update all tool references to point at it"""
    rag.vector_store = store
    for tool in rag.tool_manager.tools.values():
        if hasattr(tool, "store"):
            tool.store = store


class TestRAGSystemQuery:

    def test_query_returns_str_and_list_tuple(self, seeded_vector_store, tmp_path):
        """Return type contract: always (str, list) regardless of query content"""
        rag = _make_rag(tmp_path)
        _inject_store(rag, seeded_vector_store)
        rag.ai_generator = MagicMock()
        rag.ai_generator.generate_response.return_value = "Mocked response"

        response, sources = rag.query("What is Claude?")
        assert isinstance(response, str)
        assert isinstance(sources, list)

    def test_query_passes_non_empty_tool_definitions_to_ai_generator(
        self, seeded_vector_store, tmp_path
    ):
        """AI generator must receive tools so Claude can decide to search"""
        rag = _make_rag(tmp_path)
        _inject_store(rag, seeded_vector_store)
        rag.ai_generator = MagicMock()
        rag.ai_generator.generate_response.return_value = "ok"

        rag.query("What is Claude?")

        kwargs = rag.ai_generator.generate_response.call_args[1]
        assert "tools" in kwargs
        assert len(kwargs["tools"]) > 0

    def test_query_content_question_populates_sources_via_tool_execution(
        self, seeded_vector_store, tmp_path
    ):
        """When Claude invokes search_course_content, sources must be returned to the caller"""
        rag = _make_rag(tmp_path)
        _inject_store(rag, seeded_vector_store)

        # Wire the mocked Anthropic client: first call → tool use, second → final text
        rag.ai_generator.client = MagicMock()
        rag.ai_generator.client.messages.create.side_effect = [
            make_tool_use_response(
                tool_name="search_course_content", tool_input={"query": "Claude"}
            ),
            make_direct_response("Claude is made by Anthropic."),
        ]

        _, sources = rag.query("Tell me about Claude")
        assert len(sources) > 0

    def test_query_empty_vector_store_does_not_raise(
        self, empty_vector_store, tmp_path
    ):
        """Cold start (no indexed docs) must not produce an exception or HTTP 500"""
        rag = _make_rag(tmp_path)
        _inject_store(rag, empty_vector_store)
        rag.ai_generator = MagicMock()
        rag.ai_generator.generate_response.return_value = "No content indexed yet."

        response, sources = rag.query("What is in this course?")
        assert isinstance(response, str)

    def test_query_updates_session_history_after_exchange(
        self, seeded_vector_store, tmp_path
    ):
        rag = _make_rag(tmp_path)
        _inject_store(rag, seeded_vector_store)
        rag.ai_generator = MagicMock()
        rag.ai_generator.generate_response.return_value = "Answer."

        session_id = rag.session_manager.create_session()
        rag.query("What is Claude?", session_id=session_id)

        history = rag.session_manager.get_conversation_history(session_id)
        assert history is not None
        assert "What is Claude?" in history
