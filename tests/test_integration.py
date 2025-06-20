"""
Integration tests for RepoHealthAnalyzer with mocked LLM
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from LLMRepoReviewer.repo_reviewer import RepoHealthAnalyzer


class TestRepoHealthAnalyzerIntegration:
    """Integration tests with mocked LLM responses"""

    @pytest.fixture()
    def mock_full_system(self):
        """Mock all external dependencies for integration testing"""
        with patch("LLMRepoReviewer.repo_reviewer.chromadb.Client") as mock_chromadb, patch(
            "LLMRepoReviewer.repo_reviewer.HuggingFaceEmbeddings"
        ) as mock_embeddings, patch("LLMRepoReviewer.repo_reviewer.OpenAI") as mock_openai, patch(
            "LLMRepoReviewer.repo_reviewer.git.Repo"
        ) as mock_git:
            # Setup ChromaDB mocks
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_collection.add = MagicMock()
            mock_collection.query = MagicMock(
                return_value={
                    "documents": [["Test document content"]],
                    "metadatas": [[{"filename": "test.py"}]],
                }
            )
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

            # Setup OpenAI mock with realistic responses
            mock_openai_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content="This is a Python project that implements a test application.",
                        tool_calls=None,
                    )
                )
            ]
            mock_openai_instance.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_openai_instance

            # Setup git mock
            mock_repo = MagicMock()
            mock_repo.index.entries.keys.return_value = [
                ("README.md", None),
                ("main.py", None),
                ("src/utils.py", None),
                ("tests/test_main.py", None),
                ("pyproject.toml", None),
            ]
            mock_git.return_value = mock_repo

            yield {
                "chromadb": mock_client,
                "embeddings": mock_embed_instance,
                "openai": mock_openai_instance,
                "git": mock_repo,
                "collection": mock_collection,
            }

    @pytest.fixture()
    def sample_project(self):
        """Create a sample project structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a realistic project structure
            files = {
                "README.md": "# Sample Project\n\nA sample Python project for testing.",
                "requirements.txt": "requests>=2.25.0\nflask>=2.0.0",
                "main.py": "#!/usr/bin/env python3\n\ndef main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()",
                "src/__init__.py": "",
                "src/utils.py": 'def helper_function():\n    """A helper function."""\n    return \'helper\'',
                "tests/test_main.py": "import unittest\n\nclass TestMain(unittest.TestCase):\n    def test_main(self):\n        pass",
                "docs/api.md": "# API Documentation\n\nAPI endpoints and usage.",
                ".gitignore": "__pycache__/\n*.pyc\nvenv/",
                "pyproject.toml": "[build-system]\nrequires = ['setuptools']\n[project]\nname = 'sample-project'",
            }

            for file_path, content in files.items():
                full_path = os.path.join(tmpdir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            yield tmpdir

    def test_query_with_tool_calling(self, mock_full_system, sample_project):
        """Test query with tool calling enabled"""
        reviewer = RepoHealthAnalyzer()

        # Mock tool call response
        mock_tool_call = MagicMock()
        mock_tool_call.id = "tool_call_1"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "find_files"
        mock_tool_call.function.arguments = '{"path": ".", "name_pattern": "*.py"}'

        # First response with tool call
        mock_response_with_tools = MagicMock()
        mock_response_with_tools.choices = [
            MagicMock(
                message=MagicMock(
                    content="I'll search for Python files.", tool_calls=[mock_tool_call]
                )
            )
        ]

        # Second response after tool execution
        mock_final_response = MagicMock()
        mock_final_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Found Python files: main.py, src/utils.py", tool_calls=None
                )
            )
        ]

        # Configure OpenAI mock to return different responses
        mock_full_system["openai"].chat.completions.create.side_effect = [
            mock_response_with_tools,
            mock_final_response,
        ]

        # Mock subprocess for find command
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = "main.py\nsrc/utils.py"

            response = reviewer.query("Find all Python files", use_tools=True)

            assert "Found Python files" in response
            assert "main.py" in response
            assert "utils.py" in response

    def test_auto_analyze_workflow(self, mock_full_system, sample_project):
        """Test the complete auto-analyze workflow"""
        reviewer = RepoHealthAnalyzer()

        # Mock responses for different analysis questions
        mock_responses = [
            "This is a Python web application project.",
            "The project uses Python and Flask framework.",
            "Dependencies include Flask and requests.",
            "The project has a modular structure with src/ directory.",
            "Main components are main.py and utils.py.",
            "Testing is done with unittest framework.",
            "Code quality is good with proper documentation.",
            "Project has README and API documentation.",
            "No obvious security issues found.",
            "Build tools include pip and setuptools.",
            "No CI/CD configuration found.",
            "Configuration uses pyproject.toml file.",
        ]

        # Create mock responses for each question
        mock_openai_responses = []
        for response_text in mock_responses:
            mock_resp = MagicMock()
            mock_resp.choices = [
                MagicMock(message=MagicMock(content=response_text, tool_calls=None))
            ]
            mock_openai_responses.append(mock_resp)

        mock_full_system["openai"].chat.completions.create.side_effect = mock_openai_responses

        # Run auto-analysis
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            output_file = f.name

        try:
            result_file = reviewer.auto_analyze(sample_project, output_file)

            assert result_file == output_file
            assert os.path.exists(output_file)

            # Check report content
            with open(output_file) as f:
                report_content = f.read()

            assert "Repository Analysis Report" in report_content
            assert "Python web application" in report_content
            assert "Flask framework" in report_content
            assert sample_project in report_content

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_github_repo_analysis_workflow(self, mock_full_system):
        """Test GitHub repository cloning and analysis workflow"""
        reviewer = RepoHealthAnalyzer()

        # Mock git clone
        with patch.object(reviewer, "clone_github_repo") as mock_clone, patch.object(
            reviewer, "auto_analyze"
        ) as mock_analyze:
            mock_clone.return_value = "/tmp/cloned_repo"
            mock_analyze.return_value = "analysis_report.md"

            result = reviewer.analyze_github_repo("https://github.com/user/repo")

            assert result == "analysis_report.md"
            mock_clone.assert_called_once_with("https://github.com/user/repo")
            mock_analyze.assert_called_once_with(
                "/tmp/cloned_repo", "cloned_repo_analysis_report.md"
            )

    def test_error_handling_during_analysis(self, mock_full_system, sample_project):
        """Test error handling during analysis process"""
        reviewer = RepoHealthAnalyzer()

        # Mock OpenAI to raise an exception
        mock_full_system["openai"].chat.completions.create.side_effect = Exception("API Error")

        # Auto-analyze should handle the error gracefully
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            output_file = f.name

        try:
            result_file = reviewer.auto_analyze(sample_project, output_file)

            assert result_file == output_file
            assert os.path.exists(output_file)

            # Check that error is handled in report
            with open(output_file) as f:
                report_content = f.read()

            assert "Repository Analysis Report" in report_content
            # Should contain error messages for failed analyses
            assert "Error during analysis" in report_content

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_session_history_integration(self, mock_full_system, sample_project):
        """Test session history tracking during queries"""
        reviewer = RepoHealthAnalyzer()

        # Mock session collection query
        mock_full_system["collection"].query.return_value = {
            "documents": [
                [
                    '{"type": "user_query", "content": "What is this project?", "timestamp": "2023-01-01T00:00:00"}',
                    '{"type": "assistant_response", "content": "This is a Python project", "timestamp": "2023-01-01T00:00:01"}',
                ]
            ],
            "metadatas": [
                [
                    {"session_id": reviewer.current_session_id, "type": "user_query"},
                    {"session_id": reviewer.current_session_id, "type": "assistant_response"},
                ]
            ],
        }

        # Perform a query to generate history
        reviewer.query("What is this project?", use_tools=False)

        # Get session history
        history = reviewer.get_session_history()

        assert len(history) == 2
        assert history[0]["type"] == "user_query"
        assert history[0]["content"] == "What is this project?"
        assert history[1]["type"] == "assistant_response"
        assert history[1]["content"] == "This is a Python project"

    def test_caching_workflow_integration(self, mock_full_system, sample_project):
        """Test file caching during processing workflow"""
        reviewer = RepoHealthAnalyzer()

        # First processing - should process all files
        stats1 = reviewer.process_directory(sample_project)
        initial_processed = stats1["processed_files"]

        # Mock cache to return that files are cached
        def mock_check_cache(file_path):
            return True  # All files are now "cached"

        with patch.object(reviewer, "_check_file_cache", side_effect=mock_check_cache):
            # Second processing - should use cache
            stats2 = reviewer.process_directory(sample_project)

            assert stats2["cached_files"] == stats1["total_files"]
            assert stats2["processed_files"] == 0  # No new files to process


class TestCommandLineIntegration:
    """Test command-line interface integration"""

    @pytest.fixture()
    def mock_system(self):
        """Mock system for CLI testing"""
        with patch("LLMRepoReviewer.repo_reviewer.chromadb.Client"), patch(
            "LLMRepoReviewer.repo_reviewer.HuggingFaceEmbeddings"
        ), patch("LLMRepoReviewer.repo_reviewer.OpenAI"):
            yield

    def test_cli_help(self):
        """Test CLI help command works"""
        import subprocess

        result = subprocess.run(["llm-repo-reviewer", "--help"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "LLM Repo Reviewer" in result.stdout
        assert "--auto-analyze" in result.stdout
        assert "--output" in result.stdout

    def test_cli_version_info(self, mock_system):
        """Test that CLI can import and initialize without errors"""
        # This tests that all imports work correctly
        from LLMRepoReviewer.repo_reviewer import RepoHealthAnalyzer

        # Should be able to create instance without errors
        reviewer = RepoHealthAnalyzer()
        assert reviewer is not None
        assert len(reviewer.list_tools()) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
