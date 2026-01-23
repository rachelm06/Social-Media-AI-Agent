"""
Document chunking strategies for RAG system.
"""
import re
from typing import List, Dict, Any, Optional


def chunk_document(
    content: str,
    source_id: str,
    strategy: str = "markdown_header",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    sentences_per_chunk: int = 3
) -> List[Dict[str, Any]]:
    """
    Chunk a document using the specified strategy.
    
    Args:
        content: Document content to chunk
        source_id: Identifier for the source document
        strategy: Chunking strategy - "fixed_chars", "paragraph", "sentence", "markdown_header"
        chunk_size: Character count for fixed_chars strategy
        chunk_overlap: Overlap between chunks for fixed_chars strategy
        sentences_per_chunk: Number of sentences per chunk for sentence strategy
        
    Returns:
        List of chunk dictionaries with content and metadata
    """
    if strategy == "fixed_chars":
        return _chunk_by_fixed_chars(content, source_id, chunk_size, chunk_overlap)
    elif strategy == "paragraph":
        return _chunk_by_paragraph(content, source_id)
    elif strategy == "sentence":
        return _chunk_by_sentence(content, source_id, sentences_per_chunk)
    elif strategy == "markdown_header":
        return _chunk_by_markdown_header(content, source_id)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _chunk_by_fixed_chars(
    content: str,
    source_id: str,
    chunk_size: int,
    chunk_overlap: int
) -> List[Dict[str, Any]]:
    """Chunk by fixed character count with overlap."""
    chunks = []
    start = 0
    
    while start < len(content):
        end = start + chunk_size
        chunk_content = content[start:end]
        
        # Try to break at word boundary if not at end
        if end < len(content):
            # Find last space before chunk_size
            last_space = chunk_content.rfind(' ')
            if last_space > chunk_size * 0.8:  # Only break at word if reasonable
                chunk_content = chunk_content[:last_space]
                end = start + last_space
        
        if chunk_content.strip():
            chunks.append({
                "content": chunk_content.strip(),
                "metadata": {
                    "source_id": source_id,
                    "chunk_index": len(chunks),
                    "strategy": "fixed_chars",
                    "start_pos": start,
                    "end_pos": end
                }
            })
        
        # Move start position with overlap
        start = end - chunk_overlap
        if start >= len(content):
            break
    
    return chunks if chunks else [{"content": content, "metadata": {"source_id": source_id, "strategy": "fixed_chars"}}]


def _chunk_by_paragraph(
    content: str,
    source_id: str
) -> List[Dict[str, Any]]:
    """Chunk by paragraph boundaries (double newlines)."""
    paragraphs = content.split('\n\n')
    chunks = []
    
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        
        chunks.append({
            "content": para,
            "metadata": {
                "source_id": source_id,
                "chunk_index": i,
                "strategy": "paragraph",
                "paragraph_index": i
            }
        })
    
    return chunks if chunks else [{"content": content, "metadata": {"source_id": source_id, "strategy": "paragraph"}}]


def _chunk_by_sentence(
    content: str,
    source_id: str,
    sentences_per_chunk: int
) -> List[Dict[str, Any]]:
    """Chunk by sentence count."""
    # Simple sentence splitting by common delimiters
    sentence_endings = re.compile(r'[.!?]+\s+')
    sentences = sentence_endings.split(content)
    
    chunks = []
    current_chunk = []
    chunk_index = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        current_chunk.append(sentence)
        
        if len(current_chunk) >= sentences_per_chunk:
            chunk_content = ' '.join(current_chunk)
            chunks.append({
                "content": chunk_content,
                "metadata": {
                    "source_id": source_id,
                    "chunk_index": chunk_index,
                    "strategy": "sentence",
                    "sentence_count": len(current_chunk)
                }
            })
            current_chunk = []
            chunk_index += 1
    
    # Add remaining sentences as final chunk
    if current_chunk:
        chunk_content = ' '.join(current_chunk)
        chunks.append({
            "content": chunk_content,
            "metadata": {
                "source_id": source_id,
                "chunk_index": chunk_index,
                "strategy": "sentence",
                "sentence_count": len(current_chunk)
            }
        })
    
    return chunks if chunks else [{"content": content, "metadata": {"source_id": source_id, "strategy": "sentence"}}]


def _chunk_by_markdown_header(
    content: str,
    source_id: str
) -> List[Dict[str, Any]]:
    """Chunk by markdown headers (##)."""
    # Extract document title
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    doc_title = title_match.group(1) if title_match else source_id
    
    # Split on ## headers
    sections = re.split(r'(?=^##\s+)', content, flags=re.MULTILINE)
    
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        
        # Extract section title
        section_title_match = re.search(r'^##\s+(.+)$', section, re.MULTILINE)
        section_title = section_title_match.group(1) if section_title_match else "Introduction"
        
        # Build chunk with context
        chunk_content = f"[From: {source_id}]\n# {doc_title}\n\n{section}"
        
        chunks.append({
            "content": chunk_content,
            "metadata": {
                "source_id": source_id,
                "chunk_index": i,
                "strategy": "markdown_header",
                "section_title": section_title,
                "doc_title": doc_title
            }
        })
    
    return chunks if chunks else [{"content": content, "metadata": {"source_id": source_id, "strategy": "markdown_header"}}]
