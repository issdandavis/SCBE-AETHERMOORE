import json
import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands import Agent, tool

from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION", "us-east-1")

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()


# Define a simple function tool
@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers"""
    return a + b


@tool
def execute_python(code: str, description: str = "") -> str:
    """Execute Python in an isolated Amazon Bedrock AgentCore session."""
    if description:
        code = f"# {description}\n{code}"

    results = []
    with code_session(REGION) as code_client:
        response = code_client.invoke(
            "executeCode",
            {
                "code": code,
                "language": "python",
                "clearContext": False,
            },
        )
        for event in response["stream"]:
            if "result" in event:
                results.append(event["result"])
    return json.dumps(results, default=str)


@app.entrypoint
async def invoke(payload, context):
    with mcp_client as client:
        # Get MCP Tools
        tools = client.list_tools_sync()

        # Create agent
        agent = Agent(
            model=load_model(),
            system_prompt="""
                You are a helpful assistant with code execution capabilities. Use tools when appropriate.
            """,
            tools=[execute_python, add_numbers] + tools,
        )

        # Execute and format response
        stream = agent.stream_async(payload.get("prompt"))

        async for event in stream:
            # Handle Text parts of the response
            if "data" in event and isinstance(event["data"], str):
                yield event["data"]

            # Implement additional handling for other events
            # if "toolUse" in event:
            #   # Process toolUse

            # Handle end of stream
            # if "result" in event:
            #    yield(format_response(event["result"]))


def format_response(result) -> str:
    """Extract code from metrics and format with LLM response."""
    parts = []

    # Extract executed code from metrics
    try:
        tool_metrics = result.metrics.tool_metrics.get("execute_python")
        if tool_metrics and hasattr(tool_metrics, "tool"):
            tool_input = tool_metrics.tool.get("input", {})
            if "code" in tool_input:
                parts.append(f"## Executed Code:\n```python\n{tool_input['code']}\n```\n---\n")
    except (AttributeError, KeyError):
        pass  # No code to extract

    # Add LLM response
    parts.append(f"## 📊 Result:\n{str(result)}")
    return "\n".join(parts)


if __name__ == "__main__":
    app.run()
