from ollama import AsyncClient
from utils.constants import OLLAMA_HOST

client = AsyncClient(host='http://localhost:11434')


async def embed_text(text: str) -> dict:
    """
    Generate embedding for the given text using nomic-embed-text with Ollama.
    """
    # Use Ollama's embedding API to generate embeddings
    print("Ollama Host:", OLLAMA_HOST)
    try:
        
        response = await client.embeddings(model="nomic-embed-text", prompt=text)
        return {"embedding": response["embedding"]}
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Try alternative model names
        try:
            response = await client.embeddings(model="nomic-embed-text:latest", prompt=text)
            return {"embedding": response["embedding"]}
        except Exception as e2:
            print(f"Error with latest tag: {e2}")
            raise e2


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


async def chat_with_model(messages: list, stream: bool = True):
    """
    Chat with the Ollama model and return response.
    """
    if stream:
        return await client.chat(
            model="gemma3:1b-it-q4_K_M",
            messages=messages,
            stream=True,
        )
    else:
        return await client.chat(
            model="gemma3:1b-it-q4_K_M", 
            messages=messages, 
            stream=False
        )