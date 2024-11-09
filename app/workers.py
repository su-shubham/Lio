import asyncio
import dramatiq
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from uuid import uuid4
from pydantic import BaseModel

from app.utils.vector_db import (
    EnhancedVectorDB,
    ChatMessage,
    MessageType,
    VectorDBConfig
)
from langchain.schema import Document
from langchain.docstore.document import Document as LangchainDocument

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentInput(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None
    doc_id: Optional[str] = None
    conversation_id: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    message_type: Optional[str] = None
    limit: int = 5
    threshold: float = 0.7

# Initialize vector database with custom configuration
vector_db = EnhancedVectorDB(
    config=VectorDBConfig(
        collection_name="documents",
        similarity_threshold=0.7,
        batch_size=50
    )
)

# Worker for processing a single document and storing it in the vector database
@dramatiq.actor
def process_document_worker(doc_input: dict):
    """
    Process and store a document in the vector database.
    """
    doc_input = DocumentInput(**doc_input)
    asyncio.run(process_document(doc_input))

async def process_document(doc_input: DocumentInput) -> bool:
    try:
        message = ChatMessage(
            content=doc_input.content,
            message_type=MessageType.SYSTEM,
            timestamp=datetime.now(),
            message_id=doc_input.doc_id or str(uuid4()),
            conversation_id=doc_input.conversation_id or "default",
            metadata=doc_input.metadata or {}
        )

        success = await vector_db.embed_messages_batch([message])
        if success:
            logger.info(f"Successfully stored document: {message.message_id}")
        else:
            logger.error(f"Failed to store document: {message.message_id}")
        return success

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return False

# Worker for processing multiple documents in batch and storing them
@dramatiq.actor
def process_documents_batch_worker(documents: List[dict]):
    asyncio.run(process_documents_batch(documents))

async def process_documents_batch(documents: List[dict]) -> Dict[str, bool]:
    try:
        messages = [
            ChatMessage(
                content=doc['content'],
                message_type=MessageType.SYSTEM,
                timestamp=datetime.now(),
                message_id=doc.get('doc_id', str(uuid4())),
                conversation_id=doc.get('conversation_id', "default"),
                metadata=doc.get('metadata', {})
            )
            for doc in documents
        ]

        success = await vector_db.embed_messages_batch(messages)
        return {msg.message_id: success for msg in messages}

    except Exception as e:
        logger.error(f"Error processing document batch: {str(e)}")
        return {doc['doc_id']: False for doc in documents}

# Worker for searching documents
@dramatiq.actor
def search_documents_worker(query: dict):
    asyncio.run(search_documents(SearchQuery(**query)))

async def search_documents(query: SearchQuery) -> List[Document]:
    try:
        message_type = (
            MessageType[query.message_type.upper()]
            if query.message_type
            else None
        )

        results = await vector_db.semantic_search(
            query=query.query,
            conversation_id=query.conversation_id,
            message_type=message_type,
            top_k=query.limit
        )

        langchain_docs = [
            LangchainDocument(
                page_content=doc.page_content,
                metadata=doc.metadata
            )
            for doc in results
        ]

        return langchain_docs

    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return []

# Worker for updating documents in the vector database
@dramatiq.actor
def update_document_worker(doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    asyncio.run(update_document(doc_id, content, metadata))

async def update_document(doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    try:
        success = await vector_db.update_message(
            message_id=doc_id,
            new_content=content,
            new_metadata=metadata
        )

        if success:
            logger.info(f"Successfully updated document: {doc_id}")
        else:
            logger.error(f"Failed to update document: {doc_id}")

        return success

    except Exception as e:
        logger.error(f"Error updating document: {str(e)}")
        return False

# Worker for deleting all documents in a conversation
@dramatiq.actor
def delete_conversation_documents_worker(conversation_id: str):
    asyncio.run(delete_conversation_documents(conversation_id))

async def delete_conversation_documents(conversation_id: str) -> bool:
    try:
        success = await vector_db.delete_conversation(conversation_id)

        if success:
            logger.info(f"Successfully deleted conversation: {conversation_id}")
        else:
            logger.error(f"Failed to delete conversation: {conversation_id}")

        return success

    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return False

# Worker for creating embeddings for a given text
@dramatiq.actor
def create_embeddings_worker(text: str, metadata: Optional[Dict[str, Any]] = None):
    asyncio.run(create_embeddings(text, metadata))

async def create_embeddings(text: str, metadata: Optional[Dict[str, Any]] = None) -> List[float]:
    try:
        embeddings = await asyncio.get_event_loop().run_in_executor(
            vector_db._executor,
            lambda: vector_db.model.encode(text)
        )
        return embeddings.tolist()

    except Exception as e:
        logger.error(f"Error creating embeddings: {str(e)}")
        return []

# Worker for storing embeddings
@dramatiq.actor
def store_embeddings_worker(asset_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
    asyncio.run(store_embeddings(asset_id, text, metadata))

async def store_embeddings(asset_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    try:
        doc_input = DocumentInput(
            content=text,
            metadata=metadata,
            doc_id=asset_id
        )
        return await process_document(doc_input)

    except Exception as e:
        logger.error(f"Error storing embeddings: {str(e)}")
        return False
