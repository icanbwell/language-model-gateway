import logging
import typing
import uuid
from typing import Any

from langgraph.config import get_store
from langgraph.store.base import BaseStore
from langmem import errors
from langmem.utils import NamespaceTemplate

from language_model_gateway.gateway.tools.resilient_base_tool import ResilientBaseTool

logger = logging.getLogger(__name__)


class ManageMemoryTool(ResilientBaseTool):
    """
    Tool for managing persistent memories in conversations. Supports create, update, and delete actions.
    """

    name: str = "manage_memory"
    description: str = (
        "Create, update, or delete a memory to persist across conversations. "
        "Include the MEMORY ID when updating or deleting a MEMORY. Omit when creating a new MEMORY - it will be created for you. "
        "Proactively call this tool when you: "
        "1. Identify a new USER preference. "
        "2. Receive an explicit USER request to remember something or otherwise alter your behavior. "
        "3. Are working and want to record important context. "
        "4. Identify that an existing MEMORY is incorrect or outdated."
    )
    namespace: tuple[str, ...] | str
    schema: typing.Type[Any] = str
    actions_permitted: typing.Optional[
        tuple[typing.Literal["create", "update", "delete"], ...]
    ] = ("create", "update", "delete")
    store: typing.Optional[BaseStore] = None

    def _run(
        self,
        content: typing.Optional[typing.Any] = None,
        action: str | None = None,
        id: typing.Optional[str] = None,
    ) -> str:
        raise NotImplementedError(
            "Synchronous execution is not supported. Use the asynchronous method instead."
        )

    async def _arun(
        self,
        content: typing.Optional[typing.Any] = None,
        action: str | None = None,
        id: typing.Optional[str] = None,
    ) -> str:
        store = self._get_store()
        if self.actions_permitted and action not in self.actions_permitted:
            raise ValueError(
                f"Invalid action {action}. Must be one of {self.actions_permitted}."
            )
        if action == "create" and id is not None:
            raise ValueError(
                "You cannot provide a MEMORY ID when creating a MEMORY. Please try again, omitting the id argument."
            )
        if action in ("delete", "update") and not id:
            raise ValueError(
                "You must provide a MEMORY ID when deleting or updating a MEMORY."
            )
        namespacer = NamespaceTemplate(self.namespace)
        namespace = namespacer()
        if action == "delete":
            await store.adelete(namespace, key=str(id))
            return f"Deleted memory {id}"
        memory_id = id or str(uuid.uuid4())
        await store.aput(
            namespace,
            key=str(memory_id),
            value={"content": self._ensure_json_serializable(content)},
        )
        return f"{action}d memory {memory_id}"

    def _get_store(self) -> BaseStore:
        if self.store is not None:
            return self.store
        try:
            return get_store()
        except RuntimeError as e:
            raise errors.ConfigurationError("Could not get store") from e

    def _ensure_json_serializable(self, content: typing.Any) -> typing.Any:
        if isinstance(content, (str, int, float, bool, dict, list)):
            return content
        if hasattr(content, "model_dump"):
            try:
                return content.model_dump(mode="json")
            except Exception as e:
                logger.error(e)
                return str(content)
        return content
