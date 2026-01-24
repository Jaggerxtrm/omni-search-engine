import sys
from services.rerank_service import RerankService

def test_serialization():
    # logging.basicConfig(level=logging.ERROR)
    
    # Initialize Service
    try:
        service = RerankService(model_name="ms-marco-TinyBERT-L-2-v2", enabled=True)
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        sys.exit(1)

    # Test Data
    query = "python"
    documents = [
        {"id": "doc3", "content": "Python is a programming language."}, 
        {"id": "doc1", "content": "The cobra is a snake."}, 
    ]
    
    # Rerank
    results = service.rerank(query, documents, top_n=2)
    
    # Check types
    passed = True
    for res in results:
        score = res.get("rerank_score")
        print(f"ID: {res['id']}, Score: {score}, Type: {type(score)}")
        
        if not isinstance(score, float):
            print(f"❌ FAIL: Score for {res['id']} is {type(score)}, expected float")
            passed = False
        else:
             print(f"✅ SUCCESS: Score for {res['id']} is correct type (float)")
             
    if passed:
        print("\n✅ ALL CHECKS PASSED: Serialization safe.")
    else:
        print("\n❌ CHECKS FAILED: Serialization unsafe.")
        sys.exit(1)

if __name__ == "__main__":
    test_serialization()
