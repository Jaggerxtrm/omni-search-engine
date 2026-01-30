
import inspect
from repositories.snippet_repository import VectorStore
import os
import shutil

def verify():
    print("🔍 Validating VectorStore signatures...")
    # Initialize store in a temp dir to avoid touching production DB
    tmp_db = "temp_verify_db"
    if os.path.exists(tmp_db):
        shutil.rmtree(tmp_db)
    
    try:
        vs = VectorStore(tmp_db)

        # 1. Verify get_all_file_paths
        sig_get = inspect.signature(vs.get_all_file_paths)
        if "source_id" in sig_get.parameters:
            print("✅ get_all_file_paths: OK (accepts source_id)")
        else:
            print("❌ get_all_file_paths: FAILED (missing source_id)")

        # 2. Verify check_content_hash
        sig_check = inspect.signature(vs.check_content_hash)
        if "source_id" in sig_check.parameters:
            print("✅ check_content_hash: OK (accepts source_id)")
        else:
            print("❌ check_content_hash: FAILED (missing source_id)")
            
    finally:
        if os.path.exists(tmp_db):
            shutil.rmtree(tmp_db)

if __name__ == "__main__":
    verify()
