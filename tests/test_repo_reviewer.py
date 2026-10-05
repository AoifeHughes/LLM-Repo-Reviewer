"""
Legacy tests for RepoReviewer - kept for backwards compatibility
Most functionality is now tested in test_repo_reviewer_core.py and test_integration.py
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from LLMRepoReviewer.repo_reviewer import RepoReviewer


@pytest.fixture
def temp_directory():
    """Create a temporary directory with test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_files = {
            "test.py": "def hello():\n    return 'Hello, World!'",
            "README.md": "# Test Project\n\nThis is a test project.",
            "src/module.py": "class TestClass:\n    pass",
            "docs/guide.txt": "User guide for the test project",
        }

        for file_path, content in test_files.items():
            full_path = os.path.join(tmpdir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        yield tmpdir


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response", tool_calls=None))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client"""
    with patch("chromadb.Client") as mock:
        mock_client = MagicMock()
        mock_collection = MagicMock()

        # Setup collection methods
        mock_collection.add = MagicMock()
        mock_collection.query = MagicMock(
            return_value={
                "documents": [["Test document"]],
                "metadatas": [{"filename": "test.py"}],
            }
        )
        mock_collection.get = MagicMock(return_value={"documents": []})
        mock_collection.delete = MagicMock()

        # Setup client to return collections
        mock_client.create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection

        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_embeddings():
    """Mock HuggingFace embeddings"""
    with patch("LLMRepoReviewer.repo_reviewer.HuggingFaceEmbeddings") as mock:
        mock_embeddings = MagicMock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 384]  # Mock embeddings
        mock_embeddings.embed_query.return_value = [0.1] * 384
        mock.return_value = mock_embeddings
        yield mock_embeddings


class TestRepoReviewer:
    """Test cases for RepoReviewer"""

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_initialization(self):
        """Test repo reviewer initialization"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            assert reviewer.current_session_id is not None
            assert reviewer.current_session_id.startswith("session_")
            assert (
                len(reviewer.tool_registry.get_openai_functions()) == 3
            )  # find_files, grep_content, get_file_info

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_file_hash_calculation(self, temp_directory):
        """Test file hash calculation"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            test_file = os.path.join(temp_directory, "test.py")
            hash1 = reviewer._get_file_hash(test_file)
            hash2 = reviewer._get_file_hash(test_file)

            assert hash1 is not None
            assert hash1 == hash2  # Same file should have same hash
            assert len(hash1) == 64  # SHA256 hash length

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_text_extraction(self, temp_directory):
        """Test text extraction from files"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            # Test Python file
            py_file = os.path.join(temp_directory, "test.py")
            text = reviewer._extract_text_from_file(py_file)
            assert "def hello():" in text

            # Test Markdown file
            md_file = os.path.join(temp_directory, "README.md")
            text = reviewer._extract_text_from_file(md_file)
            assert "# Test Project" in text

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_process_directory(self, temp_directory):
        """Test directory processing"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            stats = reviewer.process_directory(temp_directory)

            assert stats["total_files"] == 4
            assert stats["session_id"] == reviewer.current_session_id
            assert "processed_files" in stats
            assert "cached_files" in stats

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_file_caching(self, temp_directory):
        """Test file caching mechanism"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            test_file = os.path.join(temp_directory, "test.py")

            # First check should return False (not cached)
            assert not reviewer._check_file_cache(test_file)

            # Update cache
            file_hash = reviewer._get_file_hash(test_file)
            reviewer._update_file_cache(
                test_file, file_hash, ["chunk1", "chunk2"], {"test": "metadata"}
            )

            # Mock the cache collection to return cached entry
            reviewer.cache_collection.get.return_value = {
                "documents": ['{"file_hash": "' + file_hash + '"}']
            }

            # Now it should be cached
            assert reviewer._check_file_cache(test_file)

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_query_without_tools(self, mock_openai_client):
        """Test querying without tool usage"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI", return_value=mock_openai_client):
            reviewer = RepoReviewer()

            response = reviewer.query("What is the purpose of this code?", use_tools=False)

            assert response == "Test response"
            mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_tool_definitions(self):
        """Test tool definitions are properly structured"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            tools = reviewer.tool_registry.get_openai_functions()
            tool_names = [tool["function"]["name"] for tool in tools]

            assert "find_files" in tool_names
            assert "grep_content" in tool_names
            assert "get_file_info" in tool_names

            # Check tool structure
            for tool in tools:
                assert tool["type"] == "function"
                assert "description" in tool["function"]
                assert "parameters" in tool["function"]

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_find_files_tool(self, temp_directory):
        """Test find_files tool execution"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "test.py\nREADME.md"

                result = reviewer.tool_registry.execute_tool(
                    "find_files", {"path": temp_directory, "name_pattern": "*.py"}
                )

                assert "Found 2 items" in result
                assert "test.py" in result

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_grep_content_tool(self, temp_directory):
        """Test grep_content tool execution"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "test.py:1:def hello():"

                result = reviewer.tool_registry.execute_tool(
                    "grep_content", {"pattern": "hello", "path": temp_directory}
                )

                assert "Found 1 matches" in result
                assert "def hello()" in result

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_get_file_info_tool(self, temp_directory):
        """Test get_file_info tool execution"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            test_file = os.path.join(temp_directory, "test.py")
            result = reviewer.tool_registry.execute_tool("get_file_info", {"file_path": test_file})

            assert test_file in result
            assert "size" in result
            assert "modified" in result
            assert "is_file" in result

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_session_history(self):
        """Test session history tracking"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            # Log some entries
            reviewer._log_to_session({"type": "test", "content": "Test entry"})

            # Mock the session collection query
            reviewer.session_collection.query.return_value = {
                "documents": [['{"type": "test", "content": "Test entry"}']],
                "metadatas": [[{"session_id": reviewer.current_session_id}]],
            }

            history = reviewer.get_session_history()

            assert len(history) > 0
            assert history[0]["type"] == "test"
            assert history[0]["content"] == "Test entry"

    @pytest.mark.usefixtures("mock_chromadb", "mock_embeddings")
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        with patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            reviewer = RepoReviewer()

            # Test with non-existent directory
            with pytest.raises(ValueError, match="Directory not found"):
                reviewer.process_directory("/non/existent/directory")

            # Test with invalid file for hash
            assert reviewer._get_file_hash("/non/existent/file.txt") is None

            # Test tool execution with error
            result = reviewer.tool_registry.execute_tool("unknown_tool", {})
            assert "Unknown tool" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
