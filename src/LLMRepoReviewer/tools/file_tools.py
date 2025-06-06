"""
File system tools for LLM Repo Reviewer
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional

from .base import BaseTool


class FindFilesTool(BaseTool):
    """Tool for finding files using the find command"""

    @property
    def name(self) -> str:
        return "find_files"

    @property
    def description(self) -> str:
        return "Find files in the indexed directory using the find command"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Starting directory path (defaults to current indexed directory)",
                },
                "name_pattern": {
                    "type": "string",
                    "description": "File name pattern (e.g., '*.py', 'test_*')",
                },
                "type": {
                    "type": "string",
                    "description": "File type: 'f' for files, 'd' for directories",
                    "enum": ["f", "d"],
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to search (default: no limit)",
                },
            },
        }

    def execute(
        self,
        path: str = ".",
        name_pattern: Optional[str] = None,
        type: str = "f",
        max_depth: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Execute find command"""
        cmd = ["find", path]

        if max_depth:
            cmd.extend(["-maxdepth", str(max_depth)])

        if type:
            cmd.extend(["-type", type])

        if name_pattern:
            cmd.extend(["-name", name_pattern])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0:
                files = result.stdout.strip().split("\n") if result.stdout.strip() else []
                return f"Found {len(files)} items:\n" + "\n".join(files[:20])  # Limit to 20 results
            return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {e!s}"


class GrepContentTool(BaseTool):
    """Tool for searching file contents using grep"""

    @property
    def name(self) -> str:
        return "grep_content"

    @property
    def description(self) -> str:
        return "Search file contents using the grep command"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (supports regular expressions)",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in",
                },
                "case_insensitive": {
                    "type": "boolean",
                    "description": "Case insensitive search (default: false)",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search recursively in directories (default: false)",
                },
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Show line numbers in results (default: true)",
                },
            },
            "required": ["pattern", "path"],
        }

    def execute(
        self,
        pattern: str,
        path: str,
        case_insensitive: bool = False,
        recursive: bool = False,
        show_line_numbers: bool = True,
        **kwargs,
    ) -> str:
        """Execute grep command"""
        cmd = ["grep"]

        if case_insensitive:
            cmd.append("-i")
        if recursive:
            cmd.append("-r")
        if show_line_numbers:
            cmd.append("-n")

        cmd.extend([pattern, path])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
                return f"Found {len(lines)} matches:\n" + "\n".join(
                    lines[:20]
                )  # Limit to 20 results
            if result.returncode == 1:
                return "No matches found"
            return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {e!s}"


class GetFileInfoTool(BaseTool):
    """Tool for getting detailed file information"""

    @property
    def name(self) -> str:
        return "get_file_info"

    @property
    def description(self) -> str:
        return "Get detailed information about a file"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file",
                }
            },
            "required": ["file_path"],
        }

    def execute(self, file_path: str, **kwargs) -> str:
        """Get file information"""
        try:
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"

            stat = os.stat(file_path)
            info = {
                "path": file_path,
                "size": f"{stat.st_size} bytes",
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_file": os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path),
            }

            if os.path.isfile(file_path):
                # Try to get line count
                try:
                    with open(file_path, encoding="utf-8") as f:
                        line_count = sum(1 for _ in f)
                    info["lines"] = line_count
                except Exception:
                    pass

            return json.dumps(info, indent=2)
        except Exception as e:
            return f"Error: {e!s}"
