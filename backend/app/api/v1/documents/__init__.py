"""
Documents module - File and document management.

This module handles:
- File uploads and storage
- Document management
- File attachments for meetings, motions, etc.
"""
from fastapi import APIRouter

# Create the documents router for v1 API endpoints
documents_router = APIRouter(prefix="/documents", tags=["documents"])

__all__ = [
    "documents_router",
]
