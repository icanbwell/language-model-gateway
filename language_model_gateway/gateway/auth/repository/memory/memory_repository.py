from typing import Type, Dict, override, Any, Callable

from bson import ObjectId

from language_model_gateway.gateway.auth.models.base_db_model import BaseDbModel
from language_model_gateway.gateway.auth.repository.base_repository import (
    AsyncBaseRepository,
)


class AsyncMemoryRepository[T: BaseDbModel](AsyncBaseRepository[T]):
    """
    In-memory repository for Pydantic models with comprehensive async support.
    """

    def __init__(self) -> None:
        """
        Initializes an in-memory repository for Pydantic models.
        This repository uses a dictionary to store models, where the keys are ObjectIds
        and the values are instances of the Pydantic model.
        """
        self._storage: dict[ObjectId, T] = {}

    @override
    async def insert(self, collection_name: str, model: T) -> ObjectId:
        """
        Insert a Pydantic model into the in-memory storage.
        :param collection_name: Name of the collection (not used in memory storage).
        :param model: The Pydantic model instance to insert.
        :return: The ID of the inserted model.
        """
        self._storage[model.id] = model
        return model.id

    @override
    async def find_by_id(
        self, collection_name: str, model_class: type[T], document_id: ObjectId
    ) -> T | None:
        """
        Find a Pydantic model by its ID in the in-memory storage.
        :param collection_name: Name of the collection (not used in memory storage).
        :param model_class: The Pydantic model class.
        :param document_id: The ID of the document to find.
        :return: The Pydantic model instance if found, otherwise None.
        """
        return self._storage.get(document_id)

    @override
    async def find_by_fields(
        self, collection_name: str, model_class: type[T], fields: dict[str, str | None]
    ) -> T | None:
        """
        Find a Pydantic model by specific fields in the in-memory storage.
        :param collection_name: Name of the collection (not used in memory storage).
        :param model_class: The Pydantic model class.
        :param fields: A dictionary of fields to match against the model.
        :return: The Pydantic model instance if found, otherwise None.
        """
        for item in self._storage.values():
            if all(getattr(item, k) == v for k, v in fields.items()):
                return item
        return None

    @override
    async def find_many(
        self,
        collection_name: str,
        model_class: type[T],
        filter_dict: dict[str, Any] | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[T]:
        """
        Find multiple Pydantic models in the in-memory storage based on filter criteria.
        :param collection_name: Name of the collection (not used in memory storage).
        :param model_class: The Pydantic model class.
        :param filter_dict: A dictionary of fields to filter the models.
        :param limit: Maximum number of items to return.
        :param skip: Number of items to skip before returning results.
        :return: A list of Pydantic model instances that match the filter criteria.
        """
        items = list(self._storage.values())
        if filter_dict:
            items = [
                item
                for item in items
                if all(getattr(item, k) == v for k, v in filter_dict.items())
            ]
        return items[skip : skip + limit]

    @override
    async def update_by_id(
        self,
        collection_name: str,
        document_id: ObjectId,
        update_data: T,
        model_class: type[T],
    ) -> T | None:
        """
        Update a Pydantic model in the in-memory storage by its ID.
        :param collection_name: Name of the collection (not used in memory storage).
        :param document_id: The ID of the document to update.
        :param update_data: The Pydantic model instance with updated data.
        :param model_class: The Pydantic model class.
        :return: The updated Pydantic model instance if the update was successful, otherwise None
        """
        if document_id in self._storage:
            self._storage[document_id] = update_data
            return update_data
        return None

    @override
    async def delete_by_id(self, collection_name: str, document_id: ObjectId) -> bool:
        """
        Delete a Pydantic model from the in-memory storage by its ID.
        :param collection_name: Name of the collection (not used in memory storage).
        :param document_id: The ID of the document to delete.
        :return: True if the deletion was successful, otherwise False.
        """
        if document_id in self._storage:
            del self._storage[document_id]
            return True
        return False

    @override
    async def insert_or_update(
        self,
        *,
        collection_name: str,
        model_class: Type[T],
        item: T,
        keys: Dict[str, str | None],
        on_update: Callable[[T], T] = lambda x: x,
        on_insert: Callable[[T], T] = lambda x: x,
    ) -> ObjectId:
        """
        Insert or update a Pydantic model in the in-memory storage.
        If the model already exists, it will be updated; otherwise, it will be inserted.
        :param collection_name: Name of the collection (not used in memory storage).
        :param model_class: The Pydantic model class.
        :param item: The Pydantic model instance to insert or update.
        :param keys: Fields to match for updating an existing item.
        :param on_update: Function to apply on update (default is identity).
        :param on_insert: Function to apply on insert (default is identity).
        :return: The ID of the inserted or updated item.

        """
        if item.id in self._storage:
            item = on_update(item)
            # Update existing item
            self._storage[item.id] = item
        else:
            # Insert new item
            item = on_insert(item)
            self._storage[item.id] = item
        return item.id
