#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI interface for LLMLibrarian with ChromaDB and tool calling"""

import os
import sys
import argparse
from .librarian import Librarian


def print_banner():
    """Print welcome banner"""
    print("\n" + "=" * 60)
    print("🤖 LLM Librarian")
    print("=" * 60)
    print("AI-powered code exploration with ChromaDB and tool calling")
    print("-" * 60)


def interactive_mode(librarian: Librarian, verbose: bool = False):
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
            elif query.lower() == "/history":
                history = librarian.get_session_history()
                if history:
                    print("\n📜 Recent queries:")
                    for entry in history:
                        if entry.get("type") == "user_query":
                            print(f"  - {entry.get('content', '')}")
                else:
                    print("No history available")
                continue
            elif query.lower() == "/tools on":
                use_tools = True
                print("✓ Tool usage enabled")
                continue
            elif query.lower() == "/tools off":
                use_tools = False
                print("✓ Tool usage disabled")
                continue
            elif query.lower().startswith("/reindex"):
                parts = query.split(maxsplit=1)
                if len(parts) > 1:
                    path = parts[1]
                    print(f"\n♻️  Reindexing {path}...")
                    try:
                        stats = librarian.process_directory(path)
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
                response = librarian.query(query, use_tools=use_tools)
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
        description="LLM Librarian - AI-powered code exploration"
    )

    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory to index (interactive prompt if not provided)",
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

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

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

    # Initialize librarian
    print("\n📚 Initializing LLM Librarian...")
    try:
        librarian = Librarian(
            api_base_url=args.api_base,
            api_key=args.api_key,
            embedding_model_name=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            collection_name=args.collection,
        )
        print("✓ Librarian initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)

    # Get directory to index
    if args.directory:
        directory = args.directory
    else:
        directory = input("\n📁 Enter directory path to index: ").strip()

    if not directory:
        print("❌ No directory provided")
        sys.exit(1)

    # Expand user path
    directory = os.path.expanduser(directory)
    directory = os.path.abspath(directory)

    # Check if auto-analyze mode
    if args.auto_analyze:
        try:
            report_file = librarian.auto_analyze(directory, args.output)
            print("\n🎉 Auto-analysis complete!")
            print(f"📄 Report saved to: {report_file}")

            # Ask if user wants to see the report
            try:
                show_report = (
                    input("\nWould you like to view the report now? (y/n): ")
                    .strip()
                    .lower()
                )
                if show_report in ["y", "yes"]:
                    with open(report_file, "r", encoding="utf-8") as f:
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
            stats = librarian.process_directory(directory)
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
            interactive_mode(librarian, verbose=args.verbose)


if __name__ == "__main__":
    main()
