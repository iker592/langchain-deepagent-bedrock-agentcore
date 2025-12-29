import ast
import html
import json
import sys
from importlib import resources
from pathlib import Path
from typing import Optional

from .constants import (
    DEEPEVAL_LATEST_RUN_FILE,
    DEEPEVAL_RESULTS_DIR,
    REPORT_CSS_FILENAME,
    REPORT_HTML_FILENAME,
)


def _format_tools(tools_list):
    if not tools_list:
        return "None"
    return ", ".join([tool.get("name", "Unknown") for tool in tools_list])


def _format_json_output(output_str):
    if not output_str:
        return "N/A"

    try:
        data = ast.literal_eval(output_str)
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)

        truncated = output_str[:60] + "..." if len(output_str) > 60 else output_str
        truncated_summary = html.escape(truncated)
        escaped_json = html.escape(formatted_json)

        summary_span = f'<span class="summary-part">{truncated_summary}</span>'
        json_pre = f'<pre class="detail-part json-display">{escaped_json}</pre>'
        return f"{summary_span}{json_pre}"

    except (SyntaxError, ValueError, TypeError):
        return html.escape(output_str)


def _format_markdown_output(markdown_str):
    if not markdown_str:
        return "N/A"

    truncated = markdown_str[:80] + "..." if len(markdown_str) > 80 else markdown_str
    truncated_summary = html.escape(truncated)
    escaped_markdown = html.escape(markdown_str)

    summary_span = f'<span class="summary-part">{truncated_summary}</span>'
    markdown_pre = f'<pre class="detail-part markdown-display">{escaped_markdown}</pre>'
    return f"{summary_span}{markdown_pre}"


def _get_metrics_details(metrics_data):
    if not metrics_data:
        return "N/A"

    total_metrics = len(metrics_data)
    passed_metrics = sum(1 for metric in metrics_data if metric.get("success", False))

    summary = f"{passed_metrics}/{total_metrics} ⓘ"

    detail_parts = [f'<span class="summary-part">{summary}</span>']
    for metric in metrics_data:
        name = metric.get("name", "Unknown")
        score = metric.get("score", 0)
        success = metric.get("success", False)
        status_icon = "✅" if success else "❌"
        detail_parts.append(f'<span class="detail-part">{name}: {score:.2f} {status_icon}</span>')

    return "".join(detail_parts)


def _format_status_with_feedback(success, metrics_data):
    status_text = "✅" if success else "❌"

    if not metrics_data:
        return status_text

    detail_parts = []
    for metric in metrics_data:
        name = metric.get("name", "Unknown")
        score = metric.get("score", 0)
        metric_success = metric.get("success", False)
        reason = metric.get("reason", "No feedback provided")
        status_icon = "✅" if metric_success else "❌"

        detail_parts.append(
            f"{status_icon} {html.escape(name)} ({score:.2f}):\n{html.escape(reason)}"
        )

    detail_text = "\n\n---\n\n".join(detail_parts)

    summary_span = f'<span class="summary-part">{status_text}</span>'
    detail_pre = f'<pre class="detail-part judge-feedback">{detail_text}</pre>'

    return f"{summary_span}{detail_pre}"


def _extract_tokens_from_comments(comments):
    if not comments:
        return "N/A"

    try:
        data = eval(comments)
        if not isinstance(data, dict):
            return "N/A"

        token_dict = data.get("accumulated_usage", {})

        if not token_dict:
            return "N/A"

        total_tokens = token_dict.get("totalTokens", 0)
        input_tokens = token_dict.get("inputTokens", 0)
        output_tokens = token_dict.get("outputTokens", 0)
        cache_read_tokens = token_dict.get("cacheReadInputTokens", 0)

        token_info = f"{total_tokens:,} total"
        if cache_read_tokens > 0:
            token_info += f" (Cache: {cache_read_tokens:,})"
        token_info += f"<br/>({input_tokens:,} in, {output_tokens:,} out)"

        return token_info

    except (SyntaxError, NameError, TypeError, ValueError):
        return comments


def _extract_model_from_comments(comments):
    if not comments:
        return None

    try:
        data = eval(comments)
        if not isinstance(data, dict):
            return None
        return data.get("agent_llm")

    except (SyntaxError, NameError, TypeError, ValueError):
        return None


def _extract_llm_latencies(comments):
    if not comments:
        return "N/A"

    try:
        data = eval(comments)
        if not isinstance(data, dict):
            return "N/A"

        latencies = data.get("llm_latencies", [])
        total_latency = data.get("total_latency", sum(latencies))

        if not latencies:
            return "N/A"

        summary = f"{total_latency:.1f}s ({len(latencies)}) ⓘ"

        detail_parts = [f'<span class="summary-part">{summary}</span>']

        for i, latency in enumerate(latencies, 1):
            if i == len(latencies) and len(latencies) > 2:
                label = "Structured Output"
            else:
                label = f"LLM Call {i}"
            detail_parts.append(f'<span class="detail-part">{label}: {latency:.2f}s</span>')

        return "".join(detail_parts)

    except (SyntaxError, NameError, TypeError, ValueError):
        return "N/A"


def _get_template_content(template_name: str) -> str:
    template_files = resources.files("yahoo_dsp_agent_sdk.eval.templates")
    return (template_files / template_name).read_text()


def _copy_css_to_output(output_dir: Path) -> Path:
    css_content = _get_template_content(REPORT_CSS_FILENAME)
    css_destination = output_dir / REPORT_CSS_FILENAME
    css_destination.write_text(css_content)
    return css_destination


def generate_report(
    input_file: str,
    output_file: str,
    title: str = "DeepEval Test Results",
    threshold: float = 90.0,
    fail_on_threshold: bool = True,
) -> dict:
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file '{input_file}' not found")

    with open(input_file, "r") as f:
        data = json.load(f)

    test_cases = data.get("testRunData", {}).get("testCases", [])

    total_tests = len(test_cases)
    passed_tests = sum(1 for tc in test_cases if tc.get("success", False))
    success_rate = round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1)

    model_name = "Unknown"
    for test_case in test_cases:
        comments = test_case.get("comments", "")
        extracted_model = _extract_model_from_comments(comments)
        if extracted_model:
            model_name = extracted_model
            break

    html_template = _get_template_content("deepeval_report.html")

    test_rows = ""
    for i, test_case in enumerate(test_cases):
        name = test_case.get("name", f"Test {i + 1}")
        user_input = _format_markdown_output(test_case.get("input", ""))
        expected = _format_json_output(test_case.get("expectedOutput", ""))
        actual = _format_json_output(test_case.get("actualOutput", ""))
        tools = _format_tools(test_case.get("toolsCalled", []))
        success = test_case.get("success", False)
        metrics_data = test_case.get("metricsData", [])
        metrics_details = _get_metrics_details(metrics_data)
        status_with_feedback = _format_status_with_feedback(success, metrics_data)
        comments = test_case.get("comments", "")
        latencies = _extract_llm_latencies(comments)
        tokens = _extract_tokens_from_comments(comments)

        status_class = "success" if success else "failure"

        test_rows += f"""
                <tr>
                    <td class="{status_class} truncate">{status_with_feedback}</td>
                    <td class="test-name truncate">{name}</td>
                    <td class="truncate">{user_input}</td>
                    <td class="truncate">{expected}</td>
                    <td class="truncate">{actual}</td>
                    <td class="tools truncate">{tools}</td>
                    <td class="score truncate">{metrics_details}</td>
                    <td class="duration truncate">{latencies}</td>
                    <td class="tokens truncate">{tokens}</td>
                </tr>"""

    html_content = html_template.replace("{TITLE}", title)
    html_content = html_content.replace("{TOTAL_TESTS}", str(total_tests))
    html_content = html_content.replace("{PASSED_TESTS}", str(passed_tests))
    html_content = html_content.replace("{SUCCESS_RATE}", str(success_rate))
    html_content = html_content.replace("{MODEL_NAME}", str(model_name))
    html_content = html_content.replace("{TEST_CASES}", test_rows)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html_content)

    css_destination = _copy_css_to_output(output_path.parent)

    result = {
        "html_file": str(output_path),
        "css_file": str(css_destination),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "success_rate": success_rate,
        "model_name": model_name,
        "passed_threshold": success_rate >= threshold,
    }

    if fail_on_threshold and success_rate < threshold:
        raise ValueError(
            f"Success rate {success_rate}% is below threshold ({threshold}%). "
            f"{passed_tests}/{total_tests} tests passed."
        )

    return result


def main(args: Optional[list] = None):
    if args is None:
        args = sys.argv[1:]

    if len(args) < 1:
        input_file = f"{DEEPEVAL_RESULTS_DIR}/{DEEPEVAL_LATEST_RUN_FILE}"
        output_file = REPORT_HTML_FILENAME
    elif len(args) == 1:
        input_file = args[0]
        output_file = REPORT_HTML_FILENAME
    else:
        input_file = args[0]
        output_file = args[1]

    try:
        result = generate_report(input_file, output_file)
        print(f"HTML report generated: {result['html_file']}")
        print(f"CSS file copied: {result['css_file']}")
        print(f"Processed {result['total_tests']} test cases")
        print(
            f"Success rate: {result['success_rate']}% "
            f"({result['passed_tests']}/{result['total_tests']})"
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
