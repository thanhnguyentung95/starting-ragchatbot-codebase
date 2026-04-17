import pytest
from unittest.mock import MagicMock, patch
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchToolExecute:

    def test_execute_basic_query_returns_formatted_string(self, course_search_tool):
        """Happy path: seeded store returns course-labelled content"""
        result = course_search_tool.execute(query="Claude AI assistant")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Introduction to Claude API" in result

    def test_execute_empty_store_does_not_raise(self, empty_vector_store):
        """Empty ChromaDB must not crash — returns a string (error or 'no content')"""
        tool = CourseSearchTool(empty_vector_store)
        result = tool.execute(query="anything")
        # The critical assertion: no exception propagates
        assert isinstance(result, str)

    def test_execute_unknown_course_name_returns_no_course_found(self, course_search_tool):
        # _resolve_course_name is semantic — mock it to return None (no match) since all
        # test embeddings are identical and cannot express dissimilarity.
        # This tests that CourseSearchTool correctly surfaces the "no course found" error path.
        with patch.object(course_search_tool.store, "_resolve_course_name", return_value=None):
            result = course_search_tool.execute(query="something", course_name="XYZ Nonexistent 9999")
        assert "No course found" in result

    def test_execute_course_name_filter_resolves_partial_match(self, course_search_tool):
        """Partial course name should resolve via semantic search to the seeded course"""
        result = course_search_tool.execute(query="Claude", course_name="Introduction")
        assert isinstance(result, str)
        assert "Introduction to Claude API" in result

    def test_execute_lesson_number_filter_returns_correct_lesson(self, course_search_tool):
        result = course_search_tool.execute(query="tool use", lesson_number=2)
        assert isinstance(result, str)
        assert "Lesson 2" in result

    def test_execute_populates_last_sources_on_hit(self, course_search_tool):
        course_search_tool.last_sources = []
        course_search_tool.execute(query="Claude")
        assert len(course_search_tool.last_sources) > 0
        first = course_search_tool.last_sources[0]
        assert "label" in first

    def test_execute_returns_error_string_on_store_failure_without_raising(self, course_search_tool):
        """Store errors must be surfaced as strings, never re-raised"""
        course_search_tool.store = MagicMock()
        course_search_tool.store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error="DB unavailable"
        )
        result = course_search_tool.execute(query="anything")
        assert result == "DB unavailable"
