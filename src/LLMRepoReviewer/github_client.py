"""
GitHub API client for repository analysis and community health metrics.

This module provides rate-limited, authenticated access to GitHub APIs for
analyzing repository health metrics that cannot be determined from local analysis.
"""

import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests


class GitHubAPIClient:
    """
    GitHub API client with rate limiting and authentication.

    Provides access to GitHub APIs for analyzing:
    - Issue and PR management patterns
    - Community engagement metrics
    - Repository maintenance patterns
    - Security and dependency information
    """

    def __init__(self, token: Optional[str] = None, rate_limit_delay: float = 1.0):
        """
        Initialize GitHub API client.

        Args:
            token: GitHub personal access token (optional, increases rate limits)
            rate_limit_delay: Minimum delay between API calls in seconds
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.base_url = "https://api.github.com"

        # Session for connection pooling
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"token {self.token}"})

        self.session.headers.update(
            {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "LLM-Repo-Health-Analyzer/1.0",
            }
        )

    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated GitHub API request with rate limiting.

        Args:
            endpoint: API endpoint (e.g., "/repos/owner/repo")
            params: Query parameters

        Returns:
            JSON response or None if request fails
        """
        self._rate_limit()

        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params or {})

            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                return None  # Repository not found or private
            if response.status_code == 403:
                print("⚠️ GitHub API rate limit exceeded or insufficient permissions")
                return None
            print(f"⚠️ GitHub API error {response.status_code}: {response.text}")
            return None

        except Exception as e:
            print(f"⚠️ GitHub API request failed: {e}")
            return None

    def extract_repo_info(self, github_url: str) -> Optional[tuple[str, str]]:
        """
        Extract owner and repository name from GitHub URL.

        Args:
            github_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo) or None if invalid URL
        """
        patterns = [
            r"github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
            r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, github_url)
            if match:
                return match.group(1), match.group(2)

        return None

    def get_repository_info(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get basic repository information."""
        return self._make_request(f"/repos/{owner}/{repo}")

    def get_issues_analysis(self, owner: str, repo: str, days: int = 90) -> Dict[str, Any]:
        """
        Analyze issue management patterns.

        Args:
            owner: Repository owner
            repo: Repository name
            days: Number of days to analyze (default: 90)

        Returns:
            Dictionary with issue analysis metrics
        """
        since_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Get recent issues
        issues_params = {"state": "all", "since": since_date, "per_page": 100, "sort": "updated"}

        issues = self._make_request(f"/repos/{owner}/{repo}/issues", issues_params)
        if not issues:
            return {"error": "Could not fetch issues data"}

        analysis = {
            "total_issues": 0,
            "open_issues": 0,
            "closed_issues": 0,
            "avg_time_to_close": None,
            "response_rate": 0.0,
            "label_usage": 0,
            "contributor_engagement": 0,
        }

        response_times = []
        labeled_issues = 0

        for issue in issues:
            # Skip pull requests (they appear in issues API)
            if "pull_request" in issue:
                continue

            analysis["total_issues"] += 1

            if issue["state"] == "open":
                analysis["open_issues"] += 1
            else:
                analysis["closed_issues"] += 1

                # Calculate time to close
                created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
                closed = datetime.fromisoformat(issue["closed_at"].replace("Z", "+00:00"))
                response_times.append((closed - created).total_seconds() / 3600)  # hours

            # Check for labels
            if issue.get("labels"):
                labeled_issues += 1

        if response_times:
            analysis["avg_time_to_close"] = sum(response_times) / len(response_times)

        if analysis["total_issues"] > 0:
            analysis["response_rate"] = analysis["closed_issues"] / analysis["total_issues"]
            analysis["label_usage"] = labeled_issues / analysis["total_issues"]

        return analysis

    def get_pull_requests_analysis(self, owner: str, repo: str, days: int = 90) -> Dict[str, Any]:
        """
        Analyze pull request management patterns.

        Args:
            owner: Repository owner
            repo: Repository name
            days: Number of days to analyze (default: 90)

        Returns:
            Dictionary with PR analysis metrics
        """
        since_date = (datetime.now() - timedelta(days=days)).isoformat()

        prs_params = {"state": "all", "since": since_date, "per_page": 100, "sort": "updated"}

        pulls = self._make_request(f"/repos/{owner}/{repo}/pulls", prs_params)
        if not pulls:
            return {"error": "Could not fetch pull requests data"}

        analysis = {
            "total_prs": len(pulls),
            "merged_prs": 0,
            "closed_prs": 0,
            "open_prs": 0,
            "avg_time_to_merge": None,
            "review_coverage": 0.0,
            "contributor_diversity": 0,
        }

        merge_times = []
        reviewed_prs = 0
        unique_contributors = set()

        for pr in pulls:
            if pr["state"] == "open":
                analysis["open_prs"] += 1
            elif pr["merged_at"]:
                analysis["merged_prs"] += 1
                # Calculate time to merge
                created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                merge_times.append((merged - created).total_seconds() / 3600)  # hours
            else:
                analysis["closed_prs"] += 1

            # Track unique contributors
            if pr["user"] and pr["user"]["login"]:
                unique_contributors.add(pr["user"]["login"])

            # Check for reviews (simplified - would need additional API call for full data)
            if pr.get("requested_reviewers") or pr.get("assignees"):
                reviewed_prs += 1

        if merge_times:
            analysis["avg_time_to_merge"] = sum(merge_times) / len(merge_times)

        if analysis["total_prs"] > 0:
            analysis["review_coverage"] = reviewed_prs / analysis["total_prs"]

        analysis["contributor_diversity"] = len(unique_contributors)

        return analysis

    def get_community_metrics(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get community engagement metrics.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary with community metrics
        """
        repo_info = self.get_repository_info(owner, repo)
        if not repo_info:
            return {"error": "Could not fetch repository information"}

        # Get contributors
        contributors = self._make_request(f"/repos/{owner}/{repo}/contributors", {"per_page": 100})

        # Get releases
        releases = self._make_request(f"/repos/{owner}/{repo}/releases", {"per_page": 20})

        metrics = {
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0),
            "watchers": repo_info.get("watchers_count", 0),
            "open_issues_count": repo_info.get("open_issues_count", 0),
            "contributors_count": len(contributors) if contributors else 0,
            "releases_count": len(releases) if releases else 0,
            "last_push": repo_info.get("pushed_at"),
            "created_at": repo_info.get("created_at"),
            "default_branch": repo_info.get("default_branch", "main"),
            "has_wiki": repo_info.get("has_wiki", False),
            "has_pages": repo_info.get("has_pages", False),
            "has_discussions": repo_info.get("has_discussions", False),
        }

        # Calculate repository age and activity
        if metrics["created_at"]:
            created = datetime.fromisoformat(metrics["created_at"].replace("Z", "+00:00"))
            age_days = (datetime.now(created.tzinfo) - created).days
            metrics["age_days"] = age_days

        # Calculate recent activity score
        if metrics["last_push"]:
            last_push = datetime.fromisoformat(metrics["last_push"].replace("Z", "+00:00"))
            days_since_push = (datetime.now(last_push.tzinfo) - last_push).days
            metrics["days_since_last_push"] = days_since_push

            # Activity score (0-100) based on recency
            if days_since_push <= 7:
                metrics["activity_score"] = 100
            elif days_since_push <= 30:
                metrics["activity_score"] = 80
            elif days_since_push <= 90:
                metrics["activity_score"] = 60
            elif days_since_push <= 180:
                metrics["activity_score"] = 40
            elif days_since_push <= 365:
                metrics["activity_score"] = 20
            else:
                metrics["activity_score"] = 0

        return metrics

    def get_security_analysis(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get security-related information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary with security metrics
        """
        # Get dependabot alerts (requires special permissions)
        # For now, we'll focus on public security features

        # Get releases for security patch patterns
        releases = self._make_request(f"/repos/{owner}/{repo}/releases", {"per_page": 20})

        security_metrics = {
            "has_security_policy": False,
            "has_dependabot": False,
            "recent_security_releases": 0,
            "vulnerability_alerts_enabled": False,  # Would need admin access to check
        }

        # Check for security-related releases
        if releases:
            security_keywords = ["security", "vulnerability", "cve", "patch", "fix"]
            for release in releases:
                release_text = (release.get("body", "") + release.get("name", "")).lower()
                if any(keyword in release_text for keyword in security_keywords):
                    security_metrics["recent_security_releases"] += 1

        # Check for security policy (already done in local analysis, but confirm)
        security_policy = self._make_request(f"/repos/{owner}/{repo}/contents/SECURITY.md")
        security_metrics["has_security_policy"] = security_policy is not None

        return security_metrics

    def analyze_repository(self, github_url: str) -> Dict[str, Any]:
        """
        Perform comprehensive GitHub API analysis of a repository.

        Args:
            github_url: GitHub repository URL

        Returns:
            Dictionary with all GitHub-based analysis results
        """
        repo_info = self.extract_repo_info(github_url)
        if not repo_info:
            return {"error": "Invalid GitHub URL"}

        owner, repo = repo_info

        print(f"📡 Analyzing GitHub repository: {owner}/{repo}")

        analysis = {
            "repository_url": github_url,
            "owner": owner,
            "repository": repo,
            "analyzed_at": datetime.now().isoformat(),
        }

        # Gather all metrics
        try:
            analysis["issues"] = self.get_issues_analysis(owner, repo)
            analysis["pull_requests"] = self.get_pull_requests_analysis(owner, repo)
            analysis["community"] = self.get_community_metrics(owner, repo)
            analysis["security"] = self.get_security_analysis(owner, repo)

            print("✅ GitHub API analysis complete")

        except Exception as e:
            print(f"⚠️ GitHub API analysis failed: {e}")
            analysis["error"] = str(e)

        return analysis
