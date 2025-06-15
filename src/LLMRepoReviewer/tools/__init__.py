"""
Tool system for LLM Repo Reviewer

This module provides a flexible tool system that allows the LLM to interact with
the file system and perform various operations during analysis.
"""

from .base import BaseTool
from .file_tools import FindFilesTool, GetFileInfoTool, GrepContentTool
from .health_tools import health_tools
from .registry import ToolRegistry

# Create the default tool registry
default_registry = ToolRegistry()

# Register built-in tools
default_registry.register(FindFilesTool())
default_registry.register(GrepContentTool())
default_registry.register(GetFileInfoTool())

# Register health analysis tools
for tool in health_tools:
    default_registry.register(tool)

__all__ = [
    "BaseTool",
    "FindFilesTool",
    "GetFileInfoTool",
    "GrepContentTool",
    "ToolRegistry",
    "default_registry",
]
