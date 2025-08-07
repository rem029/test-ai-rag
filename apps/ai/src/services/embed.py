from urllib import response
from utils.constants import MODEL_PORT
from services.clients import model_embed


async def embed_text(text: str) -> dict:
    """
    Generate embedding for the given text using nomic-embed-text with Ollama.
    """
    try:
        response = await model_embed.embeddings.create(
            input=text, encoding_format="float", model=""
        )
        vector = response[0].embedding[0]
        return {"embedding": vector}
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return {"embedding": [-1]}
