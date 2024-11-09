from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    Range
)
from qdrant_client.http.models import UpdateStatus
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional, Any
from langchain.schema import Document
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define MessageType Enum
class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

# Define ChatMessage dataclass
@dataclass
class ChatMessage:
    content: str
    message_type: MessageType
    timestamp: datetime
    message_id: str
    conversation_id: str
    metadata: Optional[Dict[str, Any]] = None

# Define VectorDBConfig before using it in the EnhancedVectorDB class
class VectorDBConfig:
    def __init__(
        self,
        collection_name: str = "chat_messages",
        vector_size: int = 384,
        distance: Distance = Distance.COSINE,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 100,
        similarity_threshold: float = 0.7
    ):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.model_name = model_name
        self.batch_size = batch_size
        self.similarity_threshold = similarity_threshold

# EnhancedVectorDB class definition
class EnhancedVectorDB:
    def __init__(
        self,
        qdrant_url: str = ":memory:",
        config: Optional[VectorDBConfig] = None
    ):
        self.config = config or VectorDBConfig()
        self.client = QdrantClient(qdrant_url)
        self.model = SentenceTransformer(self.config.model_name)
        self._initialize_collection()
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _initialize_collection(self):
        """Initialize the collection with proper schema and indexing."""
        try:
            # Create or recreate the collection with specified vector parameters
            self.client.recreate_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=self.config.vector_size,
                    distance=self.config.distance
                )
            )
            logger.info(f"Successfully initialized collection: {self.config.collection_name}")
        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise

    async def embed_messages_batch(
        self,
        messages: List[ChatMessage]
    ) -> bool:
        """Batch process and store multiple chat messages."""
        try:
            # Process messages in batches
            for i in range(0, len(messages), self.config.batch_size):
                batch = messages[i:i + self.config.batch_size]
                
                # Generate embeddings for the batch
                texts = [msg.content for msg in batch]
                embeddings = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.model.encode(texts, show_progress_bar=False)
                )

                # Create points for the batch
                points = [
                    PointStruct(
                        id=msg.message_id,
                        vector=embedding.tolist(),
                        payload={
                            "message_type": msg.message_type.value,
                            "timestamp": int(msg.timestamp.timestamp()),
                            "conversation_id": msg.conversation_id,
                            "message_id": msg.message_id,
                            "content": msg.content,
                            "metadata": msg.metadata or {}
                        }
                    )
                    for msg, embedding in zip(batch, embeddings)
                ]

                # Store the batch
                self.client.upsert(
                    collection_name=self.config.collection_name,
                    points=points,
                    wait=True
                )

            logger.info(f"Successfully embedded {len(messages)} messages")
            return True
        except Exception as e:
            logger.error(f"Error in batch embedding: {str(e)}")
            return False

    async def query_embeddings(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Query embeddings for similarity search."""
        try:
            # Perform search in Qdrant with given query embeddings
            results = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self.client.search(
                    collection_name=self.config.collection_name,
                    query_vector=query_embedding,
                    limit=top_k
                )
            )
            
            # Format results to match the expected structure
            formatted_results = [
                {
                    'payload': {
                        'content': hit.payload.get('content', ''),
                        'file_name': hit.payload.get('metadata', {}).get('file_name', 'Unknown'),
                        **hit.payload.get('metadata', {})
                    },
                    'score': hit.score
                }
                for hit in results
            ]
            
            return formatted_results

        except Exception as e:
            logger.error(f"Error querying embeddings: {str(e)}")
            return []

# Export the query_embeddings method for use in other parts of the application
async def query_embeddings(query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """Query embeddings using the vector database asynchronously."""
    vector_db_instance = EnhancedVectorDB()  # Assuming you create an instance of EnhancedVectorDB with proper config
    return await vector_db_instance.query_embeddings(query_embedding, top_k)


async def get_query_embedding(text: str) -> List[float]:
    """Generate embeddings for a given text."""
    try:
        vector_db_instance = EnhancedVectorDB()  # Create an instance of EnhancedVectorDB with proper config
        embedding = await asyncio.get_event_loop().run_in_executor(
            vector_db_instance._executor,
            lambda: vector_db_instance.model.encode(text, show_progress_bar=False)
        )
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating query embeddings: {str(e)}")
        return []


