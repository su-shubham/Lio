# app/utils/file_handler.py

import os
from typing import Optional
import PyPDF2
from docx import Document
import magic  # for file type detection

class UnsupportedFileTypeError(Exception):
    """Raised when file type is not supported."""
    pass

def detect_file_type(file_path: str) -> str:
    """Detect file type using python-magic."""
    mime = magic.Magic(mime=True)
    return mime.from_file(file_path)

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = []
        for page in pdf_reader.pages:
            text.append(page.extract_text())
        return '\n'.join(text)

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    doc = Document(file_path)
    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])

def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from supported file types (PDF, DOCX, TXT).
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: Extracted text content
        
    Raises:
        UnsupportedFileTypeError: If file type is not supported
        Exception: For other processing errors
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    file_type = detect_file_type(file_path)
    
    try:
        if 'pdf' in file_type.lower():
            return extract_text_from_pdf(file_path)
        elif 'msword' in file_type.lower() or 'officedocument' in file_type.lower():
            return extract_text_from_docx(file_path)
        elif 'text' in file_type.lower():
            return extract_text_from_txt(file_path)
        else:
            raise UnsupportedFileTypeError(f"Unsupported file type: {file_type}")
    except Exception as e:
        raise Exception(f"Error extracting text from file: {str(e)}")