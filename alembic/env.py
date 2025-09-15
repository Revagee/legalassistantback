import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from dotenv import load_dotenv

load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
from src.database.base import Base  # noqa: E402

# Import models so they are registered in Base.metadata
import src.database.users  # noqa: F401,E402
import src.database.refresh_tokens  # noqa: F401,E402
import src.database.password_resets  # noqa: F401,E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Read DATABASE_URL and ensure asyncpg driver when using Postgres
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        # Normalize postgres scheme and switch to asyncpg
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        config.set_main_option("sqlalchemy.url", database_url)

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # Read DATABASE_URL and ensure asyncpg driver when using Postgres
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        config.set_main_option("sqlalchemy.url", database_url)

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
