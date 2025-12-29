"""Bridge for converting Strands events to AG-UI protocol events."""

import json
import uuid
from typing import Any, Dict, List, Optional

from ag_ui.core.events import (
    EventType,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)


class StrandsToAGUIBridge:
    """Bridge for converting Strands agent events to AG-UI protocol events."""

    def __init__(self):
        self.current_message_id = None
        self.current_tool_call_id = None
        self.tool_args_buffer = ""
        self.tool_name = None

    def start_run(self, thread_id: str, run_id: str) -> RunStartedEvent:
        return RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread_id, run_id=run_id)

    def start_message(self, role: str = "assistant") -> TextMessageStartEvent:
        self.current_message_id = str(uuid.uuid4())
        return TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START, message_id=self.current_message_id, role=role
        )

    def add_text_content(self, text: str) -> TextMessageContentEvent:
        return TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT, message_id=self.current_message_id, delta=text
        )

    def end_message(self) -> TextMessageEndEvent:
        return TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END, message_id=self.current_message_id
        )

    def start_tool_call(self, tool_name: str) -> ToolCallStartEvent:
        self.current_tool_call_id = str(uuid.uuid4())
        self.tool_name = tool_name
        self.tool_args_buffer = ""
        return ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=self.current_tool_call_id,
            tool_call_name=tool_name,
            parent_message_id=self.current_message_id,
        )

    def add_tool_args(self, args_chunk: str) -> ToolCallArgsEvent:
        self.tool_args_buffer += args_chunk
        return ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS, tool_call_id=self.current_tool_call_id, delta=args_chunk
        )

    def end_tool_call(self, result: str = "Tool executed successfully") -> List[Any]:
        events = [
            ToolCallResultEvent(
                type=EventType.TOOL_CALL_RESULT,
                tool_call_id=self.current_tool_call_id,
                message_id=self.current_message_id,
                content=result,
                role="tool",
            ),
            ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id=self.current_tool_call_id),
        ]
        self.current_tool_call_id = None
        self.tool_args_buffer = ""
        self.tool_name = None
        return events

    def finish_run(self, thread_id: str, run_id: str, result: Any = None) -> RunFinishedEvent:
        return RunFinishedEvent(
            type=EventType.RUN_FINISHED, thread_id=thread_id, run_id=run_id, result=result
        )

    def error_event(self, error_message: str) -> RunErrorEvent:
        return RunErrorEvent(type=EventType.RUN_ERROR, message=error_message)

    def convert_strands_event(self, strands_event: Dict[str, Any]) -> List[Any]:
        agui_events = []
        if not isinstance(strands_event, dict):
            return agui_events

        if "data" in strands_event and "delta" in strands_event:
            agui_events.append(self.add_text_content(str(strands_event["data"])))
        elif "event" in strands_event:
            event_data = strands_event["event"]
            if "contentBlockStart" in event_data:
                start_data = event_data["contentBlockStart"]["start"]
                if "toolUse" in start_data:
                    agui_events.append(self.start_tool_call(start_data["toolUse"]["name"]))
            elif "contentBlockDelta" in event_data:
                delta_data = event_data["contentBlockDelta"]
                if "delta" in delta_data and "toolUse" in delta_data["delta"]:
                    tool_input = delta_data["delta"]["toolUse"]["input"]
                    if self.current_tool_call_id and tool_input:
                        agui_events.append(self.add_tool_args(str(tool_input)))
            elif "contentBlockStop" in event_data and self.current_tool_call_id:
                agui_events.extend(self.end_tool_call())

        return agui_events


class LangChainToAGUIBridge:
    """Bridge for converting LangChain agent events to AG-UI protocol events."""

    def __init__(self):
        self.current_message_id: Optional[str] = None
        self.current_tool_call_id: Optional[str] = None

    def start_run(self, thread_id: str, run_id: str) -> RunStartedEvent:
        return RunStartedEvent(type=EventType.RUN_STARTED, thread_id=thread_id, run_id=run_id)

    def start_message(self, role: str = "assistant") -> TextMessageStartEvent:
        self.current_message_id = str(uuid.uuid4())
        return TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START, message_id=self.current_message_id, role=role
        )

    def add_text_content(self, text: str) -> TextMessageContentEvent:
        return TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT, message_id=self.current_message_id, delta=text
        )

    def end_message(self) -> TextMessageEndEvent:
        return TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END, message_id=self.current_message_id
        )

    def start_tool_call(
        self, tool_name: str, tool_call_id: Optional[str] = None
    ) -> ToolCallStartEvent:
        self.current_tool_call_id = tool_call_id or str(uuid.uuid4())
        return ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=self.current_tool_call_id,
            tool_call_name=tool_name,
            parent_message_id=self.current_message_id,
        )

    def add_tool_args(self, args_chunk: str) -> ToolCallArgsEvent:
        return ToolCallArgsEvent(
            type=EventType.TOOL_CALL_ARGS, tool_call_id=self.current_tool_call_id, delta=args_chunk
        )

    def end_tool_call(self, result: str = "Tool executed successfully") -> List[Any]:
        events = [
            ToolCallResultEvent(
                type=EventType.TOOL_CALL_RESULT,
                tool_call_id=self.current_tool_call_id,
                message_id=self.current_message_id,
                content=result,
                role="tool",
            ),
            ToolCallEndEvent(type=EventType.TOOL_CALL_END, tool_call_id=self.current_tool_call_id),
        ]
        self.current_tool_call_id = None
        return events

    def finish_run(self, thread_id: str, run_id: str, result: Any = None) -> RunFinishedEvent:
        return RunFinishedEvent(
            type=EventType.RUN_FINISHED, thread_id=thread_id, run_id=run_id, result=result
        )

    def error_event(self, error_message: str) -> RunErrorEvent:
        return RunErrorEvent(type=EventType.RUN_ERROR, message=error_message)

    def process_stream_event(self, event: Dict[str, Any]) -> List[Any]:
        """Process a LangChain astream_events event and return AG-UI events."""
        agui_events = []

        event_type = event.get("event", "")

        if event_type == "on_chat_model_stream":
            content = event["data"]["chunk"]
            if hasattr(content, "content") and content.content:
                if isinstance(content.content, str):
                    agui_events.append(self.add_text_content(content.content))
                elif isinstance(content.content, list):
                    for block in content.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                agui_events.append(self.add_text_content(text))

        elif event_type == "on_tool_start":
            tool_name = event.get("name", "")
            tool_input = event["data"].get("input", {})
            tool_id = f"tool_{id(event)}"

            if self.current_tool_call_id:
                agui_events.extend(self.end_tool_call())

            agui_events.append(self.start_tool_call(tool_name, tool_id))

            if tool_input:
                args_str = json.dumps(tool_input)
                agui_events.append(self.add_tool_args(args_str))

        elif event_type == "on_tool_end":
            if self.current_tool_call_id:
                output = event["data"].get("output", "")
                agui_events.extend(self.end_tool_call(str(output)))

        return agui_events
