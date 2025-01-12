from typing import Any, Awaitable, Callable, TypeVar

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.environment import APP_CONFIG

T = TypeVar("T")


def get_connection_string() -> str:
    """Construct the database connection string from environment variables."""
    try:
        user = APP_CONFIG.get("DB_USER", "")
        password = APP_CONFIG.get("DB_PASSWORD", "")
        host = APP_CONFIG.get("DB_HOST", "")
        port = APP_CONFIG.get("DB_PORT", "")
        name = APP_CONFIG.get("DB_NAME", "")
        if not all([user, password, host, port, name]):
            raise ValueError(
                "One or more required database environment variables are missing."
            )
        return f"postgresql+psycopg_async://{user}:{password}@{host}:{port}/{name}"
    except Exception as e:
        raise RuntimeError(f"Failed to construct connection string: {e}")


class DatabaseManager:
    """Manages asynchronous interactions with the database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def run(self, func: Callable[[AsyncSession], Awaitable[T]]) -> T:
        """Execute a database operation with a managed session."""
        async with self._session_factory() as session:
            try:
                return await func(session)
            except IntegrityError as e:
                await session.rollback()
                raise RuntimeError(f"Integrity error during database operation: {e}")
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Database error: {e}")
            except Exception as e:
                await session.rollback()
                raise RuntimeError(f"Unexpected error during database operation: {e}")

    async def add(self, obj: Any) -> None:
        """Add an object to the database."""

        async def add_func(session: AsyncSession):
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

        return await self.run(add_func)

    async def delete(self, obj: Any) -> None:
        """Delete an object from the database."""

        async def delete_func(session: AsyncSession):
            await session.delete(obj)
            await session.commit()

        await self.run(delete_func)

    async def scalars(self, stmt: Any) -> Any:
        """Execute a query statement and return the scalar result."""
        return await self.run(lambda session: session.scalars(stmt))

    async def execute(self, stmt: Any) -> Any:
        """Execute a raw SQL statement and return the result."""
        return await self.run(lambda session: session.execute(stmt))

    async def update(self, obj: Any, values: dict) -> None:
        """Update an object with the specified values."""

        async def update_func(session: AsyncSession):
            managed_obj = await session.merge(obj)  # Reattach or load the object
            for key, value in values.items():
                setattr(managed_obj, key, value)
            await session.commit()

        await self.run(update_func)

    @classmethod
    def create_with_default_factory(cls) -> "DatabaseManager":
        """
        Create a DatabaseManager instance with a default engine and session factory.

        This method uses environment variables for database configuration.
        """
        connection_string = get_connection_string()

        # Create the async engine
        engine = create_async_engine(
            connection_string,
            pool_size=5,  # Customize based on your requirements
            max_overflow=10,  # Additional connections beyond the pool size
        )

        # Create the async session factory
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
        )

        return cls(session_factory)
