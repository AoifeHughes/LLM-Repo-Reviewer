#!/usr/bin/env python3
"""CLI interface for LLM Repo Reviewer with ChromaDB and tool calling"""

import argparse
import os
import sys

from .repo_reviewer import RepoReviewer


def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 60)
    print("🤖 LLM Repo Reviewer")
    print("=" * 60)
    print("AI-powered repository analysis and code review tool")
    print("-" * 60)


def interactive_mode(reviewer: RepoReviewer, verbose: bool = False):
    """Run interactive query mode"""
    print("\nEntering interactive mode. Commands:")
    print("- Type your questions to query the indexed content")
    print("- '/tools on' or '/tools off' to toggle tool usage")
    print("- '/history' to see recent queries")
    print("- '/reindex [path]' to reindex a directory")
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
                history = reviewer.get_session_history()
                if history:
                    print("\n📜 Recent queries:")
                    for entry in history:
                        if entry.get("type") == "user_query":
                            print(f"  - {entry.get('content', '')}")
                else:
                    print("No history available")
                continue
            if query.lower() == "/tools on":
                use_tools = True
                print("✓ Tool usage enabled")
                continue
            if query.lower() == "/tools off":
                use_tools = False
                print("✓ Tool usage disabled")
                continue
            if query.lower().startswith("/reindex"):
                parts = query.split(maxsplit=1)
                if len(parts) > 1:
                    path = parts[1]
                    print(f"\n♻️  Reindexing {path}...")
                    try:
                        stats = reviewer.process_directory(path)
                        print(
                            f"✓ Indexed {stats['processed_files']} files ({stats['cached_files']} cached)"
                        )
                    except Exception as e:
                        print(f"❌ Error: {e}")
                else:
                    print("Usage: /reindex <directory_path>")
                continue

            # Process query
            print("\n💭 Thinking...", end="", flush=True)

            try:
                response = reviewer.query(query, use_tools=use_tools)
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
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="LLM Repo Reviewer - AI-powered repository analysis"
    )

    parser.add_argument(
        "target",
        nargs="?",
        help="Directory path or GitHub URL to analyze (interactive prompt if not provided)",
    )

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

    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Exit after indexing (no interactive mode)",
    )

    parser.add_argument(
        "--auto-analyze",
        action="store_true",
        help="Automatically analyze the codebase and generate a report",
    )

    parser.add_argument(
        "--output",
        default="analysis_report.md",
        help="Output file for auto-analysis report (default: analysis_report.md)",
    )

    args = parser.parse_args()

    print_banner()

    # Initialize reviewer
    print("\n📚 Initializing LLM Repo Reviewer...")
    try:
        reviewer = RepoReviewer(
            api_base_url=args.api_base,
            api_key=args.api_key,
            embedding_model_name=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            collection_name=args.collection,
        )
        print("✓ Repo Reviewer initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)

    # Get target to analyze
    if args.target:
        target = args.target
    else:
        target = input("\n📁 Enter directory path or GitHub URL to analyze: ").strip()

    if not target:
        print("❌ No target provided")
        sys.exit(1)

    # Determine if target is a GitHub URL or local path
    is_github_url = target.startswith(("https://github.com/", "git@github.com:", "github.com/"))

    if is_github_url:
        # Handle GitHub URL
        if not target.startswith("https://"):
            target = f"https://{target}" if target.startswith("github.com/") else target
        directory = target  # Will be handled by analyze_github_repo
    else:
        # Handle local directory
        directory = os.path.expanduser(target)
        directory = os.path.abspath(directory)

    # Check if auto-analyze mode
    if args.auto_analyze:
        try:
            if is_github_url:
                report_file = reviewer.analyze_github_repo(target, args.output)
            else:
                report_file = reviewer.auto_analyze(directory, args.output)
            print("\n🎉 Auto-analysis complete!")
            print(f"📄 Report saved to: {report_file}")

            # Ask if user wants to see the report
            try:
                show_report = (
                    input("\nWould you like to view the report now? (y/n): ").strip().lower()
                )
                if show_report in ["y", "yes"]:
                    with open(report_file, encoding="utf-8") as f:
                        print("\n" + "=" * 80)
                        print(f.read())
                        print("=" * 80)
            except (KeyboardInterrupt, EOFError):
                pass

        except Exception as e:
            print(f"❌ Auto-analysis failed: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)
    else:
        # Index the directory
        print(f"\n🔄 Indexing directory: {directory}")
        try:
            if is_github_url:
                print(f"\n🔄 Cloning and indexing repository: {target}")
                local_path = reviewer.clone_github_repo(target)
                stats = reviewer.process_directory(local_path)
                directory = local_path  # Update for interactive mode
            else:
                print(f"\n🔄 Indexing directory: {directory}")
                stats = reviewer.process_directory(directory)
            print("\n✅ Indexing complete!")
            print(f"   Total files: {stats['total_files']}")
            print(f"   Cached files: {stats['cached_files']}")
            print(f"   Processed files: {stats['processed_files']}")
        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)

        # Enter interactive mode unless disabled
        if not args.no_interactive:
            interactive_mode(reviewer, verbose=args.verbose)


if __name__ == "__main__":
    main()
