from contextlib import contextmanager
from typing import Generator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore, IndexConfig
from langgraph.store.mongodb import MongoDBStore


class PersistenceFactory:
    """
    Factory to create different types of persistence stores.

    https://langchain-ai.github.io/langgraph/concepts/memory/
    """

    @contextmanager
    def create_store(self, persistence_type: str) -> Generator[BaseStore, None, None]:
        if persistence_type == "memory":
            index: IndexConfig = {
                "dims": 1536,
                "embed": "openai:text-embedding-3-small",
            }
            yield InMemoryStore(index=index)
        elif persistence_type == "mongo":
            # https://pypi.org/project/langgraph-checkpoint-mongodb/
            with MongoDBStore.from_conn_string(
                conn_string="mongodb://localhost:27017",
                db_name="langgraph_db",
                collection_name="checkpoints",
            ) as store:
                yield store
        else:
            raise ValueError(f"Unknown persistence type: {persistence_type}")

    @contextmanager
    def create_checkpointer(
        self, persistence_type: str
    ) -> Generator[BaseCheckpointSaver[str], None, None]:
        if persistence_type == "memory":
            yield InMemorySaver()
        elif persistence_type == "mongo":
            # https://pypi.org/project/langgraph-checkpoint-mongodb/
            with MongoDBSaver.from_conn_string(
                conn_string="mongodb://localhost:27017",
                db_name="langgraph_db",
                collection_name="checkpoints",
            ) as checkpointer:
                yield checkpointer
        else:
            raise ValueError(f"Unknown persistence type: {persistence_type}")
