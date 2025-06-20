"""
Repository editor for automated file generation and quality improvements.

This module provides functionality to generate missing files, suggest improvements,
and automate quality enhancements based on repository health assessments.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .quality_scorer import HealthScores
from .repo_indexer import RepoIndexer
from .template_manager import TemplateManager


class RepoEditor:
    """
    Repository editor that generates missing files and automates quality enhancements.

    Capabilities:
    - Generate standard files (README, CONTRIBUTING, etc.)
    - Create GitHub workflow templates
    - Add license files with proper attribution
    - Generate issue/PR templates
    - Create security policies
    - Add linting configurations
    """

    def __init__(self):
        self.template_manager = TemplateManager()
        self.indexer = RepoIndexer()

    def generate_missing_files(
        self,
        repo_path: str,
        repo_metadata: Dict[str, Any],
        context_overrides: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Generate missing standard repository files.

        Args:
            repo_path: Path to the repository
            repo_metadata: Repository metadata from indexer
            context_overrides: Additional context variables
            dry_run: If True, don't actually create files, just return what would be created

        Returns:
            List of dictionaries with file information (path, content, status)
        """
        repo_path = Path(repo_path)
        results = []

        # Get missing files
        missing_files = self.template_manager.get_missing_files(str(repo_path), repo_metadata)

        if not missing_files:
            return results

        # Create template context
        context = self.template_manager.create_context(repo_metadata, **(context_overrides or {}))

        for template_name in missing_files:
            try:
                # Generate content
                content = self.template_manager.generate_file(template_name, context)

                # Determine output path
                output_path = repo_path / template_name

                if not dry_run:
                    # Create directory if needed
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Write file
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    status = "created"
                else:
                    status = "would_create"

                results.append(
                    {
                        "path": str(output_path.relative_to(repo_path)),
                        "template": template_name,
                        "status": status,
                        "size": len(content),
                    }
                )

            except Exception as e:
                results.append(
                    {
                        "path": template_name,
                        "template": template_name,
                        "status": "error",
                        "error": str(e),
                    }
                )

        return results

    def suggest_file_improvements(
        self, repo_path: str, repo_metadata: Dict[str, Any], scores: HealthScores
    ) -> List[Dict[str, Any]]:
        """
        Suggest improvements for existing files.

        Args:
            repo_path: Path to the repository
            repo_metadata: Repository metadata
            scores: Health scores

        Returns:
            List of improvement suggestions
        """
        repo_path = Path(repo_path)
        suggestions = []

        # Check README improvements
        if repo_path.joinpath("README.md").exists():
            readme_score = repo_metadata.get("documentation", {}).get("readme_quality_score", 0)
            if readme_score < 80:
                suggestions.append(
                    {
                        "file": "README.md",
                        "category": "documentation",
                        "priority": "medium",
                        "title": "Improve README Quality",
                        "description": f"Current README score: {readme_score}/100. Consider adding missing sections.",
                        "improvements": self._suggest_readme_improvements(
                            repo_path / "README.md", repo_metadata
                        ),
                    }
                )

        # Check .gitignore improvements
        if repo_path.joinpath(".gitignore").exists():
            gitignore_suggestions = self._suggest_gitignore_improvements(
                repo_path / ".gitignore", repo_metadata
            )
            if gitignore_suggestions:
                suggestions.append(
                    {
                        "file": ".gitignore",
                        "category": "development",
                        "priority": "low",
                        "title": "Improve .gitignore",
                        "description": "Add language-specific ignore patterns",
                        "improvements": gitignore_suggestions,
                    }
                )

        # Check workflow improvements
        workflows_dir = repo_path / ".github" / "workflows"
        if workflows_dir.exists():
            workflow_suggestions = self._suggest_workflow_improvements(workflows_dir, repo_metadata)
            suggestions.extend(workflow_suggestions)

        # Check dependency file improvements
        dep_suggestions = self._suggest_dependency_improvements(repo_path, repo_metadata, scores)
        suggestions.extend(dep_suggestions)

        return suggestions

    def apply_improvements(
        self, repo_path: str, improvements: List[Dict[str, Any]], dry_run: bool = False
    ) -> List[Dict[str, str]]:
        """
        Apply suggested improvements to repository files.

        Args:
            repo_path: Path to the repository
            improvements: List of improvements to apply
            dry_run: If True, don't actually modify files

        Returns:
            List of results for each improvement applied
        """
        repo_path = Path(repo_path)
        results = []

        for improvement in improvements:
            try:
                file_path = repo_path / improvement["file"]

                if (
                    improvement["category"] == "documentation"
                    and improvement["file"] == "README.md"
                ):
                    result = self._apply_readme_improvements(file_path, improvement, dry_run)
                elif (
                    improvement["category"] == "development" and improvement["file"] == ".gitignore"
                ):
                    result = self._apply_gitignore_improvements(file_path, improvement, dry_run)
                else:
                    result = {
                        "file": improvement["file"],
                        "status": "skipped",
                        "reason": "Improvement type not yet implemented",
                    }

                results.append(result)

            except Exception as e:
                results.append(
                    {"file": improvement.get("file", "unknown"), "status": "error", "error": str(e)}
                )

        return results

    def create_development_setup(
        self,
        repo_path: str,
        repo_metadata: Dict[str, Any],
        include_pre_commit: bool = True,
        include_devcontainer: bool = False,
        dry_run: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Create development environment setup files.

        Args:
            repo_path: Path to the repository
            repo_metadata: Repository metadata
            include_pre_commit: Whether to include pre-commit hooks
            include_devcontainer: Whether to include devcontainer config
            dry_run: If True, don't actually create files

        Returns:
            List of created files
        """
        repo_path = Path(repo_path)
        results = []
        primary_language = repo_metadata.get("languages", {}).get("primary_language", "").lower()

        # Create pre-commit configuration
        if include_pre_commit and primary_language in ["python", "javascript", "typescript"]:
            precommit_config = self._create_precommit_config(primary_language)
            results.append(
                self._write_file_if_needed(
                    repo_path / ".pre-commit-config.yaml", precommit_config, dry_run
                )
            )

        # Create development container
        if include_devcontainer:
            devcontainer_config = self._create_devcontainer_config(primary_language, repo_metadata)
            devcontainer_dir = repo_path / ".devcontainer"

            if not dry_run:
                devcontainer_dir.mkdir(exist_ok=True)

            results.append(
                self._write_file_if_needed(
                    devcontainer_dir / "devcontainer.json", devcontainer_config, dry_run
                )
            )

        # Create language-specific development files
        if primary_language == "python":
            # Create tox.ini for testing across Python versions
            tox_config = self._create_tox_config(repo_metadata)
            results.append(self._write_file_if_needed(repo_path / "tox.ini", tox_config, dry_run))

        return results

    def _suggest_readme_improvements(
        self, readme_path: Path, repo_metadata: Dict[str, Any]
    ) -> List[str]:
        """Suggest specific README improvements."""
        improvements = []

        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read().lower()

            # Check for missing sections
            required_sections = {
                "installation": ["install", "setup", "getting started"],
                "usage": ["usage", "example", "how to"],
                "contributing": ["contribut", "development"],
                "license": ["license", "copyright"],
                "testing": ["test", "testing"],
            }

            for section, keywords in required_sections.items():
                if not any(keyword in content for keyword in keywords):
                    improvements.append(f"Add {section.title()} section")

            # Check for badges
            if "badge" not in content and "shields.io" not in content:
                improvements.append("Add status badges (build, coverage, version)")

            # Check for code examples
            if "```" not in content:
                improvements.append("Add code examples with syntax highlighting")

            # Check for TOC if README is long
            if content.count("\n") > 100 and "table of contents" not in content:
                improvements.append("Add table of contents for long README")

        except Exception:
            improvements.append("Unable to analyze README content")

        return improvements

    def _suggest_gitignore_improvements(
        self, gitignore_path: Path, repo_metadata: Dict[str, Any]
    ) -> List[str]:
        """Suggest .gitignore improvements."""
        improvements = []
        primary_language = repo_metadata.get("languages", {}).get("primary_language", "").lower()

        try:
            with open(gitignore_path, encoding="utf-8") as f:
                content = f.read()

            # Language-specific suggestions
            if primary_language == "python":
                python_patterns = ["__pycache__/", "*.py[cod]", ".pytest_cache/", ".coverage"]
                missing = [p for p in python_patterns if p not in content]
                if missing:
                    improvements.append(f"Add Python-specific patterns: {', '.join(missing)}")

            elif primary_language == "javascript":
                js_patterns = ["node_modules/", "*.log", ".env"]
                missing = [p for p in js_patterns if p not in content]
                if missing:
                    improvements.append(f"Add JavaScript-specific patterns: {', '.join(missing)}")

            # IDE patterns
            ide_patterns = [".vscode/", ".idea/", "*.swp"]
            missing_ide = [p for p in ide_patterns if p not in content]
            if missing_ide:
                improvements.append(f"Add IDE patterns: {', '.join(missing_ide)}")

        except Exception:
            improvements.append("Unable to analyze .gitignore content")

        return improvements

    def _suggest_workflow_improvements(
        self, workflows_dir: Path, repo_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest GitHub workflow improvements."""
        suggestions = []

        # Check if CI workflow exists and has comprehensive testing
        ci_workflows = list(workflows_dir.glob("*ci*.yml")) + list(workflows_dir.glob("*test*.yml"))

        if not ci_workflows:
            suggestions.append(
                {
                    "file": ".github/workflows/ci.yml",
                    "category": "ci_cd",
                    "priority": "high",
                    "title": "Add CI Workflow",
                    "description": "No CI workflow detected. Add automated testing.",
                    "improvements": ["Create CI workflow with automated testing"],
                }
            )
        else:
            # Analyze existing CI workflow
            for workflow in ci_workflows:
                try:
                    with open(workflow, encoding="utf-8") as f:
                        content = f.read()

                    workflow_improvements = []

                    # Check for security scanning
                    if "security" not in content.lower() and "codeql" not in content.lower():
                        workflow_improvements.append("Add CodeQL security scanning")

                    # Check for dependency vulnerability scanning
                    if "dependabot" not in content.lower() and "audit" not in content.lower():
                        workflow_improvements.append("Add dependency vulnerability scanning")

                    # Check for coverage reporting
                    if "coverage" not in content.lower() and "codecov" not in content.lower():
                        workflow_improvements.append("Add test coverage reporting")

                    if workflow_improvements:
                        suggestions.append(
                            {
                                "file": str(workflow.relative_to(workflows_dir.parent.parent)),
                                "category": "ci_cd",
                                "priority": "medium",
                                "title": "Enhance CI Workflow",
                                "description": "Add security and quality checks to CI",
                                "improvements": workflow_improvements,
                            }
                        )

                except Exception:
                    continue

        return suggestions

    def _suggest_dependency_improvements(
        self, repo_path: Path, repo_metadata: Dict[str, Any], scores: HealthScores
    ) -> List[Dict[str, Any]]:
        """Suggest improvements to dependency management."""
        suggestions = []
        primary_language = repo_metadata.get("languages", {}).get("primary_language", "").lower()

        # Python-specific suggestions
        if primary_language == "python":
            pyproject_path = repo_path / "pyproject.toml"
            requirements_path = repo_path / "requirements.txt"

            if requirements_path.exists() and not pyproject_path.exists():
                suggestions.append(
                    {
                        "file": "pyproject.toml",
                        "category": "development",
                        "priority": "medium",
                        "title": "Modernize Python Packaging",
                        "description": "Consider migrating from requirements.txt to pyproject.toml",
                        "improvements": ["Create pyproject.toml for modern Python packaging"],
                    }
                )

        # JavaScript-specific suggestions
        elif primary_language == "javascript":
            package_json = repo_path / "package.json"
            if package_json.exists():
                try:
                    import json

                    with open(package_json, encoding="utf-8") as f:
                        data = json.load(f)

                    improvements = []

                    # Check for missing scripts
                    scripts = data.get("scripts", {})
                    if "test" not in scripts:
                        improvements.append("Add test script")
                    if "lint" not in scripts:
                        improvements.append("Add lint script")

                    # Check for security
                    if "audit" not in scripts:
                        improvements.append("Add npm audit script for security")

                    if improvements:
                        suggestions.append(
                            {
                                "file": "package.json",
                                "category": "development",
                                "priority": "medium",
                                "title": "Enhance package.json",
                                "description": "Add missing scripts and configurations",
                                "improvements": improvements,
                            }
                        )

                except Exception:
                    pass

        return suggestions

    def _apply_readme_improvements(
        self, readme_path: Path, improvement: Dict[str, Any], dry_run: bool
    ) -> Dict[str, str]:
        """Apply README improvements."""
        if dry_run:
            return {
                "file": str(readme_path.name),
                "status": "would_modify",
                "changes": len(improvement.get("improvements", [])),
            }

        # For now, just return that we would apply improvements
        # In a full implementation, this would actually modify the README
        return {
            "file": str(readme_path.name),
            "status": "improvements_suggested",
            "note": "Manual review and application recommended",
        }

    def _apply_gitignore_improvements(
        self, gitignore_path: Path, improvement: Dict[str, Any], dry_run: bool
    ) -> Dict[str, str]:
        """Apply .gitignore improvements."""
        if dry_run:
            return {
                "file": str(gitignore_path.name),
                "status": "would_modify",
                "changes": len(improvement.get("improvements", [])),
            }

        try:
            # Read current content
            with open(gitignore_path, encoding="utf-8") as f:
                content = f.read()

            # Add improvements (this is a simplified implementation)
            if not content.endswith("\n"):
                content += "\n"

            content += "\n# Auto-generated improvements\n"
            for imp in improvement.get("improvements", []):
                if "Python-specific" in imp:
                    content += "# Python\n__pycache__/\n*.py[cod]\n.pytest_cache/\n.coverage\n\n"
                elif "JavaScript-specific" in imp:
                    content += "# JavaScript\nnode_modules/\n*.log\n.env\n\n"
                elif "IDE patterns" in imp:
                    content += "# IDEs\n.vscode/\n.idea/\n*.swp\n\n"

            # Write back
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "file": str(gitignore_path.name),
                "status": "modified",
                "changes": len(improvement.get("improvements", [])),
            }

        except Exception as e:
            return {"file": str(gitignore_path.name), "status": "error", "error": str(e)}

    def _write_file_if_needed(self, file_path: Path, content: str, dry_run: bool) -> Dict[str, str]:
        """Write file if it doesn't exist."""
        if file_path.exists():
            return {
                "path": str(file_path.name),
                "status": "exists",
                "note": "File already exists, skipped",
            }

        if dry_run:
            return {"path": str(file_path.name), "status": "would_create", "size": len(content)}

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {"path": str(file_path.name), "status": "created", "size": len(content)}

        except Exception as e:
            return {"path": str(file_path.name), "status": "error", "error": str(e)}

    def _create_precommit_config(self, language: str) -> str:
        """Create pre-commit configuration."""
        if language == "python":
            return """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
"""
        if language in ["javascript", "typescript"]:
            return """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.55.0
    hooks:
      - id: eslint
        files: \\.[jt]sx?$
        types: [file]

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
"""
        return """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
"""

    def _create_devcontainer_config(self, language: str, repo_metadata: Dict[str, Any]) -> str:
        """Create devcontainer configuration."""
        repo_name = repo_metadata.get("repo_id", "project")

        if language == "python":
            return f"""{{
    "name": "{repo_name}",
    "image": "mcr.microsoft.com/devcontainers/python:3.11-bullseye",
    "features": {{
        "ghcr.io/devcontainers/features/git:1": {{}}
    }},
    "postCreateCommand": "pip install -e .[dev]",
    "customizations": {{
        "vscode": {{
            "extensions": [
                "ms-python.python",
                "ms-python.flake8",
                "ms-python.mypy-type-checker",
                "charliermarsh.ruff"
            ]
        }}
    }},
    "forwardPorts": [8000],
    "portsAttributes": {{
        "8000": {{
            "label": "Application"
        }}
    }}
}}"""
        return f"""{{
    "name": "{repo_name}",
    "image": "mcr.microsoft.com/devcontainers/universal:2-linux",
    "features": {{
        "ghcr.io/devcontainers/features/git:1": {{}}
    }},
    "postCreateCommand": "echo 'Development container ready'",
    "forwardPorts": [3000, 8000]
}}"""

    def _create_tox_config(self, repo_metadata: Dict[str, Any]) -> str:
        """Create tox configuration for Python projects."""
        return """[tox]
envlist = py38,py39,py310,py311,py312,lint,type

[testenv]
deps =
    pytest
    pytest-cov
commands = pytest {posargs}

[testenv:lint]
deps = ruff
commands =
    ruff check .
    ruff format --check .

[testenv:type]
deps = mypy
commands = mypy .

[testenv:coverage]
deps =
    pytest
    pytest-cov
    coverage[toml]
commands =
    pytest --cov --cov-report=html --cov-report=term-missing
    coverage report --fail-under=80
"""
