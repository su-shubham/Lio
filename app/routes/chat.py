from fastapi import APIRouter, HTTPException
from typing import Dict
import uuid
from app.utils.vector_db import query_embeddings, get_query_embedding
from app.utils.langchain_agent import generate_response_stream, agent_manager
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import logging

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatStartRequest(BaseModel):
    asset_id: str

class ChatMessageRequest(BaseModel):
    message: str
    chat_thread_id: str

@router.post("/start")
async def start_chat(request: ChatStartRequest):
    """Start a new chat session."""
    try:
        if not request.asset_id:
            raise HTTPException(status_code=400, detail="Asset ID cannot be empty.")

        chat_thread_id = str(uuid.uuid4())
        
        # Initialize a new agent for this chat thread
        agent_manager.get_or_create_agent(chat_thread_id, request.asset_id)
        
        logger.info(f"Started chat session with chat_thread_id: {chat_thread_id}")
        return {"chat_thread_id": chat_thread_id}
    except Exception as e:
        logger.error(f"Error starting chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message")
async def chat_message(request: ChatMessageRequest):
    """Handle a chat message and generate a response."""
    try:
        if not request.chat_thread_id:
            raise HTTPException(status_code=400, detail="Chat thread ID cannot be empty.")

        if not agent_manager.agent_exists(request.chat_thread_id):
            logger.error(f"Chat thread ID {request.chat_thread_id} not found in agent_manager.")
            raise HTTPException(status_code=404, detail="Chat thread not found.")

        async def response_generator():
            query_embedding = await get_query_embedding(request.message)
            if not query_embedding:
                yield "Failed to generate query embeddings."
                return

            similar_docs = await query_embeddings(query_embedding)
            async for response_chunk in generate_response_stream(
                agent_manager.agents[request.chat_thread_id].asset_id,
                request.message,
                request.chat_thread_id,
                similar_docs
            ):
                yield response_chunk

        logger.info(f"Processing message for chat_thread_id: {request.chat_thread_id}")
        return StreamingResponse(response_generator(), media_type="text/plain")
        
    except KeyError:
        logger.error(f"Chat thread ID {request.chat_thread_id} not found in agent_manager (KeyError).")
        raise HTTPException(status_code=404, detail="Chat thread not found.")
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{chat_thread_id}")
async def get_chat_history(chat_thread_id: str):
    """Retrieve chat history for a given chat thread ID."""
    try:
        if not agent_manager.agent_exists(chat_thread_id):
            logger.error(f"Chat thread ID {chat_thread_id} not found in agent_manager.")
            raise HTTPException(status_code=404, detail="Chat thread not found.")
        
        history = agent_manager.get_chat_history(chat_thread_id)
        return {"chat_thread_id": chat_thread_id, "history": history}
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_chats():
    """List all active chat sessions."""
    active_chats = list(agent_manager.agents.keys())
    return {"active_chats": active_chats}

@router.post("/resume/{chat_thread_id}")
async def resume_chat(chat_thread_id: str):
    """Resume an existing chat session."""
    try:
        if not agent_manager.agent_exists(chat_thread_id):
            raise HTTPException(status_code=404, detail="Chat thread not found.")
        return {"message": f"Chat session {chat_thread_id} resumed successfully"}
    except Exception as e:
        logger.error(f"Error resuming chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{chat_thread_id}")
async def delete_chat_session(chat_thread_id: str):
    """Delete a chat session and its history."""
    try:
        agent_manager.remove_agent(chat_thread_id)
        logger.info(f"Deleted chat session with chat_thread_id: {chat_thread_id}")
        return {"message": f"Chat session {chat_thread_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_chat_threads():
    """Retrieve a list of all chat thread IDs."""
    chat_threads = list(agent_manager.agents.keys())
    return {"chat_threads": chat_threads}

@router.get("/metadata/{chat_thread_id}")
async def get_chat_metadata(chat_thread_id: str):
    """Retrieve metadata for a specific chat session."""
    try:
        if not agent_manager.agent_exists(chat_thread_id):
            raise HTTPException(status_code=404, detail="Chat thread not found.")
        
        # Placeholder for actual metadata retrieval logic
        metadata = {
            "chat_thread_id": chat_thread_id,
            "agent_type": type(agent_manager.agents[chat_thread_id]).__name__,
            "asset_id": agent_manager.agents[chat_thread_id].asset_id
        }
        return {"metadata": metadata}
    except Exception as e:
        logger.error(f"Error retrieving chat metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))
