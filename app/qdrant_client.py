from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, CreateCollection, PointStruct
from qdrant_client.http import models
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class VibeQdrantClient:
    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.api_key = os.getenv("QDRANT_API_KEY")
        
        self.client = QdrantClient(
            host=self.host,
            port=self.port,
            api_key=self.api_key,
            timeout=30.0
        )
        
        # Collection configuration
        self.collections = {
            "task_embeddings": {
                "vector_size": 384,  # sentence-transformers/all-MiniLM-L6-v2
                "distance": Distance.COSINE,
                "description": "Task content embeddings for semantic search"
            },
            "task_titles": {
                "vector_size": 384,
                "distance": Distance.COSINE,
                "description": "Task title embeddings for quick title matching"
            },
            "project_context": {
                "vector_size": 384,
                "distance": Distance.COSINE,
                "description": "Project-level context embeddings"
            }
        }
    
    def create_collections(self) -> bool:
        """Create all required Qdrant collections"""
        try:
            for collection_name, config in self.collections.items():
                if not self.client.collection_exists(collection_name):
                    logger.info(f"Creating collection: {collection_name}")
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=config["vector_size"],
                            distance=config["distance"]
                        )
                    )
                    logger.info(f"Collection {collection_name} created successfully")
                else:
                    logger.info(f"Collection {collection_name} already exists")
            
            return True
        except Exception as e:
            logger.error(f"Error creating collections: {str(e)}")
            return False
    
    def delete_collections(self) -> bool:
        """Delete all collections (for testing/reset)"""
        try:
            for collection_name in self.collections.keys():
                if self.client.collection_exists(collection_name):
                    self.client.delete_collection(collection_name)
                    logger.info(f"Collection {collection_name} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting collections: {str(e)}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about all collections"""
        info = {}
        try:
            for collection_name in self.collections.keys():
                if self.client.collection_exists(collection_name):
                    collection_info = self.client.get_collection(collection_name)
                    info[collection_name] = {
                        "status": collection_info.status,
                        "points_count": collection_info.points_count,
                        "vectors_count": collection_info.vectors_count,
                        "config": collection_info.config.dict()
                    }
                else:
                    info[collection_name] = {"status": "not_found"}
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            info["error"] = str(e)
        
        return info
    
    def upsert_points(self, collection_name: str, points: List[PointStruct]) -> bool:
        """Upsert points to a collection"""
        try:
            if not self.client.collection_exists(collection_name):
                logger.error(f"Collection {collection_name} does not exist")
                return False
            
            operation_info = self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} points to {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error upserting points to {collection_name}: {str(e)}")
            return False
    
    def search_similar(
        self, 
        collection_name: str, 
        query_vector: List[float], 
        limit: int = 10,
        score_threshold: float = 0.7,
        filter_conditions: Dict = None
    ) -> List[Dict]:
        """Search for similar vectors in a collection"""
        try:
            if not self.client.collection_exists(collection_name):
                logger.error(f"Collection {collection_name} does not exist")
                return []
            
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=models.Filter(**filter_conditions) if filter_conditions else None
            )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in search_result
            ]
        except Exception as e:
            logger.error(f"Error searching in {collection_name}: {str(e)}")
            return []
    
    def delete_points(self, collection_name: str, point_ids: List[str]) -> bool:
        """Delete specific points from a collection"""
        try:
            if not self.client.collection_exists(collection_name):
                logger.error(f"Collection {collection_name} does not exist")
                return False
            
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=point_ids)
            )
            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting points from {collection_name}: {str(e)}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of Qdrant connection"""
        try:
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "collections_count": len(collections.collections),
                "collections": [col.name for col in collections.collections]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Global instance
qdrant_client = VibeQdrantClient()