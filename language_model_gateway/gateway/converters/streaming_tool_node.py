from __future__ import annotations

from typing import (
    Any,
    AsyncIterator,
    Optional,
    override,
    cast,
)

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Input
from langchain_core.runnables.utils import (
    Output,
)
from langgraph.prebuilt import ToolNode


class StreamingToolNode(ToolNode):
    @override
    async def astream(
        self,
        input: Input,
        config: Optional[RunnableConfig] = None,
        **kwargs: Optional[Any],
    ) -> AsyncIterator[Output]:
        """
        Default implementation of astream, which calls ainvoke.
        Subclasses should override this method if they support streaming output.

        Args:
            input: The input to the Runnable.
            config: The config to use for the Runnable. Defaults to None.
            kwargs: Additional keyword arguments to pass to the Runnable.

        Yields:
            The output of the Runnable.
        """
        try:
            yield await self.ainvoke(input, config, **kwargs)
        except Exception as e:
            tool_call: dict[str, Any] = (
                cast(dict[str, Any], input.get("tool_call"))
                if isinstance(input, dict)
                else {}
            )
            raise Exception(
                f"Exception in tool {tool_call.get('name')} {tool_call.get('args')}: {type(e)}: {e}"
            ) from e

    # async def _arun_one(
    #     self,
    #     call: ToolCall,
    #     input_type: Literal["list", "dict"],
    #     config: RunnableConfig,
    # ) -> ToolMessage:
    #     if invalid_tool_message := self._validate_tool_call(call):
    #         return invalid_tool_message
    #
    #     try:
    #         input = {**call, **{"type": "tool_call"}}
    #         response = await self.tools_by_name[call["name"]].ainvoke(input, config)
    #
    #     # GraphInterrupt is a special exception that will always be raised.
    #     # It can be triggered in the following scenarios:
    #     # (1) a NodeInterrupt is raised inside a tool
    #     # (2) a NodeInterrupt is raised inside a graph node for a graph called as a tool
    #     # (3) a GraphInterrupt is raised when a subgraph is interrupted inside a graph called as a tool
    #     # (2 and 3 can happen in a "supervisor w/ tools" multi-agent architecture)
    #     except GraphBubbleUp as e:
    #         raise e
    #     except Exception as e:
    #         if isinstance(self.handle_tool_errors, tuple):
    #             handled_types: tuple = self.handle_tool_errors
    #         elif callable(self.handle_tool_errors):
    #             handled_types = _infer_handled_types(self.handle_tool_errors)
    #         else:
    #             # default behavior is catching all exceptions
    #             handled_types = (Exception,)
    #
    #         # Unhandled
    #         if not self.handle_tool_errors or not isinstance(e, handled_types):
    #             raise e
    #         # Handled
    #         else:
    #             content = _handle_tool_error(e, flag=self.handle_tool_errors)
    #
    #         return ToolMessage(
    #             content=content,
    #             name=call["name"],
    #             tool_call_id=call["id"],
    #             status="error",
    #         )
    #
    #     if isinstance(response, Command):
    #         return self._validate_tool_command(response, call, input_type)
    #     elif isinstance(response, ToolMessage):
    #         response.content = cast(
    #             Union[str, list], msg_content_output(response.content)
    #         )
    #         return response
    #     else:
    #         raise TypeError(
    #             f"Tool {call['name']} returned unexpected type: {type(response)}"
    #         )
