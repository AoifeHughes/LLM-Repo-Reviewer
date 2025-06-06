"""
Unit tests for the tool system
"""

import json
import os
import tempfile
from typing import Any, Dict
from unittest.mock import patch

import pytest

from LLMRepoReviewer.tools.base import BaseTool
from LLMRepoReviewer.tools.file_tools import FindFilesTool, GetFileInfoTool, GrepContentTool
from LLMRepoReviewer.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing"""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"test_param": {"type": "string", "description": "Test parameter"}},
            "required": ["test_param"],
        }

    def execute(self, test_param: str, **kwargs) -> str:
        return f"Mock tool executed with: {test_param}"


class FailingMockTool(BaseTool):
    """Mock tool that always fails for testing error handling"""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that always fails"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        }

    def execute(self, param: str, **kwargs) -> str:
        raise ValueError("This tool always fails")


class TestBaseTool:
    """Test the BaseTool abstract base class"""

    def test_mock_tool_properties(self):
        """Test that mock tool implements all required properties"""
        tool = MockTool()

        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert "test_param" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["test_param"]

    def test_to_openai_function(self):
        """Test conversion to OpenAI function format"""
        tool = MockTool()
        openai_func = tool.to_openai_function()

        assert openai_func["type"] == "function"
        assert openai_func["function"]["name"] == "mock_tool"
        assert openai_func["function"]["description"] == "A mock tool for testing"
        assert openai_func["function"]["parameters"] == tool.parameters

    def test_validate_parameters_valid(self):
        """Test parameter validation with valid parameters"""
        tool = MockTool()

        # Valid parameters
        assert tool.validate_parameters({"test_param": "value"}) is True
        assert tool.validate_parameters({"test_param": "value", "extra": "ignored"}) is True

    def test_validate_parameters_invalid(self):
        """Test parameter validation with invalid parameters"""
        tool = MockTool()

        # Missing required parameter
        assert tool.validate_parameters({}) is False
        assert tool.validate_parameters({"wrong_param": "value"}) is False

    def test_safe_execute_success(self):
        """Test safe execution with valid parameters"""
        tool = MockTool()
        result = tool.safe_execute(test_param="test_value")

        assert result == "Mock tool executed with: test_value"

    def test_safe_execute_invalid_params(self):
        """Test safe execution with invalid parameters"""
        tool = MockTool()
        result = tool.safe_execute(wrong_param="value")

        assert "Error: Invalid parameters for mock_tool" in result

    def test_safe_execute_tool_error(self):
        """Test safe execution when tool raises exception"""
        tool = FailingMockTool()
        result = tool.safe_execute(param="value")

        assert "Error executing failing_tool" in result
        assert "This tool always fails" in result


class TestToolRegistry:
    """Test the ToolRegistry class"""

    def test_empty_registry(self):
        """Test empty registry behavior"""
        registry = ToolRegistry()

        assert len(registry) == 0
        assert list(registry.list_tools()) == []
        assert registry.get_openai_functions() == []

    def test_register_tool(self):
        """Test registering a tool"""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        assert len(registry) == 1
        assert "mock_tool" in registry
        assert registry.list_tools() == ["mock_tool"]
        assert registry.get_tool("mock_tool") is tool

    def test_register_duplicate_tool(self):
        """Test registering a tool with duplicate name"""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()

        registry.register(tool1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_unregister_tool(self):
        """Test unregistering a tool"""
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)
        assert "mock_tool" in registry

        registry.unregister("mock_tool")
        assert "mock_tool" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent_tool(self):
        """Test unregistering a tool that doesn't exist"""
        registry = ToolRegistry()

        # Should not raise an error
        registry.unregister("nonexistent_tool")

    def test_get_openai_functions(self):
        """Test getting OpenAI function definitions"""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        functions = registry.get_openai_functions()

        assert len(functions) == 1
        assert functions[0]["type"] == "function"
        assert functions[0]["function"]["name"] == "mock_tool"

    def test_execute_tool_success(self):
        """Test successful tool execution"""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        result = registry.execute_tool("mock_tool", {"test_param": "value"})

        assert result == "Mock tool executed with: value"

    def test_execute_unknown_tool(self):
        """Test executing unknown tool"""
        registry = ToolRegistry()

        result = registry.execute_tool("unknown_tool", {})

        assert "Unknown tool: unknown_tool" in result

    def test_clear_registry(self):
        """Test clearing the registry"""
        registry = ToolRegistry()
        registry.register(MockTool())

        assert len(registry) == 1

        registry.clear()

        assert len(registry) == 0
        assert registry.list_tools() == []

    def test_iteration(self):
        """Test iterating over tools"""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        tools = list(registry)

        assert len(tools) == 1
        assert tools[0] is tool


class TestFileTools:
    """Test the built-in file tools"""

    def test_find_files_tool_properties(self):
        """Test FindFilesTool properties"""
        tool = FindFilesTool()

        assert tool.name == "find_files"
        assert "find" in tool.description.lower()
        assert "path" in tool.parameters["properties"]
        assert "name_pattern" in tool.parameters["properties"]

    def test_grep_content_tool_properties(self):
        """Test GrepContentTool properties"""
        tool = GrepContentTool()

        assert tool.name == "grep_content"
        assert "grep" in tool.description.lower()
        assert "pattern" in tool.parameters["properties"]
        assert "path" in tool.parameters["properties"]
        assert "pattern" in tool.parameters["required"]
        assert "path" in tool.parameters["required"]

    def test_get_file_info_tool_properties(self):
        """Test GetFileInfoTool properties"""
        tool = GetFileInfoTool()

        assert tool.name == "get_file_info"
        assert "file" in tool.description.lower()
        assert "file_path" in tool.parameters["properties"]
        assert "file_path" in tool.parameters["required"]

    @patch("subprocess.run")
    def test_find_files_tool_execution(self, mock_run):
        """Test FindFilesTool execution"""
        tool = FindFilesTool()

        # Mock successful subprocess call
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "file1.py\nfile2.py\nfile3.py"

        result = tool.execute(path=".", name_pattern="*.py")

        assert "Found 3 items" in result
        assert "file1.py" in result
        assert "file2.py" in result
        assert "file3.py" in result

        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "find" in call_args
        assert "." in call_args
        assert "*.py" in call_args

    @patch("subprocess.run")
    def test_find_files_tool_error(self, mock_run):
        """Test FindFilesTool error handling"""
        tool = FindFilesTool()

        # Mock failed subprocess call
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "No such file or directory"

        result = tool.execute(path="/nonexistent")

        assert "Error:" in result
        assert "No such file or directory" in result

    @patch("subprocess.run")
    def test_grep_content_tool_execution(self, mock_run):
        """Test GrepContentTool execution"""
        tool = GrepContentTool()

        # Mock successful subprocess call
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "file1.py:10:def function()\nfile2.py:5:class MyClass"

        result = tool.execute(pattern="def|class", path=".", recursive=True)

        assert "Found 2 matches" in result
        assert "file1.py:10:def function()" in result
        assert "file2.py:5:class MyClass" in result

    @patch("subprocess.run")
    def test_grep_content_tool_no_matches(self, mock_run):
        """Test GrepContentTool with no matches"""
        tool = GrepContentTool()

        # Mock no matches found
        mock_run.return_value.returncode = 1

        result = tool.execute(pattern="nonexistent", path=".")

        assert "No matches found" in result

    def test_get_file_info_tool_nonexistent_file(self):
        """Test GetFileInfoTool with nonexistent file"""
        tool = GetFileInfoTool()

        result = tool.execute(file_path="/nonexistent/file.txt")

        assert "File not found" in result

    def test_get_file_info_tool_existing_file(self):
        """Test GetFileInfoTool with existing file"""
        tool = GetFileInfoTool()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line 1\nline 2\nline 3")
            temp_file = f.name

        try:
            result = tool.execute(file_path=temp_file)

            # Parse the JSON result
            info = json.loads(result)

            assert info["path"] == temp_file
            assert "bytes" in info["size"]
            assert info["is_file"] is True
            assert info["is_directory"] is False
            assert info["lines"] == 3

        finally:
            # Clean up
            os.unlink(temp_file)


class TestDefaultRegistry:
    """Test the default tool registry"""

    def test_default_registry_has_tools(self):
        """Test that default registry comes with built-in tools"""
        from LLMRepoReviewer.tools import default_registry

        tools = default_registry.list_tools()

        assert "find_files" in tools
        assert "grep_content" in tools
        assert "get_file_info" in tools
        assert len(tools) >= 3

    def test_default_registry_tools_work(self):
        """Test that default registry tools can be executed"""
        from LLMRepoReviewer.tools import default_registry

        # Test get_file_info with a file that should exist
        result = default_registry.execute_tool(
            "get_file_info",
            {
                "file_path": __file__  # This test file itself
            },
        )

        # Should not be an error message
        assert not result.startswith("Error:")
        assert not result.startswith("Unknown tool:")

        # Should be valid JSON
        try:
            info = json.loads(result)
            assert "path" in info
            assert "size" in info
        except json.JSONDecodeError:
            pytest.fail("get_file_info should return valid JSON")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
