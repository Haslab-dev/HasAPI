"""
HasAPI Embeddings Module

Provides text embedding functionality with support for multiple providers.
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod

from ..utils import get_logger
from ..exceptions import DependencyError

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""
    
    @abstractmethod
    async def embed_text(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings for text(s)"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002", base_url: Optional[str] = None):
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            self.model = model
        except ImportError:
            raise DependencyError("openai", "Install with: pip install hasapi[ai]")
    
    async def embed_text(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings using OpenAI"""
        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                **kwargs
            )
            
            # Extract embeddings
            embeddings = [data.embedding for data in response.data]
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise
    
    def get_dimension(self) -> int:
        """Get embedding dimension for OpenAI model"""
        dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
        return dimensions.get(self.model, 1536)


class SentenceTransformerProvider(EmbeddingProvider):
    """Sentence Transformers embedding provider"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise DependencyError("sentence-transformers", "Install with: pip install sentence-transformers")
    
    async def embed_text(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings using Sentence Transformers"""
        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, self.model.encode, texts
            )
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Sentence Transformer embedding error: {e}")
            raise
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()


class CustomEmbeddingProvider(EmbeddingProvider):
    """Custom embedding provider"""
    
    def __init__(self, embed_func: callable, dimension: int):
        """
        Initialize custom provider
        
        Args:
            embed_func: Function that takes text(s) and returns embeddings
            dimension: Dimension of the embeddings
        """
        self.embed_func = embed_func
        self._dimension = dimension
    
    async def embed_text(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings using custom function"""
        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]
        
        result = self.embed_func(texts, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        
        return np.array(result)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self._dimension


class Embeddings:
    """
    Unified interface for text embeddings.
    
    Provides a simple API for generating text embeddings using different providers.
    """
    
    def __init__(self, provider: str = "openai", **kwargs):
        """
        Initialize embeddings with specified provider.
        
        Args:
            provider: Provider name ("openai", "sentence-transformers", "custom")
            **kwargs: Provider-specific arguments
        """
        self.provider_name = provider
        self.provider = self._create_provider(provider, **kwargs)
        self.dimension = self.provider.get_dimension()
    
    def _create_provider(self, provider: str, **kwargs) -> EmbeddingProvider:
        """Create a provider instance"""
        if provider == "openai":
            api_key = kwargs.get("api_key")
            model = kwargs.get("model", "text-embedding-ada-002")
            base_url = kwargs.get("base_url")
            if not api_key:
                raise ValueError("OpenAI provider requires 'api_key' parameter")
            return OpenAIEmbeddingProvider(api_key, model, base_url)
        
        elif provider == "sentence-transformers":
            model_name = kwargs.get("model_name", "all-MiniLM-L6-v2")
            return SentenceTransformerProvider(model_name)
        
        elif provider == "custom":
            embed_func = kwargs.get("embed_func")
            dimension = kwargs.get("dimension")
            if not embed_func:
                raise ValueError("Custom provider requires 'embed_func' parameter")
            if dimension is None:
                raise ValueError("Custom provider requires 'dimension' parameter")
            return CustomEmbeddingProvider(embed_func, dimension)
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def embed(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Text or list of texts to embed
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Numpy array of embeddings
        """
        return await self.provider.embed_text(texts, **kwargs)
    
    async def embed_query(self, query: str, **kwargs) -> np.ndarray:
        """
        Generate embedding for a search query.
        
        Args:
            query: Query text
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Numpy array of embedding
        """
        return await self.provider.embed_text(query, **kwargs)
    
    async def embed_documents(self, documents: List[str], **kwargs) -> np.ndarray:
        """
        Generate embeddings for documents.
        
        Args:
            documents: List of document texts
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Numpy array of embeddings
        """
        return await self.provider.embed_text(documents, **kwargs)
    
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        return self.dimension
    
    async def similarity(self, text1: str, text2: str, **kwargs) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Cosine similarity score
        """
        embeddings = await self.embed([text1, text2], **kwargs)
        
        # Calculate cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(similarity)
    
    async def search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search documents by semantic similarity.
        
        Args:
            query: Query text
            documents: List of document texts to search
            top_k: Number of top results to return
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List of dictionaries with document, score, and index
        """
        if not documents:
            return []
        
        # Generate embeddings
        query_embedding = await self.embed_query(query, **kwargs)
        doc_embeddings = await self.embed_documents(documents, **kwargs)
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "document": documents[idx],
                "score": float(similarities[idx]),
                "index": int(idx)
            })
        
        return results


class EmbeddingCache:
    """Simple in-memory cache for embeddings"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of cached embeddings
        """
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    def get(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding"""
        if text in self.cache:
            # Update access order
            self.access_order.remove(text)
            self.access_order.append(text)
            return self.cache[text]
        return None
    
    def put(self, text: str, embedding: np.ndarray):
        """Store embedding in cache"""
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size and text not in self.cache:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        # Add or update
        if text in self.cache:
            self.access_order.remove(text)
        
        self.cache[text] = embedding
        self.access_order.append(text)
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)


class CachedEmbeddings(Embeddings):
    """Embeddings with caching support"""
    
    def __init__(self, provider: str = "openai", cache_size: int = 1000, **kwargs):
        """
        Initialize cached embeddings.
        
        Args:
            provider: Provider name
            cache_size: Maximum cache size
            **kwargs: Provider-specific arguments
        """
        super().__init__(provider, **kwargs)
        self.cache = EmbeddingCache(cache_size)
    
    async def embed(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Generate embeddings with caching"""
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False
        
        # Check cache first
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is not None:
                cached_embeddings.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            new_embeddings = await super().embed(uncached_texts, **kwargs)
            
            # Cache new embeddings
            for text, embedding in zip(uncached_texts, new_embeddings):
                self.cache.put(text, embedding)
        else:
            new_embeddings = np.array([])
        
        # Combine results
        result = np.zeros((len(texts), self.dimension))
        
        # Fill in cached embeddings
        for i, embedding in cached_embeddings:
            result[i] = embedding
        
        # Fill in new embeddings
        for i, embedding in zip(uncached_indices, new_embeddings):
            result[i] = embedding
        
        # Return single embedding if input was single text
        if single_text:
            return result[0]
        
        return result
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": self.cache.size(),
            "max_size": self.cache.max_size
        }