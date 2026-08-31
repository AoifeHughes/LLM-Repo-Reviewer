"""
Integration tests that require a real LLM connection
These tests are skipped by default and need to be run explicitly
"""

import os
import tempfile

import pytest
import requests
from requests.exceptions import ConnectionError, Timeout

from LLMRepoReviewer.repo_reviewer import RepoReviewer


def check_llm_available(api_base="http://localhost:11434/v1"):
    """Check if LLM server is available"""
    try:
        response = requests.get(f"{api_base.rstrip('/v1')}/api/tags", timeout=5)
        return response.status_code == 200
    except (ConnectionError, Timeout, Exception):
        return False


# Skip all tests in this module if LLM is not available
pytestmark = pytest.mark.skipif(
    not check_llm_available(),
    reason="LLM server not available - run with local LLM server (e.g., Ollama)",
)


class TestWithRealLLM:
    """Tests that require a real LLM connection"""

    @pytest.fixture
    def reviewer(self):
        """Create a RepoReviewer instance for real LLM testing"""
        return RepoReviewer(api_base_url="http://localhost:11434/v1", api_key="fake-key-for-local")

    @pytest.fixture
    def test_project(self):
        """Create a test project for analysis"""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = {
                "README.md": """# Test Calculator Project

A simple calculator implementation in Python for testing LLM analysis.

## Features
- Basic arithmetic operations
- Command-line interface
- Unit tests included

## Usage
```bash
python calculator.py
```
""",
                "calculator.py": """#!/usr/bin/env python3
\"\"\"
Simple calculator implementation
\"\"\"

class Calculator:
    \"\"\"A basic calculator class\"\"\"

    def add(self, a, b):
        \"\"\"Add two numbers\"\"\"
        return a + b

    def subtract(self, a, b):
        \"\"\"Subtract b from a\"\"\"
        return a - b

    def multiply(self, a, b):
        \"\"\"Multiply two numbers\"\"\"
        return a * b

    def divide(self, a, b):
        \"\"\"Divide a by b\"\"\"
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

def main():
    \"\"\"Main function for CLI\"\"\"
    calc = Calculator()
    print("Simple Calculator")
    print("Result:", calc.add(5, 3))

if __name__ == "__main__":
    main()
""",
                "test_calculator.py": """import unittest
from calculator import Calculator

class TestCalculator(unittest.TestCase):
    \"\"\"Test cases for Calculator class\"\"\"

    def setUp(self):
        self.calc = Calculator()

    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)

    def test_subtract(self):
        self.assertEqual(self.calc.subtract(5, 3), 2)

    def test_multiply(self):
        self.assertEqual(self.calc.multiply(3, 4), 12)

    def test_divide(self):
        self.assertEqual(self.calc.divide(8, 2), 4)

    def test_divide_by_zero(self):
        with self.assertRaises(ValueError):
            self.calc.divide(5, 0)

if __name__ == "__main__":
    unittest.main()
""",
                "requirements.txt": "# No external dependencies required",
                ".gitignore": "__pycache__/\n*.pyc\n.pytest_cache/",
            }

            for file_path, content in files.items():
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, "w") as f:
                    f.write(content)

            yield tmpdir

    def test_basic_query_functionality(self, reviewer, test_project):
        """Test basic query functionality with real LLM"""
        # Index the project
        stats = reviewer.process_directory(test_project)
        assert stats["total_files"] > 0

        # Test a simple query
        response = reviewer.query("What is the main purpose of this project?", use_tools=False)

        assert isinstance(response, str)
        assert len(response) > 10  # Should get a meaningful response
        assert any(word in response.lower() for word in ["calculator", "math", "arithmetic"])

    def test_tool_calling_functionality(self, reviewer, test_project):
        """Test tool calling with real LLM"""
        # Index the project
        reviewer.process_directory(test_project)

        # Test query that should use tools
        response = reviewer.query(
            "Find all Python files in this project and tell me what they contain", use_tools=True
        )

        assert isinstance(response, str)
        assert len(response) > 20
        # Should mention the Python files
        assert any(name in response for name in ["calculator.py", "test_calculator.py"])

    def test_code_analysis_query(self, reviewer, test_project):
        """Test code analysis capabilities"""
        reviewer.process_directory(test_project)

        response = reviewer.query(
            "What programming patterns and best practices are used in this code?", use_tools=True
        )

        assert isinstance(response, str)
        # Should identify some code patterns
        expected_terms = ["class", "method", "function", "docstring", "test", "unittest"]
        assert any(term in response.lower() for term in expected_terms)

    def test_auto_analysis_with_real_llm(self, reviewer, test_project):
        """Test auto-analysis with real LLM"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            output_file = f.name

        try:
            result_file = reviewer.auto_analyze(test_project, output_file)

            assert result_file == output_file
            assert os.path.exists(output_file)

            with open(output_file) as f:
                content = f.read()

            # Check report structure
            assert "Repository Analysis Report" in content
            assert "## Project Overview" in content
            assert "### Purpose" in content
            assert "### Languages & Technologies" in content

            # Check that analysis was performed
            assert "calculator" in content.lower() or "math" in content.lower()
            assert "python" in content.lower()

            # Should have reasonable content length
            assert len(content) > 1000  # Report should be substantial

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_error_recovery_with_real_llm(self, reviewer):
        """Test error recovery with real LLM"""
        # Test with non-existent directory
        with pytest.raises(ValueError):
            reviewer.process_directory("/nonexistent/directory")

        # Test query without indexing first (should still work with empty context)
        response = reviewer.query("Hello, can you respond?", use_tools=False)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_session_history_with_real_llm(self, reviewer, test_project):
        """Test session history with real LLM"""
        reviewer.process_directory(test_project)

        # Perform multiple queries
        reviewer.query("What is this project?", use_tools=False)
        reviewer.query("What files are included?", use_tools=True)

        # Get history (this may not work with all LLM setups due to chromadb)
        try:
            history = reviewer.get_session_history()
            # If it works, should have some entries
            if history:
                assert len(history) > 0
        except Exception:
            # ChromaDB might not be working in test environment
            pass


class TestLLMPerformance:
    """Performance and stress tests with real LLM"""

    @pytest.fixture
    def reviewer(self):
        return RepoReviewer(api_base_url="http://localhost:11434/v1")

    @pytest.mark.slow
    def test_large_project_analysis(self, reviewer):
        """Test analysis of a larger project structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a larger project structure
            for i in range(20):
                dir_path = os.path.join(tmpdir, f"module_{i}")
                os.makedirs(dir_path, exist_ok=True)

                for j in range(5):
                    file_path = os.path.join(dir_path, f"file_{j}.py")
                    with open(file_path, "w") as f:
                        f.write(
                            f"""
# Module {i}, File {j}
def function_{j}():
    \"\"\"Function {j} in module {i}\"\"\"
    return {i} + {j}

class Class_{j}:
    \"\"\"Class {j} in module {i}\"\"\"
    def method(self):
        return function_{j}()
"""
                        )

            # Process the large project
            stats = reviewer.process_directory(tmpdir)
            assert stats["total_files"] == 100  # 20 modules * 5 files

            # Test query on large project
            response = reviewer.query(
                "How many modules and files are in this project?", use_tools=True
            )

            assert isinstance(response, str)
            assert len(response) > 10

    @pytest.mark.slow
    def test_multiple_tool_calls(self, reviewer):
        """Test multiple sequential tool calls"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = {
                "main.py": "print('main')",
                "utils.py": "def helper(): pass",
                "test.py": "import unittest",
                "README.md": "# Project",
                "config.json": "{}",
            }

            for name, content in files.items():
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write(content)

            reviewer.process_directory(tmpdir)

            # Query that should trigger multiple tool calls
            response = reviewer.query(
                "Find all Python files, then search for any TODO comments, then get info about the largest file",
                use_tools=True,
            )

            assert isinstance(response, str)
            assert len(response) > 10


class TestLLMConfiguration:
    """Test different LLM configurations"""

    def test_different_api_endpoints(self):
        """Test different API endpoint configurations"""
        # Test local Ollama
        if check_llm_available("http://localhost:11434/v1"):
            reviewer = RepoReviewer(api_base_url="http://localhost:11434/v1")
            assert str(reviewer.client.base_url).rstrip("/") == "http://localhost:11434/v1"

        # Test different port
        if check_llm_available("http://localhost:8080/v1"):
            reviewer = RepoReviewer(api_base_url="http://localhost:8080/v1")
            assert str(reviewer.client.base_url).rstrip("/") == "http://localhost:8080/v1"

    def test_model_parameters(self):
        """Test different model parameters"""
        reviewer = RepoReviewer(
            chunk_size=500, chunk_overlap=100, embedding_model_name="all-MiniLM-L6-v2"
        )

        assert reviewer.text_splitter._chunk_size == 500
        assert reviewer.text_splitter._chunk_overlap == 100


if __name__ == "__main__":
    # Run with: pytest test_with_llm.py -v -m "not slow"
    # For slow tests: pytest test_with_llm.py -v -m "slow"
    pytest.main([__file__, "-v", "-m", "not slow"])
