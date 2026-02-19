import os
import shutil
from typing import Any, Dict, List, Optional
import threading
import numpy as np

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

class VectorStore:
    def __init__(self, persist_directory: str, collection_name: str = "obsidian_notes"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self._lock = threading.Lock()

    def add_chunks(self, chunks: List[Any], metadatas: List[Dict], ids: List[str], embeddings: Optional[List[List[float]]] = None):
        with self._lock:
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )

    def query(self, query_embedding: List[float], n_results: int = 5, where: Optional[Dict] = None) -> Dict[str, Any]:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

    def delete_by_file_path(self, file_path: str, source_id: str = None):
        with self._lock:
            if source_id:
                where_clause = {
                    "$and": [
                        {"file_path": file_path},
                        {"source": source_id}
                    ]
                }
            else:
                where_clause = {"file_path": file_path}
            self.collection.delete(where=where_clause)

    def get_by_file_path(self, file_path: str) -> Dict[str, Any]:
        return self.collection.get(where={"file_path": file_path}, include=["embeddings", "metadatas", "documents"])

    def get_by_parent_id(self, parent_id: str) -> Dict[str, Any]:
        """Retrieve all chunks belonging to a specific parent document."""
        return self.collection.get(
            where={"parent_id": parent_id}, 
            include=["documents", "metadatas"]
        )

    def check_content_hash(self, file_path: str, source_id: str = None) -> Optional[str]:
        if source_id:
            where_clause = {
                "$and": [
                    {"file_path": file_path},
                    {"source": source_id}
                ]
            }
        else:
            where_clause = {"file_path": file_path}

        results = self.collection.get(
            where=where_clause,
            include=["metadatas"],
            limit=1
        )
        if results["metadatas"] is not None and len(results["metadatas"]) > 0:
            return results["metadatas"][0].get("content_hash")
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_chunks": self.collection.count(),
            "total_files": len(self.get_all_file_paths()),
            "persist_directory": self.client.get_settings().persist_directory, # Access settings correctly
            "collection_name": self.collection.name
        }

    def get_all_file_paths(self, source_id: str = None) -> List[str]:
        # This is expensive, but Chroma doesn't have a distinct query yet
        # We fetch only metadatas to be lighter
        where_filter = None
        if source_id:
            where_filter = {"source": source_id}
            
        results = self.collection.get(include=["metadatas"], where=where_filter)
        if results["metadatas"] is None or len(results["metadatas"]) == 0:
            return []
        
        files = set()
        for meta in results["metadatas"]:
            if "file_path" in meta:
                files.add(meta["file_path"])
        return list(files)

    def get_vault_statistics(self) -> Dict[str, Any]:
        """
        Compute detailed vault statistics.
        This is an expensive operation as it scans all metadata.
        """
        results = self.collection.get(include=["metadatas"])
        metadatas = results["metadatas"] if results["metadatas"] is not None else []
        
        total_chunks = len(metadatas)
        files = set()
        all_tags = []
        all_links = []
        
        for meta in metadatas:
            files.add(meta.get("file_path", "unknown"))
            
            # Extract tags (stored as comma-separated string)
            tags_str = meta.get("tags", "")
            if tags_str:
                all_tags.extend([t.strip() for t in tags_str.split(",") if t.strip()])
                
            # Extract outbound links (stored as comma-separated string)
            links_str = meta.get("outbound_links", "")
            if links_str:
                # Links format: [[Target]] or [[Target|Alias]]
                # We just want to count them for now
                raw_links = [l.strip() for l in links_str.split(",") if l.strip()]
                all_links.extend(raw_links)

        # Compute aggregations
        from collections import Counter
        tag_counts = Counter(all_tags)
        
        # Parse links to get target notes
        link_targets = []
        for l in all_links:
            # Simple parsing: take content before | or #
            target = l.split("|")[0].split("#")[0].strip()
            link_targets.append(target)
            
        link_counts = Counter(link_targets)

        return {
            "total_files": len(files),
            "total_chunks": total_chunks,
            "total_links": len(all_links),
            "unique_links": len(set(link_targets)),
            "total_tags": len(all_tags),
            "unique_tags": len(set(all_tags)),
            "most_linked_notes": [{"note": k, "count": v} for k, v in link_counts.most_common(10)],
            "most_used_tags": [{"tag": k, "count": v} for k, v in tag_counts.most_common(10)]
        }

    def get_all_embeddings(self) -> Dict[str, List[List[float]]]:
        """
        Retrieve all embeddings grouped by file_path.
        Used for global analysis like duplicate detection.
        """
        results = self.collection.get(include=["embeddings", "metadatas"])
        if results["embeddings"] is None or len(results["embeddings"]) == 0:
            return {}
            
        file_embeddings = {}
        for i, meta in enumerate(results["metadatas"]):
            fpath = meta.get("file_path", "unknown")
            if fpath not in file_embeddings:
                file_embeddings[fpath] = []
            file_embeddings[fpath].append(results["embeddings"][i])
            
        return file_embeddings

    def find_duplicates(self, similarity_threshold: float) -> List[Dict[str, Any]]:
        """
        Find potentially duplicate notes based on high semantic similarity.
        Moved from server.py to centralize vector logic.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Get all embeddings grouped by file
        try:
            file_embeddings = self.get_all_embeddings()
        except Exception as e:
            logger.error(f"Error in get_all_embeddings: {e}")
            raise
        
        if len(file_embeddings) < 2:
            return []
            
        # 2. Compute average embedding per file (centroid)
        centroids = {}
        for fpath, embeds in file_embeddings.items():
            if embeds is None or len(embeds) == 0:
                continue
            try:
                arr = np.array(embeds)
                centroid = np.mean(arr, axis=0)
                norm = np.linalg.norm(centroid)
                if float(norm) > 0:
                    coords = centroid / norm
                    centroids[fpath] = coords
            except Exception as e:
                logger.error(f"Error processing embeddings for {fpath}: {e}")
                raise
                
        # 3. Pairwise comparison
        duplicates = []
        keys = list(centroids.keys())
        
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                try:
                    file_a = keys[i]
                    file_b = keys[j]
                    
                    vec_a = centroids[file_a]
                    vec_b = centroids[file_b]
                    
                    sim = np.dot(vec_a, vec_b)

                    # Handle numpy scalar robustly
                    if isinstance(sim, np.ndarray):
                        sim_val = float(sim.item())
                    else:
                        sim_val = float(sim)

                    # Ensure threshold is scalar for comparison
                    threshold_scalar = float(similarity_threshold)
                    if sim_val >= threshold_scalar:
                        duplicates.append({
                            "file_a": file_a,
                            "file_b": file_b,
                            "similarity": round(sim_val, 4)
                        })
                except Exception as e:
                    logger.error(f"Error comparing {keys[i]} and {keys[j]}: {e}")
                    raise
                    
        return sorted(duplicates, key=lambda x: x["similarity"], reverse=True)

    def reset(self):
        """Clear all data."""
        with self._lock:
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.create_collection(self.collection.name)

def create_vector_store(persist_directory: str, collection_name: str = "obsidian_notes") -> VectorStore:
    """Factory function to create a VectorStore instance."""
    return VectorStore(persist_directory=persist_directory, collection_name=collection_name)
