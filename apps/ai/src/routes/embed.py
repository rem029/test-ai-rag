from fastapi import APIRouter
from controller.embed import insert_embedding_logic

router = APIRouter()


@router.post("/insert_embedding")
async def insert_embedding(texts: list[str]):
    """
    Convert an array of text to embeddings and insert them into the database.
    """
    return await insert_embedding_logic(texts)