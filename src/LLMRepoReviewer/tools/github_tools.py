"""
GitHub API tools for enhanced repository analysis.

This module provides LLM-callable tools that use the GitHub API to gather
community health metrics and maintenance patterns not available from local analysis.
"""

from typing import Any, Dict

from ..github_client import GitHubAPIClient
from .base import BaseTool


class GitHubIssueAnalysisTool(BaseTool):
    """Tool to analyze GitHub issue management patterns."""

    name = "analyze_github_issues"
    description = "Analyze GitHub issue response times, closure rates, and management patterns"

    def __init__(self):
        self.github_client = GitHubAPIClient()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL to analyze"},
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 90)",
                    "default": 90,
                },
            },
            "required": ["github_url"],
        }

    def execute(self, **kwargs) -> str:
        """Execute GitHub issue analysis."""
        github_url = kwargs.get("github_url")
        days = kwargs.get("days", 90)

        if not github_url:
            return "Error: GitHub URL is required"

        repo_info = self.github_client.extract_repo_info(github_url)
        if not repo_info:
            return "Error: Invalid GitHub URL format"

        owner, repo = repo_info

        try:
            analysis = self.github_client.get_issues_analysis(owner, repo, days)

            if "error" in analysis:
                return f"Error analyzing issues: {analysis['error']}"

            result = f"# GitHub Issue Analysis ({days} days)\n\n"
            result += f"**Repository**: {owner}/{repo}\n\n"

            total = analysis.get("total_issues", 0)
            open_issues = analysis.get("open_issues", 0)
            closed = analysis.get("closed_issues", 0)

            result += "## Issue Statistics\n"
            result += f"- **Total Issues**: {total}\n"
            result += f"- **Open Issues**: {open_issues}\n"
            result += f"- **Closed Issues**: {closed}\n"

            if total > 0:
                response_rate = analysis.get("response_rate", 0) * 100
                result += f"- **Response Rate**: {response_rate:.1f}%\n"

                label_usage = analysis.get("label_usage", 0) * 100
                result += f"- **Label Usage**: {label_usage:.1f}%\n"

            avg_close_time = analysis.get("avg_time_to_close")
            if avg_close_time:
                if avg_close_time < 24:
                    result += f"- **Avg Time to Close**: {avg_close_time:.1f} hours\n"
                else:
                    result += f"- **Avg Time to Close**: {avg_close_time/24:.1f} days\n"

            # Assessment
            result += "\n## Assessment\n"

            if total == 0:
                result += "- No recent issues found - may indicate low activity or well-maintained project\n"
            elif response_rate > 0.8:
                result += "- ✅ Excellent issue response rate\n"
            elif response_rate > 0.6:
                result += "- 😊 Good issue response rate\n"
            elif response_rate > 0.4:
                result += "- 😐 Moderate issue response rate\n"
            else:
                result += "- ⚠️ Low issue response rate - may need attention\n"

            if label_usage > 0.7:
                result += "- ✅ Good use of issue labels for organization\n"
            elif label_usage > 0.3:
                result += "- 😊 Moderate use of issue labels\n"
            else:
                result += "- 💡 Consider using more issue labels for better organization\n"

            return result

        except Exception as e:
            return f"Error during GitHub issue analysis: {e}"


class GitHubPullRequestAnalysisTool(BaseTool):
    """Tool to analyze GitHub pull request management patterns."""

    name = "analyze_github_pull_requests"
    description = "Analyze GitHub PR review practices, merge times, and contributor patterns"

    def __init__(self):
        self.github_client = GitHubAPIClient()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL to analyze"},
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 90)",
                    "default": 90,
                },
            },
            "required": ["github_url"],
        }

    def execute(self, **kwargs) -> str:
        """Execute GitHub PR analysis."""
        github_url = kwargs.get("github_url")
        days = kwargs.get("days", 90)

        if not github_url:
            return "Error: GitHub URL is required"

        repo_info = self.github_client.extract_repo_info(github_url)
        if not repo_info:
            return "Error: Invalid GitHub URL format"

        owner, repo = repo_info

        try:
            analysis = self.github_client.get_pull_requests_analysis(owner, repo, days)

            if "error" in analysis:
                return f"Error analyzing pull requests: {analysis['error']}"

            result = f"# GitHub Pull Request Analysis ({days} days)\n\n"
            result += f"**Repository**: {owner}/{repo}\n\n"

            total = analysis.get("total_prs", 0)
            merged = analysis.get("merged_prs", 0)
            closed = analysis.get("closed_prs", 0)
            open_prs = analysis.get("open_prs", 0)

            result += "## Pull Request Statistics\n"
            result += f"- **Total PRs**: {total}\n"
            result += f"- **Merged PRs**: {merged}\n"
            result += f"- **Closed PRs**: {closed}\n"
            result += f"- **Open PRs**: {open_prs}\n"

            if total > 0:
                merge_rate = merged / total * 100
                result += f"- **Merge Rate**: {merge_rate:.1f}%\n"

                review_coverage = analysis.get("review_coverage", 0) * 100
                result += f"- **Review Coverage**: {review_coverage:.1f}%\n"

            contributor_diversity = analysis.get("contributor_diversity", 0)
            result += f"- **Unique Contributors**: {contributor_diversity}\n"

            avg_merge_time = analysis.get("avg_time_to_merge")
            if avg_merge_time:
                if avg_merge_time < 24:
                    result += f"- **Avg Time to Merge**: {avg_merge_time:.1f} hours\n"
                else:
                    result += f"- **Avg Time to Merge**: {avg_merge_time/24:.1f} days\n"

            # Assessment
            result += "\n## Assessment\n"

            if total == 0:
                result += "- No recent pull requests found\n"
            else:
                if merge_rate > 80:
                    result += "- ✅ High pull request merge rate indicates active development\n"
                elif merge_rate > 60:
                    result += "- 😊 Good pull request merge rate\n"
                elif merge_rate > 40:
                    result += "- 😐 Moderate pull request merge rate\n"
                else:
                    result += "- ⚠️ Low pull request merge rate - may indicate review bottlenecks\n"

                if review_coverage > 70:
                    result += "- ✅ Good pull request review practices\n"
                elif review_coverage > 40:
                    result += "- 😊 Moderate pull request review coverage\n"
                else:
                    result += "- 💡 Consider implementing more systematic PR reviews\n"

                if contributor_diversity > 5:
                    result += "- ✅ Good contributor diversity\n"
                elif contributor_diversity > 2:
                    result += "- 😊 Moderate contributor diversity\n"
                else:
                    result += "- 💡 Limited contributor diversity - consider community outreach\n"

            return result

        except Exception as e:
            return f"Error during GitHub PR analysis: {e}"


class GitHubCommunityMetricsTool(BaseTool):
    """Tool to analyze GitHub community engagement metrics."""

    name = "analyze_github_community"
    description = "Analyze GitHub stars, forks, activity, and community engagement metrics"

    def __init__(self):
        self.github_client = GitHubAPIClient()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL to analyze"}
            },
            "required": ["github_url"],
        }

    def execute(self, **kwargs) -> str:
        """Execute GitHub community metrics analysis."""
        github_url = kwargs.get("github_url")

        if not github_url:
            return "Error: GitHub URL is required"

        repo_info = self.github_client.extract_repo_info(github_url)
        if not repo_info:
            return "Error: Invalid GitHub URL format"

        owner, repo = repo_info

        try:
            metrics = self.github_client.get_community_metrics(owner, repo)

            if "error" in metrics:
                return f"Error analyzing community metrics: {metrics['error']}"

            result = "# GitHub Community Metrics\n\n"
            result += f"**Repository**: {owner}/{repo}\n\n"

            # Engagement metrics
            stars = metrics.get("stars", 0)
            forks = metrics.get("forks", 0)
            watchers = metrics.get("watchers", 0)

            result += "## Engagement Statistics\n"
            result += f"- **Stars**: {stars:,}\n"
            result += f"- **Forks**: {forks:,}\n"
            result += f"- **Watchers**: {watchers:,}\n"

            contributors = metrics.get("contributors_count", 0)
            releases = metrics.get("releases_count", 0)
            open_issues = metrics.get("open_issues_count", 0)

            result += f"- **Contributors**: {contributors}\n"
            result += f"- **Releases**: {releases}\n"
            result += f"- **Open Issues**: {open_issues}\n"

            # Activity metrics
            age_days = metrics.get("age_days", 0)
            days_since_push = metrics.get("days_since_last_push", 0)
            activity_score = metrics.get("activity_score", 0)

            result += "\n## Activity Metrics\n"
            result += f"- **Repository Age**: {age_days} days\n"
            result += f"- **Days Since Last Push**: {days_since_push}\n"
            result += f"- **Activity Score**: {activity_score}/100\n"

            # Features
            has_wiki = metrics.get("has_wiki", False)
            has_pages = metrics.get("has_pages", False)
            has_discussions = metrics.get("has_discussions", False)

            result += "\n## Repository Features\n"
            result += f"- **Wiki**: {'✅' if has_wiki else '❌'}\n"
            result += f"- **GitHub Pages**: {'✅' if has_pages else '❌'}\n"
            result += f"- **Discussions**: {'✅' if has_discussions else '❌'}\n"

            # Assessment
            result += "\n## Community Health Assessment\n"

            # Popularity assessment
            if stars > 1000:
                result += "- ✅ High community interest (1000+ stars)\n"
            elif stars > 100:
                result += "- 😊 Good community interest (100+ stars)\n"
            elif stars > 10:
                result += "- 😐 Moderate community interest (10+ stars)\n"
            else:
                result += "- 💡 Limited community visibility - consider promotion\n"

            # Fork ratio assessment
            if forks > 0 and stars > 0:
                fork_ratio = forks / stars
                if fork_ratio > 0.2:
                    result += "- ✅ High fork ratio indicates active development community\n"
                elif fork_ratio > 0.1:
                    result += "- 😊 Good fork ratio\n"
                else:
                    result += "- 😐 Low fork ratio - mostly passive interest\n"

            # Activity assessment
            if activity_score >= 80:
                result += "- ✅ Very active project (recent commits)\n"
            elif activity_score >= 60:
                result += "- 😊 Active project\n"
            elif activity_score >= 40:
                result += "- 😐 Moderately active project\n"
            elif activity_score >= 20:
                result += "- ⚠️ Low activity - project may be slowing down\n"
            else:
                result += "- 🚨 Very low activity - project may be abandoned\n"

            # Contributor diversity
            if contributors > 20:
                result += "- ✅ High contributor diversity (20+ contributors)\n"
            elif contributors > 5:
                result += "- 😊 Good contributor diversity (5+ contributors)\n"
            elif contributors > 1:
                result += "- 😐 Limited contributor diversity\n"
            else:
                result += "- 💡 Single contributor - consider community building\n"

            return result

        except Exception as e:
            return f"Error during GitHub community analysis: {e}"


class GitHubSecurityAnalysisTool(BaseTool):
    """Tool to analyze GitHub security features and practices."""

    name = "analyze_github_security"
    description = "Analyze GitHub security features, alerts, and security-related releases"

    def __init__(self):
        self.github_client = GitHubAPIClient()

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "github_url": {"type": "string", "description": "GitHub repository URL to analyze"}
            },
            "required": ["github_url"],
        }

    def execute(self, **kwargs) -> str:
        """Execute GitHub security analysis."""
        github_url = kwargs.get("github_url")

        if not github_url:
            return "Error: GitHub URL is required"

        repo_info = self.github_client.extract_repo_info(github_url)
        if not repo_info:
            return "Error: Invalid GitHub URL format"

        owner, repo = repo_info

        try:
            security = self.github_client.get_security_analysis(owner, repo)

            if "error" in security:
                return f"Error analyzing security: {security['error']}"

            result = "# GitHub Security Analysis\n\n"
            result += f"**Repository**: {owner}/{repo}\n\n"

            result += "## Security Features\n"

            has_policy = security.get("has_security_policy", False)
            result += f"- **Security Policy**: {'✅' if has_policy else '❌'}\n"

            has_dependabot = security.get("has_dependabot", False)
            result += f"- **Dependabot**: {'✅' if has_dependabot else '❌'}\n"

            security_releases = security.get("recent_security_releases", 0)
            result += f"- **Recent Security Releases**: {security_releases}\n"

            alerts_enabled = security.get("vulnerability_alerts_enabled", False)
            result += f"- **Vulnerability Alerts**: {'✅' if alerts_enabled else '❌'}\n"

            # Assessment
            result += "\n## Security Assessment\n"

            if has_policy:
                result += "- ✅ Security policy documented - good practice\n"
            else:
                result += "- ⚠️ No security policy found - consider adding SECURITY.md\n"

            if security_releases > 0:
                result += f"- ✅ {security_releases} security-related releases found - shows active security maintenance\n"
            else:
                result += "- 💡 No recent security releases found\n"

            if has_dependabot:
                result += "- ✅ Dependabot enabled for automated dependency updates\n"
            else:
                result += "- 💡 Consider enabling Dependabot for automated security updates\n"

            return result

        except Exception as e:
            return f"Error during GitHub security analysis: {e}"


# Register GitHub tools
github_tools = [
    GitHubIssueAnalysisTool(),
    GitHubPullRequestAnalysisTool(),
    GitHubCommunityMetricsTool(),
    GitHubSecurityAnalysisTool(),
]
