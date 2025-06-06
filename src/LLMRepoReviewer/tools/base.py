"""
Base tool class for the LLM Repo Reviewer tool system
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """
    Abstract base class for all tools that can be used by the LLM.

    Each tool must implement:
    - name: A unique identifier for the tool
    - description: What the tool does
    - parameters: OpenAI function calling schema for parameters
    - execute: The actual tool implementation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool's unique name"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the tool does"""

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Return the OpenAI function calling schema for the tool's parameters"""

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Parameters as defined in the parameters schema

        Returns:
            str: The result of the tool execution
        """

    def to_openai_function(self) -> Dict[str, Any]:
        """
        Convert the tool to OpenAI function calling format.

        Returns:
            Dict[str, Any]: OpenAI function calling schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate that the provided parameters match the expected schema.

        Args:
            parameters: The parameters to validate

        Returns:
            bool: True if parameters are valid
        """
        # Basic validation - check required parameters exist
        required = self.parameters.get("required", [])
        return all(param in parameters for param in required)

    def safe_execute(self, **kwargs) -> str:
        """
        Execute the tool with error handling.

        Args:
            **kwargs: Parameters for the tool

        Returns:
            str: Tool result or error message
        """
        try:
            if not self.validate_parameters(kwargs):
                return f"Error: Invalid parameters for {self.name}"

            return self.execute(**kwargs)

        except Exception as e:
            return f"Error executing {self.name}: {e!s}"
