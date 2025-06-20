#!/usr/bin/env python3
"""Enhanced CLI interface for GitHub Repository Health Analyzer with subcommands"""

import argparse
import os
import shutil
import sys

from .repo_reviewer import RepoHealthAnalyzer


def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 60)
    print("🏥 GitHub Repository Health Analyzer")
    print("=" * 60)
    print("AI-powered repository health analysis and quality assessment tool")
    print("-" * 60)


def create_analyzer(args) -> RepoHealthAnalyzer:
    """Create and initialize the RepoHealthAnalyzer."""
    print("\n📚 Initializing Repository Health Analyzer...")
    try:
        analyzer = RepoHealthAnalyzer(
            api_base_url=args.api_base,
            api_key=args.api_key,
            embedding_model_name=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            collection_name=args.collection,
        )
        print("✓ Repository Health Analyzer initialized")
        return analyzer
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def handle_github_url(url: str) -> str:
    """Handle GitHub URL cloning."""
    print(f"\n🌐 Detected GitHub URL: {url}")

    # Extract repo name
    if url.startswith("http"):
        repo_name = url.split("/")[-1].replace(".git", "")
    else:
        repo_name = url.split(":")[-1].split("/")[-1].replace(".git", "")

    local_path = os.path.join("reviewing", repo_name)

    # Clean up any existing directory
    if os.path.exists(local_path):
        print(f"🗑️  Removing existing directory: {local_path}")
        shutil.rmtree(local_path)

    # Clone repository
    print(f"📥 Cloning repository to: {local_path}")
    try:
        import git

        os.makedirs("reviewing", exist_ok=True)
        repo = git.Repo.clone_from(url, local_path)
        print("✅ Repository cloned successfully")
        return local_path
    except Exception as e:
        print(f"❌ Failed to clone repository: {e}")
        sys.exit(1)


def cmd_analyze(args):
    """Handle the analyze command."""
    print("\n🏥 Starting repository health analysis...")

    analyzer = create_analyzer(args)

    # Determine target path
    target_path = args.target or "."

    # Handle GitHub URLs
    if target_path.startswith(("http", "git@", "github.com")):
        target_path = handle_github_url(target_path)

    try:
        results = analyzer.analyze_repository_health(
            directory_path=target_path,
            output_file=args.output,
            include_llm_analysis=not args.quick,
            generate_missing_files=args.generate_files,
            context_overrides={
                "author_name": args.author_name,
                "author_email": args.author_email,
                "description": args.description,
            }
            if any([args.author_name, args.author_email, args.description])
            else None,
        )

        # Display summary
        health_scores = results["health_scores"]
        grade = results["overall_grade"]

        print("\n📊 Analysis Complete!")
        print(f"Overall Health Score: {health_scores['overall']}/100 ({grade})")
        print(f"📄 Report saved to: {results['report_file']}")

        if args.show_scores:
            print("\n🏥 Health Breakdown:")
            for category, score in health_scores.items():
                if category != "overall":
                    print(f"  {category.title()}: {score}/100")

        if results["missing_files_generated"]:
            print(f"\n📝 Generated {len(results['missing_files_generated'])} missing files")

        # Ask if user wants to see the report
        if not args.no_prompt:
            try:
                show_report = input("\nView report now? (y/N): ").strip().lower()
                if show_report in ["y", "yes"]:
                    with open(results["report_file"], encoding="utf-8") as f:
                        print("\n" + "=" * 80)
                        print(f.read())
                        print("=" * 80)
            except (KeyboardInterrupt, EOFError):
                pass

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


def cmd_improve(args):
    """Handle the improve command."""
    print("\n🎯 Generating improvement suggestions...")

    analyzer = create_analyzer(args)
    target_path = args.target or "."

    try:
        suggestions = analyzer.suggest_improvements(
            directory_path=target_path, focus_areas=args.focus_areas
        )

        health_scores = suggestions["health_scores"]
        print(f"\nCurrent Health Score: {health_scores['overall']}/100")

        if suggestions["priority_actions"]:
            print("\n🚨 Priority Actions:")
            for action in suggestions["priority_actions"]:
                print(f"  {action}")

        if suggestions["missing_files"]:
            print(f"\n📝 Missing Files ({len(suggestions['missing_files'])}):")
            for file in suggestions["missing_files"]:
                print(f"  - {file}")

        if suggestions["file_improvements"]:
            print(f"\n🔧 File Improvements ({len(suggestions['file_improvements'])}):")
            for imp in suggestions["file_improvements"][:5]:  # Show top 5
                priority = imp.get("priority", "medium").upper()
                print(f"  [{priority}] {imp.get('title', 'Unknown')}: {imp.get('description', '')}")

        print("\n💡 Tip: Use 'repohealth generate' to create missing files automatically")

    except Exception as e:
        print(f"❌ Failed to generate suggestions: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


def cmd_generate(args):
    """Handle the generate command."""
    print("\n📝 Generating missing repository files...")

    analyzer = create_analyzer(args)
    target_path = args.target or "."

    try:
        results = analyzer.generate_missing_files(
            directory_path=target_path,
            file_types=args.files,
            context_overrides={
                "author_name": args.author_name,
                "author_email": args.author_email,
                "description": args.description,
                "license_type": args.license,
            }
            if any([args.author_name, args.author_email, args.description, args.license])
            else None,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print("\n👀 Preview Mode - No files were created:")
        else:
            print("\n✅ File Generation Complete:")

        successful = [r for r in results if r.get("status") in ["created", "would_create"]]
        errors = [r for r in results if r.get("status") == "error"]

        if successful:
            print(
                f"\n📄 Files {'to be created' if args.dry_run else 'created'} ({len(successful)}):"
            )
            for result in successful:
                print(f"  ✅ {result.get('path', 'Unknown')}")

        if errors:
            print(f"\n❌ Errors ({len(errors)}):")
            for result in errors:
                print(
                    f"  ❌ {result.get('path', 'Unknown')}: {result.get('error', 'Unknown error')}"
                )

        if args.dry_run and successful:
            print("\n💡 To actually create these files, run without --dry-run")
        elif successful and not args.dry_run:
            print("\n🎯 Next steps:")
            print("  1. Review and customize the generated files")
            print("  2. Update project-specific information")
            print("  3. Commit the new files to your repository")

    except Exception as e:
        print(f"❌ File generation failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


def cmd_chat(args):
    """Handle the chat command (interactive mode)."""
    analyzer = create_analyzer(args)

    # Index target if provided
    if args.target:
        target_path = args.target
        if target_path.startswith(("http", "git@", "github.com")):
            target_path = handle_github_url(target_path)

        print(f"\n📚 Indexing {target_path}...")
        try:
            stats = analyzer.process_directory(target_path)
            print(f"✓ Indexed {stats['total_files']} files")
        except Exception as e:
            print(f"❌ Failed to index: {e}")
            return 1

    interactive_mode(analyzer, args.verbose)
    return 0


def interactive_mode(analyzer: RepoHealthAnalyzer, verbose: bool = False):
    """Run interactive query mode"""
    print("\nEntering interactive mode. Commands:")
    print("- Type your questions to query the indexed content")
    print("- '/tools on' or '/tools off' to toggle tool usage")
    print("- '/history' to see recent queries")
    print("- '/reindex [path]' to reindex a directory")
    print("- '/health [path]' to run health analysis")
    print("- '/improve [path]' to get improvement suggestions")
    print("- '/quit' or '/exit' to exit")
    print("-" * 60)

    use_tools = True

    while True:
        try:
            query = input("\n🔍 Query: ").strip()

            if not query:
                continue

            # Handle commands
            if query.lower() in ["/quit", "/exit", "/q"]:
                print("\n👋 Goodbye!")
                break
            if query.lower() == "/history":
                history = analyzer.get_session_history()
                if history:
                    print("\n📜 Recent queries:")
                    for entry in history:
                        if entry.get("type") == "user_query":
                            print(f"  - {entry.get('content', '')}")
                else:
                    print("\n📜 No query history found")
                continue
            if query.lower() == "/tools on":
                use_tools = True
                print("🔧 Tool usage enabled")
                continue
            if query.lower() == "/tools off":
                use_tools = False
                print("🔧 Tool usage disabled")
                continue
            if query.startswith("/reindex"):
                parts = query.split(maxsplit=1)
                path = parts[1] if len(parts) > 1 else "."
                print(f"🔄 Reindexing {path}...")
                try:
                    stats = analyzer.process_directory(path)
                    print(f"✓ Reindexed {stats['total_files']} files")
                except Exception as e:
                    print(f"❌ Reindexing failed: {e}")
                continue
            if query.startswith("/health"):
                parts = query.split(maxsplit=1)
                path = parts[1] if len(parts) > 1 else "."
                print(f"🏥 Running health analysis on {path}...")
                try:
                    results = analyzer.analyze_repository_health(
                        directory_path=path,
                        output_file="interactive_health_report.md",
                        include_llm_analysis=False,
                    )
                    health_scores = results["health_scores"]
                    print(
                        f"📊 Health Score: {health_scores['overall']}/100 ({results['overall_grade']})"
                    )
                    print(f"📄 Report: {results['report_file']}")
                except Exception as e:
                    print(f"❌ Health analysis failed: {e}")
                continue
            if query.startswith("/improve"):
                parts = query.split(maxsplit=1)
                path = parts[1] if len(parts) > 1 else "."
                print(f"🎯 Getting improvement suggestions for {path}...")
                try:
                    suggestions = analyzer.suggest_improvements(directory_path=path)
                    print(f"Priority actions: {len(suggestions['priority_actions'])}")
                    print(f"Missing files: {len(suggestions['missing_files'])}")
                    print(f"File improvements: {len(suggestions['file_improvements'])}")
                    if suggestions["priority_actions"]:
                        print("\nTop priority actions:")
                        for action in suggestions["priority_actions"][:3]:
                            print(f"  {action}")
                except Exception as e:
                    print(f"❌ Failed to get suggestions: {e}")
                continue

            # Regular query
            print("🤔 Thinking...", end="", flush=True)
            try:
                response = analyzer.query(query, use_tools=use_tools)
                print("\r" + " " * 50 + "\r", end="")  # Clear "Thinking..." message
                print(f"🤖 Assistant:\n{response}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                if verbose:
                    import traceback

                    traceback.print_exc()

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type '/quit' to exit.")
        except EOFError:
            print("\n\n👋 Goodbye!")
            break


def main():
    """Main entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="GitHub Repository Health Analyzer - AI-powered repository health analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  repohealth analyze                    # Analyze current directory
  repohealth analyze /path/to/repo      # Analyze specific directory
  repohealth analyze --quick            # Quick analysis without LLM
  repohealth improve --focus security   # Focus on security improvements
  repohealth generate --files README    # Generate README.md only
  repohealth chat                       # Interactive chat mode""",
    )

    # Common arguments
    parser.add_argument(
        "--api-base",
        default=os.environ.get("OPENAI_API_BASE", "http://localhost:11434/v1"),
        help="OpenAI-compatible API base URL",
    )

    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", "sk-xxxxxxxxxxxxxxxx"),
        help="API key (placeholder for local servers)",
    )

    parser.add_argument(
        "--embedding-model",
        default="all-MiniLM-L6-v2",
        help="HuggingFace embedding model name",
    )

    parser.add_argument(
        "--chunk-size", type=int, default=1000, help="Text chunk size for splitting"
    )

    parser.add_argument(
        "--chunk-overlap", type=int, default=200, help="Overlap between text chunks"
    )

    parser.add_argument(
        "--collection", default="llm_librarian", help="ChromaDB collection name prefix"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze repository health")
    analyze_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Directory path or GitHub URL to analyze (default: current directory)",
    )
    analyze_parser.add_argument(
        "--output",
        default="health_report.md",
        help="Output file for health report (default: health_report.md)",
    )
    analyze_parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick analysis without detailed LLM analysis",
    )
    analyze_parser.add_argument(
        "--generate-files",
        action="store_true",
        help="Automatically generate missing files during analysis",
    )
    analyze_parser.add_argument(
        "--show-scores",
        action="store_true",
        help="Show detailed score breakdown",
    )
    analyze_parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Don't prompt to view report",
    )
    analyze_parser.add_argument(
        "--author-name",
        help="Author name for generated files",
    )
    analyze_parser.add_argument(
        "--author-email",
        help="Author email for generated files",
    )
    analyze_parser.add_argument(
        "--description",
        help="Project description for generated files",
    )

    # Improve command
    improve_parser = subparsers.add_parser("improve", help="Get improvement suggestions")
    improve_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Directory path to analyze (default: current directory)",
    )
    improve_parser.add_argument(
        "--focus-areas",
        nargs="+",
        choices=["documentation", "security", "testing", "community", "ci_cd", "legal"],
        help="Focus on specific areas for improvements",
    )

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate missing repository files")
    generate_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Directory path (default: current directory)",
    )
    generate_parser.add_argument(
        "--files",
        nargs="+",
        help="Specific file types to generate (README, CONTRIBUTING, SECURITY, etc.)",
    )
    generate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be generated without creating files",
    )
    generate_parser.add_argument(
        "--author-name",
        help="Author name for generated files",
    )
    generate_parser.add_argument(
        "--author-email",
        help="Author email for generated files",
    )
    generate_parser.add_argument(
        "--description",
        help="Project description for generated files",
    )
    generate_parser.add_argument(
        "--license",
        default="MIT",
        help="License type for generated files (default: MIT)",
    )

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Interactive chat mode")
    chat_parser.add_argument(
        "target",
        nargs="?",
        help="Directory path or GitHub URL to index first (optional)",
    )

    # Legacy support
    parser.add_argument(
        "--auto-analyze",
        action="store_true",
        help="Legacy: use 'analyze' command instead",
    )
    parser.add_argument(
        "--output",
        help="Legacy: use 'analyze --output' instead",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Legacy: use specific commands instead",
    )

    # Positional argument for legacy support
    parser.add_argument(
        "legacy_target",
        nargs="?",
        help="Directory path or GitHub URL (use subcommands for better control)",
    )

    args = parser.parse_args()

    print_banner()

    # Handle legacy mode (no subcommand)
    if not args.command:
        if args.auto_analyze:
            # Legacy auto-analyze mode
            print("\n⚠️  --auto-analyze is deprecated. Use 'repohealth analyze' instead.")
            # Convert to analyze command
            args.command = "analyze"
            args.target = args.legacy_target or "."
            args.quick = False
            args.generate_files = False
            args.show_scores = False
            args.no_prompt = False
            args.author_name = None
            args.author_email = None
            args.description = None
            if not hasattr(args, "output") or not args.output:
                args.output = "health_report.md"
        elif args.legacy_target:
            # Legacy mode with target - switch to analyze
            print("\n💡 Tip: Use 'repohealth analyze' for better control over analysis options.")
            args.command = "analyze"
            args.target = args.legacy_target
            args.quick = False
            args.generate_files = False
            args.show_scores = True
            args.no_prompt = False
            args.author_name = None
            args.author_email = None
            args.description = None
            if not hasattr(args, "output") or not args.output:
                args.output = "health_report.md"
        else:
            # Default to chat mode
            print("\n💡 Tip: Use subcommands for specific actions:")
            print("  repohealth analyze    - Analyze repository health")
            print("  repohealth improve    - Get improvement suggestions")
            print("  repohealth generate   - Generate missing files")
            print("  repohealth chat       - Interactive chat mode")
            args.command = "chat"
            args.target = None

    # Route to appropriate command handler
    try:
        if args.command == "analyze":
            return cmd_analyze(args)
        if args.command == "improve":
            return cmd_improve(args)
        if args.command == "generate":
            return cmd_generate(args)
        if args.command == "chat":
            return cmd_chat(args)
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
