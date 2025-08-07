from typing import Literal
from utils.constants import MODEL_PORT
from openai import AsyncOpenAI

model_main = AsyncOpenAI(base_url=MODEL_PORT["main"], api_key="no-key")
model_embed = AsyncOpenAI(base_url=MODEL_PORT["embed"], api_key="no-key")


model_clients = {
    "main": model_main,
    "embed": model_embed,
}


async def check_model(model: Literal["main", "embed"] = "main"):
    try:
        client = model_clients[model]
        response = await client.models.list()
        print("Connection successful. Models:", [m.id for m in response.data])
        return True
    except Exception as e:
        print("Connection failed:", e)
        return False
