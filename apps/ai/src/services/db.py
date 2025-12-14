from typing import Optional
import psycopg2
from services.embed import chunk_text, embed_text
from services.logger import get_logger
from utils.constants import DB_CONFIG

# Global database connection
_db_connection = None

logger = get_logger()


def get_db_connection():
    """Get a database cursor using a persistent connection from constants.py"""
    global _db_connection

    # Check if connection exists and is still valid
    if _db_connection is None or _db_connection.closed:
        logger.log_and_print("Creating new database connection...")
        logger.log_and_print("DB Config:", DB_CONFIG)

        _db_connection = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
        )

    return _db_connection.cursor()


def get_db_connection_instance():
    """Get the actual database connection instance for commit/rollback operations"""
    global _db_connection

    # Check if connection exists and is still valid
    if _db_connection is None or _db_connection.closed:
        logger.log_and_print("Creating new database connection...")
        logger.log_and_print("DB Config:", DB_CONFIG)

        _db_connection = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
        )

    return _db_connection


def initialize_database():
    """Function to initialize the database and create tables"""
    try:
        logger.log_and_print("Attempting to connect to the database...")
        connection = get_db_connection_instance()
        cursor = connection.cursor()

        # Example table schema
        cursor.execute(
            """
            CREATE EXTENSION IF NOT EXISTS vector;
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                sessionId TEXT DEFAULT 'default_session',
                message TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'system',
                embedding vector(768),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        connection.commit()
        cursor.close()
        logger.log_and_print("Database connection successful and table initialized.")
    except psycopg2.Error as e:
        logger.log_and_print(
            "Failed to connect to the database or initialize table:", e
        )


async def get_embeddings_from_db(embedding: dict):
    """
    Fetch embeddings and similarity scores from the database based on the user message.
    """
    cursor = get_db_connection()

    cursor.execute(
        """
        SELECT message, embedding <=> %s::vector AS similarity
        FROM messages
        WHERE role ='system'
        ORDER BY similarity ASC
        LIMIT 3
        """,
        (embedding["embedding"],),
    )
    results = cursor.fetchall()
    resultsFinal = [{"message": row[0], "similarity": row[1]} for row in results]

    cursor.close()
    return resultsFinal


async def save_message(message: str, role: str, session_id: Optional[str] = None):
    """
    Save a message and its embedding to the database.
    """
    connection = get_db_connection_instance()
    cursor = connection.cursor()
    effective_session_id = session_id if session_id is not None else "default_session"
    logger.log_and_print(
        f"Saving message to database for session: {effective_session_id}"
    )
    try:
        print(f"Embedding message... Length: {len(message)}")
        embedding = await embed_text(message)
        cursor.execute(
            """
            INSERT INTO messages (message, role, embedding, sessionId)
            VALUES (%s, %s, %s, %s);
            """,
            (message, role, embedding["embedding"], effective_session_id),
        )
        connection.commit()
        # chunks = chunk_text(message, 768)
        # for chunk in chunks:
        #     embedding = await embed_text(chunk)
        #     if not chunk or embedding is None:
        #         logger.log_and_print("Chunk or embedding is None, skipping save.")
        #         return
        #     cursor.execute(
        #         """
        #         INSERT INTO messages (message, role, embedding, sessionId)
        #         VALUES (%s, %s, %s, %s);
        #         """,
        #         (chunk, role, embedding["embedding"], effective_session_id),
        #     )
        #     connection.commit()
    except psycopg2.Error as e:
        logger.log_and_print("Database error:", e)
        connection.rollback()  # Rollback the transaction
    finally:
        cursor.close()


async def get_recent_messages(limit: int, session_id: Optional[str] = None):
    """
    Fetch the most recent messages and their roles from the database.
    Filters messages from users and assistant, sorted by latest date.
    """
    cursor = get_db_connection()
    effective_session_id = session_id if session_id is not None else "default_session"
    logger.log_and_print("Fetching recent messages for session:", effective_session_id)
    try:
        cursor.execute(
            """
            SELECT message, role, created_at
            FROM messages
            WHERE role IN ('user', 'assistant')
            AND sessionId = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (effective_session_id, limit),
        )
        results = cursor.fetchall()
        return [
            {"message": row[0], "role": row[1], "created_at": row[2]} for row in results
        ]
    except psycopg2.Error as e:
        logger.log_and_print("Database error while fetching recent messages:", e)
        return []
    finally:
        cursor.close()
