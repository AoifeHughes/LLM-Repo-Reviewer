"""
Repository indexer for comprehensive repository metadata and structure analysis.

This module provides enhanced indexing capabilities that go beyond simple file processing
to extract detailed repository structure, configuration files, and metadata for health assessment.
"""

import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import git


class RepoIndexer:
    """
    Advanced repository indexer that extracts comprehensive metadata and structure information.

    Capabilities:
    - Repository structure analysis and organization patterns
    - Configuration file parsing (package.json, requirements.txt, etc.)
    - Documentation quality assessment
    - CI/CD workflow detection
    - Dependency analysis
    - License and legal compliance checking
    """

    def __init__(self):
        self.supported_config_files = {
            "python": [
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "setup.cfg",
                "Pipfile",
                "Pipfile.lock",
                "poetry.lock",
                "conda.yaml",
                "environment.yml",
            ],
            "javascript": [
                "package.json",
                "yarn.lock",
                "package-lock.json",
                "pnpm-lock.yaml",
                "bun.lockb",
            ],
            "typescript": ["tsconfig.json", "package.json"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "julia": ["Project.toml", "JuliaProject.toml", "Manifest.toml"],
            "java": ["pom.xml", "build.gradle", "build.gradle.kts", "gradle.properties"],
            "go": ["go.mod", "go.sum"],
            "php": ["composer.json", "composer.lock"],
            "ruby": ["Gemfile", "Gemfile.lock", "*.gemspec"],
            "csharp": ["*.csproj", "*.sln", "packages.config", "Directory.Build.props"],
            "swift": ["Package.swift", "*.xcodeproj", "*.xcworkspace"],
            "dart": ["pubspec.yaml", "pubspec.lock"],
            "elixir": ["mix.exs", "mix.lock"],
            "haskell": ["*.cabal", "stack.yaml", "cabal.project"],
            "ocaml": ["dune-project", "*.opam"],
            "r": ["DESCRIPTION", "NAMESPACE", "*.Rproj"],
            "matlab": ["*.prj", "*.mlapp", "*.mlx"],
            "clojure": ["project.clj", "deps.edn", "build.boot"],
            "scala": ["build.sbt", "*.sbt"],
            "kotlin": ["build.gradle.kts", "pom.xml"],
        }

        self.documentation_files = [
            "README.md",
            "README.rst",
            "README.txt",
            "README",
            "CHANGELOG.md",
            "CHANGELOG.rst",
            "CHANGELOG.txt",
            "CHANGELOG",
            "CONTRIBUTING.md",
            "CONTRIBUTING.rst",
            "CONTRIBUTING.txt",
            "CODE_OF_CONDUCT.md",
            "SECURITY.md",
            "LICENSE",
            "LICENSE.md",
            "LICENSE.txt",
            "COPYING",
            "COPYING.md",
            "COPYING.txt",
            "MIT-LICENSE",
            "MIT-LICENSE.txt",
            "APACHE-LICENSE",
            "APACHE-LICENSE.txt",
            "INSTALL.md",
            "INSTALL.rst",
            "INSTALL.txt",
            "docs/",
            "documentation/",
            "wiki/",
        ]

        self.community_files = [
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
            "SECURITY.md",
            ".github/ISSUE_TEMPLATE/",
            ".github/PULL_REQUEST_TEMPLATE/",
            ".github/issue_template.md",
            ".github/pull_request_template.md",
            "SUPPORT.md",
            "GOVERNANCE.md",
        ]

    def index_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Perform comprehensive repository indexing.

        Args:
            repo_path: Path to the repository root

        Returns:
            Dict containing comprehensive repository metadata
        """
        repo_path = Path(repo_path).resolve()

        return {
            "repo_id": repo_path.name,
            "last_analyzed": datetime.now().isoformat(),
            "repo_path": str(repo_path),
            "structure": self._analyze_structure(repo_path),
            "languages": self._detect_languages(repo_path),
            "dependencies": self._analyze_dependencies(repo_path),
            "documentation": self._assess_documentation(repo_path),
            "community": self._assess_community_health(repo_path),
            "security": self._assess_security(repo_path),
            "ci_cd": self._analyze_ci_cd(repo_path),
            "git_info": self._extract_git_info(repo_path),
            "file_analysis": self._analyze_files(repo_path),
        }

    def _analyze_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository structure and organization."""
        structure = {
            "total_files": 0,
            "total_directories": 0,
            "max_depth": 0,
            "directory_distribution": Counter(),
            "file_distribution": Counter(),
            "organization_score": 0,
        }

        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common artifacts
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["__pycache__", "node_modules", "venv", "env", "target", "build"]
            ]

            level = root.replace(str(repo_path), "").count(os.sep)
            structure["max_depth"] = max(structure["max_depth"], level)
            structure["total_directories"] += len(dirs)
            structure["total_files"] += len(files)

            rel_path = os.path.relpath(root, repo_path)
            if rel_path != ".":
                structure["directory_distribution"][rel_path] += len(files)

            for file in files:
                ext = os.path.splitext(file)[1]
                if ext:
                    structure["file_distribution"][ext] += 1

        # Calculate organization score based on common patterns
        structure["organization_score"] = self._calculate_organization_score(repo_path, structure)

        return structure

    def _calculate_organization_score(self, repo_path: Path, structure: Dict) -> int:
        """Calculate organization score based on common project patterns."""
        score = 0

        # Common directory patterns
        common_dirs = ["src", "lib", "tests", "test", "docs", "examples", "scripts"]
        existing_dirs = [d for d in os.listdir(repo_path) if os.path.isdir(repo_path / d)]

        score += len(set(common_dirs) & set(existing_dirs)) * 10

        # Depth score (not too deep, not too shallow)
        if 2 <= structure["max_depth"] <= 5:
            score += 20
        elif structure["max_depth"] <= 8:
            score += 10

        # File distribution score
        if structure["total_files"] > 0:
            # Reward balanced distribution
            file_counts = list(structure["directory_distribution"].values())
            if file_counts and max(file_counts) / sum(file_counts) < 0.8:
                score += 15

        return min(score, 100)

    def _detect_languages(self, repo_path: Path) -> Dict[str, Any]:
        """Detect programming languages and their distribution."""
        language_map = {
            # Python
            ".py": "Python",
            ".pyx": "Python",
            ".pyi": "Python",
            # JavaScript/TypeScript
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".mjs": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            # Java/JVM
            ".java": "Java",
            ".kt": "Kotlin",
            ".kts": "Kotlin",
            ".scala": "Scala",
            ".clj": "Clojure",
            ".cljs": "ClojureScript",
            # C/C++
            ".c": "C",
            ".cpp": "C++",
            ".cxx": "C++",
            ".cc": "C++",
            ".c++": "C++",
            ".h": "C/C++",
            ".hpp": "C++",
            ".hxx": "C++",
            ".hh": "C++",
            # Systems Programming
            ".rs": "Rust",
            ".go": "Go",
            ".zig": "Zig",
            ".nim": "Nim",
            ".v": "V",
            # Web/Mobile
            ".php": "PHP",
            ".rb": "Ruby",
            ".cs": "C#",
            ".fs": "F#",
            ".vb": "Visual Basic",
            ".swift": "Swift",
            ".dart": "Dart",
            # Functional
            ".hs": "Haskell",
            ".lhs": "Haskell",
            ".ml": "OCaml",
            ".mli": "OCaml",
            ".elm": "Elm",
            ".ex": "Elixir",
            ".exs": "Elixir",
            # Scientific/Numeric
            ".jl": "Julia",
            ".r": "R",
            ".R": "R",
            ".m": "MATLAB",
            ".f90": "Fortran",
            ".f95": "Fortran",
            ".f03": "Fortran",
            ".f08": "Fortran",
            ".for": "Fortran",
            ".f": "Fortran",
            # Shell/Scripting
            ".sh": "Shell",
            ".bash": "Shell",
            ".zsh": "Shell",
            ".fish": "Shell",
            ".ps1": "PowerShell",
            ".bat": "Batch",
            ".cmd": "Batch",
            ".pl": "Perl",
            ".pm": "Perl",
            ".lua": "Lua",
            # Hardware Description
            ".vhd": "VHDL",
            ".vhdl": "VHDL",
            ".sv": "SystemVerilog",
            # Data/Config
            ".sql": "SQL",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".xml": "XML",
            # Documentation
            ".md": "Markdown",
            ".rst": "reStructuredText",
            ".tex": "LaTeX",
        }

        language_files = Counter()
        language_lines = Counter()

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ["__pycache__", "node_modules", "venv", "env"]
            ]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in language_map:
                    language = language_map[ext]
                    language_files[language] += 1

                    # Count lines for better language distribution
                    try:
                        file_path = os.path.join(root, file)
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            lines = sum(1 for line in f if line.strip())
                            language_lines[language] += lines
                    except Exception:
                        pass

        total_files = sum(language_files.values())
        total_lines = sum(language_lines.values())

        languages = {}
        for lang in language_files:
            languages[lang] = {
                "files": language_files[lang],
                "lines": language_lines[lang],
                "file_percentage": language_files[lang] / total_files * 100
                if total_files > 0
                else 0,
                "line_percentage": language_lines[lang] / total_lines * 100
                if total_lines > 0
                else 0,
            }

        # Determine primary language with fallback detection
        primary_language = self._determine_primary_language(
            repo_path, language_lines, language_files
        )

        return {
            "languages": languages,
            "primary_language": primary_language,
            "total_files": total_files,
            "total_lines": total_lines,
        }

    def _determine_primary_language(
        self, repo_path: Path, language_lines: Counter, language_files: Counter
    ) -> str:
        """Determine primary language using multiple detection strategies."""

        # Strategy 1: Use line count if we have significant code
        if language_lines and sum(language_lines.values()) > 100:
            return max(language_lines, key=language_lines.get)

        # Strategy 2: Check for language-specific project files
        language_indicators = {
            "Julia": ["Project.toml", "JuliaProject.toml", "Manifest.toml"],
            "Python": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
            "JavaScript": ["package.json", "yarn.lock", "package-lock.json"],
            "TypeScript": ["tsconfig.json", "package.json"],
            "Rust": ["Cargo.toml", "Cargo.lock"],
            "Go": ["go.mod", "go.sum"],
            "Java": ["pom.xml", "build.gradle", "build.gradle.kts"],
            "C#": ["*.csproj", "*.sln", "Directory.Build.props"],
            "Ruby": ["Gemfile", "Gemfile.lock", "*.gemspec"],
            "PHP": ["composer.json", "composer.lock"],
            "Swift": ["Package.swift", "*.xcodeproj", "*.xcworkspace"],
            "Dart": ["pubspec.yaml", "pubspec.lock"],
            "Elixir": ["mix.exs", "mix.lock"],
            "Haskell": ["*.cabal", "stack.yaml", "cabal.project"],
            "OCaml": ["dune-project", "*.opam", "_build"],
            "R": ["DESCRIPTION", "NAMESPACE", "*.Rproj"],
            "MATLAB": ["*.prj", "*.mlapp", "*.mlx"],
        }

        for language, indicators in language_indicators.items():
            for indicator in indicators:
                if "*" in indicator:
                    # Handle wildcard patterns
                    pattern = indicator.replace("*", "")
                    for item in repo_path.iterdir():
                        if item.name.endswith(pattern):
                            return language
                else:
                    # Handle exact file matches
                    if (repo_path / indicator).exists():
                        return language

        # Strategy 3: Check shebang lines for scripts
        shebang_language = self._detect_shebang_language(repo_path)
        if shebang_language:
            return shebang_language

        # Strategy 4: Use file count if we have multiple files
        if language_files:
            return max(language_files, key=language_files.get)

        # Strategy 5: Final fallback
        return "Unknown"

    def _detect_shebang_language(self, repo_path: Path) -> Optional[str]:
        """Detect primary language from shebang lines in executable files."""
        shebang_map = {
            "python": "Python",
            "python3": "Python",
            "node": "JavaScript",
            "bash": "Shell",
            "sh": "Shell",
            "zsh": "Shell",
            "fish": "Shell",
            "ruby": "Ruby",
            "perl": "Perl",
            "php": "PHP",
            "julia": "Julia",
        }

        script_files = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                file_path = Path(root) / file
                # Check files without extensions that might be scripts
                if (not file_path.suffix and file_path.is_file()) or file_path.suffix in [
                    ".sh",
                    ".py",
                    ".rb",
                    ".pl",
                    ".js",
                ]:
                    script_files.append(file_path)

        shebang_languages = Counter()
        for script_file in script_files[:20]:  # Limit to avoid too much I/O
            try:
                with open(script_file, encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#!"):
                        for interpreter, language in shebang_map.items():
                            if interpreter in first_line:
                                shebang_languages[language] += 1
                                break
            except Exception:
                continue

        return shebang_languages.most_common(1)[0][0] if shebang_languages else None

    def _analyze_dependencies(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze project dependencies and configuration files."""
        dependencies = {
            "dependency_files": [],
            "package_managers": [],
            "dependencies_count": 0,
            "dev_dependencies_count": 0,
            "outdated_dependencies": [],
            "security_vulnerabilities": [],
        }

        # Check for dependency files
        for lang, files in self.supported_config_files.items():
            for file_pattern in files:
                matches = list(repo_path.glob(file_pattern))
                if matches:
                    dependencies["dependency_files"].extend(
                        [str(m.relative_to(repo_path)) for m in matches]
                    )
                    dependencies["package_managers"].append(lang)

        # Parse specific dependency files
        self._parse_package_json(repo_path, dependencies)
        self._parse_requirements_txt(repo_path, dependencies)
        self._parse_pyproject_toml(repo_path, dependencies)

        return dependencies

    def _parse_package_json(self, repo_path: Path, dependencies: Dict):
        """Parse package.json for JavaScript/Node.js projects."""
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, encoding="utf-8") as f:
                    data = json.load(f)
                    dependencies["dependencies_count"] += len(data.get("dependencies", {}))
                    dependencies["dev_dependencies_count"] += len(data.get("devDependencies", {}))
            except Exception:
                pass

    def _parse_requirements_txt(self, repo_path: Path, dependencies: Dict):
        """Parse requirements.txt for Python projects."""
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, encoding="utf-8") as f:
                    lines = [
                        line.strip() for line in f if line.strip() and not line.startswith("#")
                    ]
                    dependencies["dependencies_count"] += len(lines)
            except Exception:
                pass

    def _parse_pyproject_toml(self, repo_path: Path, dependencies: Dict):
        """Parse pyproject.toml for modern Python projects."""
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                try:
                    import tomllib
                except ImportError:
                    tomllib = None
                if tomllib:
                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                        project_deps = data.get("project", {}).get("dependencies", [])
                        dependencies["dependencies_count"] += len(project_deps)
            except Exception:
                pass

    def _assess_documentation(self, repo_path: Path) -> Dict[str, Any]:
        """Assess documentation quality and completeness."""
        doc_assessment = {
            "readme_exists": False,
            "readme_quality_score": 0,
            "changelog_exists": False,
            "contributing_exists": False,
            "documentation_files": [],
            "api_docs_exists": False,
            "code_comments_ratio": 0.0,
        }

        # Check for standard documentation files
        for doc_file in self.documentation_files:
            file_path = repo_path / doc_file
            if file_path.exists():
                doc_assessment["documentation_files"].append(doc_file)

                if "README" in doc_file.upper():
                    doc_assessment["readme_exists"] = True
                    doc_assessment["readme_quality_score"] = self._assess_readme_quality(file_path)
                elif "CHANGELOG" in doc_file.upper():
                    doc_assessment["changelog_exists"] = True
                elif "CONTRIBUTING" in doc_file.upper():
                    doc_assessment["contributing_exists"] = True

        # Check for API documentation
        api_docs_patterns = ["docs/api/", "api/", "**/api.md", "**/API.md"]
        for pattern in api_docs_patterns:
            if list(repo_path.glob(pattern)):
                doc_assessment["api_docs_exists"] = True
                break

        # Assess code comments ratio
        doc_assessment["code_comments_ratio"] = self._calculate_comment_ratio(repo_path)

        return doc_assessment

    def _assess_readme_quality(self, readme_path: Path) -> int:
        """Assess README quality based on common sections and content."""
        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read().lower()

            score = 0
            required_sections = [
                ("description", ["description", "about", "what is"]),
                ("installation", ["install", "setup", "getting started"]),
                ("usage", ["usage", "example", "how to"]),
                ("contributing", ["contribut", "development"]),
                ("license", ["license", "copyright"]),
            ]

            for _, keywords in required_sections:
                if any(keyword in content for keyword in keywords):
                    score += 20

            # Bonus points for badges, links, code examples
            if any(badge in content for badge in ["![", "https://img.shields.io", "badge"]):
                score += 10
            if "```" in content or "    " in content:  # Code blocks
                score += 10
            if content.count("http") > 2:  # Multiple links
                score += 5

            return min(score, 100)
        except Exception:
            return 0

    def _calculate_comment_ratio(self, repo_path: Path) -> float:
        """Calculate the ratio of comments to code lines."""
        total_lines = 0
        comment_lines = 0

        comment_patterns = {
            ".py": [r"^\s*#", r'^\s*"""', r"^\s*\'\'\'"],
            ".js": [r"^\s*//", r"^\s*/\*", r"^\s*\*"],
            ".java": [r"^\s*//", r"^\s*/\*", r"^\s*\*"],
            ".cpp": [r"^\s*//", r"^\s*/\*", r"^\s*\*"],
            ".c": [r"^\s*//", r"^\s*/\*", r"^\s*\*"],
        }

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in comment_patterns:
                    try:
                        file_path = os.path.join(root, file)
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            for file_line in f:
                                line = file_line.strip()
                                if line:
                                    total_lines += 1
                                    if any(
                                        re.match(pattern, line) for pattern in comment_patterns[ext]
                                    ):
                                        comment_lines += 1
                    except Exception:
                        pass

        return comment_lines / total_lines if total_lines > 0 else 0.0

    def _assess_community_health(self, repo_path: Path) -> Dict[str, Any]:
        """Assess community health indicators."""
        community = {
            "contributing_guidelines": False,
            "code_of_conduct": False,
            "security_policy": False,
            "issue_templates": False,
            "pr_templates": False,
            "community_files": [],
            "github_features": [],
        }

        # Check for community files
        for community_file in self.community_files:
            file_path = repo_path / community_file
            if file_path.exists():
                community["community_files"].append(community_file)

                if "CONTRIBUTING" in community_file.upper():
                    community["contributing_guidelines"] = True
                elif "CODE_OF_CONDUCT" in community_file.upper():
                    community["code_of_conduct"] = True
                elif "SECURITY" in community_file.upper():
                    community["security_policy"] = True
                elif "ISSUE_TEMPLATE" in community_file.upper():
                    community["issue_templates"] = True
                elif "PULL_REQUEST_TEMPLATE" in community_file.upper():
                    community["pr_templates"] = True

        # Check for GitHub-specific features
        github_dir = repo_path / ".github"
        if github_dir.exists():
            community["github_features"] = [
                f
                for f in os.listdir(github_dir)
                if os.path.isfile(github_dir / f) or os.path.isdir(github_dir / f)
            ]

        return community

    def _assess_security(self, repo_path: Path) -> Dict[str, Any]:
        """Assess security practices and potential issues."""
        security = {
            "security_policy_exists": False,
            "dependency_lock_files": [],
            "secrets_found": [],
            "security_workflows": [],
            "gitignore_exists": False,
            "security_score": 0,
        }

        # Check for security policy
        security_files = ["SECURITY.md", ".github/SECURITY.md"]
        for sec_file in security_files:
            if (repo_path / sec_file).exists():
                security["security_policy_exists"] = True
                break

        # Check for dependency lock files
        lock_files = [
            "package-lock.json",
            "yarn.lock",
            "Pipfile.lock",
            "Cargo.lock",
            "Gemfile.lock",
        ]
        for lock_file in lock_files:
            if (repo_path / lock_file).exists():
                security["dependency_lock_files"].append(lock_file)

        # Check for .gitignore
        if (repo_path / ".gitignore").exists():
            security["gitignore_exists"] = True

        # Scan for potential secrets (basic patterns)
        security["secrets_found"] = self._scan_for_secrets(repo_path)

        # Check for security workflows
        workflows_dir = repo_path / ".github" / "workflows"
        if workflows_dir.exists():
            for workflow in workflows_dir.glob("*.yml"):
                with open(workflow, encoding="utf-8") as f:
                    content = f.read()
                    if any(
                        keyword in content.lower()
                        for keyword in ["security", "vulnerability", "dependabot"]
                    ):
                        security["security_workflows"].append(workflow.name)

        # Calculate security score
        security["security_score"] = self._calculate_security_score(security)

        return security

    def _scan_for_secrets(self, repo_path: Path) -> List[Dict[str, str]]:
        """Basic scan for potential secrets in code."""
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\']([^"\']+)', "API Key"),
            (r'password\s*[=:]\s*["\']([^"\']+)', "Password"),
            (r'secret[_-]?key\s*[=:]\s*["\']([^"\']+)', "Secret Key"),
            (r'token\s*[=:]\s*["\']([^"\']+)', "Token"),
            (r'["\'][A-Za-z0-9+/]{40,}["\']', "Base64 Encoded"),
        ]

        secrets = []

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith((".py", ".js", ".java", ".php", ".rb", ".go")):
                    try:
                        file_path = os.path.join(root, file)
                        with open(file_path, encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                            for pattern, secret_type in secret_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    if len(match) > 8:  # Filter out obvious non-secrets
                                        secrets.append(
                                            {
                                                "file": os.path.relpath(file_path, repo_path),
                                                "type": secret_type,
                                                "pattern": pattern,
                                            }
                                        )
                    except Exception:
                        pass

        return secrets[:10]  # Limit to first 10 findings

    def _calculate_security_score(self, security: Dict) -> int:
        """Calculate overall security score."""
        score = 0

        if security["security_policy_exists"]:
            score += 25
        if security["dependency_lock_files"]:
            score += 20
        if security["gitignore_exists"]:
            score += 15
        if security["security_workflows"]:
            score += 20
        if not security["secrets_found"]:
            score += 20

        return min(score, 100)

    def _analyze_ci_cd(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze CI/CD setup and automation."""
        ci_cd = {
            "github_actions": [],
            "other_ci": [],
            "has_automated_testing": False,
            "has_automated_deployment": False,
            "workflow_quality_score": 0,
        }

        # Check for GitHub Actions
        workflows_dir = repo_path / ".github" / "workflows"
        if workflows_dir.exists():
            for workflow in workflows_dir.glob("*.yml"):
                ci_cd["github_actions"].append(
                    {"name": workflow.name, "path": str(workflow.relative_to(repo_path))}
                )

                # Analyze workflow content
                try:
                    with open(workflow, encoding="utf-8") as f:
                        content = f.read()
                        if any(
                            keyword in content.lower()
                            for keyword in ["test", "pytest", "jest", "mvn test"]
                        ):
                            ci_cd["has_automated_testing"] = True
                        if any(
                            keyword in content.lower()
                            for keyword in ["deploy", "release", "publish"]
                        ):
                            ci_cd["has_automated_deployment"] = True
                except Exception:
                    pass

        # Check for other CI systems
        ci_files = [".travis.yml", ".circleci/config.yml", "appveyor.yml", "azure-pipelines.yml"]
        for ci_file in ci_files:
            if (repo_path / ci_file).exists():
                ci_cd["other_ci"].append(ci_file)

        # Calculate workflow quality score
        ci_cd["workflow_quality_score"] = self._calculate_workflow_score(ci_cd)

        return ci_cd

    def _calculate_workflow_score(self, ci_cd: Dict) -> int:
        """Calculate CI/CD workflow quality score."""
        score = 0

        if ci_cd["github_actions"] or ci_cd["other_ci"]:
            score += 30
        if ci_cd["has_automated_testing"]:
            score += 40
        if ci_cd["has_automated_deployment"]:
            score += 30

        return min(score, 100)

    def _extract_git_info(self, repo_path: Path) -> Dict[str, Any]:
        """Extract Git repository information."""
        git_info = {
            "is_git_repo": False,
            "branch_count": 0,
            "commit_count": 0,
            "contributors": 0,
            "last_commit": None,
            "repo_age_days": 0,
            "creation_date": None,
        }

        try:
            repo = git.Repo(repo_path)
            git_info["is_git_repo"] = True

            # Count branches
            git_info["branch_count"] = len(list(repo.branches))

            # Count commits (limit for performance on large repos)
            commits = list(repo.iter_commits(max_count=10000))
            git_info["commit_count"] = len(commits)

            # Get last commit
            if commits:
                last_commit = commits[0]  # Most recent commit
                git_info["last_commit"] = last_commit.committed_datetime.isoformat()

                # Calculate repo age using the oldest commit
                # Use reverse iteration to get the first commit efficiently
                try:
                    first_commit = next(repo.iter_commits(max_count=1, reverse=True))
                    creation_date = first_commit.committed_datetime.replace(tzinfo=None)
                    git_info["creation_date"] = creation_date.isoformat()

                    # Calculate age in days
                    age = datetime.now() - creation_date
                    git_info["repo_age_days"] = max(age.days, 0)  # Ensure non-negative

                except Exception as e:
                    # Fallback: use last commit if we can't get first commit
                    print(f"Warning: Could not determine repository creation date: {e}")
                    fallback_date = last_commit.committed_datetime.replace(tzinfo=None)
                    age = datetime.now() - fallback_date
                    git_info["repo_age_days"] = max(age.days, 0)

            # Count unique contributors (limit for performance)
            contributors = set()
            for commit in repo.iter_commits(max_count=5000):  # Limit to avoid performance issues
                if commit.author and commit.author.email:
                    contributors.add(commit.author.email)
            git_info["contributors"] = len(contributors)

        except Exception as e:
            print(f"Warning: Error extracting git info: {e}")

        return git_info

    def _analyze_files(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze individual files for patterns and quality indicators."""
        file_analysis = {
            "large_files": [],
            "empty_files": [],
            "test_files": 0,
            "config_files": 0,
            "todo_comments": 0,
            "fixme_comments": 0,
        }

        todo_pattern = re.compile(r"(TODO|FIXME|HACK|XXX)", re.IGNORECASE)

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                if file.startswith("."):
                    continue

                file_path = Path(root) / file
                relative_path = file_path.relative_to(repo_path)

                try:
                    # Check file size
                    size = file_path.stat().st_size
                    if size > 1024 * 1024:  # Files larger than 1MB
                        file_analysis["large_files"].append(
                            {"path": str(relative_path), "size_mb": round(size / (1024 * 1024), 2)}
                        )
                    elif size == 0:
                        file_analysis["empty_files"].append(str(relative_path))

                    # Count test files
                    if any(
                        pattern in file.lower() for pattern in ["test_", "_test", "spec_", "_spec"]
                    ):
                        file_analysis["test_files"] += 1

                    # Count config files
                    if any(
                        file.endswith(ext)
                        for ext in [".json", ".yml", ".yaml", ".toml", ".ini", ".cfg"]
                    ):
                        file_analysis["config_files"] += 1

                    # Scan for TODO/FIXME comments
                    if file.endswith((".py", ".js", ".java", ".cpp", ".c", ".go", ".rs")):
                        try:
                            with open(file_path, encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                todos = todo_pattern.findall(content)
                                file_analysis["todo_comments"] += todos.count("TODO")
                                file_analysis["fixme_comments"] += todos.count("FIXME")
                        except Exception:
                            pass

                except Exception:
                    pass

        return file_analysis
