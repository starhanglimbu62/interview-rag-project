from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVISION = "20261103_0001"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_upgrade_creates_schema_in_fresh_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    engine = create_engine(database_url)

    command.upgrade(_alembic_config(database_url), "head")

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "bookings",
        "documents",
    }
    assert {
        column["name"] for column in inspector.get_columns("documents")
    } == {
        "id",
        "filename",
        "file_type",
        "character_count",
        "page_count",
        "chunk_count",
        "chunking_strategy",
        "chunk_size",
        "overlap",
        "embedding_model",
        "vector_database",
        "status",
        "created_at",
    }
    assert {
        column["name"] for column in inspector.get_columns("bookings")
    } == {
        "id",
        "candidate_name",
        "email",
        "interview_at",
        "status",
        "created_at",
    }
    assert {
        index["name"] for index in inspector.get_indexes("bookings")
    } == {"uq_bookings_active_interview_at"}
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("bookings")
    } == {"check_booking_status"}
    engine.dispose()


def test_existing_schema_can_be_stamped_without_recreating_tables(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing.db'}"
    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine)

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE bookings (id VARCHAR(36) PRIMARY KEY)"
        )

    command.stamp(_alembic_config(database_url), "head")

    with session_factory() as session:
        version = session.scalar(text("SELECT version_num FROM alembic_version"))

    assert version == REVISION
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "bookings",
        "documents",
    }
    engine.dispose()
