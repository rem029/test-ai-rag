from utils.constants import MODEL_PORT
from openai import OpenAI

model_main = OpenAI(base_url=MODEL_PORT["main"], api_key="no-key")
model_embed = OpenAI(base_url=MODEL_PORT["embed"], api_key="no-key")
