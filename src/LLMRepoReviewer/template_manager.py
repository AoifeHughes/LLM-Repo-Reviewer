"""
Template management system for repository file generation.

This module provides templates for various repository components and generates
customized versions based on project metadata and programming language.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import BaseLoader, Environment


class TemplateLoader(BaseLoader):
    """Custom template loader for embedded templates."""

    def __init__(self, templates: Dict[str, str]):
        self.templates = templates

    def get_source(self, environment: Environment, template: str) -> tuple:
        if template not in self.templates:
            msg = f"Template {template} not found"
            raise FileNotFoundError(msg)

        source = self.templates[template]
        return source, None, lambda: True


class TemplateManager:
    """
    Manages templates for various repository components.

    Provides templates for:
    - Documentation (README, API docs, changelogs)
    - Community (Contributing guidelines, code of conduct, issue templates)
    - Security (Security policies, vulnerability reporting)
    - Development (CI/CD workflows, linting configs)
    - Legal (License files, attribution notices)
    """

    def __init__(self):
        self.templates = self._load_templates()
        self.env = Environment(loader=TemplateLoader(self.templates))

    def _load_templates(self) -> Dict[str, str]:
        """Load all embedded templates."""
        return {
            "README.md": self._readme_template(),
            "CONTRIBUTING.md": self._contributing_template(),
            "CODE_OF_CONDUCT.md": self._code_of_conduct_template(),
            "SECURITY.md": self._security_template(),
            "LICENSE": self._license_template(),
            "CHANGELOG.md": self._changelog_template(),
            ".github/workflows/ci.yml": self._ci_workflow_template(),
            ".github/workflows/release.yml": self._release_workflow_template(),
            ".github/ISSUE_TEMPLATE/bug_report.md": self._bug_report_template(),
            ".github/ISSUE_TEMPLATE/feature_request.md": self._feature_request_template(),
            ".github/PULL_REQUEST_TEMPLATE.md": self._pr_template(),
            ".gitignore": self._gitignore_template(),
            "pyproject.toml": self._pyproject_template(),
            "package.json": self._package_json_template(),
            "Cargo.toml": self._cargo_template(),
            "pom.xml": self._pom_template(),
        }

    def generate_file(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Generate file content from template.

        Args:
            template_name: Name of the template to use
            context: Variables to substitute in template

        Returns:
            Generated file content
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def get_missing_files(self, repo_path: str, repo_metadata: Dict[str, Any]) -> List[str]:
        """
        Identify missing standard files for a repository.

        Args:
            repo_path: Path to repository
            repo_metadata: Repository metadata from indexer

        Returns:
            List of missing file names
        """
        repo_path = Path(repo_path)
        missing_files = []

        # Check for standard files
        standard_files = {
            "README.md": ["README.md", "README.rst", "README.txt", "README"],
            "CONTRIBUTING.md": ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING.txt"],
            "CODE_OF_CONDUCT.md": ["CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.rst"],
            "SECURITY.md": ["SECURITY.md", ".github/SECURITY.md"],
            "LICENSE": ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"],
            "CHANGELOG.md": ["CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG.txt", "HISTORY.md"],
            ".gitignore": [".gitignore"],
        }

        for template_name, possible_files in standard_files.items():
            if not any((repo_path / f).exists() for f in possible_files):
                missing_files.append(template_name)

        # Check for language-specific files
        primary_language = repo_metadata.get("languages", {}).get("primary_language", "").lower()

        if primary_language == "python":
            if not any(
                (repo_path / f).exists() for f in ["pyproject.toml", "setup.py", "setup.cfg"]
            ):
                missing_files.append("pyproject.toml")
        elif primary_language == "javascript":
            if not (repo_path / "package.json").exists():
                missing_files.append("package.json")
        elif primary_language == "rust":
            if not (repo_path / "Cargo.toml").exists():
                missing_files.append("Cargo.toml")
        elif primary_language == "java" and not any(
            (repo_path / f).exists() for f in ["pom.xml", "build.gradle"]
        ):
            missing_files.append("pom.xml")

        # Check for GitHub templates
        github_dir = repo_path / ".github"
        if not github_dir.exists():
            missing_files.extend(
                [
                    ".github/ISSUE_TEMPLATE/bug_report.md",
                    ".github/ISSUE_TEMPLATE/feature_request.md",
                    ".github/PULL_REQUEST_TEMPLATE.md",
                ]
            )

        # Check for CI/CD workflows
        workflows_dir = repo_path / ".github" / "workflows"
        if not workflows_dir.exists() or not list(workflows_dir.glob("*.yml")):
            missing_files.append(".github/workflows/ci.yml")

        return missing_files

    def create_context(self, repo_metadata: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Create template context from repository metadata.

        Args:
            repo_metadata: Repository metadata from indexer
            **kwargs: Additional context variables

        Returns:
            Template context dictionary
        """
        # Extract basic information
        repo_name = repo_metadata.get("repo_id", "my-project")
        primary_language = repo_metadata.get("languages", {}).get("primary_language", "Python")

        # Create base context
        context = {
            "repo_name": repo_name,
            "project_name": repo_name.replace("-", " ").replace("_", " ").title(),
            "primary_language": primary_language,
            "current_year": datetime.now().year,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "author_name": kwargs.get("author_name", "Project Author"),
            "author_email": kwargs.get("author_email", "author@example.com"),
            "description": kwargs.get("description", f"A {primary_language} project"),
            "license_type": kwargs.get("license_type", "MIT"),
            "homepage_url": kwargs.get("homepage_url", f"https://github.com/author/{repo_name}"),
            "bug_tracker_url": kwargs.get(
                "bug_tracker_url", f"https://github.com/author/{repo_name}/issues"
            ),
        }

        # Add language-specific context
        context.update(self._get_language_context(primary_language))

        # Merge additional kwargs
        context.update(kwargs)

        return context

    def _get_language_context(self, language: str) -> Dict[str, Any]:
        """Get language-specific template context."""
        language_contexts = {
            "python": {
                "test_command": "pytest",
                "lint_command": "ruff check .",
                "format_command": "ruff format .",
                "type_check_command": "mypy .",
                "install_command": "pip install -e .",
                "dev_install_command": "pip install -e .[dev]",
                "package_manager": "pip",
                "test_framework": "pytest",
            },
            "javascript": {
                "test_command": "npm test",
                "lint_command": "npm run lint",
                "format_command": "npm run format",
                "install_command": "npm install",
                "dev_install_command": "npm install --include=dev",
                "package_manager": "npm",
                "test_framework": "jest",
            },
            "rust": {
                "test_command": "cargo test",
                "lint_command": "cargo clippy",
                "format_command": "cargo fmt",
                "install_command": "cargo build",
                "dev_install_command": "cargo build",
                "package_manager": "cargo",
                "test_framework": "cargo test",
            },
            "java": {
                "test_command": "mvn test",
                "lint_command": "mvn checkstyle:check",
                "install_command": "mvn install",
                "dev_install_command": "mvn install",
                "package_manager": "maven",
                "test_framework": "junit",
            },
        }

        return language_contexts.get(
            language.lower(),
            {
                "test_command": "make test",
                "lint_command": "make lint",
                "install_command": "make install",
                "package_manager": "make",
            },
        )

    # Template definitions
    def _readme_template(self) -> str:
        return """# {{ project_name }}

{{ description }}

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

```bash
{{ install_command }}
```

## Usage

```{{ primary_language.lower() }}
# Basic usage example
```

## Development

### Prerequisites

- {{ primary_language }} (version requirements)
{% if package_manager != "make" -%}
- {{ package_manager }}
{% endif %}

### Setup

```bash
# Clone the repository
git clone {{ homepage_url }}.git
cd {{ repo_name }}

# Install dependencies
{{ dev_install_command }}
```

### Running Tests

```bash
{{ test_command }}
```

### Code Quality

```bash
# Linting
{{ lint_command }}

{% if format_command -%}
# Formatting
{{ format_command }}
{% endif %}
{% if type_check_command -%}

# Type checking
{{ type_check_command }}
{% endif %}
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the {{ license_type }} License - see the [LICENSE](LICENSE) file for details.

## Support

If you have any questions or need help, please:

1. Check the [documentation](docs/)
2. Search [existing issues]({{ bug_tracker_url }})
3. Create a [new issue]({{ bug_tracker_url }}/new)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and releases.
"""

    def _contributing_template(self) -> str:
        return """# Contributing to {{ project_name }}

Thank you for your interest in contributing to {{ project_name }}! This document provides guidelines for contributing.

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Before submitting a bug report:

1. Check if the issue already exists in our [issue tracker]({{ bug_tracker_url }})
2. Ensure you're using the latest version
3. Test with minimal reproduction steps

When submitting a bug report, include:

- Clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behavior
- Environment details (OS, {{ primary_language }} version, etc.)
- Code samples or error messages

### Suggesting Features

Feature requests are welcome! Please:

1. Check existing feature requests first
2. Describe the problem your feature would solve
3. Explain your proposed solution
4. Consider alternative solutions

### Code Contributions

#### Development Setup

1. Fork the repository
2. Clone your fork: `git clone {{ homepage_url }}/your-username/{{ repo_name }}.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `{{ dev_install_command }}`

#### Making Changes

1. Write clear, readable code
2. Follow existing code style and conventions
3. Add tests for new functionality
4. Update documentation as needed
5. Ensure all tests pass: `{{ test_command }}`
6. Run linting: `{{ lint_command }}`

#### Submitting Changes

1. Commit your changes with clear messages
2. Push to your fork
3. Submit a pull request with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots (if applicable)

## Development Guidelines

### Code Style

- Follow {{ primary_language }} conventions
- Use descriptive variable and function names
- Add comments for complex logic
- Keep functions small and focused

### Testing

- Write tests for all new features
- Ensure existing tests still pass
- Aim for good test coverage
- Use meaningful test names

### Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Update changelog for notable changes

## Review Process

1. All submissions require review
2. Maintainers will provide feedback
3. Address review comments promptly
4. Once approved, changes will be merged

## Questions?

Feel free to ask questions by:

- Opening an issue with the "question" label
- Reaching out to maintainers directly

Thank you for contributing!
"""

    def _code_of_conduct_template(self) -> str:
        return """# Code of Conduct

## Our Pledge

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

## Our Standards

Examples of behavior that contributes to a positive environment:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

Examples of unacceptable behavior:

- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

## Enforcement Responsibilities

Community leaders are responsible for clarifying and enforcing our standards of acceptable behavior and will take appropriate and fair corrective action in response to any behavior that they deem inappropriate, threatening, offensive, or harmful.

## Scope

This Code of Conduct applies within all community spaces, and also applies when an individual is officially representing the community in public spaces.

## Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the community leaders responsible for enforcement at {{ author_email }}.

All complaints will be reviewed and investigated promptly and fairly.

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org/), version 2.0.
"""

    def _security_template(self) -> str:
        return """# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of {{ project_name }} seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to {{ author_email }} with the subject line "SECURITY: {{ project_name }} vulnerability report".

### What to Include

Please include the following information in your report:

- Type of issue (buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will provide a detailed response within 7 days indicating next steps
- We will notify you when the vulnerability has been fixed
- We may ask for additional information or guidance during the process

### Responsible Disclosure

We ask that you:

- Give us reasonable time to investigate and fix the issue before public disclosure
- Avoid accessing, modifying, or deleting data without explicit permission
- Avoid degrading the user experience, disrupting systems, or destroying data
- Only interact with accounts you own or with explicit permission from the account holder

### Recognition

We appreciate your efforts to responsibly disclose security vulnerabilities and will acknowledge your contribution in our security advisories (with your permission).

## Security Best Practices

When using {{ project_name }}, please:

- Keep your dependencies up to date
- Use strong authentication methods
- Validate all inputs
- Follow the principle of least privilege
- Regularly audit your security practices

Thank you for helping keep {{ project_name }} and our users safe!
"""

    def _license_template(self) -> str:
        return """MIT License

Copyright (c) {{ current_year }} {{ author_name }}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

    def _changelog_template(self) -> str:
        return """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.0.0] - {{ current_date }}

### Added
- Initial release of {{ project_name }}
- Core functionality implemented
- Documentation and examples

[Unreleased]: {{ homepage_url }}/compare/v1.0.0...HEAD
[1.0.0]: {{ homepage_url }}/releases/tag/v1.0.0
"""

    def _ci_workflow_template(self) -> str:
        # Default to generic template since we don't have language context during init
        return self._generic_ci_workflow_template()

    def _generic_ci_workflow_template(self) -> str:
        return """name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup
      run: |
        # Add setup commands here
        echo "Setting up environment"

    - name: Install dependencies
      run: |
        # Add installation commands here
        echo "Installing dependencies"

    - name: Run tests
      run: |
        # Add test commands here
        echo "Running tests"
"""

    def _release_workflow_template(self) -> str:
        return """name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Create Release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: ${{ github.ref }}
        release_name: Release ${{ github.ref }}
        draft: false
        prerelease: false
"""

    def _bug_report_template(self) -> str:
        return """---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. iOS]
 - {{ primary_language }} Version: [e.g. 3.9]
 - Version: [e.g. 1.0.0]

**Additional context**
Add any other context about the problem here.
"""

    def _feature_request_template(self) -> str:
        return """---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''

---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.
"""

    def _pr_template(self) -> str:
        return """## Description

Brief description of the changes in this PR.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Existing tests updated if needed

## Checklist

- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] Documentation updated as needed
- [ ] No new warnings introduced

## Related Issues

Closes #(issue number)
"""

    def _gitignore_template(self) -> str:
        return """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# poetry
poetry.lock

# pdm
.pdm.toml

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""

    def _pyproject_template(self) -> str:
        return """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{ repo_name }}"
authors = [
  { name = "{{ author_name }}", email = "{{ author_email }}" },
]
description = "{{ description }}"
readme = "README.md"
requires-python = ">=3.8"
classifiers = [
  "Development Status :: 3 - Alpha",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.8",
  "Programming Language :: Python :: 3.9",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
]
dynamic = ["version"]
dependencies = [
  # Add your dependencies here
]

[project.optional-dependencies]
dev = [
  "pytest",
  "pytest-cov",
  "ruff",
  "mypy",
]

[project.urls]
Homepage = "{{ homepage_url }}"
"Bug Tracker" = "{{ bug_tracker_url }}"

[tool.hatch.version]
path = "src/{{ repo_name }}/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["src/{{ repo_name }}"]

[tool.pytest.ini_options]
minversion = "6.0"
addopts = ["-ra", "--strict-markers", "--strict-config"]
testpaths = ["tests"]

[tool.ruff]
target-version = "py38"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "UP"]
ignore = []

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
"""

    def _package_json_template(self) -> str:
        return """{
  "name": "{{ repo_name }}",
  "version": "1.0.0",
  "description": "{{ description }}",
  "main": "index.js",
  "scripts": {
    "test": "jest",
    "lint": "eslint .",
    "format": "prettier --write .",
    "start": "node index.js"
  },
  "keywords": [],
  "author": "{{ author_name }} <{{ author_email }}>",
  "license": "{{ license_type }}",
  "devDependencies": {
    "jest": "^29.0.0",
    "eslint": "^8.0.0",
    "prettier": "^2.0.0"
  },
  "repository": {
    "type": "git",
    "url": "{{ homepage_url }}.git"
  },
  "bugs": {
    "url": "{{ bug_tracker_url }}"
  },
  "homepage": "{{ homepage_url }}#readme"
}
"""

    def _cargo_template(self) -> str:
        return """[package]
name = "{{ repo_name }}"
version = "0.1.0"
edition = "2021"
authors = ["{{ author_name }} <{{ author_email }}>"]
description = "{{ description }}"
license = "{{ license_type }}"
repository = "{{ homepage_url }}"
homepage = "{{ homepage_url }}"
readme = "README.md"

[dependencies]

[dev-dependencies]
"""

    def _pom_template(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>{{ repo_name }}</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <name>{{ project_name }}</name>
    <description>{{ description }}</description>
    <url>{{ homepage_url }}</url>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""
