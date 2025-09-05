from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from language_model_gateway.gateway.auth.repository.base_repository import (
    AsyncBaseRepository,
)
from language_model_gateway.gateway.auth.repository.memory.memory_repository import (
    AsyncMemoryRepository,
)
from language_model_gateway.gateway.auth.repository.mongo.mongo_repository import (
    AsyncMongoRepository,
)
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)


class RepositoryFactory:
    """
    Factory class to create repository instances.
    """

    @staticmethod
    def get_repository[T: BaseDbModel](
        *, repository_type: str, environment_variables: EnvironmentVariables
    ) -> AsyncBaseRepository[T]:
        """
        Returns an instance of the specified repository type.

        :param repository_type: The type of repository to create.
        :param environment_variables: An instance of EnvironmentVariables containing configuration.
        :return: An instance of the specified repository.
        """
        if repository_type.lower() == "mongo":
            assert environment_variables.mongo_uri
            assert environment_variables.mongo_db_name
            return AsyncMongoRepository(
                connection_string=environment_variables.mongo_uri,
                database_name=environment_variables.mongo_db_name,
                username=environment_variables.mongo_db_username,
                password=environment_variables.mongo_db_password,
            )
        elif repository_type.lower() == "memory":
            return AsyncMemoryRepository()
        else:
            raise ValueError(f"Unsupported repository type: {repository_type}")
