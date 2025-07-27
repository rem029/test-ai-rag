from itertools import tee
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from ollama import AsyncClient
import httpx
import json
import psycopg2

client = AsyncClient(host="http://localhost:11434")

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()


class MessageRequest(BaseModel):
    text: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded image
    audioResponse: Optional[bool] = False
    stream: Optional[bool] = False
    messages: Optional[list] = []  # Store conversation history
    context: Optional[str] = None  # Optional context to replace system_prompt


@app.post("/message")
async def handle_message(request: MessageRequest):
    """
    Unified endpoint to handle text, image, and audio requests.
    """
    if request.image:
        # Vision logic
        description = await analyze_image(request.image)
        return {"description": description}

    if request.text:
        response_stream = stream_response(request.text, request.stream, request.context)
        return StreamingResponse(response_stream, media_type="text/plain")

    if request.audioResponse:
        # Text-to-speech logic
        audio_path = await text_to_speech(request.text)
        return {"audio_path": audio_path}

    return {"error": "Invalid request"}


async def embed_text(text: str) -> dict:
    """
    Generate embedding for the given text using nomic-embed-text with Ollama.
    """
    # Use Ollama's embedding API to generate embeddings
    response = await client.embeddings(model="nomic-embed-text", prompt=text)
    return {"embedding": response["embedding"]}


async def text_to_speech(text: str) -> str:
    """
    Generate TTS audio for the given text.
    """
    # Placeholder logic for TTS
    return "output.wav"


async def analyze_image(image_data: str) -> str:
    """
    Analyze the given image and return a description.
    """
    # Placeholder logic for vision analysis
    return "Image description"


async def stream_response(
    text: str, stream: bool = True, context: Optional[str] = None
):
    """
    Stream response from Ollama API using the gemma3:1b-it-q4_K_M model.
    The text is sent as input, and the embedding is sent as context.
    Defaults context to null if no embedding is found.
    """
    # Embedding and response generation logic
    embedding = await embed_text(text)
    db_embeddings = await get_embeddings_from_db(embedding)

    # Convert embedding to a string representation for context
    embedding_context = "\n".join([f"- {item['message']}" for item in db_embeddings])

    if context:
        system_prompt = f"{context}\n"
        system_prompt += f"\nContext:\n{embedding_context}"
    else:
        system_prompt = (
            "You are Mary Test's official support agent.\n\n"
            "Behavior Rules:\n"
            "- If greeted politely (e.g., 'hello', 'hi', 'good morning'), respond with:\n"
            '  "Hello, I am Mary Test\'s official support agent. How can I assist you today?"\n'
            "- If the question is NOT related to Mary Test, respond with:\n"
            '  "I\'m sorry, I can only answer questions about Mary Test."\n\n'
            "Topic Restriction:\n"
            "You are only allowed to answer questions directly related to the company Mary Test. "
            "Do not respond to general tech queries, personal questions, or anything outside the company's scope.\n\n"
            "You may only use the facts below to answer questions. Do not fabricate or assume details.\n\n"
            f"{embedding_context}\n"
            "Strictly respond using information from the list above."
        )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    print("System messages:\n===\n", system_prompt, "\n===")

    recent_messages = await get_recent_messages(limit=5)  # Fetch the last 5 messages
    recent_messages.reverse()  # Reverse the list to maintain chronological order
    print("Last messages:\n===")
    for msg in recent_messages:
        print(msg["role"], ":", msg["message"])
        messages.append({"role": msg["role"], "content": msg["message"]})
    print("===")

    messages.append({"role": "user", "content": text})
    await save_message(text, "user", embedding)

    print("Response:\n")
    if stream:
        text = ""
        async for part in await client.chat(
            model="gemma3:1b-it-q4_K_M",
            # model="moondream:1.8b-v2-q4_K_M",
            messages=messages,
            stream=True,
        ):
            content = part["message"]["content"]
            if part.done:
                embedding = await embed_text(text)
                await save_message(text, "assistant", embedding)
            for char in content:  # Yield character by character
                text += char
                print(char, end="", flush=True)
                # Save the message content directly
                yield char
    else:
        response = await client.chat(
            model="gemma3:1b-it-q4_K_M", messages=messages, stream=False
        )
        content = response["message"]["content"]
        embedding = await embed_text(content)
        await save_message(content, "assistant", embedding)
        for char in content:  # Yield character by character
            print(char, end="", flush=True)
            yield char

    # # Save the entire content and embedding after processing


# PostgreSQL connection details
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "postgres",
    "password": "123",
    "database": "test_db",
}


# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname=DB_CONFIG["database"],
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"],
    host=DB_CONFIG["host"],
    port=DB_CONFIG["port"],
)
cursor = conn.cursor()


# Function to initialize the database and create tables
def initialize_database():
    try:
        print("Attempting to connect to the database...")
        connection = psycopg2.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
        )
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
        connection.close()
        print("Database connection successful and table initialized.")
    except psycopg2.Error as e:
        print("Failed to connect to the database or initialize table:", e)


# Call the function to initialize the database
initialize_database()


# Fetch embeddings and similarity scores from the database
async def get_embeddings_from_db(embedding: dict):
    """
    Fetch embeddings and similarity scores from the database based on the user message.
    """
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
    return resultsFinal


@app.post("/insert_embedding")
async def insert_embedding(texts: list[str]):
    """
    Convert an array of text to embeddings and insert them into the database.
    """
    try:
        for text in texts:
            embedding = await embed_text(text)
            await save_message(text, "system", embedding)
        conn.commit()
        return {"status": "success", "message": "Embeddings inserted successfully."}
    except psycopg2.Error as e:
        print("Database error:", e)
        conn.rollback()  # Rollback the transaction
        return {
            "status": "error",
            "message": "Failed to insert embeddings into the database.",
        }


async def save_message(message: str, role: str, embedding: dict):
    """
    Save a message and its embedding to the database.
    """
    try:
        cursor.execute(
            """
            INSERT INTO messages (message, role, embedding)
            VALUES (%s, %s, %s)
            """,
            (message, role, embedding["embedding"]),
        )
        conn.commit()
    except psycopg2.Error as e:
        print("Database error:", e)
        conn.rollback()  # Rollback the transaction


async def get_recent_messages(limit: int):
    """
    Fetch the most recent messages and their roles from the database.
    Filters messages from users and assistant, sorted by latest date.
    """
    try:
        cursor.execute(
            """
            SELECT message, role, created_at
            FROM messages
            WHERE role IN ('user', 'assistant')
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        results = cursor.fetchall()
        return [
            {"message": row[0], "role": row[1], "created_at": row[2]} for row in results
        ]
    except psycopg2.Error as e:
        print("Database error while fetching recent messages:", e)
        return []
