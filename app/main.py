# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import document, chat
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with metadata
app = FastAPI(
    title="Lio: Advanced Retrieval-Augmented Generation Service",
    description=(
        "Lio is a comprehensive service designed for efficient document processing "
        "and interactive chat capabilities powered by retrieval-augmented generation. "
        "Leverage the power of advanced retrieval techniques to integrate document context seamlessly "
        "into chat interactions for more precise and context-aware responses."
    ),
    version="1.0.0",
    contact={
        "name": "suNetworks",
        "email": "code.shubham.com@gmail.com",
        "url": "https://bento.me/su-shubham"
    }
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your domain for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include document and chat routes with tags for better documentation
app.include_router(
    document.router, 
    prefix="/api/documents", 
    tags=["Document Processing"],
    responses={404: {"description": "Not found"}}
)
app.include_router(
    chat.router, 
    prefix="/api/chat", 
    tags=["Chat Interaction"],
    responses={404: {"description": "Not found"}}
)

# Event handlers for startup and shutdown
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up the RAG service...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the RAG service...")
