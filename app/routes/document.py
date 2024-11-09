from fastapi import APIRouter, HTTPException, UploadFile
from pathlib import Path
import uuid
from app.workers import create_embeddings_worker

router = APIRouter()

@router.post("/process")
async def process_document(file: UploadFile):
    # Define a directory where the application has write permissions
    upload_dir = Path("./uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist

    file_location = upload_dir / file.filename

    # Save the file to the designated location
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    # Generate a unique asset ID for the uploaded document
    asset_id = str(uuid.uuid4())

    # Send the file for background processing using the worker
    create_embeddings_worker.send(str(file_location), asset_id)

    return {"message": "File processing initiated.", "file_path": str(file_location), "asset_id": asset_id}
