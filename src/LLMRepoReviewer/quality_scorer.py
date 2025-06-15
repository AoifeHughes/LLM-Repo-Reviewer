"""
Quality scoring system for repository health assessment.

This module implements the comprehensive health scoring framework with weighted categories
and configurable standards for different programming languages and project types.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .repo_indexer import RepoIndexer


@dataclass
class HealthScores:
    """Container for repository health scores."""

    overall: int
    documentation: int
    testing: int
    security: int
    community: int
    legal: int
    ci_cd: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format."""
        return {
            "overall": self.overall,
            "documentation": self.documentation,
            "testing": self.testing,
            "security": self.security,
            "community": self.community,
            "legal": self.legal,
            "ci_cd": self.ci_cd,
        }


@dataclass
class HealthFindings:
    """Container for health assessment findings and recommendations."""

    critical: List[str]
    high: List[str]
    medium: List[str]
    low: List[str]

    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary format."""
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
        }


class QualityScorer:
    """
    Advanced quality scoring system for repository health assessment.

    Implements weighted scoring across six key categories:
    - Documentation Health (25%)
    - Testing & Code Quality (20%)
    - Security Posture (20%)
    - Community Health (15%)
    - Legal Compliance (10%)
    - CI/CD Maturity (10%)
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the quality scorer with optional custom configuration.

        Args:
            config_path: Path to custom configuration file
        """
        self.config = self._load_config(config_path)
        self.indexer = RepoIndexer()

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load scoring configuration."""
        default_config = {
            "scoring_weights": {
                "documentation": 0.25,
                "testing": 0.20,
                "security": 0.20,
                "community": 0.15,
                "legal": 0.10,
                "ci_cd": 0.10,
            },
            "minimum_thresholds": {
                "overall_health": 60,
                "security_score": 70,
                "documentation_score": 50,
            },
            "language_specific": {
                "python": {
                    "testing_frameworks": ["pytest", "unittest", "nose"],
                    "linting_tools": ["flake8", "black", "mypy", "pylint"],
                    "dependency_files": ["requirements.txt", "setup.py", "pyproject.toml"],
                    "package_manager": "pip",
                },
                "javascript": {
                    "testing_frameworks": ["jest", "mocha", "jasmine", "cypress"],
                    "linting_tools": ["eslint", "prettier", "jshint"],
                    "dependency_files": ["package.json", "yarn.lock"],
                    "package_manager": "npm",
                },
                "java": {
                    "testing_frameworks": ["junit", "testng", "mockito"],
                    "linting_tools": ["checkstyle", "spotbugs", "pmd"],
                    "dependency_files": ["pom.xml", "build.gradle"],
                    "package_manager": "maven",
                },
                "rust": {
                    "testing_frameworks": ["cargo test", "proptest"],
                    "linting_tools": ["clippy", "rustfmt"],
                    "dependency_files": ["Cargo.toml", "Cargo.lock"],
                    "package_manager": "cargo",
                },
            },
        }

        if config_path:
            try:
                with open(config_path) as f:
                    custom_config = json.load(f)
                    # Merge configs (custom overrides default)
                    self._deep_merge(default_config, custom_config)
            except Exception:
                pass  # Use default config if custom config fails to load

        return default_config

    def _deep_merge(self, base: Dict, overlay: Dict) -> None:
        """Deep merge overlay dictionary into base dictionary."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def calculate_health_scores(self, repo_metadata: Dict[str, Any]) -> HealthScores:
        """
        Calculate comprehensive health scores for a repository.

        Args:
            repo_metadata: Repository metadata from RepoIndexer

        Returns:
            HealthScores object with all category scores
        """
        scores = {
            "documentation": self._score_documentation(repo_metadata),
            "testing": self._score_testing_quality(repo_metadata),
            "security": self._score_security(repo_metadata),
            "community": self._score_community_health(repo_metadata),
            "legal": self._score_legal_compliance(repo_metadata),
            "ci_cd": self._score_ci_cd_maturity(repo_metadata),
        }

        # Calculate weighted overall score
        weights = self.config["scoring_weights"]
        overall = sum(scores[category] * weights[category] for category in scores)
        scores["overall"] = int(overall)

        return HealthScores(**scores)

    def _score_documentation(self, metadata: Dict[str, Any]) -> int:
        """Score documentation health (25% of overall score)."""
        doc_data = metadata.get("documentation", {})
        score = 0

        # README Quality (40% of documentation score)
        if doc_data.get("readme_exists", False):
            readme_score = doc_data.get("readme_quality_score", 0)
            score += readme_score * 0.4

        # API Documentation (30% of documentation score)
        if doc_data.get("api_docs_exists", False):
            score += 30

        # Project Documentation (20% of documentation score)
        doc_files = len(doc_data.get("documentation_files", []))
        if doc_files >= 3:
            score += 20
        elif doc_files >= 1:
            score += 10

        # Code Comments (10% of documentation score)
        comment_ratio = doc_data.get("code_comments_ratio", 0)
        if comment_ratio >= 0.15:
            score += 10
        elif comment_ratio >= 0.05:
            score += 5

        return min(int(score), 100)

    def _score_testing_quality(self, metadata: Dict[str, Any]) -> int:
        """Score testing and code quality (20% of overall score)."""
        score = 0

        # Test Coverage and Structure (60%)
        file_analysis = metadata.get("file_analysis", {})
        test_files = file_analysis.get("test_files", 0)
        total_files = metadata.get("structure", {}).get("total_files", 1)

        test_ratio = test_files / total_files if total_files > 0 else 0
        if test_ratio >= 0.3:
            score += 60
        elif test_ratio >= 0.1:
            score += 40
        elif test_ratio > 0:
            score += 20

        # Language-specific testing framework detection (25%)
        primary_lang = metadata.get("languages", {}).get("primary_language", "").lower()
        lang_config = self.config["language_specific"].get(primary_lang, {})
        testing_frameworks = lang_config.get("testing_frameworks", [])

        if self._has_testing_framework(metadata, testing_frameworks):
            score += 25

        # Code Quality Indicators (15%)
        todo_count = file_analysis.get("todo_comments", 0)
        fixme_count = file_analysis.get("fixme_comments", 0)

        # Lower TODO/FIXME counts indicate better code quality
        quality_issues = todo_count + fixme_count
        if quality_issues == 0:
            score += 15
        elif quality_issues <= 5:
            score += 10
        elif quality_issues <= 20:
            score += 5

        return min(int(score), 100)

    def _score_security(self, metadata: Dict[str, Any]) -> int:
        """Score security posture (20% of overall score)."""
        security_data = metadata.get("security", {})
        score = 0

        # Security Policy (25%)
        if security_data.get("security_policy_exists", False):
            score += 25

        # Dependency Management (25%)
        lock_files = security_data.get("dependency_lock_files", [])
        if lock_files:
            score += 25

        # Secrets Scanning (20%)
        secrets_found = len(security_data.get("secrets_found", []))
        if secrets_found == 0:
            score += 20
        elif secrets_found <= 2:
            score += 10

        # Security Workflows (15%)
        security_workflows = security_data.get("security_workflows", [])
        if security_workflows:
            score += 15

        # Basic Security Practices (15%)
        if security_data.get("gitignore_exists", False):
            score += 15

        return min(int(score), 100)

    def _score_community_health(self, metadata: Dict[str, Any]) -> int:
        """Score community health (15% of overall score)."""
        community_data = metadata.get("community", {})
        score = 0

        # Contributing Guidelines (30%)
        if community_data.get("contributing_guidelines", False):
            score += 30

        # Code of Conduct (25%)
        if community_data.get("code_of_conduct", False):
            score += 25

        # Issue and PR Templates (25%)
        if community_data.get("issue_templates", False):
            score += 15
        if community_data.get("pr_templates", False):
            score += 10

        # GitHub Features (20%)
        github_features = len(community_data.get("github_features", []))
        if github_features >= 3:
            score += 20
        elif github_features >= 1:
            score += 10

        return min(int(score), 100)

    def _score_legal_compliance(self, metadata: Dict[str, Any]) -> int:
        """Score legal compliance (10% of overall score)."""
        score = 0

        # License File (70%)
        doc_files = metadata.get("documentation", {}).get("documentation_files", [])
        has_license = any("LICENSE" in f.upper() or "COPYING" in f.upper() for f in doc_files)
        if has_license:
            score += 70

        # Attribution and Copyright (30%)
        # Check for copyright notices in common files
        if self._has_copyright_notices(metadata):
            score += 30

        return min(int(score), 100)

    def _score_ci_cd_maturity(self, metadata: Dict[str, Any]) -> int:
        """Score CI/CD maturity (10% of overall score)."""
        ci_cd_data = metadata.get("ci_cd", {})
        score = 0

        # Automated Testing (50%)
        if ci_cd_data.get("has_automated_testing", False):
            score += 50

        # CI/CD Setup (30%)
        github_actions = len(ci_cd_data.get("github_actions", []))
        other_ci = len(ci_cd_data.get("other_ci", []))
        if github_actions > 0 or other_ci > 0:
            score += 30

        # Automated Deployment (20%)
        if ci_cd_data.get("has_automated_deployment", False):
            score += 20

        return min(int(score), 100)

    def _has_testing_framework(self, metadata: Dict[str, Any], frameworks: List[str]) -> bool:
        """Check if repository uses any of the specified testing frameworks."""
        # Check dependency files for testing frameworks
        dependency_files = metadata.get("dependencies", {}).get("dependency_files", [])

        for dep_file in dependency_files:
            if any(framework.lower() in dep_file.lower() for framework in frameworks):
                return True

        # Check for test file patterns
        file_analysis = metadata.get("file_analysis", {})
        return file_analysis.get("test_files", 0) > 0

    def _has_copyright_notices(self, metadata: Dict[str, Any]) -> bool:
        """Check for copyright notices in repository."""
        # Simple heuristic based on common copyright indicators
        doc_files = metadata.get("documentation", {}).get("documentation_files", [])
        return len(doc_files) >= 2  # Assume projects with multiple docs have proper attribution

    def generate_findings(self, metadata: Dict[str, Any], scores: HealthScores) -> HealthFindings:
        """
        Generate findings and recommendations based on health assessment.

        Args:
            metadata: Repository metadata
            scores: Calculated health scores

        Returns:
            HealthFindings with categorized issues and recommendations
        """
        findings = HealthFindings(critical=[], high=[], medium=[], low=[])

        # Critical findings (show-stoppers)
        if scores.security < 50:
            findings.critical.append("Security score critically low - immediate attention required")

        if not metadata.get("documentation", {}).get("readme_exists", False):
            findings.critical.append("Missing README file")

        # High priority findings
        if scores.security < 70:
            if not metadata.get("security", {}).get("security_policy_exists", False):
                findings.high.append("Missing SECURITY.md file")

            secrets = metadata.get("security", {}).get("secrets_found", [])
            if secrets:
                findings.high.append(f"Found {len(secrets)} potential secrets in code")

        if scores.testing < 40:
            findings.high.append("Test coverage appears low - consider adding more tests")

        if not metadata.get("community", {}).get("contributing_guidelines", False):
            findings.high.append("Missing CONTRIBUTING.md guidelines")

        # Medium priority findings
        if scores.documentation < 70:
            if not metadata.get("documentation", {}).get("api_docs_exists", False):
                findings.medium.append("Consider adding API documentation")

            comment_ratio = metadata.get("documentation", {}).get("code_comments_ratio", 0)
            if comment_ratio < 0.1:
                findings.medium.append(
                    "Code comment ratio is low - consider adding more documentation"
                )

        if not metadata.get("community", {}).get("code_of_conduct", False):
            findings.medium.append("Missing CODE_OF_CONDUCT.md file")

        if not metadata.get("ci_cd", {}).get("has_automated_testing", False):
            findings.medium.append("No automated testing detected in CI/CD")

        # Low priority findings
        if not metadata.get("community", {}).get("issue_templates", False):
            findings.low.append("Consider adding GitHub issue templates")

        if not metadata.get("community", {}).get("pr_templates", False):
            findings.low.append("Consider adding GitHub pull request templates")

        todo_count = metadata.get("file_analysis", {}).get("todo_comments", 0)
        if todo_count > 10:
            findings.low.append(f"Found {todo_count} TODO comments - consider addressing them")

        large_files = metadata.get("file_analysis", {}).get("large_files", [])
        if large_files:
            findings.low.append(f"Found {len(large_files)} large files - consider optimization")

        return findings

    def generate_recommendations(
        self, metadata: Dict[str, Any], scores: HealthScores, findings: HealthFindings
    ) -> List[Dict[str, str]]:
        """
        Generate actionable recommendations for improving repository health.

        Args:
            metadata: Repository metadata
            scores: Health scores
            findings: Assessment findings

        Returns:
            List of recommendation dictionaries with category, priority, title, and description
        """
        recommendations = []

        # Security recommendations
        if scores.security < 80:
            if not metadata.get("security", {}).get("security_policy_exists", False):
                recommendations.append(
                    {
                        "category": "security",
                        "priority": "high",
                        "title": "Add Security Policy",
                        "description": "Create SECURITY.md with vulnerability reporting process",
                        "template_available": True,
                    }
                )

            if not metadata.get("security", {}).get("dependency_lock_files"):
                recommendations.append(
                    {
                        "category": "security",
                        "priority": "medium",
                        "title": "Add Dependency Lock Files",
                        "description": "Use lock files to ensure reproducible builds and security",
                        "template_available": False,
                    }
                )

        # Documentation recommendations
        if scores.documentation < 80:
            readme_score = metadata.get("documentation", {}).get("readme_quality_score", 0)
            if readme_score < 70:
                recommendations.append(
                    {
                        "category": "documentation",
                        "priority": "high",
                        "title": "Improve README Quality",
                        "description": "Add missing sections: installation, usage, contributing guidelines",
                        "template_available": True,
                    }
                )

            if not metadata.get("documentation", {}).get("api_docs_exists", False):
                recommendations.append(
                    {
                        "category": "documentation",
                        "priority": "medium",
                        "title": "Add API Documentation",
                        "description": "Create comprehensive API documentation for better usability",
                        "template_available": True,
                    }
                )

        # Testing recommendations
        if scores.testing < 70:
            test_files = metadata.get("file_analysis", {}).get("test_files", 0)
            if test_files == 0:
                recommendations.append(
                    {
                        "category": "testing",
                        "priority": "high",
                        "title": "Add Test Suite",
                        "description": "Implement comprehensive test coverage for code reliability",
                        "template_available": True,
                    }
                )
            else:
                recommendations.append(
                    {
                        "category": "testing",
                        "priority": "medium",
                        "title": "Improve Test Coverage",
                        "description": "Increase test coverage to 80%+ for better code quality",
                        "template_available": False,
                    }
                )

        # Community recommendations
        if scores.community < 70:
            if not metadata.get("community", {}).get("contributing_guidelines", False):
                recommendations.append(
                    {
                        "category": "community",
                        "priority": "medium",
                        "title": "Add Contributing Guidelines",
                        "description": "Create CONTRIBUTING.md to help new contributors",
                        "template_available": True,
                    }
                )

            if not metadata.get("community", {}).get("code_of_conduct", False):
                recommendations.append(
                    {
                        "category": "community",
                        "priority": "low",
                        "title": "Add Code of Conduct",
                        "description": "Establish community standards with CODE_OF_CONDUCT.md",
                        "template_available": True,
                    }
                )

        # CI/CD recommendations
        if scores.ci_cd < 60 and not metadata.get("ci_cd", {}).get("has_automated_testing", False):
            recommendations.append(
                {
                    "category": "ci_cd",
                    "priority": "medium",
                    "title": "Add Automated Testing",
                    "description": "Set up CI/CD pipeline with automated test execution",
                    "template_available": True,
                }
            )

        return recommendations

    def compare_repositories(self, repo_scores: List[Tuple[str, HealthScores]]) -> Dict[str, Any]:
        """
        Compare multiple repositories and provide benchmarking insights.

        Args:
            repo_scores: List of (repo_name, scores) tuples

        Returns:
            Comparison analysis with rankings and insights
        """
        if not repo_scores:
            return {}

        comparison = {
            "repository_count": len(repo_scores),
            "rankings": {"overall": [], "by_category": {}},
            "averages": {},
            "insights": [],
        }

        # Calculate rankings
        overall_ranking = sorted(repo_scores, key=lambda x: x[1].overall, reverse=True)
        comparison["rankings"]["overall"] = [
            {"repo": name, "score": scores.overall} for name, scores in overall_ranking
        ]

        # Category rankings
        categories = ["documentation", "testing", "security", "community", "legal", "ci_cd"]
        for category in categories:
            category_ranking = sorted(
                repo_scores, key=lambda x: getattr(x[1], category), reverse=True
            )
            comparison["rankings"]["by_category"][category] = [
                {"repo": name, "score": getattr(scores, category)}
                for name, scores in category_ranking
            ]

        # Calculate averages
        all_scores = [scores for _, scores in repo_scores]
        comparison["averages"] = {
            "overall": sum(s.overall for s in all_scores) / len(all_scores),
            "documentation": sum(s.documentation for s in all_scores) / len(all_scores),
            "testing": sum(s.testing for s in all_scores) / len(all_scores),
            "security": sum(s.security for s in all_scores) / len(all_scores),
            "community": sum(s.community for s in all_scores) / len(all_scores),
            "legal": sum(s.legal for s in all_scores) / len(all_scores),
            "ci_cd": sum(s.ci_cd for s in all_scores) / len(all_scores),
        }

        # Generate insights
        avg_overall = comparison["averages"]["overall"]
        if avg_overall < 60:
            comparison["insights"].append(
                "Overall repository health is below recommended threshold"
            )

        avg_security = comparison["averages"]["security"]
        if avg_security < 70:
            comparison["insights"].append("Security practices need improvement across repositories")

        # Find best and worst performing categories
        category_avgs = {k: v for k, v in comparison["averages"].items() if k != "overall"}
        best_category = max(category_avgs, key=category_avgs.get)
        worst_category = min(category_avgs, key=category_avgs.get)

        comparison["insights"].extend(
            [
                f"Strongest area: {best_category} (avg: {category_avgs[best_category]:.1f})",
                f"Weakest area: {worst_category} (avg: {category_avgs[worst_category]:.1f})",
            ]
        )

        return comparison
