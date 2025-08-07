from ollama import AsyncClient
from utils.constants import MODEL_PORT

client = AsyncClient(host="http://localhost:11434")


async def embed_text(text: str) -> dict:
    """
    Generate embedding for the given text using nomic-embed-text with Ollama.
    """
    # Use Ollama's embedding API to generate embeddings
    try:

        response = await client.embeddings(model=MODEL_PORT, prompt=text)
        return {"embedding": response["embedding"]}
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Try alternative model names
        try:
            response = await client.embeddings(
                model="nomic-embed-text:latest", prompt=text
            )
            return {"embedding": response["embedding"]}
        except Exception as e2:
            print(f"Error with latest tag: {e2}")
            raise e2
