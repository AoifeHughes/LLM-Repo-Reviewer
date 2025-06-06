"""
Tool registry for managing and discovering tools
"""

from typing import Any, Dict, List, Optional

from .base import BaseTool


class ToolRegistry:
    """
    Registry for managing tools that can be used by the LLM.

    Provides methods to register tools, get tool definitions for OpenAI,
    and execute tools by name.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a new tool.

        Args:
            tool: The tool instance to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if tool.name in self._tools:
            msg = f"Tool '{tool.name}' is already registered"
            raise ValueError(msg)

        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool by name.

        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            BaseTool: The tool instance, or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """
        Get a list of all registered tool names.

        Returns:
            List[str]: List of tool names
        """
        return list(self._tools.keys())

    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """
        Get all tools formatted for OpenAI function calling.

        Returns:
            List[Dict[str, Any]]: List of OpenAI function schemas
        """
        return [tool.to_openai_function() for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            str: Result of the tool execution or error message
        """
        tool = self.get_tool(tool_name)
        if tool is None:
            return f"Unknown tool: {tool_name}"

        return tool.safe_execute(**arguments)

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools

    def __iter__(self):
        """Iterate over registered tools."""
        return iter(self._tools.values())
