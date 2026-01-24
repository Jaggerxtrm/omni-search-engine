import sys
from unittest.mock import MagicMock, Mock

# --- START MOCKING ---
# Mock dependencies that are not installed or heavy
mock_pydantic = MagicMock()
mock_settings = MagicMock()
mock_chroma = MagicMock()

# Mock Pydantic classes to allow subclassing
class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class MockBaseSettings:
     def __init__(self, **kwargs):
        pass

mock_pydantic.BaseModel = MockBaseModel
mock_settings.BaseSettings = MockBaseSettings
mock_settings.SettingsConfigDict = MagicMock()
mock_pydantic.Field = lambda default=None, **kwargs: default

sys.modules["pydantic"] = mock_pydantic
sys.modules["pydantic_settings"] = mock_settings

# Mock Chromadb structure
mock_chromadb_config = MagicMock()
mock_chroma.config = mock_chromadb_config
sys.modules["chromadb"] = mock_chroma
sys.modules["chromadb.config"] = mock_chromadb_config

sys.modules["fastmcp"] = MagicMock()
# Mock watchdog
mock_watchdog = MagicMock()
sys.modules["watchdog"] = mock_watchdog
sys.modules["watchdog.events"] = MagicMock()
sys.modules["watchdog.observers"] = MagicMock()

# Mock openai
sys.modules["openai"] = MagicMock()

# Mock flashrank
sys.modules["flashrank"] = MagicMock()

# --- END MOCKING ---

import pytest
import asyncio
import shutil
from pathlib import Path

# Now we can import project modules. 
# They will use the mocked base classes.
from settings import SourceConfig, Settings
# We need to reload settings if it was already imported? 
# Pytest isolates usually but importlib might cache.
# Assuming clean run.

from services.indexer_service import create_indexer, VaultIndexer
from repositories.snippet_repository import create_vector_store, VectorStore
from dependencies import get_embedding_service

# Mock Embeddings
class MockEmbeddingService:
    async def embed_texts(self, texts):
        return [[0.1] * 1536 for _ in texts]
    
    async def embed_single(self, text):
        return [0.1] * 1536

# Mock Chunker (since we don't want to rely on real one or text splitting nuances)
class MockChunker:
    def chunk_markdown(self, content):
        # Return dummy chunks
        chunk = MagicMock()
        chunk.content = content
        chunk.chunk_index = 0
        chunk.token_count = 10
        chunk.header_context = "context"
        chunk.file_path = "path" # will be overwritten
        chunk.note_title = "Title"
        return [chunk]

@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires python3.7 or higher")
def test_multi_source_indexing_sync():
    asyncio.run(_test_multi_source_indexing_logic())

async def _test_multi_source_indexing_logic():
    # Setup Paths
    test_root = Path("test_env")
    if test_root.exists():
        shutil.rmtree(test_root)
    test_root.mkdir()
    
    vault_path = test_root / "vault"
    vault_path.mkdir()
    (vault_path / "note.md").write_text("# Obsidian Note\nTarget content in vault.")
    
    project_path = test_root / "project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Project Readme\nTarget content in project.")
    
    # Setup MOCKED Vector Store
    # VectorStore inits client internally. We need to control what chromadb.PersistentClient returns.
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    
    # Configure global mock_chroma to return this client
    # Note: we imported 'mock_chroma' from sys.modules earlier but we don't have reference here easily
    # unless we import it or rely on it being the same object. 
    # Better: Patch 'chromadb.PersistentClient'
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr("chromadb.PersistentClient", lambda path, settings: mock_client)
        
        # Instantiate VectorStore (it will call PersistentClient)
        store = VectorStore(persist_directory=str(test_root / "db"))
    
    # Setup Config
    sources = [
        SourceConfig(id="vault", name="Vault", path=vault_path.resolve(), type="obsidian"),
        SourceConfig(id="project", name="Project", path=project_path.resolve(), type="code")
    ]
    
    # Setup Indexer with dependencies
    indexer = VaultIndexer(
        vault_path=vault_path, # Legacy
        vector_store=store,
        embedding_service=MockEmbeddingService(),
        chunker=MockChunker()
        # chunker is usually instantiated inside, but we passed it? 
        # create_indexer does it. 
        # Let's instantiate IndexerService manually to inject MockChunker
    )
    # Inject MockChunker if constructor doesn't accept it
    indexer.chunker = MockChunker()
    
    # Mock settings calls inside indexer logic
    # We need to patch get_settings used inside index_vault
    with pytest.MonkeyPatch.context() as m:
        # Patch settings module
        import settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.sources = sources
        m.setattr(settings, "get_settings", lambda: mock_settings_obj)
        
        # Run Indexing
        result = await indexer.index_vault(force=True)
        
        # Verify call to vector_store.add_chunks for Vault file
        # We expect add_chunks called twice (once for note.md, once for README.md)
        assert mock_collection.add.call_count == 2
        
        # Inspect calls
        calls = mock_collection.add.call_args_list
        
        found_vault = False
        found_project = False
        
        for call in calls:
            # Chromadb add args: ids, embeddings, metadatas, documents
            # kwargs look like: ids=[...], metadatas=[...], ...
            kwargs = call.kwargs
            if not kwargs:
                 # positional? add(ids, embeddings, metadatas, documents)
                 # VectorStore.add_chunks calls collection.add(embeddings=..., documents=..., metadatas=..., ids=...)
                 kwargs = call[1] # kwargs dict
            
            ids = kwargs.get("ids", [])
            metadatas = kwargs.get("metadatas", [])
            
            if ids and f"vault::note.md::0" in ids[0]:
                 found_vault = True
                 assert metadatas[0]["source"] == "vault"
                 
            if ids and f"project::README.md::0" in ids[0]:
                 found_project = True
                 assert metadatas[0]["source"] == "project"
        
        assert found_vault, "Vault file was not indexed with correct ID schema"
        assert found_project, "Project file was not indexed with correct ID schema"
        
        print("\nMulti-source indexing logic verified (ID formatting and Metadata correct)!")
    
    # Cleanup
    if test_root.exists():
        shutil.rmtree(test_root)

if __name__ == "__main__":
    asyncio.run(test_multi_source_indexing())
