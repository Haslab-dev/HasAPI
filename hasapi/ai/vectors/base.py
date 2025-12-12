"""
HasAPI Vector Store Base Classes

Abstract base classes for vector storage implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np

from ...utils import get_logger

logger = get_logger(__name__)


class VectorStore(ABC):
    """
    Abstract base class for vector stores.
    
    Provides a common interface for storing and searching vectors.
    """
    
    @abstractmethod
    async def add_vectors(
        self,
        vectors: np.ndarray,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Add vectors to the store.
        
        Args:
            vectors: Numpy array of vectors to add
            ids: Optional list of IDs for the vectors
            metadata: Optional list of metadata dictionaries
            
        Returns:
            List of IDs for the added vectors
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filter_expr: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filter_expr: Optional filter expression
            
        Returns:
            List of search results with scores and metadata
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a vector by ID.
        
        Args:
            vector_id: ID of the vector to retrieve
            
        Returns:
            Vector data or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, vector_ids: List[str]) -> bool:
        """
        Delete vectors by ID.
        
        Args:
            vector_ids: List of IDs to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def update(
        self,
        vector_id: str,
        vector: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a vector by ID.
        
        Args:
            vector_id: ID of the vector to update
            vector: New vector (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """
        Get the number of vectors in the store.
        
        Returns:
            Number of vectors
        """
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all vectors from the store.
        
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimension of vectors in the store.
        
        Returns:
            Vector dimension
        """
        pass


class VectorSearchResult:
    """Container for vector search results"""
    
    def __init__(
        self,
        id: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None,
        vector: Optional[np.ndarray] = None
    ):
        self.id = id
        self.score = score
        self.metadata = metadata or {}
        self.vector = vector
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "score": self.score,
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"VectorSearchResult(id={self.id}, score={self.score:.4f})"


class VectorDocument:
    """Container for vector documents"""
    
    def __init__(
        self,
        text: str,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None
    ):
        self.id = id
        self.text = text
        self.embedding = embedding
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"VectorDocument(id={self.id}, text={self.text[:50]}...)"


class FilterExpression:
    """Builder for filter expressions"""
    
    def __init__(self):
        self.filters = []
    
    def equals(self, field: str, value: Any) -> "FilterExpression":
        """Add equals filter"""
        self.filters.append({"field": field, "op": "eq", "value": value})
        return self
    
    def not_equals(self, field: str, value: Any) -> "FilterExpression":
        """Add not equals filter"""
        self.filters.append({"field": field, "op": "ne", "value": value})
        return self
    
    def in_list(self, field: str, values: List[Any]) -> "FilterExpression":
        """Add in list filter"""
        self.filters.append({"field": field, "op": "in", "value": values})
        return self
    
    def not_in_list(self, field: str, values: List[Any]) -> "FilterExpression":
        """Add not in list filter"""
        self.filters.append({"field": field, "op": "nin", "value": values})
        return self
    
    def greater_than(self, field: str, value: Any) -> "FilterExpression":
        """Add greater than filter"""
        self.filters.append({"field": field, "op": "gt", "value": value})
        return self
    
    def greater_than_or_equal(self, field: str, value: Any) -> "FilterExpression":
        """Add greater than or equal filter"""
        self.filters.append({"field": field, "op": "gte", "value": value})
        return self
    
    def less_than(self, field: str, value: Any) -> "FilterExpression":
        """Add less than filter"""
        self.filters.append({"field": field, "op": "lt", "value": value})
        return self
    
    def less_than_or_equal(self, field: str, value: Any) -> "FilterExpression":
        """Add less than or equal filter"""
        self.filters.append({"field": field, "op": "lte", "value": value})
        return self
    
    def contains(self, field: str, value: str) -> "FilterExpression":
        """Add contains filter"""
        self.filters.append({"field": field, "op": "contains", "value": value})
        return self
    
    def and_(self, *filters: "FilterExpression") -> "FilterExpression":
        """Add AND filter"""
        and_filters = [f.to_dict() for f in filters]
        self.filters.append({"op": "and", "filters": and_filters})
        return self
    
    def or_(self, *filters: "FilterExpression") -> "FilterExpression":
        """Add OR filter"""
        or_filters = [f.to_dict() for f in filters]
        self.filters.append({"op": "or", "filters": or_filters})
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        if len(self.filters) == 1:
            return self.filters[0]
        elif len(self.filters) > 1:
            return {"op": "and", "filters": self.filters}
        else:
            return {}


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def euclidean_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Euclidean distance
    """
    return np.linalg.norm(vec1 - vec2)


def manhattan_distance(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate Manhattan distance between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Manhattan distance
    """
    return np.sum(np.abs(vec1 - vec2))


def dot_product(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate dot product between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Dot product
    """
    return np.dot(vec1, vec2)


class DistanceMetric:
    """Enum for distance metrics"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    MANHATTAN = "manhattan"
    DOT_PRODUCT = "dot_product"
    
    @staticmethod
    def get_function(metric: str):
        """Get distance function for metric"""
        functions = {
            DistanceMetric.COSINE: cosine_similarity,
            DistanceMetric.EUCLIDEAN: euclidean_distance,
            DistanceMetric.MANHATTAN: manhattan_distance,
            DistanceMetric.DOT_PRODUCT: dot_product
        }
        
        if metric not in functions:
            raise ValueError(f"Unknown distance metric: {metric}")
        
        return functions[metric]