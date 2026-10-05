#!/usr/bin/env python3
"""
Test runner for LLM Repo Reviewer

This script provides different ways to run the test suite:
- Unit tests (no external dependencies)
- Integration tests (mocked LLM)
- Full tests with real LLM (requires running LLM server)
"""

import argparse
import subprocess
import sys

import requests


def check_llm_available(api_base="http://localhost:11434/v1"):
    """Check if LLM server is available"""
    try:
        response = requests.get(f"{api_base.rstrip('/v1')}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'=' * 60}")
    print(f"🧪 {description}")
    print(f"{'=' * 60}")
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print("\n📋 Output:")
        print(result.stdout)

    if result.stderr:
        print("\n⚠️  Errors/Warnings:")
        print(result.stderr)

    if result.returncode == 0:
        print(f"\n✅ {description} completed successfully!")
    else:
        print(f"\n❌ {description} failed with exit code {result.returncode}")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run LLM Repo Reviewer tests")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "with-llm", "all", "quick"],
        help="Type of tests to run",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument(
        "--api-base",
        default="http://localhost:11434/v1",
        help="LLM API base URL for real LLM tests",
    )

    args = parser.parse_args()

    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    if args.verbose:
        base_cmd.append("-v")

    if args.coverage:
        base_cmd = [
            "python",
            "-m",
            "pytest",
            "--cov=LLMRepoReviewer",
            "--cov-report=html",
            "--cov-report=term",
        ]
        if args.verbose:
            base_cmd.append("-v")

    success = True

    if args.test_type == "unit":
        print("🔧 Running unit tests (no external dependencies)")
        success &= run_command(
            base_cmd + ["tests/test_tools.py", "tests/test_repo_reviewer_core.py"], "Unit Tests"
        )

    elif args.test_type == "integration":
        print("🔀 Running integration tests (mocked LLM)")
        success &= run_command(base_cmd + ["tests/test_integration.py"], "Integration Tests")

    elif args.test_type == "with-llm":
        print("🤖 Running tests with real LLM")
        if not check_llm_available(args.api_base):
            print(f"❌ LLM server not available at {args.api_base}")
            print("💡 Start a local LLM server (e.g., Ollama) to run these tests")
            return False

        success &= run_command(
            base_cmd + ["tests/test_with_llm.py", "-m", "not slow"], "Tests with Real LLM"
        )

    elif args.test_type == "quick":
        print("⚡ Running quick test suite")
        success &= run_command(
            base_cmd + ["tests/test_tools.py", "tests/test_repo_reviewer_core.py", "-x"],
            "Quick Tests (stop on first failure)",
        )

    elif args.test_type == "all":
        print("🎯 Running all available tests")

        # Unit tests
        print("\n📦 Phase 1: Unit Tests")
        success &= run_command(
            base_cmd + ["tests/test_tools.py", "tests/test_repo_reviewer_core.py"], "Unit Tests"
        )

        # Integration tests
        print("\n🔗 Phase 2: Integration Tests")
        success &= run_command(base_cmd + ["tests/test_integration.py"], "Integration Tests")

        # LLM tests if available
        if check_llm_available(args.api_base):
            print("\n🤖 Phase 3: Real LLM Tests")
            success &= run_command(
                base_cmd + ["tests/test_with_llm.py", "-m", "not slow"], "Tests with Real LLM"
            )
        else:
            print(f"\n⚠️  Skipping LLM tests - server not available at {args.api_base}")

        # Legacy tests
        print("\n📜 Phase 4: Legacy Tests")
        success &= run_command(base_cmd + ["tests/test_repo_reviewer.py"], "Legacy Tests")

    # Summary
    print(f"\n{'=' * 60}")
    if success:
        print("🎉 All tests completed successfully!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("💥 Some tests failed!")
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
