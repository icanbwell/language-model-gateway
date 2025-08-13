import logging
from typing import Any, Dict, Optional, Type, Mapping, cast, override
from pydantic import BaseModel
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from bson import ObjectId
from pymongo.results import InsertOneResult, UpdateResult

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from language_model_gateway.gateway.auth.repository.base_repository import (
    AsyncBaseRepository,
)

logger = logging.getLogger(__name__)

# disable pymongo logging to avoid cluttering the logs
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
logging.getLogger("pymongo.command").setLevel(logging.WARNING)


class AsyncMongoRepository[T: BaseDbModel](AsyncBaseRepository[T]):
    """
    Async MongoDB repository for Pydantic models with comprehensive async support.
    """

    def __init__(
        self,
        connection_string: str,
        database_name: str,
    ):
        """
        Initialize async MongoDB connection.

        Args:
            connection_string (str): MongoDB connection string
            database_name (str): Name of the database
        """
        assert connection_string, "MONGO_URL environment variable is not set."
        assert database_name, "Database name must be provided."
        self.connection_string = connection_string
        self.database_name = database_name
        self._client = AsyncIOMotorClient(connection_string)
        self._db: AsyncIOMotorDatabase = self._client[database_name]

    async def connect(self) -> None:
        """
        Establish and verify database connection.
        """
        try:
            # Ping the database to verify connection
            await self._db.command("ping")
            logger.info(
                f"Successfully connected to MongoDB: {self.connection_string} in database {self.database_name}"
            )
        except Exception as e:
            logger.info(f"Failed to connect to MongoDB: {e}")
            raise

    async def close(self) -> None:
        """
        Close the MongoDB connection.
        """
        self._client.close()

    @override
    async def insert(self, collection_name: str, model: BaseModel) -> ObjectId:
        """
        Save a Pydantic model to MongoDB collection asynchronously.

        Args:
            collection_name (str): Name of the collection
            model (BaseModel): Pydantic model to save

        Returns:
            ObjectId: Inserted document's ID
        """
        logger.debug(
            f"Saving document in collection {collection_name} with data: {model}"
        )
        collection: AsyncIOMotorCollection = self._db[collection_name]

        # Convert model to dictionary
        document = self._convert_model_to_dict(model)

        # Remove None values to prevent storing null fields
        document = {k: v for k, v in document.items() if v is not None}

        result: InsertOneResult = await collection.insert_one(document)
        logger.debug(
            f"Document inserted with ID: {result.inserted_id} in collection {collection_name} with data: {document} result: {result}"
        )
        return cast(ObjectId, result.inserted_id)

    @override
    async def find_by_id(
        self, collection_name: str, model_class: Type[T], document_id: ObjectId
    ) -> Optional[T]:
        """
        Find a document by its ID asynchronously.

        Args:
            collection_name (str): Name of the collection
            model_class (Type[T]): Pydantic model class
            document_id (str): Document ID

        Returns:
            Optional[T]: Pydantic model instance or None
        """
        logger.debug(
            f"Finding document with ID: {document_id} in collection {collection_name}"
        )
        collection: AsyncIOMotorCollection = self._db[collection_name]

        # Convert string ID to ObjectId
        object_id = ObjectId(document_id)

        document = await collection.find_one({"_id": object_id})

        if document is None:
            return None

        return self._convert_dict_to_model(document, model_class)

    @override
    async def find_by_fields(
        self,
        collection_name: str,
        model_class: Type[T],
        fields: Dict[str, str],
    ) -> Optional[T]:
        """
        Find a document by a specific field value asynchronously.

        Args:
            collection_name (str): Name of the collection
            model_class (Type[T]): Pydantic model class
            fields (Dict[str, str]): Fields value
        Returns:
            Optional[T]: Pydantic model instance or None
        """
        logger.debug(f"Finding {fields} in collection {collection_name}")
        collection: AsyncIOMotorCollection = self._db[collection_name]

        # Create filter dictionary
        filter_dict = fields

        document = await collection.find_one(filter=filter_dict)

        if document is None:
            return None

        return self._convert_dict_to_model(document, model_class)

    @override
    async def find_many(
        self,
        collection_name: str,
        model_class: Type[T],
        filter_dict: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[T]:
        """
        Find multiple documents matching a filter asynchronously.

        Args:
            collection_name (str): Name of the collection
            model_class (Type[T]): Pydantic model class
            filter_dict (Optional[Dict[str, Any]]): Filter criteria
            limit (int): Maximum number of documents to return
            skip (int): Number of documents to skip

        Returns:
            list[T]: List of Pydantic model instances
        """
        logger.debug(
            f"Finding documents in collection {collection_name} with filter: {filter_dict}, limit: {limit}, skip: {skip}"
        )
        collection: AsyncIOMotorCollection = self._db[collection_name]

        filter_dict = filter_dict or {}

        # Cursor for finding documents
        cursor = collection.find(filter_dict).limit(limit).skip(skip)

        # Convert documents to models
        documents = await cursor.to_list(length=limit)

        return [self._convert_dict_to_model(doc, model_class) for doc in documents]

    @override
    async def update_by_id(
        self,
        collection_name: str,
        document_id: ObjectId,
        update_data: BaseModel,
        model_class: Type[T],
    ) -> Optional[T]:
        """
        Update a document by its ID asynchronously.

        Args:
            collection_name (str): Name of the collection
            document_id (str): Document ID
            update_data (BaseModel): Pydantic model with update data
            model_class (Type[T]): Pydantic model class

        Returns:
            Optional[T]: Updated document or None
        """
        logger.debug(f"Updating document {document_id} in collection {collection_name}")
        collection: AsyncIOMotorCollection = self._db[collection_name]

        # Convert update data to dictionary, removing None values
        update_dict = self._convert_model_to_dict(update_data)
        update_dict = {k: v for k, v in update_dict.items() if v is not None}

        # Perform update
        result = await collection.find_one_and_update(
            {"_id": document_id},
            {"$set": update_dict},
            return_document=True,  # Return the updated document
        )

        return self._convert_dict_to_model(result, model_class) if result else None

    @override
    async def delete_by_id(self, collection_name: str, document_id: ObjectId) -> bool:
        """
        Delete a document by its ID asynchronously.

        Args:
            collection_name (str): Name of the collection
            document_id (str): Document ID

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        logger.debug(
            f"Deleting document {document_id} from collection {collection_name}"
        )
        collection: AsyncIOMotorCollection = self._db[collection_name]

        # Convert string ID to ObjectId
        object_id = ObjectId(document_id)

        # Delete document
        result = await collection.delete_one({"_id": object_id})

        return result.deleted_count > 0

    @staticmethod
    def _convert_model_to_dict(model: BaseModel) -> Dict[str, Any]:
        """
        Convert Pydantic model to dictionary.

        Args:
            model (BaseModel): Pydantic model to convert

        Returns:
            Dict[str, Any]: Converted dictionary
        """
        document = model.model_dump(exclude_unset=True)

        # Convert ObjectId to string if present
        if "_id" in document and isinstance(document["_id"], ObjectId):
            document["_id"] = str(document["_id"])

        return document

    @staticmethod
    def _convert_dict_to_model(document: Mapping[str, Any], model_class: Type[T]) -> T:
        """
        Convert MongoDB document to Pydantic model.

        Args:
            document (Dict[str, Any]): MongoDB document
            model_class (Type[T]): Pydantic model class

        Returns:
            T: Pydantic model instance
        """
        # Convert Mapping to dict for assignment
        document = dict(document)
        return model_class(**document)

    @override
    async def insert_or_update(
        self,
        *,
        collection_name: str,
        model_class: Type[T],
        item: T,
        fields: Dict[str, str],
    ) -> ObjectId:
        """
        Insert a new item or update an existing one in the collection.

        Args:
            collection_name (str): Name of the collection
            model_class (Type[T]): Pydantic model class
            item (T): Pydantic model instance to insert or update
            fields (Dict[str, str]): Fields that uniquely identify the document
        Returns:
            ObjectId: The ID of the inserted or updated document
        """
        logger.debug(
            f"Inserting or updating item in collection {collection_name} with data: {item}"
        )
        collection: AsyncIOMotorCollection = self._db[collection_name]

        # Convert item to dictionary
        document = self._convert_model_to_dict(item)

        # Remove None values to prevent storing null fields
        document = {k: v for k, v in document.items() if v is not None}

        # find the document by the fields that uniquely identify it
        existing_item = await self.find_by_fields(
            collection_name=collection_name, fields=fields, model_class=model_class
        )
        if existing_item:
            # If the document exists, update it
            update_result: UpdateResult = await collection.update_one(
                {"_id": existing_item.id},
                {"$set": document},
            )
            if update_result.modified_count == 0:
                logger.debug(
                    f"No changes made to document with ID: {existing_item.id} in collection {collection_name}"
                )
            else:
                logger.debug(
                    f"Document updated with ID: {existing_item.id} in collection {collection_name} with data: {document} result: {update_result}"
                )
            return existing_item.id
        else:
            # If the document does not exist, insert it
            insert_result: InsertOneResult = await collection.insert_one(document)
            if not insert_result.acknowledged:
                logger.error(
                    f"Failed to insert document in collection {collection_name} with data: {document}"
                )
                raise Exception("Insert operation was not acknowledged by MongoDB")
            logger.debug(
                f"Document inserted with ID: {insert_result.inserted_id} in collection {collection_name} with data: {document} result: {insert_result}"
            )
            return cast(ObjectId, insert_result.inserted_id)
