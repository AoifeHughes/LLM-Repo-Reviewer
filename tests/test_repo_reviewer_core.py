"""
Unit tests for RepoHealthAnalyzer core functionality (without LLM)
"""

import json
import os
import tempfile
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from LLMRepoReviewer.repo_reviewer import RepoHealthAnalyzer
from LLMRepoReviewer.tools.base import BaseTool


class TestRepoHealthAnalyzerCore:
    """Test RepoHealthAnalyzer core functionality without LLM dependencies"""

    @pytest.fixture()
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch("LLMRepoReviewer.repo_reviewer.chromadb.Client") as mock_chromadb, patch(
            "LLMRepoReviewer.repo_reviewer.HuggingFaceEmbeddings"
        ) as mock_embeddings, patch("LLMRepoReviewer.repo_reviewer.OpenAI") as mock_openai:
            # Setup ChromaDB mocks
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.add = MagicMock()
            mock_collection.query = MagicMock(return_value={"documents": [[]], "metadatas": [[]]})
            mock_collection.get = MagicMock(return_value={"documents": []})
            mock_collection.delete = MagicMock()

            mock_client.create_collection.return_value = mock_collection
            mock_client.get_collection.return_value = mock_collection
            mock_chromadb.return_value = mock_client

            # Setup embeddings mock
            mock_embed_instance = MagicMock()
            mock_embed_instance.embed_documents.return_value = [[0.1] * 384]
            mock_embed_instance.embed_query.return_value = [0.1] * 384
            mock_embeddings.return_value = mock_embed_instance

            # Setup OpenAI mock
            mock_openai_instance = MagicMock()
            mock_openai.return_value = mock_openai_instance

            yield {
                "chromadb": mock_client,
                "embeddings": mock_embed_instance,
                "openai": mock_openai_instance,
                "collection": mock_collection,
            }

    @pytest.fixture()
    def temp_directory(self):
        """Create a temporary directory with test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = {
                "test.py": "def hello():\n    return 'Hello, World!'",
                "README.md": "# Test Project\n\nThis is a test project.",
                "config.json": '{"name": "test", "version": "1.0"}',
                "src/module.py": "class TestClass:\n    pass",
                "docs/guide.txt": "User guide for the test project",
            }

            for file_path, content in test_files.items():
                full_path = os.path.join(tmpdir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            yield tmpdir

    def test_initialization(self, mock_dependencies):
        """Test RepoHealthAnalyzer initialization"""
        reviewer = RepoHealthAnalyzer()

        assert reviewer.current_session_id is not None
        assert reviewer.current_session_id.startswith("session_")
        assert len(reviewer.tools) >= 3  # Should have the default tools
        assert reviewer.tool_registry is not None

    def test_tool_management(self, mock_dependencies):
        """Test tool registration and management"""
        reviewer = RepoHealthAnalyzer()

        # Test initial tools
        initial_tools = reviewer.list_tools()
        assert "find_files" in initial_tools
        assert "grep_content" in initial_tools
        assert "get_file_info" in initial_tools

        # Create a custom tool
        class TestTool(BaseTool):
            @property
            def name(self) -> str:
                return "test_tool"

            @property
            def description(self) -> str:
                return "Test tool"

            @property
            def parameters(self) -> dict:
                return {"type": "object", "properties": {}}

            def execute(self, **kwargs) -> str:
                return "test result"

        # Register custom tool
        test_tool = TestTool()
        reviewer.register_tool(test_tool)

        updated_tools = reviewer.list_tools()
        assert "test_tool" in updated_tools
        assert len(updated_tools) == len(initial_tools) + 1

        # Unregister tool
        reviewer.unregister_tool("test_tool")
        final_tools = reviewer.list_tools()
        assert "test_tool" not in final_tools
        assert len(final_tools) == len(initial_tools)

    def test_file_hash_calculation(self, mock_dependencies, temp_directory):
        """Test file hash calculation"""
        reviewer = RepoHealthAnalyzer()

        test_file = os.path.join(temp_directory, "test.py")

        # Calculate hash twice
        hash1 = reviewer._get_file_hash(test_file)
        hash2 = reviewer._get_file_hash(test_file)

        assert hash1 is not None
        assert hash1 == hash2  # Same file should have same hash
        assert len(hash1) == 64  # SHA256 hash length
        assert isinstance(hash1, str)

    def test_file_hash_nonexistent_file(self, mock_dependencies):
        """Test file hash calculation for nonexistent file"""
        reviewer = RepoHealthAnalyzer()

        hash_result = reviewer._get_file_hash("/nonexistent/file.txt")
        assert hash_result is None

    def test_text_extraction(self, mock_dependencies, temp_directory):
        """Test text extraction from various file types"""
        reviewer = RepoHealthAnalyzer()

        # Test Python file
        py_file = os.path.join(temp_directory, "test.py")
        text = reviewer._extract_text_from_file(py_file)
        assert "def hello():" in text
        assert "Hello, World!" in text

        # Test Markdown file
        md_file = os.path.join(temp_directory, "README.md")
        text = reviewer._extract_text_from_file(md_file)
        assert "# Test Project" in text
        assert "test project" in text

        # Test JSON file
        json_file = os.path.join(temp_directory, "config.json")
        text = reviewer._extract_text_from_file(json_file)
        assert "test" in text
        assert "1.0" in text

        # Test unsupported file type
        unsupported_file = os.path.join(temp_directory, "test.bin")
        with open(unsupported_file, "wb") as f:
            f.write(b"\x00\x01\x02")

        text = reviewer._extract_text_from_file(unsupported_file)
        assert text is None

    def test_file_matches_pattern(self, mock_dependencies, temp_directory):
        """Test file pattern matching"""
        reviewer = RepoHealthAnalyzer()

        test_file = os.path.join(temp_directory, "test.py")

        with patch("subprocess.run") as mock_run:
            # Test successful match
            mock_run.return_value.returncode = 0
            result = reviewer._file_matches_pattern(test_file, "hello")
            assert result is True

            # Test no match
            mock_run.return_value.returncode = 1
            result = reviewer._file_matches_pattern(test_file, "nonexistent")
            assert result is False

            # Test error case
            mock_run.side_effect = Exception("Command failed")
            result = reviewer._file_matches_pattern(test_file, "pattern")
            assert result is False

    @patch("LLMRepoReviewer.repo_reviewer.git.Repo")
    def test_get_git_tracked_files_success(self, mock_git_repo, mock_dependencies, temp_directory):
        """Test getting git-tracked files successfully"""
        reviewer = RepoHealthAnalyzer()

        # Mock git repository
        mock_repo = MagicMock()
        mock_repo.index.entries = [("test.py", None), ("README.md", None), ("src/module.py", None)]
        mock_git_repo.return_value = mock_repo

        tracked_files = reviewer._get_git_tracked_files(temp_directory)

        assert len(tracked_files) == 3
        assert any("test.py" in f for f in tracked_files)
        assert any("README.md" in f for f in tracked_files)
        assert any("module.py" in f for f in tracked_files)

    @patch("LLMRepoReviewer.repo_reviewer.git.Repo")
    def test_get_git_tracked_files_not_git_repo(
        self, mock_git_repo, mock_dependencies, temp_directory
    ):
        """Test fallback when directory is not a git repository"""
        reviewer = RepoHealthAnalyzer()

        # Mock git repository initialization failure - use the correct exception type
        import git

        mock_git_repo.side_effect = git.exc.InvalidGitRepositoryError("Not a git repository")

        tracked_files = reviewer._get_git_tracked_files(temp_directory)

        # Should fall back to all files
        assert len(tracked_files) > 0
        assert any("test.py" in f for f in tracked_files)
        assert any("README.md" in f for f in tracked_files)

    def test_gather_project_stats(self, mock_dependencies, temp_directory):
        """Test project statistics gathering"""
        reviewer = RepoHealthAnalyzer()

        with patch.object(reviewer, "_get_git_tracked_files") as mock_git_files:
            # Mock git tracked files
            mock_git_files.return_value = [
                os.path.join(temp_directory, "test.py"),
                os.path.join(temp_directory, "README.md"),
                os.path.join(temp_directory, "config.json"),
                os.path.join(temp_directory, "src/module.py"),
            ]

            stats = reviewer._gather_project_stats(temp_directory)

            assert stats["total_files"] == 4
            assert stats["languages"]["Python"] == 2  # test.py and module.py
            assert stats["file_types"][".py"] == 2
            assert stats["file_types"][".md"] == 1
            assert stats["file_types"][".json"] == 1
            assert stats["loc_estimate"] > 0  # Should have counted some lines

    def test_gather_project_stats_with_dependencies(self, mock_dependencies, temp_directory):
        """Test project statistics gathering with dependency files"""
        reviewer = RepoHealthAnalyzer()

        # Create dependency files
        with open(os.path.join(temp_directory, "requirements.txt"), "w") as f:
            f.write("requests\nflask")
        with open(os.path.join(temp_directory, "package.json"), "w") as f:
            f.write('{"dependencies": {"react": "^17.0.0"}}')

        with patch.object(reviewer, "_get_git_tracked_files") as mock_git_files:
            mock_git_files.return_value = [
                os.path.join(temp_directory, "test.py"),
                os.path.join(temp_directory, "requirements.txt"),
                os.path.join(temp_directory, "package.json"),
            ]

            stats = reviewer._gather_project_stats(temp_directory)

            assert "requirements.txt" in stats["dependencies"]
            assert "package.json" in stats["dependencies"]

    def test_create_report(self, mock_dependencies):
        """Test report creation"""
        reviewer = RepoHealthAnalyzer()

        # Mock data
        directory_path = "/test/path"
        stats = {"total_files": 10}
        project_stats = {
            "languages": Counter({"Python": 5, "JavaScript": 3}),
            "file_types": Counter({".py": 5, ".js": 3, ".md": 2}),
            "loc_estimate": 1000,
            "dependencies": ["requirements.txt"],
        }
        analysis_results = {
            "purpose": "This is a test project",
            "languages": "Python, JavaScript",
            "dependencies": "Flask, React",
            "architecture": "Modular design",
            "components": "Main module, API module",
            "testing": "pytest framework",
            "code_quality": "Good quality with some TODOs",
            "documentation": "Well documented",
            "build_tools": "pip, npm",
            "ci_cd": "GitHub Actions",
            "config": "Environment variables",
            "security": "No obvious issues",
        }

        report = reviewer._create_report(directory_path, stats, project_stats, analysis_results)

        assert "Repository Analysis Report" in report
        assert directory_path in report
        assert "10" in report  # total_files
        assert "Python (5)" in report
        assert "~1,000" in report  # loc_estimate
        assert "This is a test project" in report
        assert "pytest framework" in report

    def test_session_management(self, mock_dependencies):
        """Test session management functionality"""
        reviewer = RepoHealthAnalyzer()

        # Test session creation
        original_session = reviewer.current_session_id
        assert original_session.startswith("session_")

        # Test starting new session (add small delay to ensure different timestamp)
        import time

        time.sleep(1)
        reviewer._start_new_session()
        new_session = reviewer.current_session_id
        assert new_session != original_session
        assert new_session.startswith("session_")

        # Test session logging
        test_entry = {"type": "test", "content": "test message"}
        reviewer._log_to_session(test_entry)

        # Verify the collection add method was called
        mock_dependencies["collection"].add.assert_called()

    def test_cache_operations(self, mock_dependencies, temp_directory):
        """Test file caching operations"""
        reviewer = RepoHealthAnalyzer()

        test_file = os.path.join(temp_directory, "test.py")
        file_hash = reviewer._get_file_hash(test_file)

        # Test cache update
        chunk_ids = ["chunk1", "chunk2"]
        metadata = {"test": "metadata"}

        reviewer._update_file_cache(test_file, file_hash, chunk_ids, metadata)

        # Verify cache collection operations
        mock_dependencies["collection"].add.assert_called()

        # Test cache check with mock
        with patch.object(reviewer.cache_collection, "get") as mock_get:
            mock_get.return_value = {"documents": [json.dumps({"file_hash": file_hash})]}

            is_cached = reviewer._check_file_cache(test_file)
            assert is_cached is True

            # Test with different hash
            mock_get.return_value = {"documents": [json.dumps({"file_hash": "different_hash"})]}

            is_cached = reviewer._check_file_cache(test_file)
            assert is_cached is False


class TestRepoHealthAnalyzerErrorHandling:
    """Test error handling in RepoHealthAnalyzer"""

    @pytest.fixture()
    def mock_dependencies(self):
        """Mock dependencies for error testing"""
        with patch("LLMRepoReviewer.repo_reviewer.chromadb.Client") as mock_chromadb, patch(
            "LLMRepoReviewer.repo_reviewer.HuggingFaceEmbeddings"
        ) as mock_embeddings, patch("LLMRepoReviewer.repo_reviewer.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_client.create_collection.return_value = mock_collection
            mock_client.get_collection.return_value = mock_collection
            mock_chromadb.return_value = mock_client

            mock_embeddings.return_value = MagicMock()
            mock_openai.return_value = MagicMock()

            yield mock_client

    def test_process_directory_not_found(self, mock_dependencies):
        """Test processing non-existent directory"""
        reviewer = RepoHealthAnalyzer()

        with pytest.raises(ValueError, match="Directory not found"):
            reviewer.process_directory("/nonexistent/directory")

    def test_extract_text_with_encoding_errors(self, mock_dependencies):
        """Test text extraction with encoding errors"""
        reviewer = RepoHealthAnalyzer()

        # Create a file with binary content
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".py") as f:
            f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8
            bad_file = f.name

        try:
            text = reviewer._extract_text_from_file(bad_file)
            # Should handle the error gracefully
            assert text is None
        finally:
            os.unlink(bad_file)

    def test_tool_execution_error_handling(self, mock_dependencies):
        """Test tool execution error handling"""
        reviewer = RepoHealthAnalyzer()

        # Test unknown tool
        result = reviewer._execute_tool("unknown_tool", {})
        assert "Unknown tool" in result

        # Test with tool registry error handling
        with patch.object(reviewer.tool_registry, "execute_tool") as mock_execute:
            mock_execute.return_value = "Error: Tool failed"

            result = reviewer._execute_tool("find_files", {"path": "."})
            assert "Error: Tool failed" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
