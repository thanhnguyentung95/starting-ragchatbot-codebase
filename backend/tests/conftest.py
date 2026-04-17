import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Make backend modules and tests/ helpers importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from response_builders import make_direct_response, make_tool_use_response  # noqa: E402

from ai_generator import AIGenerator  # noqa: E402
from models import Course, CourseChunk, Lesson  # noqa: E402
from search_tools import CourseSearchTool  # noqa: E402
from vector_store import VectorStore  # noqa: E402

# ---------------------------------------------------------------------------
# Embedding stub — satisfies ChromaDB 1.0.x EmbeddingFunction interface
# without downloading any ML model
# ---------------------------------------------------------------------------


class _MockEmbeddingFunction:
    """Minimal stub accepted by ChromaDB's embedding function validation"""

    @classmethod
    def name(cls) -> str:
        return "mock-embedding"

    @classmethod
    def is_legacy(cls) -> bool:
        return False

    def __call__(self, input):  # ChromaDB passes `input`, not `texts`
        return [[float(i % 10) / 10.0 for i in range(384)] for _ in input]

    def get_config(self):
        return {}

    @classmethod
    def build_from_config(cls, config):
        return cls()

    def validate_config_update(self, old_config, new_config):
        pass


PATCH_TARGET = "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
MOCK_EF = _MockEmbeddingFunction()

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

TEST_COURSE = Course(
    title="Introduction to Claude API",
    course_link="https://example.com/course",
    instructor="Test Instructor",
    lessons=[
        Lesson(
            lesson_number=1,
            title="Getting Started",
            lesson_link="https://example.com/lesson/1",
        ),
        Lesson(
            lesson_number=2,
            title="Tool Use",
            lesson_link="https://example.com/lesson/2",
        ),
        Lesson(
            lesson_number=3,
            title="Advanced Topics",
            lesson_link="https://example.com/lesson/3",
        ),
    ],
)

TEST_CHUNKS = [
    CourseChunk(
        content="Claude is an AI assistant made by Anthropic for helpful, harmless tasks.",
        course_title="Introduction to Claude API",
        lesson_number=1,
        chunk_index=0,
    ),
    CourseChunk(
        content="Tools allow Claude to call external functions and retrieve data dynamically.",
        course_title="Introduction to Claude API",
        lesson_number=2,
        chunk_index=1,
    ),
    CourseChunk(
        content="Prompt engineering and system prompts significantly improve response quality.",
        course_title="Introduction to Claude API",
        lesson_number=3,
        chunk_index=2,
    ),
]

# ---------------------------------------------------------------------------
# VectorStore fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_vector_store(tmp_path):
    """VectorStore in a temp dir with mock embeddings, pre-loaded with 3 chunks"""
    with patch(PATCH_TARGET, return_value=MOCK_EF):
        store = VectorStore(
            chroma_path=str(tmp_path / "chroma"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=5,
        )
        store.add_course_metadata(TEST_COURSE)
        store.add_course_content(TEST_CHUNKS)
        yield store


@pytest.fixture
def empty_vector_store(tmp_path):
    """VectorStore with no data — triggers n_results-overflow and cold-start paths"""
    with patch(PATCH_TARGET, return_value=MOCK_EF):
        yield VectorStore(
            chroma_path=str(tmp_path / "chroma_empty"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=5,
        )


@pytest.fixture
def course_search_tool(seeded_vector_store):
    return CourseSearchTool(seeded_vector_store)


# ---------------------------------------------------------------------------
# AIGenerator fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ai_generator_direct():
    """AIGenerator whose Anthropic client always returns a text response (no tool use)"""
    gen = AIGenerator(api_key="test-key", model="claude-test")
    gen.client = MagicMock()
    gen.client.messages.create.return_value = make_direct_response()
    return gen


@pytest.fixture
def ai_generator_tool_use():
    """AIGenerator whose Anthropic client first requests tool use, then returns text"""
    gen = AIGenerator(api_key="test-key", model="claude-test")
    gen.client = MagicMock()
    gen.client.messages.create.side_effect = [
        make_tool_use_response(),
        make_direct_response("Based on search results, Claude is an AI assistant."),
    ]
    return gen
