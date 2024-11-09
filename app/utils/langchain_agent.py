import asyncio
from typing import List, Dict, Optional
from langchain.schema import Document
import cohere
import openai
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedAgent:
    def __init__(self, asset_id: str, language_model: str = "openai"):
        self.asset_id = asset_id
        self.language_model = language_model.lower()
        self.history = []  # Store chat history

        if self.language_model == "cohere":
            cohere_api_key = os.getenv("COHERE_API_KEY")
            if not cohere_api_key:
                raise ValueError("COHERE_API_KEY not found in environment variables.")
            self.client = cohere.Client(cohere_api_key)
        elif self.language_model == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")
            openai.api_key = openai_api_key
        else:
            raise ValueError("Invalid language_model specified. Choose 'cohere' or 'openai'.")

    async def generate_response_stream(self, message: str, similar_docs: Optional[List[Document]] = None):
        """Stream the generated response in chunks with document context."""
        try:
            # Include relevant document context in the prompt if available
            document_context = "\n\n".join([f"Context from document: {doc.page_content[:500]}" for doc in similar_docs or []])
            combined_prompt = f"{document_context}\nUser: {message}\nNote: Only respond using the information found in the provided context above."

            if self.language_model == "cohere":
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.generate(
                        model='command-xlarge-nightly',
                        prompt=combined_prompt,
                        max_tokens=300,
                        temperature=0
                    )
                )
                output = response.generations[0].text
            elif self.language_model == "openai":
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: openai.Completion.create(
                        engine="text-davinci-003",
                        prompt=combined_prompt,
                        max_tokens=300,
                        temperature=0
                    )
                )
                output = response.choices[0]['text']
            else:
                output = "Invalid language model."

            self.history.append({"user": message, "response": output})
            for chunk in self._chunk_response(output, chunk_size=50):
                yield chunk
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            yield "I apologize, but I encountered an error while processing your request."

    def _chunk_response(self, text: str, chunk_size: int = 50):
        """Split response into smaller chunks for streaming."""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    def get_history(self):
        """Retrieve chat history."""
        return self.history

class AgentManager:
    def __init__(self):
        self.agents: Dict[str, EnhancedAgent] = {}

    def get_or_create_agent(self, chat_thread_id: str, asset_id: str, language_model: str = "cohere") -> EnhancedAgent:
        if chat_thread_id not in self.agents:
            logger.info(f"Creating new agent for chat_thread_id: {chat_thread_id}")
            self.agents[chat_thread_id] = EnhancedAgent(asset_id, language_model)
        return self.agents[chat_thread_id]

    def remove_agent(self, chat_thread_id: str):
        if chat_thread_id in self.agents:
            logger.info(f"Removing agent for chat_thread_id: {chat_thread_id}")
            del self.agents[chat_thread_id]
        else:
            logger.warning(f"Attempted to remove non-existent agent for chat_thread_id: {chat_thread_id}")

    def agent_exists(self, chat_thread_id: str) -> bool:
        return chat_thread_id in self.agents

    def get_chat_history(self, chat_thread_id: str) -> List[Dict[str, str]]:
        """Retrieve chat history for a given chat thread ID."""
        if chat_thread_id in self.agents:
            return self.agents[chat_thread_id].get_history()
        return []

# Create an instance of AgentManager
agent_manager = AgentManager()

async def generate_response_stream(
    asset_id: str,
    message: str,
    chat_thread_id: str,
    language_model: str = "cohere",
    similar_docs: Optional[List[Document]] = None
):
    """Stream a response using the enhanced agent."""
    agent = agent_manager.get_or_create_agent(chat_thread_id, asset_id, language_model)
    async for response_chunk in agent.generate_response_stream(message, similar_docs):
        yield response_chunk
