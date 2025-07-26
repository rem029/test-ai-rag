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
        # Embedding and response generation logic
        # Fetch embeddings from the database
        db_embeddings = await get_embeddings_from_db(request.text)

        # Pass the embeddings to stream_response
        response_stream = stream_response(request.text, db_embeddings, request.stream)
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


async def stream_response(text: str, embedding: dict, stream: bool = True):
    """
    Stream response from Ollama API using the gemma3:1b-it-q4_K_M model.
    The text is sent as input, and the embedding is sent as context.
    Defaults context to null if no embedding is found.
    """
    # Convert embedding to a string representation for context
    embedding_context = "\n".join([f"- {item['message']}" for item in embedding])

    # system_prompt = (
    #     "If asked about me, respond using the context below. "
    #     "Use context below to answer the question but do not mention it in your responses.\n\n"
    #     f"Context:\n{embedding_context}\n"
    # )

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

    print("System prompt:\n===\n", system_prompt, "\n===")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]

    print("Response:\n", end="")
    if stream:
        async for part in await client.chat(
            model="gemma3:1b-it-q4_K_M",
            # model="moondream:1.8b-v2-q4_K_M",
            messages=messages,
            stream=True,
        ):
            content = part["message"]["content"]
            for char in content:  # Yield character by character
                print(char, end="", flush=True)
                yield char
    else:
        response = await client.chat(
            model="gemma3:1b-it-q4_K_M", messages=messages, stream=False
        )
        content = response["message"]["content"]
        for char in content:  # Yield character by character
            print(char, end="", flush=True)
            yield char


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
                user_message TEXT NOT NULL,
                system_response TEXT NOT NULL,
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
async def get_embeddings_from_db(user_message: str):
    """
    Fetch embeddings and similarity scores from the database based on the user message.
    """
    embedding = await embed_text(user_message)
    cursor.execute(
        """
        SELECT user_message, embedding <=> %s::vector AS similarity
        FROM messages
        ORDER BY similarity ASC
        LIMIT 3
        """,
        (embedding["embedding"],),
    )
    results = cursor.fetchall()
    resultsFinal = [{"message": row[0], "similarity": row[1]} for row in results]
    print("Results from DB:", resultsFinal)
    return resultsFinal


@app.post("/insert_embedding")
async def insert_embedding(texts: list[str]):
    """
    Convert an array of text to embeddings and insert them into the database.
    """
    try:
        for text in texts:
            embedding = await embed_text(text)
            cursor.execute(
                """
                INSERT INTO messages (user_message, system_response, embedding)
                VALUES (%s, %s, %s)
                """,
                (text, "", embedding["embedding"]),
            )
        conn.commit()
        return {"status": "success", "message": "Embeddings inserted successfully."}
    except psycopg2.Error as e:
        print("Database error:", e)
        conn.rollback()  # Rollback the transaction
        return {
            "status": "error",
            "message": "Failed to insert embeddings into the database.",
        }
