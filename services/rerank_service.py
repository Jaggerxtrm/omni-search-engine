from typing import Any, Dict, List
from flashrank import Ranker, RerankRequest
from logger import get_logger

logger = get_logger("rerank")

class RerankService:
    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2", enabled: bool = True):
        self.enabled = enabled
        self.model_name = model_name
        self.ranker = None
        
        if enabled:
            try:
                # Initialize FlashRank with specified model
                logger.info(f"Initializing RerankService with model: {model_name}")
                self.ranker = Ranker(model_name=model_name)
            except Exception as e:
                logger.error(f"Failed to initialize FlashRank: {e}", exc_info=True)
                # Fallback to disabled if initialization fails
                self.enabled = False

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
        """
        Rerank a list of documents based on query relevance.
        
        Args:
            query: Search query
            documents: List of dicts, each must have a 'content' field.
                       The entire dict will be returned but reordered.
            top_n: Number of results to return after reranking
            
        Returns:
            Reordered list of documents (top_n)
        """
        if not self.enabled or not self.ranker:
            logger.debug("Reranking disabled or unavailable, returning original order")
            return documents[:top_n]
            
        if not documents:
            return []
            
        try:
            # Prepare FlashRank request
            # FlashRank expects list of {"id": int/str, "text": str, "meta": dict}
            passages = []
            doc_map = {} # Map ID to original doc to reconstruction
            
            for i, doc in enumerate(documents):
                # Use index as ID if no ID present, or ensure ID is string
                doc_id = str(doc.get("id", i))
                content = doc.get("content", "")
                
                passages.append({
                    "id": doc_id,
                    "text": content,
                    "meta": doc # Store original doc in meta to retrieve later easily
                })
                doc_map[doc_id] = doc
                
            rerank_request = RerankRequest(query=query, passages=passages)
            results = self.ranker.rerank(rerank_request)
            
            # Reconstruct sorted results
            reranked_docs = []
            for res in results:
                # res is dict with 'id', 'score', 'meta'
                doc_id = res['id']
                score = res['score']
                
                original_doc = doc_map.get(doc_id)
                if original_doc:
                    # Inject new rerank score
                    original_doc["rerank_score"] = float(score)
                    # Keep original vector similarity if present, or maybe overwrite 'similarity'?
                    # Users might want to see both. Let's keep similarity as vector_similarity
                    # and use rerank_score for final sorting.
                    reranked_docs.append(original_doc)
            
            return reranked_docs[:top_n]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}", exc_info=True)
            # Fallback
            return documents[:top_n]
