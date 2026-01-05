import json
import logging
from logging import DEBUG
from typing import Callable, Awaitable, Any

from langchain_mcp_adapters.interceptors import (
    MCPToolCallRequest,
    MCPToolCallResult,
    ToolCallInterceptor,
)
from mcp.types import (
    CallToolResult,
)
from opentelemetry import baggage
from opentelemetry import context as otel_context
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context

# OpenTelemetry propagation for trace context
from opentelemetry.trace import get_tracer, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MCP"])


class TracingMcpCallInterceptor:
    def __init__(
        self, *, environment_variables: LanguageModelGatewayEnvironmentVariables
    ) -> None:
        self.environment_variables = environment_variables
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                f"environment_variables must be LanguageModelGatewayEnvironmentVariables, got {type(self.environment_variables)}"
            )

    # noinspection PyMethodMayBeStatic
    def get_tool_interceptor_tracing(self) -> ToolCallInterceptor:
        """
        Interceptor that wraps each MCP tool call in an OpenTelemetry span.
        Captures useful attributes and marks errors on exceptions.
        """

        async def tool_interceptor_tracing(
            request: MCPToolCallRequest,
            handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
        ) -> MCPToolCallResult:
            span_name = f"mcp.tool.{getattr(request, 'tool_name', 'call')}"
            tracer = get_tracer(__name__)
            # Start span as current so downstream HTTP client propagation uses the active context
            with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
                # Add common attributes for filtering/analysis
                try:
                    span.set_attribute(
                        "mcp.server_name", getattr(request, "server_name", "unknown")
                    )
                    span.set_attribute(
                        "mcp.tool_name", getattr(request, "tool_name", "unknown")
                    )
                    # Serialize complex arguments into JSON string to satisfy OTEL attribute type requirements
                    args_val: Any = getattr(request, "arguments", {})
                    try:
                        args_str = json.dumps(args_val, ensure_ascii=False)
                    except Exception:
                        args_str = str(args_val)
                    span.set_attribute("mcp.arguments", args_str)
                except Exception:
                    # defensive: attribute setting should not break the call
                    pass

                # Ensure OpenTelemetry trace context is propagated to downstream MCP tools
                try:
                    # https://opentelemetry.io/docs/languages/python/propagation/#manual-context-propagation
                    current_context: Context = otel_context.get_current()
                    baggage_context: Context | None = baggage.set_baggage(
                        "source",
                        "language-model-gateway",
                        context=current_context,
                    )
                    propagation_context: Context = (
                        baggage_context
                        if baggage_context is not None
                        else current_context
                    )
                    if request.headers is None:
                        request.headers = {}
                    W3CBaggagePropagator().inject(
                        carrier=request.headers,
                        context=propagation_context,
                    )
                    TraceContextTextMapPropagator().inject(
                        carrier=request.headers,
                        context=propagation_context,
                    )
                    if logger.isEnabledFor(DEBUG):
                        logger.debug(
                            f"Injected OpenTelemetry context into MCP headers: {request.headers}"
                        )
                except Exception as otel_err:
                    # Do not fail tool loading if OTEL propagation fails; just log
                    logger.debug(f"OTEL inject failed: {type(otel_err)} {otel_err}")

                try:
                    logger.debug(
                        f"Starting MCP tool call span: {span_name} for tool: {getattr(request, 'tool_name', 'unknown')}"
                    )
                    result = await handler(request)
                    # Optionally record result metadata size
                    try:
                        if isinstance(result, CallToolResult):
                            span.set_attribute(
                                "mcp.result.content_blocks", len(result.content)
                            )
                            if result.structuredContent is not None:
                                span.set_attribute("mcp.result.structured", True)
                    except Exception:
                        logger.debug(f"MCP tool call failed: {type(result)} {result}")
                        pass
                    logger.debug(
                        f"Completed MCP tool call span: {span_name} for tool: {getattr(request, 'tool_name', 'unknown')}"
                    )
                    return result
                except Exception as err:
                    # Record exception on span, mark status error, then re-raise
                    try:
                        span.record_exception(err)
                        # status API may differ by SDK version; recording exception is sufficient
                    except Exception:
                        pass
                    raise

        return tool_interceptor_tracing
