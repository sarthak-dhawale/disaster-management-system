from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from app.config import DB_URL, DB_TIME_ZONE

if make_url(DB_URL).drivername != "mysql+pymysql":
    raise ValueError("The application requires MySQL through PyMySQL")
engine = create_engine(
    DB_URL,
    echo=False,
    hide_parameters=True,
    pool_pre_ping=True,
    isolation_level="READ COMMITTED",
    pool_recycle=1800,
    pool_size=5,
    max_overflow=5,
    connect_args={
        "connect_timeout": 5,
        "read_timeout": 15,
        "write_timeout": 15,
        "charset": "utf8mb4",
        "init_command": f"SET time_zone = '{DB_TIME_ZONE}'",
    },
)


@event.listens_for(engine, "checkout")
def clear_history_context(connection, record, proxy):
    # MySQL user variables survive rollback and pooling; clear them before reuse.
    with connection.cursor() as cursor:
        cursor.execute(
            "SET @dms_actor_id=NULL,@dms_actor_name=NULL,@dms_movement_kind=NULL,@dms_movement_note=NULL,@dms_allocation_id=NULL"
        )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def test_database_connection():
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar() == 1
    except SQLAlchemyError:
        return False
