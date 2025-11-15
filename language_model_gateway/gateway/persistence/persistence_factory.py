from contextlib import contextmanager
from typing import Generator

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore, IndexConfig
from langgraph.store.mongodb import MongoDBStore

from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.utilities.mongo_url_utils import MongoUrlHelpers


class PersistenceFactory:
    """
    Factory to create different types of persistence stores.

    https://langchain-ai.github.io/langgraph/concepts/memory/
    """

    def __init__(
        self, *, environment_variables: LanguageModelGatewayEnvironmentVariables
    ) -> None:
        self._environment_variables = environment_variables

    @contextmanager
    def create_store(self, persistence_type: str) -> Generator[BaseStore, None, None]:
        if persistence_type == "memory":
            index: IndexConfig = {
                "dims": 1536,
                "embed": "openai:text-embedding-3-small",
            }
            yield InMemoryStore(index=index)
        elif persistence_type == "mongo":
            # https://pypi.org/project/langgraph-store-mongodb/
            # https://www.mongodb.com/docs/atlas/ai-integrations/langgraph/
            # https://langchain-ai.github.io/langgraph/how-tos/memory/add-memory/
            mongo_llm_storage_uri = self._environment_variables.mongo_llm_storage_uri
            if mongo_llm_storage_uri is None:
                raise ValueError("mongo_llm_storage_uri must not be None")
            llm_storage_db_username = (
                self._environment_variables.mongo_llm_storage_db_username
            )
            if llm_storage_db_username is None:
                raise ValueError("mongo_llm_storage_db_username must not be None")
            llm_storage_db_password = (
                self._environment_variables.mongo_llm_storage_db_password
            )
            if llm_storage_db_password is None:
                raise ValueError("mongo_llm_storage_db_password must not be None")
            connection_string: str = MongoUrlHelpers.add_credentials_to_mongo_url(
                mongo_url=mongo_llm_storage_uri,
                username=llm_storage_db_username,
                password=llm_storage_db_password,
            )
            llm_storage_db_name = self._environment_variables.mongo_llm_storage_db_name
            if llm_storage_db_name is None:
                raise ValueError("mongo_llm_storage_db_name must not be None")
            llm_store_collection_name = (
                self._environment_variables.mongo_llm_storage_store_collection_name
            )
            if llm_store_collection_name is None:
                raise ValueError(
                    "mongo_llm_storage_store_collection_name must not be None"
                )

            # index: VectorIndexConfig = {
            #     "dims": 1536,
            #     "embed": "openai:text-embedding-3-small",
            # }
            with MongoDBStore.from_conn_string(
                conn_string=connection_string,
                db_name=llm_storage_db_name,
                collection_name=llm_store_collection_name,
                index_config=None,
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
            # https://www.mongodb.com/docs/atlas/ai-integrations/langgraph/
            mongo_llm_storage_uri = self._environment_variables.mongo_llm_storage_uri
            if mongo_llm_storage_uri is None:
                raise ValueError("mongo_llm_storage_uri must not be None")
            llm_storage_db_username = (
                self._environment_variables.mongo_llm_storage_db_username
            )
            if llm_storage_db_username is None:
                raise ValueError("mongo_llm_storage_db_username must not be None")
            llm_storage_db_password = (
                self._environment_variables.mongo_llm_storage_db_password
            )
            if llm_storage_db_password is None:
                raise ValueError("mongo_llm_storage_db_password must not be None")
            connection_string: str = MongoUrlHelpers.add_credentials_to_mongo_url(
                mongo_url=mongo_llm_storage_uri,
                username=llm_storage_db_username,
                password=llm_storage_db_password,
            )
            llm_storage_db_name = self._environment_variables.mongo_llm_storage_db_name
            if llm_storage_db_name is None:
                raise ValueError("mongo_llm_storage_db_name must not be None")
            llm_storage_checkpointer_collection_name = self._environment_variables.mongo_llm_storage_checkpointer_collection_name
            if llm_storage_checkpointer_collection_name is None:
                raise ValueError(
                    "mongo_llm_storage_checkpointer_collection_name must not be None"
                )

            with MongoDBSaver.from_conn_string(
                conn_string=connection_string,
                db_name=llm_storage_db_name,
                checkpoint_collection_name=llm_storage_checkpointer_collection_name,
            ) as checkpointer:
                yield checkpointer
        else:
            raise ValueError(f"Unknown persistence type: {persistence_type}")
