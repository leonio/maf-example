"""Reports every tool call (to the run's timeline here; to logs, metrics or an audit table in a real system).

`FunctionMiddleware` is Agent Framework's hook around each function invocation: the model still sees the tool's
own name, description and schema, and the middleware sees the arguments before and the result after. The same hook
can deny a call or substitute a result, which is where policy for risky tools usually lives. For tracing every call
with arguments and results, turn on Agent Framework's OpenTelemetry instead (`agent_framework.observability`).

"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from agent_framework import FunctionInvocationContext, FunctionMiddleware

from .tracker import shorten

OnCall = Callable[[str, str, str, str], Awaitable[None]]  # agent, tool, arguments, result


class ToolCallObserver(FunctionMiddleware):
    def __init__(self, agent: str, on_call: OnCall):
        self.agent = agent
        self.on_call = on_call

    async def process(self, context: FunctionInvocationContext, call_next: Callable[[], Awaitable[None]]) -> None:
        await call_next()
        arguments = dict(context.arguments or {})
        summary = ", ".join(f"{k}={shorten(v, 40)}" for k, v in arguments.items())
        await self.on_call(self.agent, context.function.name, summary, shorten(_result_text(context.result), 90))


def _result_text(result: object) -> str:
    if isinstance(result, list):
        return " ".join(getattr(c, "text", None) or str(getattr(c, "result", "") or c) for c in result)
    return "" if result is None else str(result)
