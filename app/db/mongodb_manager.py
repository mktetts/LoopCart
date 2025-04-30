import asyncio
import logging
import sys
from collections.abc import Awaitable, Mapping, Sequence
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from config.settings import settings
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorClientSession,
    AsyncIOMotorDatabase,
)
from pymongo.results import InsertOneResult, UpdateResult

logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
log = logging.getLogger("dbmanager")

P = ParamSpec("P")
R = TypeVar("R")


class MongoDBManager:
    def __init__(self) -> None:
        try:
            self.mongodb_client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(
                settings.MONGOURI, serverSelectionTimeoutMS=5000
            )
            self.db: AsyncIOMotorDatabase[dict[str, Any]] = self.mongodb_client.get_database()
            # asyncio.run(self._check_connection())
            log.info("✅ Database connection successful!")
        except Exception:
            log.exception("❌ Database connection failed:")
            sys.exit(1)

    async def _check_connection(self) -> None:
        await self.mongodb_client.admin.command("ping")

    async def create(
        self,
        collection_name: str,
        **data: Any,
    ) -> InsertOneResult:
        data["created_at"] = datetime.now(timezone.utc)
        data["updated_at"] = datetime.now(timezone.utc)
        return await self.db[collection_name].insert_one(data)

    async def read(self, collection_name: str, **kwargs: Any) -> list[dict[str, Any]]:
        cursor = self.db[collection_name].find(kwargs)
        return await cursor.to_list()

    async def find_by_id(self, collection_name: str, **kwargs: Any) -> dict[str, Any] | None:
        result = await self.db[collection_name].find_one(kwargs)
        return result if result else None

    async def update(
        self,
        collection_name: str,
        update_data: dict[str, Any],
        upsert: bool = False,
    ) -> UpdateResult:
        if not update_data:
            raise ValueError("No update data provided")

        update_data.setdefault("$set", {})["updated_at"] = datetime.now(timezone.utc)
        update_data.setdefault("$setOnInsert", {})["created_at"] = datetime.now(timezone.utc)

        result: UpdateResult = await self.db[collection_name].update_one(
            update_data, upsert=upsert
        )
        return result

    def with_db_transaction(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            session: AsyncIOMotorClientSession = await self.mongodb_client.start_session()
            async with session.start_transaction():
                try:
                    log.debug("🔄 Transaction started")
                    kwargs["session"] = session
                    result: R = await func(*args, **kwargs)
                except Exception:
                    await session.abort_transaction()
                    log.debug("🚨 Transaction aborted")
                    raise
                else:
                    await session.commit_transaction()
                    log.debug("✅ Transaction committed")
                    return result
                finally:
                    log.debug("🛑 Ending session...")
                    await session.end_session()

        return wrapper


mongodb_manager: MongoDBManager = MongoDBManager()
# await mongodb_manager.check_connection()
