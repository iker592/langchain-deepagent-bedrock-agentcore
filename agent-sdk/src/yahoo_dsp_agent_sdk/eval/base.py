import inspect
import json
import os
import time
from typing import Callable, Type

from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ArgumentCorrectnessMetric,
    GEval,
    TaskCompletionMetric,
    ToolCorrectnessMetric,
)
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall

from ..agent import Agent
from ..mcps import MCPManager
from .constants import (
    EXPECTED_OUTPUT_KEY_NAME,
    EXPECTED_TOOLS_KEY_NAME,
    INPUT_KEY_NAME,
)
from .mock_builder import MockToolBuilder
from .models import create_bedrock_eval_model
from .rubric_parser import load_rubric_config


class AgentEvalTest:
    def __init__(
        self,
        agent_class: Type[Agent],
        mock_tools_factory: Callable[[object], MockToolBuilder],
        rubric_file: str = "rubric.md",
        task_description: str | None = None,
        geval_metric_factory: Callable[[], GEval] | None = None,
        agent_module_path: str | None = None,
        datasets_dir: str | None = None,
        datasets_file: str = "datasets.json",
        eval_model: DeepEvalBaseLLM | None = None,
    ):
        self.agent_class = agent_class
        self.agent_module_path = agent_module_path or agent_class.__module__
        self._eval_model = eval_model
        self._mock_tools_factory = mock_tools_factory
        self._geval_metric_factory = geval_metric_factory

        if datasets_dir is None:
            frame = inspect.stack()[1]
            datasets_dir = os.path.dirname(os.path.abspath(frame.filename))
        self.datasets_dir = datasets_dir

        rubric_path = os.path.join(self.datasets_dir, rubric_file)
        if os.path.exists(rubric_path):
            self._rubric = load_rubric_config(rubric_path)
        else:
            self._rubric = None

        if task_description:
            self.task_description = task_description
        elif self._rubric and self._rubric.task_completion_criteria:
            self.task_description = self._rubric.task_completion_criteria
        else:
            self.task_description = f"Evaluate if the {agent_class.__name__} performed correctly."

        dataset = EvaluationDataset()
        dataset.add_goldens_from_json_file(
            file_path=os.path.join(self.datasets_dir, datasets_file),
            input_key_name=INPUT_KEY_NAME,
            expected_tools_key_name=EXPECTED_TOOLS_KEY_NAME,
            expected_output_key_name=EXPECTED_OUTPUT_KEY_NAME,
        )
        self.goldens = dataset.goldens

    def create_agent(self) -> Agent:
        return self.agent_class()

    def get_mock_tools(self, mocker) -> MockToolBuilder:
        return self._mock_tools_factory(mocker)

    def get_geval_metric(self) -> GEval:
        if self._geval_metric_factory is not None:
            return self._geval_metric_factory()

        if self._rubric and self._rubric.geval:
            config = self._rubric.geval
            return GEval(
                name=config.name,
                criteria=config.criteria,
                evaluation_steps=config.evaluation_steps,
                evaluation_params=[
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ],
                model=self.get_eval_model(),
            )

        raise ValueError(
            "No GEval configuration found. Provide rubric.md with ## GEval section "
            "or pass geval_metric_factory."
        )

    def get_eval_model(self) -> DeepEvalBaseLLM:
        if self._eval_model is not None:
            return self._eval_model
        return create_bedrock_eval_model()

    def load_expected_output(self, expected_output_value: str | None) -> str | None:
        if not expected_output_value:
            return expected_output_value

        if expected_output_value.endswith(".json"):
            if self.datasets_dir:
                json_file_path = os.path.join(self.datasets_dir, expected_output_value)
            else:
                json_file_path = expected_output_value

            if os.path.exists(json_file_path):
                with open(json_file_path) as f:
                    return str(json.load(f))

        return expected_output_value

    def run_test(self, golden: Golden, monkeypatch, mocker) -> None:
        mock_tools_builder = self.get_mock_tools(mocker)
        mock_mcp_client = mocker.MagicMock()

        mcp_tools = mock_tools_builder.build(mock_mcp_client)
        mock_mcp_client.list_tools_sync.return_value = mcp_tools

        direct_call_handlers = mock_tools_builder.get_direct_call_handlers()

        def mock_call_tool(tool_name, *args, **kwargs):
            if tool_name in direct_call_handlers:
                return direct_call_handlers[tool_name]()
            return None

        # Create mock MCPManager instance
        mock_mcp_manager = mocker.MagicMock(spec=MCPManager)
        mock_mcp_manager.get_filtered_tools.return_value = mcp_tools
        mock_mcp_manager.call_tool.side_effect = mock_call_tool
        mock_mcp_manager.tool_tags = []
        mock_mcp_manager.max_retries = 3
        mock_mcp_manager.retry_delay = 1.0

        # Mock MCPManager class to return our mock instance
        monkeypatch.setattr(
            f"{self.agent_module_path}.{MCPManager.__name__}",
            lambda **kwargs: mock_mcp_manager,
        )

        agent = self.create_agent()

        start_time = time.time()
        res, response = agent.invoke(golden.input)
        total_time = time.time() - start_time

        summary = response.metrics.get_summary()

        used_tools = self._extract_tools_called(summary)
        llm_latencies = self._extract_llm_latencies(summary)

        llm_latency_sum = sum(llm_latencies)
        structured_output_latency = total_time - llm_latency_sum
        if structured_output_latency > 0:
            llm_latencies.append(structured_output_latency)

        comments = json.dumps(
            {
                "accumulated_usage": summary.get("accumulated_usage", {}),
                "llm_latencies": llm_latencies,
                "total_latency": total_time,
                "agent_llm": agent.agent.model.config.get("model_id", "llm_model_not_found"),
                "trajectory": self._extract_trajectory(summary),
            }
        )

        eval_model = self.get_eval_model()
        correctness_metric = self.get_geval_metric()
        expected_output = self.load_expected_output(golden.expected_output)

        test_case = LLMTestCase(
            input=agent.agent.system_prompt + "\n" + golden.input,
            expected_output=expected_output,
            expected_tools=golden.expected_tools,
            actual_output=str(res),
            tools_called=used_tools,
            comments=comments,
        )

        assert_test(
            test_case=test_case,
            metrics=[
                AnswerRelevancyMetric(model=eval_model),
                TaskCompletionMetric(
                    model=eval_model,
                    task=self.task_description,
                ),
                ToolCorrectnessMetric(model=eval_model),
                ArgumentCorrectnessMetric(model=eval_model),
                correctness_metric,
            ],
        )

    def _extract_tools_called(self, summary: dict) -> list[ToolCall]:
        used_tools = []
        for tool_name, tool_data in summary.get("tool_usage", {}).items():
            tool_info = tool_data.get("tool_info", {})
            if tool_info:
                tool_call = ToolCall(
                    name=tool_name,
                    input_parameters=tool_info.get("input_params", {}),
                )
                used_tools.append(tool_call)
        return used_tools

    def _extract_llm_latencies(self, summary: dict) -> list[float]:
        llm_latencies = []
        for trace in summary.get("traces", []):
            for child in trace.get("children", []):
                if child.get("name") == "stream_messages":
                    duration = child.get("duration", 0)
                    llm_latencies.append(duration)
        return llm_latencies

    def _extract_trajectory(self, summary: dict) -> list[dict]:
        """Extract the agent's execution trajectory from traces."""
        trajectory = []
        for trace in summary.get("traces", []):
            cycle_name = trace.get("name", "")
            for child in trace.get("children", []):
                name = child.get("name", "")
                message = child.get("message") or {}
                role = message.get("role", "") if message else ""
                content = message.get("content", []) if message else []
                duration = child.get("duration", 0)
                is_tool = name.startswith("Tool:")

                text = ""
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            if "text" in item:
                                text = item.get("text", "")[:2000]
                                break
                            elif "toolResult" in item:
                                tool_result = item.get("toolResult", {})
                                result_content = tool_result.get("content", [])
                                if isinstance(result_content, list) and result_content:
                                    first_item = result_content[0]
                                    if isinstance(first_item, dict) and "text" in first_item:
                                        text = first_item.get("text", "")[:2000]
                                if not text:
                                    text = json.dumps(tool_result, indent=2)[:2000]
                                break
                            elif "toolUse" in item:
                                tool_use = item.get("toolUse", {})
                                tool_input = tool_use.get("input", {})
                                text = json.dumps(tool_input, indent=2)[:2000]
                                break

                entry = {
                    "cycle": cycle_name,
                    "type": "tool" if is_tool else "llm",
                    "name": child.get("raw_name") or name,
                    "role": role,
                    "content": text,
                    "duration": round(duration, 3),
                }
                trajectory.append(entry)
        return trajectory
