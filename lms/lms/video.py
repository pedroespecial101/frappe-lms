# Copyright (c) 2024, Frappe Technologies and contributors
# License: MIT. See LICENSE

"""
Video streaming API endpoint with HTTP byte-range support.

This module provides video file serving with proper byte-range request handling,
enabling video seeking (skip forward/backward) in HTML5 video players.

The default Frappe static file middleware (via Werkzeug's SharedDataMiddleware)
does NOT support HTTP Range requests, which causes video seeking to fail.
This endpoint fixes that by properly implementing RFC 7233 byte ranges.
"""

import os
import mimetypes
import frappe
from frappe import _
from werkzeug.wrappers import Response


@frappe.whitelist(allow_guest=True)
def stream(file: str = None):
    """
    Stream a video file with HTTP byte-range support.
    
    This endpoint enables video seeking by properly handling Range headers
    and returning 206 Partial Content responses.
    
    Args:
        file: The filename to stream (relative to public/files directory)
        
    Returns:
        Response: A streaming response with appropriate headers for video playback
        
    Example:
        /api/method/lms.lms.video.stream?file=wistia_abc123.mp4
    """
    if not file:
        frappe.throw(_("File parameter is required"), frappe.exceptions.ValidationError)
    
    # Security: Prevent path traversal attacks
    if ".." in file or file.startswith("/"):
        frappe.throw(_("Invalid file path"), frappe.exceptions.ValidationError)
    
    # Build the full file path
    site_path = frappe.get_site_path()
    file_path = os.path.join(site_path, "public", "files", file)
    
    # Resolve any symlinks and verify the file exists
    try:
        real_path = os.path.realpath(file_path)
    except Exception:
        frappe.throw(_("File not found"), frappe.exceptions.DoesNotExistError)
    
    if not os.path.isfile(real_path):
        frappe.throw(_("File not found"), frappe.exceptions.DoesNotExistError)
    
    # Get file info
    file_size = os.path.getsize(real_path)
    mime_type = mimetypes.guess_type(file)[0] or "application/octet-stream"
    
    # Parse the Range header
    range_header = frappe.request.headers.get("Range")
    
    if range_header:
        return _serve_partial_content(real_path, file_size, mime_type, range_header)
    else:
        return _serve_full_content(real_path, file_size, mime_type)


def _parse_range_header(range_header: str, file_size: int) -> tuple:
    """
    Parse HTTP Range header (RFC 7233).
    
    Args:
        range_header: The Range header value (e.g., "bytes=0-1023")
        file_size: Total size of the file
        
    Returns:
        Tuple of (start_byte, end_byte) or None if invalid
    """
    if not range_header.startswith("bytes="):
        return None
    
    try:
        range_spec = range_header[6:]  # Remove "bytes=" prefix
        
        if range_spec.startswith("-"):
            # Suffix range: last N bytes (e.g., "bytes=-500")
            suffix_length = int(range_spec[1:])
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif range_spec.endswith("-"):
            # Open-ended range: from start to end (e.g., "bytes=1024-")
            start = int(range_spec[:-1])
            end = file_size - 1
        else:
            # Closed range: specific byte range (e.g., "bytes=0-1023")
            parts = range_spec.split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else file_size - 1
        
        # Validate range
        if start < 0 or start >= file_size or end < start:
            return None
        
        # Clamp end to file size
        end = min(end, file_size - 1)
        
        return (start, end)
        
    except (ValueError, IndexError):
        return None


def _serve_partial_content(file_path: str, file_size: int, mime_type: str, range_header: str) -> Response:
    """
    Serve a partial file response (206 Partial Content).
    
    Args:
        file_path: Absolute path to the file
        file_size: Total file size in bytes
        mime_type: MIME type of the file
        range_header: The Range header from the request
        
    Returns:
        Response with partial content and appropriate headers
    """
    range_info = _parse_range_header(range_header, file_size)
    
    if range_info is None:
        # Invalid range - return 416 Range Not Satisfiable
        response = Response("Range Not Satisfiable", status=416)
        response.headers["Content-Range"] = f"bytes */{file_size}"
        return response
    
    start, end = range_info
    content_length = end - start + 1
    
    # Read the requested byte range
    with open(file_path, "rb") as f:
        f.seek(start)
        data = f.read(content_length)
    
    response = Response(data, status=206, mimetype=mime_type)
    response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    response.headers["Content-Length"] = str(content_length)
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    return response


def _serve_full_content(file_path: str, file_size: int, mime_type: str) -> Response:
    """
    Serve the full file content (200 OK).
    
    Args:
        file_path: Absolute path to the file
        file_size: Total file size in bytes
        mime_type: MIME type of the file
        
    Returns:
        Response with full file content
    """
    def generate():
        """Generator to stream file in chunks."""
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    response = Response(generate(), status=200, mimetype=mime_type)
    response.headers["Content-Length"] = str(file_size)
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    return response
