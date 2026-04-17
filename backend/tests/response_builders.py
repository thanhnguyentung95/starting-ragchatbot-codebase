"""
Reusable Anthropic API response mock builders for test assertions.
"""
from unittest.mock import MagicMock


def make_direct_response(text="Direct answer."):
    """Build a mock Anthropic Message with stop_reason=end_turn"""
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [MagicMock(type="text", text=text)]
    return resp


def make_tool_use_response(tool_name="search_course_content", tool_input=None):
    """Build a mock Anthropic Message with stop_reason=tool_use"""
    block = MagicMock()
    block.type = "tool_use"
    block.id = "toolu_01"
    block.name = tool_name
    block.input = tool_input or {"query": "Claude API basics"}

    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [block]
    return resp
