"""
Repository classification system for context-aware health scoring.

This module classifies repositories into different types to enable dynamic
scoring weights based on the project's purpose and security requirements.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .repo_indexer import RepoIndexer


class RepositoryType(Enum):
    """Repository classification categories."""

    HIGH_SECURITY = "high_security"  # Web apps, APIs, auth systems, financial
    MEDIUM_SECURITY = "medium_security"  # Libraries, CLI tools, desktop apps
    LOW_SECURITY = "low_security"  # Documentation, tutorials, demos
    RESEARCH = "research"  # Academic papers, datasets, experiments
    UNKNOWN = "unknown"  # Cannot determine type


class RepositoryClassifier:
    """
    Intelligent repository type classifier.

    Uses multiple strategies to determine repository type:
    1. File pattern analysis (frameworks, configs, content types)
    2. Dependency analysis (security-relevant packages)
    3. README/description analysis
    4. Project structure patterns
    """

    def __init__(self):
        self.indexer = RepoIndexer()

        # High-security indicators
        self.high_security_patterns = {
            "web_frameworks": [
                "django",
                "flask",
                "fastapi",
                "express",
                "koa",
                "nest",
                "spring-boot",
                "rails",
                "laravel",
                "symfony",
                "sinatra",
            ],
            "auth_systems": [
                "passport",
                "oauth",
                "jwt",
                "auth0",
                "keycloak",
                "okta",
                "authentication",
                "authorization",
                "login",
                "session",
            ],
            "databases": [
                "postgresql",
                "mysql",
                "mongodb",
                "redis",
                "elasticsearch",
                "database",
                "db",
                "sql",
                "nosql",
            ],
            "payment_systems": [
                "stripe",
                "paypal",
                "payment",
                "billing",
                "checkout",
                "commerce",
                "transaction",
                "financial",
            ],
            "file_patterns": [
                "**/models.py",
                "**/views.py",
                "**/routes.py",
                "**/controllers.py",
                "**/middleware.py",
                "**/auth.py",
                "**/login.py",
                "**/session.py",
                "**/*auth*",
                "**/*login*",
                "**/*session*",
                "**/*security*",
            ],
            "config_files": [
                "docker-compose.yml",
                "Dockerfile",
                "kubernetes",
                "helm",
                "nginx.conf",
                "apache.conf",
                ".env.example",
            ],
        }

        # Medium-security indicators
        self.medium_security_patterns = {
            "library_indicators": [
                "setup.py",
                "pyproject.toml",
                "package.json",
                "Cargo.toml",
                "pom.xml",
                "build.gradle",
                "gemspec",
                "composer.json",
            ],
            "cli_patterns": [
                "bin/",
                "scripts/",
                "cli.py",
                "main.py",
                "__main__.py",
                "command",
                "cli",
                "tool",
                "utility",
            ],
            "desktop_frameworks": [
                "electron",
                "tkinter",
                "qt",
                "gtk",
                "swing",
                "javafx",
                "wpf",
                "winforms",
                "kivy",
                "fltk",
            ],
        }

        # Low-security indicators
        self.low_security_patterns = {
            "documentation": [
                "docs/",
                "documentation/",
                "wiki/",
                "book/",
                "guide/",
                "tutorial",
                "example",
                "demo",
                "sample",
                "getting-started",
            ],
            "static_sites": [
                "jekyll",
                "hugo",
                "gatsby",
                "next.js",
                "nuxt",
                "vuepress",
                "gitbook",
                "mkdocs",
                "sphinx",
                "docusaurus",
            ],
            "file_types": [".md", ".rst", ".txt", ".html", ".css", ".pdf"],
        }

        # Research indicators
        self.research_patterns = {
            "academic_files": [
                "paper.pdf",
                "manuscript.pdf",
                "thesis.pdf",
                "dissertation.pdf",
                "requirements.txt",
                "environment.yml",
                "conda.yaml",
                "Manifest.toml",
            ],
            "data_science": [
                "jupyter",
                "notebook",
                "pandas",
                "numpy",
                "scipy",
                "matplotlib",
                "sklearn",
                "tensorflow",
                "pytorch",
                "dataset",
                "analysis",
            ],
            "research_keywords": [
                "research",
                "academic",
                "paper",
                "study",
                "experiment",
                "analysis",
                "dataset",
                "benchmark",
                "evaluation",
                "probabilistic",
                "bayesian",
                "inference",
                "mcmc",
                "statistical",
                "modeling",
                "simulation",
                "algorithm",
                "optimization",
            ],
            "julia_research": [
                "mcmc",
                "probabilistic",
                "bayesian",
                "turing",
                "dynamicppl",
                "hamiltonian",
                "monte carlo",
                "gibbs",
                "nuts",
                "sampling",
                "inference",
                "distributions",
                "flux",
                "mlj",
                "juliastats",
            ],
            "academic_domains": [
                "bioinformatics",
                "computational",
                "numerical",
                "scientific",
                "machine learning",
                "statistics",
                "optimization",
                "physics",
                "mathematics",
                "biology",
                "chemistry",
                "astronomy",
                "economics",
            ],
        }

    def classify_repository(
        self, repo_path: str, repo_metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Classify repository type and return classification details.

        Args:
            repo_path: Path to repository
            repo_metadata: Optional pre-computed repository metadata

        Returns:
            Dictionary with classification results and confidence scores
        """
        if not repo_metadata:
            repo_metadata = self.indexer.index_repository(repo_path)

        scores = {
            RepositoryType.HIGH_SECURITY: 0,
            RepositoryType.MEDIUM_SECURITY: 0,
            RepositoryType.LOW_SECURITY: 0,
            RepositoryType.RESEARCH: 0,
        }

        # File pattern analysis
        file_scores = self._analyze_file_patterns(Path(repo_path))
        for repo_type, score in file_scores.items():
            scores[repo_type] += score

        # Dependency analysis
        dep_scores = self._analyze_dependencies(repo_metadata)
        for repo_type, score in dep_scores.items():
            scores[repo_type] += score

        # Project structure analysis
        structure_scores = self._analyze_structure(repo_metadata)
        for repo_type, score in structure_scores.items():
            scores[repo_type] += score

        # README/description analysis
        readme_scores = self._analyze_readme(repo_path)
        for repo_type, score in readme_scores.items():
            scores[repo_type] += score

        # Determine final classification
        max_score = max(scores.values())
        if max_score == 0:
            final_type = RepositoryType.UNKNOWN
            confidence = 0.0
        else:
            final_type = max(scores, key=scores.get)
            confidence = max_score / (sum(scores.values()) or 1)

        return {
            "type": final_type,
            "confidence": confidence,
            "scores": {t.value: s for t, s in scores.items()},
            "reasoning": self._generate_reasoning(scores, repo_metadata),
        }

    def _analyze_file_patterns(self, repo_path: Path) -> Dict[RepositoryType, float]:
        """Analyze file patterns to determine repository type."""
        scores = {t: 0.0 for t in RepositoryType if t != RepositoryType.UNKNOWN}

        # Check for high-security file patterns
        for pattern in self.high_security_patterns["file_patterns"]:
            if list(repo_path.glob(pattern)):
                scores[RepositoryType.HIGH_SECURITY] += 2.0

        # Check for config files indicating web applications
        for config_file in self.high_security_patterns["config_files"]:
            if (repo_path / config_file).exists():
                scores[RepositoryType.HIGH_SECURITY] += 1.5

        # Check for library package files
        for lib_file in self.medium_security_patterns["library_indicators"]:
            if (repo_path / lib_file).exists():
                scores[RepositoryType.MEDIUM_SECURITY] += 1.0

        # Check for documentation patterns
        for doc_pattern in self.low_security_patterns["documentation"]:
            if list(repo_path.glob(f"**/{doc_pattern}")):
                scores[RepositoryType.LOW_SECURITY] += 1.0

        # Check for research files
        for research_file in self.research_patterns["academic_files"]:
            if list(repo_path.glob(f"**/{research_file}")):
                scores[RepositoryType.RESEARCH] += 2.0

        return scores

    def _analyze_dependencies(self, repo_metadata: Dict) -> Dict[RepositoryType, float]:
        """Analyze dependencies to determine repository type."""
        scores = {t: 0.0 for t in RepositoryType if t != RepositoryType.UNKNOWN}

        dependencies = repo_metadata.get("dependencies", {})
        dep_files = dependencies.get("dependency_files", [])

        # Analyze dependency file contents for frameworks and libraries
        for dep_file in dep_files:
            dep_content = self._read_dependency_file(dep_file)
            if not dep_content:
                continue

            # Check for high-security frameworks
            for framework in self.high_security_patterns["web_frameworks"]:
                if framework in dep_content.lower():
                    scores[RepositoryType.HIGH_SECURITY] += 2.0

            for auth in self.high_security_patterns["auth_systems"]:
                if auth in dep_content.lower():
                    scores[RepositoryType.HIGH_SECURITY] += 1.5

            for db in self.high_security_patterns["databases"]:
                if db in dep_content.lower():
                    scores[RepositoryType.HIGH_SECURITY] += 1.0

            # Check for desktop frameworks
            for desktop in self.medium_security_patterns["desktop_frameworks"]:
                if desktop in dep_content.lower():
                    scores[RepositoryType.MEDIUM_SECURITY] += 1.5

            # Check for data science libraries
            for ds_lib in self.research_patterns["data_science"]:
                if ds_lib in dep_content.lower():
                    scores[RepositoryType.RESEARCH] += 1.0

            # Check for Julia research/scientific packages
            for julia_lib in self.research_patterns["julia_research"]:
                if julia_lib in dep_content.lower():
                    scores[RepositoryType.RESEARCH] += 2.0  # Higher weight for Julia research

        return scores

    def _analyze_structure(self, repo_metadata: Dict) -> Dict[RepositoryType, float]:
        """Analyze repository structure patterns."""
        scores = {t: 0.0 for t in RepositoryType if t != RepositoryType.UNKNOWN}

        # Analyze primary language
        languages = repo_metadata.get("languages", {})
        primary_lang = languages.get("primary_language", "").lower()

        # Web-oriented languages suggest higher security needs
        if primary_lang in ["javascript", "typescript", "php", "python", "java", "c#"]:
            scores[RepositoryType.HIGH_SECURITY] += 0.5

        # Documentation languages suggest lower security needs
        if primary_lang in ["markdown", "html", "css"]:
            scores[RepositoryType.LOW_SECURITY] += 2.0

        # Scientific languages suggest research
        if primary_lang in ["r", "matlab", "julia", "fortran"]:
            scores[RepositoryType.RESEARCH] += 1.5

        # Analyze file distribution
        structure = repo_metadata.get("structure", {})
        file_dist = structure.get("file_distribution", {})

        # High proportion of documentation files
        doc_files = file_dist.get(".md", 0) + file_dist.get(".rst", 0) + file_dist.get(".txt", 0)
        total_files = sum(file_dist.values()) or 1
        doc_ratio = doc_files / total_files

        if doc_ratio > 0.5:
            scores[RepositoryType.LOW_SECURITY] += 2.0
        elif doc_ratio > 0.3:
            scores[RepositoryType.LOW_SECURITY] += 1.0

        return scores

    def _analyze_readme(self, repo_path: str) -> Dict[RepositoryType, float]:
        """Analyze README content for classification clues."""
        scores = {t: 0.0 for t in RepositoryType if t != RepositoryType.UNKNOWN}

        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        readme_content = ""

        for readme_file in readme_files:
            readme_path = Path(repo_path) / readme_file
            if readme_path.exists():
                try:
                    with open(readme_path, encoding="utf-8", errors="ignore") as f:
                        readme_content = f.read().lower()
                    break
                except Exception:
                    continue

        if not readme_content:
            return scores

        # Search for security-relevant keywords
        for keyword in self.high_security_patterns["auth_systems"]:
            if keyword in readme_content:
                scores[RepositoryType.HIGH_SECURITY] += 1.0

        for keyword in self.high_security_patterns["payment_systems"]:
            if keyword in readme_content:
                scores[RepositoryType.HIGH_SECURITY] += 2.0

        # Search for documentation/tutorial keywords
        doc_keywords = ["tutorial", "guide", "documentation", "example", "demo", "learning"]
        for keyword in doc_keywords:
            if keyword in readme_content:
                scores[RepositoryType.LOW_SECURITY] += 0.5

        # Search for research keywords
        for keyword in self.research_patterns["research_keywords"]:
            if keyword in readme_content:
                scores[RepositoryType.RESEARCH] += 1.0

        # Search for Julia research specific terms
        for keyword in self.research_patterns["julia_research"]:
            if keyword in readme_content:
                scores[RepositoryType.RESEARCH] += 1.5

        # Search for academic domain keywords
        for keyword in self.research_patterns["academic_domains"]:
            if keyword in readme_content:
                scores[RepositoryType.RESEARCH] += 0.8

        return scores

    def _read_dependency_file(self, file_path: str) -> Optional[str]:
        """Read and return contents of a dependency file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None

    def _generate_reasoning(
        self, scores: Dict[RepositoryType, float], repo_metadata: Dict
    ) -> List[str]:
        """Generate human-readable reasoning for classification."""
        reasoning = []

        # Get the top scoring categories
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        primary_lang = repo_metadata.get("languages", {}).get("primary_language", "Unknown")

        reasoning.append(f"Primary language: {primary_lang}")

        for repo_type, score in sorted_scores[:2]:  # Top 2 scores
            if score > 0:
                if repo_type == RepositoryType.HIGH_SECURITY:
                    reasoning.append(
                        f"High security score ({score:.1f}): Web frameworks, auth systems, or databases detected"
                    )
                elif repo_type == RepositoryType.MEDIUM_SECURITY:
                    reasoning.append(
                        f"Medium security score ({score:.1f}): Library or CLI tool patterns detected"
                    )
                elif repo_type == RepositoryType.LOW_SECURITY:
                    reasoning.append(
                        f"Low security score ({score:.1f}): Documentation or tutorial patterns detected"
                    )
                elif repo_type == RepositoryType.RESEARCH:
                    reasoning.append(
                        f"Research score ({score:.1f}): Academic or data science patterns detected"
                    )

        return reasoning

    def get_security_weight(self, repo_type: RepositoryType, confidence: float) -> float:
        """
        Get appropriate security weight for repository type.

        Args:
            repo_type: Classified repository type
            confidence: Classification confidence (0.0-1.0)

        Returns:
            Security weight (0.0-1.0)
        """
        base_weights = {
            RepositoryType.HIGH_SECURITY: 0.30,  # 30% - Very important
            RepositoryType.MEDIUM_SECURITY: 0.20,  # 20% - Standard (current default)
            RepositoryType.LOW_SECURITY: 0.08,  # 8% - Less critical
            RepositoryType.RESEARCH: 0.05,  # 5% - Minimal importance
            RepositoryType.UNKNOWN: 0.20,  # 20% - Conservative default
        }

        base_weight = base_weights[repo_type]

        # Adjust based on confidence - be more aggressive for high confidence research/low security
        if confidence < 0.3:
            # Low confidence, be conservative (closer to default)
            return 0.18
        if confidence < 0.6:
            # Medium confidence, blend with default
            return (base_weight + 0.18) / 2
        # High confidence, use full weight
        # For research projects with high confidence, be very aggressive
        if repo_type == RepositoryType.RESEARCH and confidence > 0.8:
            return 0.03  # Very low security weight for high-confidence research
        return base_weight

    def get_adjusted_weights(
        self, repo_type: RepositoryType, confidence: float
    ) -> Dict[str, float]:
        """
        Get full set of adjusted weights for repository type.

        Args:
            repo_type: Classified repository type
            confidence: Classification confidence (0.0-1.0)

        Returns:
            Dictionary of category weights that sum to 1.0
        """
        security_weight = self.get_security_weight(repo_type, confidence)

        # Adjust other weights to compensate
        remaining_weight = 1.0 - security_weight

        # Base weights for other categories
        if repo_type == RepositoryType.LOW_SECURITY or repo_type == RepositoryType.RESEARCH:
            # Documentation and academic repos - emphasize documentation and community
            base_non_security = remaining_weight
            weights = {
                "documentation": base_non_security * 0.40,  # 40% of remaining weight
                "testing": base_non_security * 0.15,  # 15% of remaining weight
                "security": security_weight,
                "community": base_non_security
                * 0.25,  # 25% of remaining weight (for research activity)
                "legal": base_non_security * 0.10,  # 10% of remaining weight
                "ci_cd": base_non_security * 0.10,  # 10% of remaining weight
            }
        else:
            # High/medium security - standard distribution with adjusted security
            base_total = 0.25 + 0.20 + 0.15 + 0.10 + 0.10  # Original weights minus security
            scale_factor = remaining_weight / base_total

            weights = {
                "documentation": 0.25 * scale_factor,
                "testing": 0.20 * scale_factor,
                "security": security_weight,
                "community": 0.15 * scale_factor,
                "legal": 0.10 * scale_factor,
                "ci_cd": 0.10 * scale_factor,
            }

        # Ensure weights sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:  # Small tolerance for floating point
            # Adjust the largest non-security weight to make total = 1.0
            largest_key = max((k for k in weights if k != "security"), key=lambda k: weights[k])
            weights[largest_key] += 1.0 - total

        return weights
