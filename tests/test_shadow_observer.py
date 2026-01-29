import unittest
from unittest.mock import MagicMock, patch
import sys
import time
from pathlib import Path

# Mock dependencies that are hard to install or irrelevant for this test
sys.modules["chromadb"] = MagicMock()
sys.modules["fastmcp"] = MagicMock()
sys.modules["repositories.snippet_repository"] = MagicMock()
sys.modules["services.indexer_service"] = MagicMock()
sys.modules["tiktoken"] = MagicMock()
sys.modules["yaml"] = MagicMock()
sys.modules["bs4"] = MagicMock()

# Now import the module under test
from watcher import ShadowObserver

class TestShadowObserver(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("/tmp/test_shadow")
        self.tmp_dir.mkdir(exist_ok=True)
        self.observer = ShadowObserver(self.tmp_dir)
        self.observer.ai_debounce_seconds = 0.1 # Fast test

    def tearDown(self):
        # Cleanup
        if (self.tmp_dir / "dev-log.md").exists():
            (self.tmp_dir / "dev-log.md").unlink()
        self.tmp_dir.rmdir()

    def test_log_creation(self):
        """Test that dev-log.md is created with header."""
        self.assertTrue((self.tmp_dir / "dev-log.md").exists())
        content = (self.tmp_dir / "dev-log.md").read_text()
        self.assertIn("# Developer Log", content)

    def test_session_logic(self):
        """Test session creation and timeouts."""
        file_path = self.tmp_dir / "notes/test.md"
        
        # 1. New Session
        self.observer.on_file_processed(file_path, 5, "vault")
        
        log_content = (self.tmp_dir / "dev-log.md").read_text()
        self.assertIn('type="session_start"', log_content)
        self.assertIn('[[notes/test.md]]', log_content)
        
        # Get session ID
        session_id_1 = self.observer.active_sessions[str(file_path)]['session_id']
        
        # 2. Modification (same session)
        self.observer.on_file_processed(file_path, 2, "vault")
        log_content = (self.tmp_dir / "dev-log.md").read_text()
        self.assertIn('type="modification"', log_content)
        
        # Verify session ID reused
        session_id_2 = self.observer.active_sessions[str(file_path)]['session_id']
        self.assertEqual(session_id_1, session_id_2)

    @patch("subprocess.run")
    def test_ai_trigger(self, mock_run):
        """Test that AI summary is triggered after debounce."""
        file_path = self.tmp_dir / "notes/test_ai.md"
        
        # Mock git diff output
        mock_run.return_value.stdout = "diff --git ...\\n+ new line"
        mock_run.return_value.returncode = 0
        
        # Trigger event
        self.observer.on_file_processed(file_path, 1, "vault")
        
        # Wait for debounce
        time.sleep(0.2)
        self.observer.tick()
        
        # Verify calls
        # Call 1: git diff
        # Call 2: qwen
        self.assertTrue(mock_run.call_count >= 2)
        
        # Check qwen call
        qwen_call = mock_run.call_args_list[-1]
        args = qwen_call[0][0]
        self.assertEqual(args[0], "qwen")
        self.assertIn("Analyze the following git diff", args[1])

if __name__ == "__main__":
    unittest.main()
