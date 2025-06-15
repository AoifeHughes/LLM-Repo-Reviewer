"""
Health analysis tools for LLM integration.

This module provides tool functions that can be called by the LLM to perform
repository health analysis, generate missing files, and provide recommendations.
"""

from typing import Any, Dict, List

from ..quality_scorer import QualityScorer
from ..repo_editor import RepoEditor
from ..repo_indexer import RepoIndexer
from ..template_manager import TemplateManager
from .base import BaseTool


class AnalyzeRepositoryHealthTool(BaseTool):
    """Tool to analyze repository health and generate scores."""

    name = "analyze_repository_health"
    description = "Perform comprehensive health analysis of a repository and return detailed scores"

    def __init__(self):
        self.indexer = RepoIndexer()
        self.scorer = QualityScorer()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to the repository to analyze"},
                "analysis_depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Depth of analysis to perform",
                    "default": "standard",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to focus on (documentation, security, testing, etc.)",
                    "default": [],
                },
            },
            "required": ["repo_path"],
        }

    def execute(self, **kwargs) -> str:
        """Execute repository health analysis."""
        repo_path = kwargs.get("repo_path", ".")
        analysis_depth = kwargs.get("analysis_depth", "standard")
        focus_areas = kwargs.get("focus_areas", [])

        try:
            # Index repository metadata
            repo_metadata = self.indexer.index_repository(repo_path)

            # Calculate health scores
            health_scores = self.scorer.calculate_health_scores(repo_metadata)

            # Generate findings and recommendations
            findings = self.scorer.generate_findings(repo_metadata, health_scores)
            recommendations = self.scorer.generate_recommendations(
                repo_metadata, health_scores, findings
            )

            # Filter recommendations by focus areas if specified
            if focus_areas:
                recommendations = [
                    rec for rec in recommendations if rec.get("category") in focus_areas
                ]

            # Prepare summary based on analysis depth
            if analysis_depth == "quick":
                return self._format_quick_summary(health_scores, findings)
            if analysis_depth == "deep":
                return self._format_deep_analysis(
                    health_scores, findings, recommendations, repo_metadata
                )
            return self._format_standard_analysis(health_scores, findings, recommendations)

        except Exception as e:
            return f"Error analyzing repository health: {e!s}"

    def _format_quick_summary(self, health_scores, findings) -> str:
        """Format quick health summary."""
        grade = self._calculate_grade(health_scores.overall)
        critical_count = len(findings.critical)
        high_count = len(findings.high)

        summary = f"**Repository Health Score: {health_scores.overall}/100 ({grade})**\n\n"
        summary += f"- Critical Issues: {critical_count}\n"
        summary += f"- High Priority Issues: {high_count}\n"
        summary += f"- Security Score: {health_scores.security}/100\n"
        summary += f"- Documentation Score: {health_scores.documentation}/100\n"
        summary += f"- Testing Score: {health_scores.testing}/100\n"

        if critical_count > 0:
            summary += "\n⚠️ **Critical Issues:**\n"
            for issue in findings.critical:
                summary += f"- {issue}\n"

        return summary

    def _format_standard_analysis(self, health_scores, findings, recommendations) -> str:
        """Format standard health analysis."""
        grade = self._calculate_grade(health_scores.overall)

        analysis = "# Repository Health Analysis\n\n"
        analysis += f"**Overall Score: {health_scores.overall}/100 ({grade})**\n\n"

        # Scores breakdown
        analysis += "## Health Scores\n\n"
        analysis += f"- **Documentation**: {health_scores.documentation}/100\n"
        analysis += f"- **Testing & Quality**: {health_scores.testing}/100\n"
        analysis += f"- **Security**: {health_scores.security}/100\n"
        analysis += f"- **Community**: {health_scores.community}/100\n"
        analysis += f"- **Legal Compliance**: {health_scores.legal}/100\n"
        analysis += f"- **CI/CD Maturity**: {health_scores.ci_cd}/100\n\n"

        # Findings
        if findings.critical:
            analysis += "## 🚨 Critical Issues\n"
            for issue in findings.critical:
                analysis += f"- {issue}\n"
            analysis += "\n"

        if findings.high:
            analysis += "## ⚠️ High Priority Issues\n"
            for issue in findings.high:
                analysis += f"- {issue}\n"
            analysis += "\n"

        # Top recommendations
        if recommendations:
            analysis += "## 🎯 Top Recommendations\n"
            for i, rec in enumerate(recommendations[:5], 1):
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    rec.get("priority", "medium"), "🔵"
                )
                analysis += f"{i}. **{rec.get('title')}** {priority_emoji}\n"
                analysis += f"   {rec.get('description')}\n\n"

        return analysis

    def _format_deep_analysis(self, health_scores, findings, recommendations, repo_metadata) -> str:
        """Format deep health analysis with detailed metrics."""
        standard = self._format_standard_analysis(health_scores, findings, recommendations)

        # Add detailed repository statistics
        structure = repo_metadata.get("structure", {})
        languages = repo_metadata.get("languages", {})
        security = repo_metadata.get("security", {})

        deep_analysis = standard + "\n## 📊 Detailed Metrics\n\n"

        # Repository structure
        deep_analysis += "### Repository Structure\n"
        deep_analysis += f"- Total Files: {structure.get('total_files', 'N/A')}\n"
        deep_analysis += f"- Total Directories: {structure.get('total_directories', 'N/A')}\n"
        deep_analysis += f"- Max Depth: {structure.get('max_depth', 'N/A')}\n"
        deep_analysis += (
            f"- Organization Score: {structure.get('organization_score', 'N/A')}/100\n\n"
        )

        # Language distribution
        if languages.get("languages"):
            deep_analysis += "### Language Distribution\n"
            for lang, data in languages["languages"].items():
                percentage = data.get("line_percentage", 0)
                files = data.get("files", 0)
                deep_analysis += f"- {lang}: {percentage:.1f}% ({files} files)\n"
            deep_analysis += "\n"

        # Security details
        if security:
            deep_analysis += "### Security Analysis\n"
            deep_analysis += (
                f"- Security Policy: {'✅' if security.get('security_policy_exists') else '❌'}\n"
            )
            deep_analysis += (
                f"- Dependency Lock Files: {len(security.get('dependency_lock_files', []))}\n"
            )
            deep_analysis += (
                f"- Potential Secrets Found: {len(security.get('secrets_found', []))}\n"
            )
            deep_analysis += (
                f"- GitIgnore Present: {'✅' if security.get('gitignore_exists') else '❌'}\n\n"
            )

        return deep_analysis

    def _calculate_grade(self, score: int) -> str:
        """Calculate letter grade from score."""
        if score >= 90:
            return "A+"
        if score >= 85:
            return "A"
        if score >= 80:
            return "A-"
        if score >= 75:
            return "B+"
        if score >= 70:
            return "B"
        if score >= 65:
            return "B-"
        if score >= 60:
            return "C+"
        if score >= 55:
            return "C"
        if score >= 50:
            return "C-"
        if score >= 40:
            return "D"
        return "F"


class CheckDocumentationQualityTool(BaseTool):
    """Tool to check documentation quality specifically."""

    name = "check_documentation_quality"
    description = "Analyze README, API docs, and project documentation quality"

    def __init__(self):
        self.indexer = RepoIndexer()
        self.scorer = QualityScorer()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to the repository",
                    "default": ".",
                },
                "check_completeness": {
                    "type": "boolean",
                    "description": "Check for missing documentation files",
                    "default": True,
                },
                "language_specific": {
                    "type": "boolean",
                    "description": "Include language-specific documentation recommendations",
                    "default": True,
                },
            },
            "required": ["repo_path"],
        }

    def execute(self, **kwargs) -> str:
        """Execute documentation quality check."""
        repo_path = kwargs.get("repo_path", ".")
        check_completeness = kwargs.get("check_completeness", True)
        language_specific = kwargs.get("language_specific", True)

        try:
            repo_metadata = self.indexer.index_repository(repo_path)
            doc_data = repo_metadata.get("documentation", {})

            # Calculate documentation score
            health_scores = self.scorer.calculate_health_scores(repo_metadata)
            doc_score = health_scores.documentation

            analysis = "# Documentation Quality Analysis\n\n"
            analysis += f"**Documentation Score: {doc_score}/100**\n\n"

            # README analysis
            readme_exists = doc_data.get("readme_exists", False)
            readme_score = doc_data.get("readme_quality_score", 0)

            analysis += "## README Analysis\n"
            if readme_exists:
                analysis += f"- ✅ README exists (Quality: {readme_score}/100)\n"
                if readme_score < 70:
                    analysis += "- ⚠️ README quality could be improved\n"
                    analysis += "  - Consider adding: installation, usage, contributing sections\n"
            else:
                analysis += "- ❌ README file missing\n"
                analysis += "- 🚨 **Critical**: Create a README.md file immediately\n"

            analysis += "\n"

            # Documentation files
            doc_files = doc_data.get("documentation_files", [])
            analysis += f"## Documentation Files ({len(doc_files)} found)\n"

            standard_docs = {
                "CHANGELOG": "Track project changes and releases",
                "CONTRIBUTING": "Guide contributors on how to help",
                "API": "Document API endpoints and usage",
                "INSTALL": "Installation instructions",
            }

            found_types = []
            for doc_file in doc_files:
                for doc_type in standard_docs:
                    if doc_type.lower() in doc_file.lower():
                        found_types.append(doc_type)
                        analysis += f"- ✅ {doc_type} documentation found\n"

            # Missing documentation
            missing_docs = [doc for doc in standard_docs if doc not in found_types]
            if missing_docs:
                analysis += "\n### Missing Documentation\n"
                for doc_type in missing_docs:
                    analysis += f"- ❌ {doc_type}: {standard_docs[doc_type]}\n"

            # Code comments
            comment_ratio = doc_data.get("code_comments_ratio", 0)
            analysis += "\n## Code Documentation\n"
            analysis += f"- Comment Ratio: {comment_ratio:.1%}\n"

            if comment_ratio < 0.05:
                analysis += "- ⚠️ Very low code comment ratio\n"
                analysis += "- 💡 Consider adding more inline documentation\n"
            elif comment_ratio < 0.10:
                analysis += "- 📝 Moderate code comment ratio\n"
                analysis += "- 💡 Could benefit from more documentation\n"
            else:
                analysis += "- ✅ Good code comment ratio\n"

            # Language-specific recommendations
            if language_specific:
                primary_lang = (
                    repo_metadata.get("languages", {}).get("primary_language", "").lower()
                )
                lang_recs = self._get_language_doc_recommendations(primary_lang)
                if lang_recs:
                    analysis += f"\n## {primary_lang.title()} Documentation Recommendations\n"
                    for rec in lang_recs:
                        analysis += f"- {rec}\n"

            return analysis

        except Exception as e:
            return f"Error checking documentation quality: {e!s}"

    def _get_language_doc_recommendations(self, language: str) -> List[str]:
        """Get language-specific documentation recommendations."""
        recommendations = {
            "python": [
                "Use docstrings for functions and classes",
                "Consider using Sphinx for API documentation",
                "Add type hints for better code documentation",
                "Include examples in docstrings",
            ],
            "javascript": [
                "Use JSDoc comments for functions",
                "Document API endpoints with OpenAPI/Swagger",
                "Include TypeScript definitions for better docs",
                "Add usage examples in comments",
            ],
            "rust": [
                "Use /// comments for public APIs",
                "Run 'cargo doc' to generate documentation",
                "Include examples in documentation comments",
                "Document error handling patterns",
            ],
            "java": [
                "Use JavaDoc for public methods and classes",
                "Generate documentation with 'javadoc'",
                "Document exceptions and return values",
                "Include code examples in JavaDoc",
            ],
        }

        return recommendations.get(language, [])


class SuggestImprovementsTool(BaseTool):
    """Tool to suggest specific improvements for repository health."""

    name = "suggest_improvements"
    description = "Generate actionable improvement suggestions for repository health"

    def __init__(self):
        self.indexer = RepoIndexer()
        self.scorer = QualityScorer()
        self.editor = RepoEditor()
        self.template_manager = TemplateManager()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to the repository",
                    "default": ".",
                },
                "priority_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Areas to prioritize (security, documentation, testing, etc.)",
                    "default": [],
                },
                "include_templates": {
                    "type": "boolean",
                    "description": "Include information about available templates",
                    "default": True,
                },
            },
            "required": ["repo_path"],
        }

    def execute(self, **kwargs) -> str:
        """Execute improvement suggestions generation."""
        repo_path = kwargs.get("repo_path", ".")
        priority_areas = kwargs.get("priority_areas", [])
        include_templates = kwargs.get("include_templates", True)

        try:
            # Get repository analysis
            repo_metadata = self.indexer.index_repository(repo_path)
            health_scores = self.scorer.calculate_health_scores(repo_metadata)

            # Get missing files and improvement suggestions
            missing_files = self.template_manager.get_missing_files(repo_path, repo_metadata)
            file_improvements = self.editor.suggest_file_improvements(
                repo_path, repo_metadata, health_scores
            )

            # Filter by priority areas if specified
            if priority_areas:
                file_improvements = [
                    imp for imp in file_improvements if imp.get("category") in priority_areas
                ]

            improvements = "# Repository Improvement Suggestions\n\n"
            improvements += f"**Current Health Score: {health_scores.overall}/100**\n\n"

            # Critical actions first
            critical_actions = []
            if health_scores.security < 50:
                critical_actions.append(
                    "🚨 **CRITICAL**: Address security vulnerabilities immediately"
                )
            if "README.md" in missing_files:
                critical_actions.append("🚨 **CRITICAL**: Create README.md file")
            if health_scores.overall < 40:
                critical_actions.append(
                    "🚨 **CRITICAL**: Repository health is severely compromised"
                )

            if critical_actions:
                improvements += "## 🚨 Critical Actions Required\n\n"
                for action in critical_actions:
                    improvements += f"- {action}\n"
                improvements += "\n"

            # Missing files
            if missing_files:
                improvements += f"## 📝 Missing Standard Files ({len(missing_files)})\n\n"
                for file in missing_files:
                    improvements += f"- **{file}**"
                    if include_templates:
                        improvements += " ✅ (Template available)"
                    improvements += "\n"
                improvements += "\n"

            # Specific file improvements
            if file_improvements:
                improvements += "## 🔧 File Improvements\n\n"
                for imp in file_improvements:
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        imp.get("priority", "medium"), "🔵"
                    )
                    improvements += f"### {imp.get('file', 'Unknown File')} {priority_emoji}\n"
                    improvements += f"**{imp.get('title', 'Improvement')}**\n"
                    improvements += f"{imp.get('description', 'No description available')}\n\n"

                    if imp.get("improvements"):
                        improvements += "Specific improvements:\n"
                        for specific in imp["improvements"]:
                            improvements += f"- {specific}\n"
                        improvements += "\n"

            # Category-specific recommendations
            improvements += "## 📊 Category Recommendations\n\n"

            categories = [
                ("Security", health_scores.security, "Implement security best practices"),
                ("Documentation", health_scores.documentation, "Improve project documentation"),
                ("Testing", health_scores.testing, "Enhance test coverage and quality"),
                ("Community", health_scores.community, "Strengthen community guidelines"),
                ("CI/CD", health_scores.ci_cd, "Improve automation and workflows"),
            ]

            for category, score, description in categories:
                if score < 70:  # Only show recommendations for areas that need improvement
                    status = "🔴" if score < 50 else "🟡"
                    improvements += f"- **{category}** {status} ({score}/100): {description}\n"

            if include_templates:
                improvements += "\n## 🛠️ Template Generation\n\n"
                improvements += "The following files can be automatically generated:\n"
                template_files = [
                    "README.md",
                    "CONTRIBUTING.md",
                    "CODE_OF_CONDUCT.md",
                    "SECURITY.md",
                    "LICENSE",
                    ".gitignore",
                    ".github/workflows/ci.yml",
                ]
                for template in template_files:
                    if template in missing_files:
                        improvements += f"- ✅ {template}\n"

            return improvements

        except Exception as e:
            return f"Error generating improvement suggestions: {e!s}"


class GenerateMissingFilesTool(BaseTool):
    """Tool to generate missing repository files."""

    name = "generate_missing_files"
    description = "Create templates for missing standard repository files"

    def __init__(self):
        self.indexer = RepoIndexer()
        self.editor = RepoEditor()
        self.template_manager = TemplateManager()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to the repository",
                    "default": ".",
                },
                "file_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific file types to generate (README, CONTRIBUTING, etc.)",
                    "default": [],
                },
                "customize_for_language": {
                    "type": "boolean",
                    "description": "Customize templates for the repository's primary language",
                    "default": True,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview what would be generated without creating files",
                    "default": True,
                },
            },
            "required": ["repo_path"],
        }

    def execute(self, **kwargs) -> str:
        """Execute missing file generation."""
        repo_path = kwargs.get("repo_path", ".")
        file_types = kwargs.get("file_types", [])
        customize_for_language = kwargs.get("customize_for_language", True)
        dry_run = kwargs.get("dry_run", True)

        try:
            # Get repository metadata
            repo_metadata = self.indexer.index_repository(repo_path)

            # Get missing files
            missing_files = self.template_manager.get_missing_files(repo_path, repo_metadata)

            # Filter by file types if specified
            if file_types:
                missing_files = [
                    f for f in missing_files if any(ft.lower() in f.lower() for ft in file_types)
                ]

            if not missing_files:
                return "✅ No missing files found. Repository appears to have all standard files."

            # Generate context for templates
            context = {}
            if customize_for_language:
                primary_lang = repo_metadata.get("languages", {}).get("primary_language", "Python")
                context["primary_language"] = primary_lang

            # Generate files
            results = self.editor.generate_missing_files(repo_path, repo_metadata, context, dry_run)

            # Format results
            output = "# File Generation Results\n\n"

            if dry_run:
                output += "**Preview Mode** - No files were actually created\n\n"
            else:
                output += "**Files Generated Successfully**\n\n"

            successful = [r for r in results if r.get("status") in ["created", "would_create"]]
            errors = [r for r in results if r.get("status") == "error"]
            skipped = [r for r in results if r.get("status") == "exists"]

            if successful:
                output += f"## ✅ Generated Files ({len(successful)})\n\n"
                for result in successful:
                    path = result.get("path", "Unknown")
                    size = result.get("size", 0)
                    status = "📝 Would create" if dry_run else "✅ Created"
                    output += f"- **{path}** - {status} ({size:,} chars)\n"
                output += "\n"

            if skipped:
                output += f"## ⏭️ Skipped Files ({len(skipped)})\n\n"
                for result in skipped:
                    path = result.get("path", "Unknown")
                    output += f"- **{path}** - Already exists\n"
                output += "\n"

            if errors:
                output += f"## ❌ Errors ({len(errors)})\n\n"
                for result in errors:
                    path = result.get("path", "Unknown")
                    error = result.get("error", "Unknown error")
                    output += f"- **{path}** - Error: {error}\n"
                output += "\n"

            # Add guidance
            if dry_run and successful:
                output += "## 🎯 Next Steps\n\n"
                output += "To actually create these files, run with `dry_run=False`.\n"
                output += (
                    "Review the generated content and customize as needed for your project.\n\n"
                )

            if not dry_run and successful:
                output += "## 🎯 Post-Generation Steps\n\n"
                output += "1. Review and customize the generated files\n"
                output += "2. Update project-specific information (URLs, contact info, etc.)\n"
                output += "3. Commit the new files to your repository\n"
                output += "4. Consider running another health analysis to see improved scores\n\n"

            return output

        except Exception as e:
            return f"Error generating missing files: {e!s}"


# Register health analysis tools
health_tools = [
    AnalyzeRepositoryHealthTool(),
    CheckDocumentationQualityTool(),
    SuggestImprovementsTool(),
    GenerateMissingFilesTool(),
]
