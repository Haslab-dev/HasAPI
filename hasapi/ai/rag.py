"""
HasAPI RAG Module

Retrieval-Augmented Generation implementation for building knowledge bases.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
import uuid

from .embeddings import Embeddings, CachedEmbeddings
from .vectors import InMemoryVectorStore, FilterExpression
from .llm import LLM
from ..utils import get_logger, generate_id

logger = get_logger(__name__)


class Document:
    """Document container for RAG"""
    
    def __init__(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        embedding: Optional[List[float]] = None
    ):
        self.id = id or generate_id()
        self.text = text
        self.metadata = metadata or {}
        self.embedding = embedding
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"Document(id={self.id}, text={self.text[:50]}...)"


class TextSplitter:
    """Text splitter for chunking documents"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n"
    ):
        """
        Initialize text splitter.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            separator: Separator to split text on
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Split on separator first
        sections = text.split(self.separator)
        chunks = []
        current_chunk = ""
        
        for section in sections:
            # Check if adding this section would exceed chunk size
            if len(current_chunk) + len(section) + len(self.separator) <= self.chunk_size:
                if current_chunk:
                    current_chunk += self.separator + section
                else:
                    current_chunk = section
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Start new chunk with section
                current_chunk = section
                
                # Handle sections that are too long
                while len(current_chunk) > self.chunk_size:
                    # Split section
                    chunks.append(current_chunk[:self.chunk_size])
                    current_chunk = current_chunk[self.chunk_size - self.chunk_overlap:]
        
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to split
            
        Returns:
            List of chunked documents
        """
        chunked_docs = []
        
        for doc in documents:
            chunks = self.split_text(doc.text)
            
            for i, chunk in enumerate(chunks):
                # Create metadata for chunk
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    "source_doc_id": doc.id,
                    "chunk_index": i,
                    "chunk_count": len(chunks)
                })
                
                chunked_doc = Document(
                    text=chunk,
                    metadata=chunk_metadata,
                    id=f"{doc.id}_chunk_{i}"
                )
                
                chunked_docs.append(chunked_doc)
        
        return chunked_docs


class RAG:
    """
    Retrieval-Augmented Generation implementation.
    
    Provides functionality for building knowledge bases and answering questions
    based on retrieved context.
    """
    
    def __init__(
        self,
        embeddings: Optional[Embeddings] = None,
        llm: Optional[LLM] = None,
        vector_store: Optional[InMemoryVectorStore] = None,
        text_splitter: Optional[TextSplitter] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize RAG system.
        
        Args:
            embeddings: Embeddings instance for document indexing
            llm: LLM instance for answer generation
            vector_store: Vector store for document storage
            text_splitter: Text splitter for chunking documents
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity threshold
        """
        self.embeddings = embeddings or CachedEmbeddings("openai", api_key="your-api-key")
        self.llm = llm or LLM("openai", api_key="your-api-key")
        self.vector_store = vector_store
        self.text_splitter = text_splitter or TextSplitter()
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # Initialize vector store if not provided
        if self.vector_store is None:
            dimension = self.embeddings.get_dimension()
            self.vector_store = InMemoryVectorStore(dimension)
        
        self.documents = {}  # id -> Document
    
    async def add_documents(
        self,
        documents: Union[List[str], List[Document]],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Add documents to knowledge base.
        
        Args:
            documents: List of documents (strings or Document objects)
            metadata: Optional metadata for string documents
            
        Returns:
            List of document IDs
        """
        # Normalize input to Document objects
        if isinstance(documents[0], str):
            if metadata is None:
                metadata = [{} for _ in documents]
            elif len(metadata) != len(documents):
                raise ValueError("Number of metadata entries must match number of documents")
            
            doc_objects = []
            for text, meta in zip(documents, metadata):
                doc = Document(text=text, metadata=meta)
                doc_objects.append(doc)
        else:
            doc_objects = documents
        
        # Split documents into chunks
        chunked_docs = self.text_splitter.split_documents(doc_objects)
        
        # Generate embeddings for chunks
        chunk_texts = [doc.text for doc in chunked_docs]
        embeddings = await self.embeddings.embed_documents(chunk_texts)
        
        # Add to vector store
        vector_ids = await self.vector_store.add_vectors(
            embeddings,
            ids=[doc.id for doc in chunked_docs],
            metadata=[doc.to_dict() for doc in chunked_docs]
        )
        
        # Store documents
        for doc in chunked_docs:
            self.documents[doc.id] = doc
        
        logger.info(f"Added {len(chunked_docs)} chunks to knowledge base")
        return vector_ids
    
    async def add_texts(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Add text documents to knowledge base.
        
        Args:
            texts: List of text documents
            metadata: Optional metadata for each text
            
        Returns:
            List of document IDs
        """
        return await self.add_documents(texts, metadata)
    
    async def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query knowledge base for relevant documents.
        
        Args:
            question: Question to answer
            top_k: Number of documents to retrieve
            filter_expr: Optional filter expression
            
        Returns:
            Dictionary with retrieved documents and metadata
        """
        # Generate query embedding
        query_embedding = await self.embeddings.embed_query(question)
        
        # Search vector store
        top_k = top_k or self.top_k
        results = await self.vector_store.search(
            query_embedding,
            top_k=top_k,
            filter_expr=filter_expr
        )
        
        # Filter by similarity threshold
        filtered_results = [
            result for result in results
            if result["score"] >= self.similarity_threshold
        ]
        
        # Get full documents
        retrieved_docs = []
        for result in filtered_results:
            doc_id = result["id"]
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                retrieved_docs.append({
                    "document": doc.to_dict(),
                    "score": result["score"],
                    "metadata": result["metadata"]
                })
        
        return {
            "question": question,
            "retrieved_documents": retrieved_docs,
            "total_retrieved": len(retrieved_docs),
            "search_metadata": {
                "top_k": top_k,
                "similarity_threshold": self.similarity_threshold,
                "total_searched": len(results)
            }
        }
    
    async def answer(
        self,
        question: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Answer a question using retrieved context.
        
        Args:
            question: Question to answer
            top_k: Number of documents to retrieve
            filter_expr: Optional filter expression
            model: LLM model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional LLM parameters
            
        Returns:
            Dictionary with answer and retrieved documents
        """
        # Retrieve relevant documents
        query_result = await self.query(question, top_k, filter_expr)
        retrieved_docs = query_result["retrieved_documents"]
        
        if not retrieved_docs:
            return {
                "question": question,
                "answer": "I don't have enough information to answer this question.",
                "retrieved_documents": [],
                "sources": []
            }
        
        # Build context from retrieved documents
        context_parts = []
        sources = []
        
        for i, doc_data in enumerate(retrieved_docs):
            doc = doc_data["document"]
            score = doc_data["score"]
            
            context_parts.append(f"[Document {i+1}]: {doc['text']}")
            sources.append({
                "id": doc["id"],
                "score": score,
                "metadata": doc["metadata"]
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using LLM
        prompt = self._build_rag_prompt(question, context)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
            {"role": "user", "content": prompt}
        ]
        
        llm_response = await self.llm.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "question": question,
            "answer": llm_response["content"],
            "retrieved_documents": retrieved_docs,
            "sources": sources,
            "usage": llm_response.get("usage"),
            "model": llm_response.get("model")
        }
    
    async def stream_answer(
        self,
        question: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream an answer to a question using retrieved context.
        
        Args:
            question: Question to answer
            top_k: Number of documents to retrieve
            filter_expr: Optional filter expression
            model: LLM model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional LLM parameters
            
        Yields:
            Answer tokens as they are generated
        """
        # Retrieve relevant documents
        query_result = await self.query(question, top_k, filter_expr)
        retrieved_docs = query_result["retrieved_documents"]
        
        if not retrieved_docs:
            yield "I don't have enough information to answer this question."
            return
        
        # Build context from retrieved documents
        context_parts = []
        for i, doc_data in enumerate(retrieved_docs):
            doc = doc_data["document"]
            context_parts.append(f"[Document {i+1}]: {doc['text']}")
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using LLM
        prompt = self._build_rag_prompt(question, context)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
            {"role": "user", "content": prompt}
        ]
        
        async for token in self.llm.stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield token
    
    def _build_rag_prompt(self, question: str, context: str) -> str:
        """Build RAG prompt with context and question"""
        return f"""Use the following context to answer the question. If you don't know the answer based on the context, just say that you don't have enough information.

Context:
{context}

Question: {question}

Answer:"""
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """
        Delete documents from the knowledge base.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            True if successful
        """
        # Delete from vector store
        success = await self.vector_store.delete(document_ids)
        
        # Delete from document store
        for doc_id in document_ids:
            if doc_id in self.documents:
                del self.documents[doc_id]
        
        return success
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Get a document by ID.
        
        Args:
            document_id: ID of document to retrieve
            
        Returns:
            Document or None if not found
        """
        return self.documents.get(document_id)
    
    async def list_documents(
        self,
        filter_expr: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Document]:
        """
        List documents in the knowledge base.
        
        Args:
            filter_expr: Optional filter expression
            limit: Maximum number of documents to return
            
        Returns:
            List of documents
        """
        docs = list(self.documents.values())
        
        # Apply filters if provided
        if filter_expr:
            # Simple filter implementation
            filtered_docs = []
            for doc in docs:
                if self._matches_filter(doc.metadata, filter_expr):
                    filtered_docs.append(doc)
            docs = filtered_docs
        
        # Apply limit
        if limit:
            docs = docs[:limit]
        
        return docs
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_expr: Dict[str, Any]) -> bool:
        """Check if metadata matches filter expression"""
        # Simple implementation - could be enhanced
        for key, value in filter_expr.items():
            if metadata.get(key) != value:
                return False
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG system"""
        vector_stats = await self.vector_store.get_stats()
        
        return {
            "document_count": len(self.documents),
            "vector_store": vector_stats,
            "text_splitter": {
                "chunk_size": self.text_splitter.chunk_size,
                "chunk_overlap": self.text_splitter.chunk_overlap
            },
            "retrieval": {
                "top_k": self.top_k,
                "similarity_threshold": self.similarity_threshold
            }
        }