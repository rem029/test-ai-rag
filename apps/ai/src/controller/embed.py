import psycopg2
from services.ai import embed_text
from services.db import save_message


async def insert_embedding_logic(texts: list[str]):
    """
    Convert an array of text to embeddings and insert them into the database.
    """
    try:
        for text in texts:
            print("@insert_embedding_logic", "inserting...", text)
            await save_message(text, "system")
        return {"status": "success", "message": "Embeddings inserted successfully."}
    except psycopg2.Error as e:
        print("Database error:", e)
        return {
            "status": "error",
            "message": "Failed to insert embeddings into the database.",
        }
