import sys
import logging
from services.rerank_service import RerankService

def test_reranking():
    # setup_logging() # skip complex logging setup to keep stdout clean
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Initialize Service
    try:
        service = RerankService(model_name="ms-marco-TinyBERT-L-2-v2", enabled=True)
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        sys.exit(1)
        
    if not service.ranker:
        print("❌ Failed to initialize FlashRank ranker (service.ranker is None)")
        sys.exit(1)

    # Test Data
    query = "python programming language"
    documents = [
        {"id": "doc1", "content": "The cobra is a venomous snake found in India."}, 
        {"id": "doc2", "content": "I like to drink coffee in the morning."}, 
        {"id": "doc3", "content": "Python is a high-level, general-purpose programming language."}, 
        {"id": "doc4", "content": "Java is a class-based, object-oriented programming language."}, 
    ]
    
    print(f"\nQuery: {query}")
    print("Original Order: doc1, doc2, doc3, doc4")
    
    # Rerank
    print("\n--- Reranking ---")
    try:
        results = service.rerank(query, documents, top_n=4)
    except Exception as e:
        print(f"❌ Rerank Call Failed: {e}")
        sys.exit(1)
    
    print("\nReranked Results:")
    for res in results:
        print(f"ID: {res['id']}, Score: {res.get('rerank_score', 'N/A')}, Content: {res['content'][:50]}...")
        
    # Verification
    if not results:
        print("\n❌ FAIL: No results returned")
        sys.exit(1)
        
    top_doc = results[0]
    if top_doc['id'] == "doc3":
        print("\n✅ SUCCESS: 'doc3' (Python definition) is ranked #1")
    else:
        print(f"\n❌ FAIL: Expected 'doc3' at top, got '{top_doc['id']}'")
        sys.exit(1)

if __name__ == "__main__":
    test_reranking()
