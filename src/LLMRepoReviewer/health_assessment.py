"""
Health assessment templates and reporting for repository analysis.

This module provides comprehensive health reporting with structured findings,
recommendations, and executive summaries based on the repository health framework.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .quality_scorer import HealthFindings, HealthScores


class HealthAssessment:
    """
    Comprehensive health assessment and reporting system.

    Generates structured reports with:
    - Executive summary with key metrics
    - Detailed health scores by category
    - Prioritized findings and recommendations
    - Comparison with similar repositories
    - Actionable improvement plans
    """

    def __init__(self):
        self.analysis_questions = self._get_health_analysis_questions()

    def _get_health_analysis_questions(self) -> Dict[str, str]:
        """Get comprehensive health analysis questions for LLM analysis."""
        return {
            "repository_overview": """
                Analyze the repository structure and provide an overview of:
                1. Main purpose and functionality of the project
                2. Target audience and use cases
                3. Project maturity level (experimental, alpha, beta, stable)
                4. Technology stack and architectural decisions
                """,
            "documentation_analysis": """
                Evaluate the documentation quality by examining:
                1. README completeness and clarity
                2. API documentation availability and quality
                3. Code comments and inline documentation
                4. Examples and tutorials
                5. Architecture and design documentation
                """,
            "code_quality_assessment": """
                Assess code quality indicators:
                1. Code organization and structure
                2. Consistent coding style and conventions
                3. Error handling patterns
                4. Performance considerations
                5. Technical debt indicators (TODO, FIXME, HACK comments)
                """,
            "testing_evaluation": """
                Analyze testing practices:
                1. Test coverage and comprehensiveness
                2. Testing frameworks and tools used
                3. Unit, integration, and end-to-end test distribution
                4. Test quality and maintainability
                5. Continuous testing in CI/CD
                """,
            "security_review": """
                Review security practices and potential vulnerabilities:
                1. Dependency security and vulnerability management
                2. Secrets management and sensitive data handling
                3. Input validation and sanitization
                4. Authentication and authorization patterns
                5. Security policies and vulnerability reporting process
                """,
            "community_health": """
                Evaluate community and collaboration health:
                1. Contributing guidelines and processes
                2. Issue and pull request management
                3. Community engagement and responsiveness
                4. Code of conduct and inclusive practices
                5. Maintainer information and governance
                """,
            "development_practices": """
                Assess development and deployment practices:
                1. Version control practices and branching strategy
                2. CI/CD pipeline quality and automation
                3. Release management and versioning
                4. Dependency management and updates
                5. Development environment setup and documentation
                """,
            "legal_compliance": """
                Review legal and licensing aspects:
                1. License clarity and compatibility
                2. Third-party dependency licensing
                3. Copyright and attribution practices
                4. Compliance with open source standards
                5. Intellectual property considerations
                """,
        }

    def generate_health_report(
        self,
        repo_metadata: Dict[str, Any],
        health_scores: HealthScores,
        findings: HealthFindings,
        recommendations: List[Dict[str, str]],
        llm_analysis: Optional[Dict[str, str]] = None,
        comparison_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate comprehensive health assessment report.

        Args:
            repo_metadata: Repository metadata from indexer
            health_scores: Calculated health scores
            findings: Assessment findings
            recommendations: Improvement recommendations
            llm_analysis: Optional LLM analysis responses
            comparison_data: Optional comparison with similar repositories

        Returns:
            Formatted health report as markdown
        """
        # Prepare context
        context = {
            "repo_name": repo_metadata.get("repo_id", "Repository"),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "repo_path": repo_metadata.get("repo_path", ""),
            "analysis_date": repo_metadata.get("last_analyzed", ""),
            "primary_language": repo_metadata.get("languages", {}).get(
                "primary_language", "Unknown"
            ),
            "total_files": repo_metadata.get("structure", {}).get("total_files", 0),
            "total_lines": repo_metadata.get("languages", {}).get("total_lines", 0),
            "health_scores": health_scores,
            "findings": findings,
            "recommendations": recommendations,
            "llm_analysis": llm_analysis or {},
            "comparison_data": comparison_data or {},
            "repo_metadata": repo_metadata,
        }

        return self._render_health_report_template(context)

    def _render_health_report_template(self, context: Dict[str, Any]) -> str:
        """Render the health report template with context data."""
        template = self._get_health_report_template()

        # Format template with context
        try:
            return template.format(**self._prepare_template_context(context))
        except KeyError as e:
            # Fallback for missing template variables
            return f"Error generating report: Missing template variable {e}"

    def _prepare_template_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and format context for template rendering."""
        health_scores = context["health_scores"]
        findings = context["findings"]
        recommendations = context["recommendations"]
        repo_metadata = context["repo_metadata"]

        # Calculate overall health grade
        overall_grade = self._calculate_health_grade(health_scores.overall)

        # Format health scores table
        scores_table = self._format_health_scores_table(health_scores)

        # Format findings by priority
        critical_findings = self._format_findings_list(findings.critical, "🚨")
        high_findings = self._format_findings_list(findings.high, "⚠️")
        medium_findings = self._format_findings_list(findings.medium, "📋")
        low_findings = self._format_findings_list(findings.low, "💡")

        # Format recommendations
        formatted_recommendations = self._format_recommendations(recommendations)

        # Format repository statistics
        repo_stats = self._format_repository_statistics(repo_metadata)

        # Format language distribution
        language_info = self._format_language_distribution(repo_metadata.get("languages", {}))

        # Format security findings
        security_summary = self._format_security_summary(repo_metadata.get("security", {}))

        # Format CI/CD status
        cicd_status = self._format_cicd_status(repo_metadata.get("ci_cd", {}))

        # Format community health indicators
        community_health = self._format_community_health(repo_metadata.get("community", {}))

        # LLM Analysis sections
        llm_analysis = context.get("llm_analysis", {})

        return {
            "repo_name": context["repo_name"],
            "date": context["date"],
            "repo_path": context["repo_path"],
            "overall_score": health_scores.overall,
            "overall_grade": overall_grade,
            "health_emoji": self._get_health_emoji(health_scores.overall),
            "scores_table": scores_table,
            "repo_stats": repo_stats,
            "language_info": language_info,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "medium_findings": medium_findings,
            "low_findings": low_findings,
            "recommendations": formatted_recommendations,
            "security_summary": security_summary,
            "cicd_status": cicd_status,
            "community_health": community_health,
            "repository_overview": llm_analysis.get("repository_overview", "Analysis pending..."),
            "documentation_analysis": llm_analysis.get(
                "documentation_analysis", "Analysis pending..."
            ),
            "code_quality_assessment": llm_analysis.get(
                "code_quality_assessment", "Analysis pending..."
            ),
            "testing_evaluation": llm_analysis.get("testing_evaluation", "Analysis pending..."),
            "security_review": llm_analysis.get("security_review", "Analysis pending..."),
            "community_assessment": llm_analysis.get("community_health", "Analysis pending..."),
            "development_practices": llm_analysis.get(
                "development_practices", "Analysis pending..."
            ),
            "legal_compliance": llm_analysis.get("legal_compliance", "Analysis pending..."),
            "comparison_insights": self._format_comparison_insights(
                context.get("comparison_data", {})
            ),
        }

    def _calculate_health_grade(self, score: int) -> str:
        """Calculate letter grade from numeric score."""
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

    def _get_health_emoji(self, score: int) -> str:
        """Get emoji representation of health score."""
        if score >= 90:
            return "🌟"
        if score >= 80:
            return "✅"
        if score >= 70:
            return "😊"
        if score >= 60:
            return "😐"
        if score >= 50:
            return "😟"
        return "🚨"

    def _format_health_scores_table(self, scores: HealthScores) -> str:
        """Format health scores as a table."""
        categories = [
            ("Overall Health", scores.overall, "🎯"),
            ("Documentation", scores.documentation, "📚"),
            ("Testing & Quality", scores.testing, "🧪"),
            ("Security", scores.security, "🔒"),
            ("Community", scores.community, "👥"),
            ("Legal Compliance", scores.legal, "⚖️"),
            ("CI/CD Maturity", scores.ci_cd, "🔄"),
        ]

        table = "| Category | Score | Grade | Status |\n"
        table += "|----------|-------|-------|--------|\n"

        for name, score, emoji in categories:
            grade = self._calculate_health_grade(score)
            status = self._get_score_status(score)
            table += f"| {emoji} {name} | {score}/100 | {grade} | {status} |\n"

        return table

    def _get_score_status(self, score: int) -> str:
        """Get status description for score."""
        if score >= 80:
            return "Excellent"
        if score >= 70:
            return "Good"
        if score >= 60:
            return "Fair"
        if score >= 50:
            return "Poor"
        return "Critical"

    def _format_findings_list(self, findings: List[str], emoji: str) -> str:
        """Format findings list with emoji bullets."""
        if not findings:
            return f"{emoji} None identified\n"

        result = ""
        for finding in findings:
            result += f"{emoji} {finding}\n"
        return result

    def _format_recommendations(self, recommendations: List[Dict[str, str]]) -> str:
        """Format recommendations as numbered list."""
        if not recommendations:
            return "No specific recommendations at this time."

        result = ""
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                rec.get("priority", "medium"), "🔵"
            )
            result += f"{i}. **{rec.get('title', 'Improvement')}** {priority_emoji}\n"
            result += f"   - **Category**: {rec.get('category', 'General').title()}\n"
            result += f"   - **Description**: {rec.get('description', 'No description provided')}\n"
            if rec.get("template_available"):
                result += "   - **Template Available**: ✅ Can be auto-generated\n"
            result += "\n"

        return result

    def _format_repository_statistics(self, repo_metadata: Dict[str, Any]) -> str:
        """Format repository statistics."""
        structure = repo_metadata.get("structure", {})
        git_info = repo_metadata.get("git_info", {})
        file_analysis = repo_metadata.get("file_analysis", {})

        stats = f"""
| Metric | Value |
|--------|-------|
| **Total Files** | {structure.get('total_files', 'N/A')} |
| **Total Directories** | {structure.get('total_directories', 'N/A')} |
| **Max Directory Depth** | {structure.get('max_depth', 'N/A')} |
| **Test Files** | {file_analysis.get('test_files', 'N/A')} |
| **Config Files** | {file_analysis.get('config_files', 'N/A')} |
| **Large Files (>1MB)** | {len(file_analysis.get('large_files', []))} |
| **Empty Files** | {len(file_analysis.get('empty_files', []))} |
| **Git Commits** | {git_info.get('commit_count', 'N/A')} |
| **Contributors** | {git_info.get('contributors', 'N/A')} |
| **Repository Age** | {git_info.get('repo_age_days', 'N/A')} days |
"""
        return stats.strip()

    def _format_language_distribution(self, languages_data: Dict[str, Any]) -> str:
        """Format programming language distribution."""
        languages = languages_data.get("languages", {})
        primary = languages_data.get("primary_language", "Unknown")

        if not languages:
            return f"**Primary Language**: {primary}\n\nNo detailed language analysis available."

        result = f"**Primary Language**: {primary}\n\n"
        result += "| Language | Files | Lines | Percentage |\n"
        result += "|----------|-------|-------|------------|\n"

        # Sort by line percentage
        sorted_langs = sorted(
            languages.items(), key=lambda x: x[1].get("line_percentage", 0), reverse=True
        )

        for lang, data in sorted_langs:
            files = data.get("files", 0)
            lines = data.get("lines", 0)
            percentage = data.get("line_percentage", 0)
            result += f"| {lang} | {files} | {lines:,} | {percentage:.1f}% |\n"

        return result

    def _format_security_summary(self, security_data: Dict[str, Any]) -> str:
        """Format security assessment summary."""
        security_score = security_data.get("security_score", 0)
        policy_exists = security_data.get("security_policy_exists", False)
        secrets_found = len(security_data.get("secrets_found", []))
        lock_files = len(security_data.get("dependency_lock_files", []))

        result = f"**Security Score**: {security_score}/100\n\n"
        result += f"- **Security Policy**: {'✅' if policy_exists else '❌'} {'Present' if policy_exists else 'Missing'}\n"
        result += f"- **Dependency Lock Files**: {lock_files} found\n"
        result += f"- **Potential Secrets**: {secrets_found} detected\n"
        result += f"- **GitIgnore**: {'✅' if security_data.get('gitignore_exists') else '❌'}\n"

        if secrets_found > 0:
            result += f"\n⚠️ **Warning**: {secrets_found} potential secrets detected in code. Review immediately.\n"

        return result

    def _format_cicd_status(self, cicd_data: Dict[str, Any]) -> str:
        """Format CI/CD status summary."""
        github_actions = len(cicd_data.get("github_actions", []))
        other_ci = len(cicd_data.get("other_ci", []))
        has_testing = cicd_data.get("has_automated_testing", False)
        has_deployment = cicd_data.get("has_automated_deployment", False)

        result = f"**CI/CD Maturity Score**: {cicd_data.get('workflow_quality_score', 0)}/100\n\n"
        result += f"- **GitHub Actions**: {github_actions} workflows\n"
        result += f"- **Other CI Systems**: {other_ci} configurations\n"
        result += f"- **Automated Testing**: {'✅' if has_testing else '❌'}\n"
        result += f"- **Automated Deployment**: {'✅' if has_deployment else '❌'}\n"

        if github_actions > 0:
            result += "\n**Workflows**:\n"
            for workflow in cicd_data.get("github_actions", []):
                result += f"- {workflow.get('name', 'Unknown')}\n"

        return result

    def _format_community_health(self, community_data: Dict[str, Any]) -> str:
        """Format community health indicators."""
        contributing = community_data.get("contributing_guidelines", False)
        conduct = community_data.get("code_of_conduct", False)
        security_policy = community_data.get("security_policy", False)
        issue_templates = community_data.get("issue_templates", False)
        pr_templates = community_data.get("pr_templates", False)

        result = "**Community Health Indicators**:\n\n"
        result += f"- **Contributing Guidelines**: {'✅' if contributing else '❌'}\n"
        result += f"- **Code of Conduct**: {'✅' if conduct else '❌'}\n"
        result += f"- **Security Policy**: {'✅' if security_policy else '❌'}\n"
        result += f"- **Issue Templates**: {'✅' if issue_templates else '❌'}\n"
        result += f"- **PR Templates**: {'✅' if pr_templates else '❌'}\n"

        github_features = len(community_data.get("github_features", []))
        if github_features > 0:
            result += f"\n**GitHub Features**: {github_features} configured\n"

        return result

    def _format_comparison_insights(self, comparison_data: Dict[str, Any]) -> str:
        """Format repository comparison insights."""
        if not comparison_data:
            return "No comparison data available."

        # This would be populated when comparing multiple repositories
        return "Repository comparison analysis would appear here when available."

    def _get_health_report_template(self) -> str:
        """Get the comprehensive health report template."""
        return """# 🏥 Repository Health Assessment Report

**Repository**: {repo_name}
**Assessment Date**: {date}
**Overall Health Score**: {overall_score}/100 ({overall_grade}) {health_emoji}

---

## 📊 Executive Summary

This repository has achieved an overall health score of **{overall_score}/100** ({overall_grade}), indicating {overall_grade} health status. The assessment evaluates six key categories of repository quality and provides actionable recommendations for improvement.

### Health Scores by Category

{scores_table}

---

## 📈 Repository Statistics

{repo_stats}

---

## 💻 Technology Overview

{language_info}

---

## 🔍 Assessment Findings

### 🚨 Critical Issues
{critical_findings}

### ⚠️ High Priority Issues
{high_findings}

### 📋 Medium Priority Issues
{medium_findings}

### 💡 Low Priority Improvements
{low_findings}

---

## 🎯 Recommendations

{recommendations}

---

## 🔒 Security Assessment

{security_summary}

---

## 🔄 CI/CD & Automation

{cicd_status}

---

## 👥 Community Health

{community_health}

---

## 📝 Detailed Analysis

### Repository Overview
{repository_overview}

### Documentation Quality
{documentation_analysis}

### Code Quality Assessment
{code_quality_assessment}

### Testing Evaluation
{testing_evaluation}

### Security Review
{security_review}

### Community Assessment
{community_assessment}

### Development Practices
{development_practices}

### Legal Compliance
{legal_compliance}

---

## 📊 Benchmarking

{comparison_insights}

---

## 🚀 Next Steps

Based on this assessment, we recommend focusing on the highest priority findings first:

1. **Address Critical Issues**: Resolve any critical security or functionality issues immediately
2. **Implement High Priority Improvements**: Focus on documentation, testing, or security gaps
3. **Establish Development Standards**: Set up automated quality checks and CI/CD processes
4. **Enhance Community Guidelines**: Add missing community health files and templates
5. **Monitor Progress**: Re-run health assessments periodically to track improvements

---

*This report was generated by the GitHub Repository Health Analyzer - an AI-powered tool for comprehensive repository quality assessment.*

**Report ID**: {date}
**Analysis Version**: 2.0
**Tools Used**: Repository Indexer, Quality Scorer, Security Scanner, LLM Analysis
"""


# Analysis questions for comprehensive LLM-based repository assessment
HEALTH_ANALYSIS_QUESTIONS = {
    "repository_overview": """
        Analyze this repository and provide a comprehensive overview including:
        1. What is the main purpose and functionality of this project?
        2. Who is the target audience and what are the primary use cases?
        3. What is the project's maturity level (experimental, alpha, beta, stable)?
        4. What technology stack and architectural decisions were made?
        5. How does this project fit into the broader ecosystem of its domain?

        Be specific and cite examples from the codebase where relevant.
        """,
    "documentation_analysis": """
        Evaluate the documentation quality by examining:
        1. README completeness - does it cover installation, usage, contributing?
        2. API documentation - are functions, classes, and modules well documented?
        3. Code comments - is complex logic explained appropriately?
        4. Examples and tutorials - are there practical usage examples?
        5. Architecture documentation - is the system design explained?

        Rate the documentation quality and suggest specific improvements.
        """,
    "code_quality_assessment": """
        Assess the code quality by analyzing:
        1. Code organization and structure - is it logical and consistent?
        2. Coding style and conventions - is the style consistent throughout?
        3. Error handling - are errors handled gracefully and appropriately?
        4. Performance considerations - are there obvious inefficiencies?
        5. Technical debt - what do TODO, FIXME, HACK comments indicate?

        Provide specific examples of good practices and areas for improvement.
        """,
    "testing_evaluation": """
        Analyze the testing practices:
        1. Test coverage - what percentage of code is covered by tests?
        2. Testing frameworks - what tools and libraries are used?
        3. Test types - are there unit, integration, and end-to-end tests?
        4. Test quality - are tests well-written and maintainable?
        5. CI/CD integration - are tests run automatically?

        Assess the testing maturity and suggest improvements.
        """,
    "security_review": """
        Review security practices and identify potential vulnerabilities:
        1. Dependency security - are dependencies up-to-date and secure?
        2. Secrets management - are API keys, passwords handled securely?
        3. Input validation - is user input properly sanitized?
        4. Authentication/authorization - are access controls implemented correctly?
        5. Security policies - is there a vulnerability reporting process?

        Highlight any security concerns and best practices observed.
        """,
    "community_health": """
        Evaluate community and collaboration aspects:
        1. Contributing guidelines - how easy is it for new contributors?
        2. Issue management - are issues well-organized and responded to?
        3. Pull request process - is there a clear review process?
        4. Community engagement - how active and welcoming is the community?
        5. Governance - is project leadership and decision-making clear?

        Assess the project's community health and collaboration effectiveness.
        """,
    "development_practices": """
        Assess development and deployment practices:
        1. Version control - are branching and commit practices good?
        2. CI/CD pipeline - is automation comprehensive and reliable?
        3. Release management - is versioning and release process clear?
        4. Dependency management - are dependencies well-managed?
        5. Development environment - is local setup documented and automated?

        Evaluate the development workflow maturity and suggest improvements.
        """,
    "legal_compliance": """
        Review legal and licensing aspects:
        1. License clarity - is the license clearly stated and appropriate?
        2. Dependency licensing - are third-party licenses compatible?
        3. Copyright notices - are copyright and attribution handled correctly?
        4. Open source compliance - does it follow open source best practices?
        5. Intellectual property - are there any IP concerns?

        Assess legal compliance and highlight any potential issues.
        """,
}
