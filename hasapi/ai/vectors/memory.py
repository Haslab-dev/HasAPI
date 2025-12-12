"""
HasAPI In-Memory Vector Store

Fast in-memory vector store implementation for small to medium datasets.
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional, Union
import numpy as np

from .base import VectorStore, VectorSearchResult, FilterExpression, DistanceMetric
from ...utils import get_logger

logger = get_logger(__name__)


class InMemoryVectorStore(VectorStore):
    """
    In-memory vector store implementation.
    
    Provides fast vector storage and search for small to medium datasets.
    Uses NumPy for efficient vector operations.
    """
    
    def __init__(self, dimension: int, distance_metric: str = DistanceMetric.COSINE):
        """
        Initialize in-memory vector store.
        
        Args:
            dimension: Dimension of vectors
            distance_metric: Distance metric to use
        """
        self.dimension = dimension
        self.distance_metric = distance_metric
        self.distance_func = DistanceMetric.get_function(distance_metric)
        
        # Storage
        self.vectors = {}  # id -> vector
        self.metadata = {}  # id -> metadata
        
        # For efficient search
        self.vector_matrix = None  # numpy matrix of all vectors
        self.id_list = []  # list of ids in same order as matrix rows
        
        self._lock = None
    
    async def _get_lock(self):
        """Get or create async lock"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
    
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
            ids: Optional list of IDs for vectors
            metadata: Optional list of metadata dictionaries
            
        Returns:
            List of IDs for added vectors
        """
        async with await self._get_lock():
            # Normalize input
            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            
            num_vectors = vectors.shape[0]
            
            # Validate dimension
            if vectors.shape[1] != self.dimension:
                raise ValueError(f"Vector dimension {vectors.shape[1]} doesn't match store dimension {self.dimension}")
            
            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(num_vectors)]
            elif len(ids) != num_vectors:
                raise ValueError(f"Number of IDs ({len(ids)}) doesn't match number of vectors ({num_vectors})")
            
            # Validate metadata
            if metadata is None:
                metadata = [{} for _ in range(num_vectors)]
            elif len(metadata) != num_vectors:
                raise ValueError(f"Number of metadata entries ({len(metadata)}) doesn't match number of vectors ({num_vectors})")
            
            # Add vectors
            added_ids = []
            for i, (vector, vector_id, meta) in enumerate(zip(vectors, ids, metadata)):
                # Check for duplicate ID
                if vector_id in self.vectors:
                    logger.warning(f"Vector ID {vector_id} already exists, overwriting")
                
                self.vectors[vector_id] = vector.copy()
                self.metadata[vector_id] = meta.copy()
                added_ids.append(vector_id)
            
            # Rebuild matrix for efficient search
            self._rebuild_matrix()
            
            return added_ids
    
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
        async with await self._get_lock():
            if not self.vectors:
                return []
            
            # Normalize query vector
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)
            
            if query_vector.shape[1] != self.dimension:
                raise ValueError(f"Query vector dimension {query_vector.shape[1]} doesn't match store dimension {self.dimension}")
            
            # Apply filters if provided
            candidate_indices = self._apply_filters(filter_expr)
            
            if not candidate_indices:
                return []
            
            # Calculate similarities
            candidate_matrix = self.vector_matrix[candidate_indices]
            
            if self.distance_metric == DistanceMetric.COSINE:
                # For cosine similarity, we can use matrix operations
                similarities = self._cosine_similarity_batch(query_vector[0], candidate_matrix)
            else:
                # For other metrics, calculate individually
                similarities = []
                for vector in candidate_matrix:
                    if self.distance_metric == DistanceMetric.EUCLIDEAN:
                        # Convert distance to similarity (lower distance = higher similarity)
                        dist = self.distance_func(query_vector[0], vector)
                        sim = 1.0 / (1.0 + dist)  # Convert to similarity
                    elif self.distance_metric == DistanceMetric.MANHATTAN:
                        # Convert distance to similarity
                        dist = self.distance_func(query_vector[0], vector)
                        sim = 1.0 / (1.0 + dist)  # Convert to similarity
                    else:  # DOT_PRODUCT
                        sim = self.distance_func(query_vector[0], vector)
                    similarities.append(sim)
                
                similarities = np.array(similarities)
            
            # Get top-k results
            if len(similarities) < top_k:
                top_k = len(similarities)
            
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                original_idx = candidate_indices[idx]
                vector_id = self.id_list[original_idx]
                score = float(similarities[idx])
                
                result = {
                    "id": vector_id,
                    "score": score,
                    "metadata": self.metadata[vector_id].copy()
                }
                results.append(result)
            
            return results
    
    async def get_by_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID"""
        async with await self._get_lock():
            if vector_id not in self.vectors:
                return None
            
            return {
                "id": vector_id,
                "vector": self.vectors[vector_id].copy(),
                "metadata": self.metadata[vector_id].copy()
            }
    
    async def delete(self, vector_ids: List[str]) -> bool:
        """Delete vectors by ID"""
        async with await self._get_lock():
            deleted_any = False
            
            for vector_id in vector_ids:
                if vector_id in self.vectors:
                    del self.vectors[vector_id]
                    del self.metadata[vector_id]
                    deleted_any = True
            
            if deleted_any:
                self._rebuild_matrix()
            
            return deleted_any
    
    async def update(
        self,
        vector_id: str,
        vector: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a vector by ID"""
        async with await self._get_lock():
            if vector_id not in self.vectors:
                return False
            
            if vector is not None:
                if vector.shape[0] != self.dimension:
                    raise ValueError(f"Vector dimension {vector.shape[0]} doesn't match store dimension {self.dimension}")
                self.vectors[vector_id] = vector.copy()
            
            if metadata is not None:
                self.metadata[vector_id] = metadata.copy()
            
            # Rebuild matrix if vector was updated
            if vector is not None:
                self._rebuild_matrix()
            
            return True
    
    async def count(self) -> int:
        """Get number of vectors in store"""
        return len(self.vectors)
    
    async def clear(self) -> bool:
        """Clear all vectors from store"""
        async with await self._get_lock():
            self.vectors.clear()
            self.metadata.clear()
            self.vector_matrix = None
            self.id_list.clear()
            return True
    
    def get_dimension(self) -> int:
        """Get dimension of vectors in store"""
        return self.dimension
    
    def _rebuild_matrix(self):
        """Rebuild the vector matrix for efficient search"""
        if not self.vectors:
            self.vector_matrix = None
            self.id_list = []
            return
        
        # Create matrix and id list in consistent order
        self.id_list = list(self.vectors.keys())
        vectors = [self.vectors[vector_id] for vector_id in self.id_list]
        self.vector_matrix = np.array(vectors)
    
    def _apply_filters(self, filter_expr: Optional[Dict[str, Any]]) -> List[int]:
        """Apply filters and return indices of matching vectors"""
        if filter_expr is None:
            return list(range(len(self.id_list)))
        
        # Simple filter implementation
        matching_indices = []
        
        for i, vector_id in enumerate(self.id_list):
            metadata = self.metadata[vector_id]
            
            if self._matches_filter(metadata, filter_expr):
                matching_indices.append(i)
        
        return matching_indices
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_expr: Dict[str, Any]) -> bool:
        """Check if metadata matches filter expression"""
        if "op" not in filter_expr:
            # Simple field equality
            field = filter_expr.get("field")
            value = filter_expr.get("value")
            return metadata.get(field) == value
        
        op = filter_expr["op"]
        
        if op == "eq":
            field = filter_expr["field"]
            value = filter_expr["value"]
            return metadata.get(field) == value
        
        elif op == "ne":
            field = filter_expr["field"]
            value = filter_expr["value"]
            return metadata.get(field) != value
        
        elif op == "in":
            field = filter_expr["field"]
            values = filter_expr["value"]
            return metadata.get(field) in values
        
        elif op == "nin":
            field = filter_expr["field"]
            values = filter_expr["value"]
            return metadata.get(field) not in values
        
        elif op == "gt":
            field = filter_expr["field"]
            value = filter_expr["value"]
            return metadata.get(field) > value
        
        elif op == "gte":
            field = filter_expr["field"]
            value = filter_expr["value"]
            return metadata.get(field) >= value
        
        elif op == "lt":
            field = filter_expr["field"]
            value = filter_expr["value"]
            return metadata.get(field) < value
        
        elif op == "lte":
            field = filter_expr["field"]
            value = filter_expr["value"]
            return metadata.get(field) <= value
        
        elif op == "contains":
            field = filter_expr["field"]
            value = filter_expr["value"]
            field_value = metadata.get(field)
            if isinstance(field_value, str):
                return value in field_value
            elif isinstance(field_value, (list, tuple)):
                return value in field_value
            return False
        
        elif op == "and":
            # All sub-filters must match
            for sub_filter in filter_expr.get("filters", []):
                if not self._matches_filter(metadata, sub_filter):
                    return False
            return True
        
        elif op == "or":
            # At least one sub-filter must match
            for sub_filter in filter_expr.get("filters", []):
                if self._matches_filter(metadata, sub_filter):
                    return True
            return False
        
        return False
    
    def _cosine_similarity_batch(self, query_vec: np.ndarray, vectors: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity for batch of vectors"""
        # Normalize vectors
        query_norm = query_vec / np.linalg.norm(query_vec)
        vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        # Calculate dot products
        similarities = np.dot(vectors_norm, query_norm)
        
        return similarities
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        async with await self._get_lock():
            return {
                "count": len(self.vectors),
                "dimension": self.dimension,
                "distance_metric": self.distance_metric,
                "memory_usage_bytes": self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        # Rough estimate
        vectors_size = len(self.vectors) * self.dimension * 4  # float32
        metadata_size = len(str(self.metadata))  # Rough estimate
        ids_size = len(self.id_list) * 36  # Average UUID string size
        
        return vectors_size + metadata_size + ids_size