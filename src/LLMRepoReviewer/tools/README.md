# Tool System

The LLM Repo Reviewer includes a flexible tool system that allows the AI to interact with the file system and perform various operations during analysis.

## Built-in Tools

### FindFilesTool
- **Name**: `find_files`
- **Description**: Find files using the system find command
- **Parameters**:
  - `path` (optional): Directory to search in
  - `name_pattern` (optional): File name pattern (e.g., "*.py")
  - `type` (optional): File type ("f" for files, "d" for directories)
  - `max_depth` (optional): Maximum search depth

### GrepContentTool
- **Name**: `grep_content`
- **Description**: Search file contents using grep
- **Parameters**:
  - `pattern` (required): Search pattern
  - `path` (required): File/directory to search
  - `case_insensitive` (optional): Case insensitive search
  - `recursive` (optional): Search recursively
  - `show_line_numbers` (optional): Show line numbers

### GetFileInfoTool
- **Name**: `get_file_info`
- **Description**: Get detailed file information
- **Parameters**:
  - `file_path` (required): Path to the file

## Creating Custom Tools

To create a custom tool, inherit from `BaseTool` and implement the required methods:

```python
from src.LLMRepoReviewer.tools.base import BaseTool
from typing import Dict, Any


class MyCustomTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Description of what my tool does"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Description of parameter",
                },
            },
            "required": ["param1"],
        }

    def execute(self, param1: str, **kwargs) -> str:
        # Your tool logic here
        return f"Tool executed with {param1}"
```

## Registering Tools

### At Runtime
```python
from src.LLMRepoReviewer.repo_reviewer import RepoReviewer

reviewer = RepoReviewer()
custom_tool = MyCustomTool()
reviewer.register_tool(custom_tool)
```

### In the Default Registry
Add your tool to `tools/__init__.py`:

```python
from .my_tool import MyCustomTool

# Register with default registry
default_registry.register(MyCustomTool())
```

## Tool Guidelines

1. **Error Handling**: Tools should handle errors gracefully and return descriptive error messages
2. **Security**: Be careful with tools that execute system commands or access files
3. **Performance**: Consider timeouts for long-running operations
4. **Output Format**: Return human-readable strings that the LLM can understand
5. **Parameter Validation**: Use the OpenAI function calling schema for parameter validation

## Examples

See `example_custom_tool.py` in the project root for a complete example of creating and using a custom tool.
