from unittest.mock import MagicMock

import pytest
from response_builders import make_direct_response, make_tool_use_response

from ai_generator import AIGenerator


class TestGenerateResponseDirect:

    def test_returns_content_text_when_no_tool_use(self, ai_generator_direct):
        result = ai_generator_direct.generate_response(query="What is Claude?")
        assert result == "Direct answer."

    def test_tool_choice_auto_set_when_tools_provided(self, ai_generator_direct):
        tools = [
            {
                "name": "search_course_content",
                "description": "search",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            }
        ]
        ai_generator_direct.generate_response(query="test", tools=tools)
        kwargs = ai_generator_direct.client.messages.create.call_args[1]
        assert kwargs["tool_choice"] == {"type": "auto"}

    def test_tools_absent_from_params_when_not_provided(self, ai_generator_direct):
        ai_generator_direct.generate_response(query="test")
        kwargs = ai_generator_direct.client.messages.create.call_args[1]
        assert "tools" not in kwargs


class TestHandleToolExecution:

    def test_tool_manager_called_with_correct_name_and_args(self):
        """Core contract: execute_tool must be called with the name and input Claude chose"""
        gen = AIGenerator(api_key="test", model="test")
        gen.client = MagicMock()
        gen.client.messages.create.side_effect = [
            make_tool_use_response(
                tool_name="search_course_content", tool_input={"query": "Claude API"}
            ),
            make_direct_response("Final answer."),
        ]
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "search result text"

        result = gen.generate_response(
            query="Tell me about Claude",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="Claude API"
        )
        assert result == "Final answer."

    def test_tool_result_block_included_in_second_api_call(self):
        """Tool output must be sent back to Claude as a tool_result message"""
        gen = AIGenerator(api_key="test", model="test")
        gen.client = MagicMock()
        gen.client.messages.create.side_effect = [
            make_tool_use_response(),
            make_direct_response(),
        ]
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "some content"

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        second_call_messages = gen.client.messages.create.call_args_list[1][1][
            "messages"
        ]
        # Last message in the second call should be the user-role tool_result
        last_msg = second_call_messages[-1]
        assert last_msg["role"] == "user"
        assert any(b["type"] == "tool_result" for b in last_msg["content"])

    def test_empty_final_response_content_returns_fallback_string(self):
        """
        After fix: empty content list must return a fallback string instead of
        crashing with IndexError → HTTP 500.
        """
        gen = AIGenerator(api_key="test", model="test")
        gen.client = MagicMock()
        empty_final = MagicMock()
        empty_final.stop_reason = "end_turn"
        empty_final.content = []  # previously crashed here
        gen.client.messages.create.side_effect = [make_tool_use_response(), empty_final]
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        result = gen.generate_response(
            query="test", tools=[{}], tool_manager=tool_manager
        )
        assert isinstance(result, str)
        assert len(result) > 0
