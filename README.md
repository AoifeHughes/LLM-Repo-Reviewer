# LLM Librarian

An AI-powered code exploration tool that indexes your codebase and provides intelligent Q&A capabilities using ChromaDB for vector storage and OpenAI-compatible APIs.

## Features

- 🚀 **ChromaDB Vector Storage**: Fast and scalable semantic search
- 🔧 **Tool Calling**: AI can use `find` and `grep` commands for precise searches  
- 💾 **Smart Caching**: Only reprocess changed files
- 📚 **Multiple File Types**: Python, Markdown, PDF, YAML, JSON, and more
- 🤖 **OpenAI-Compatible**: Works with local LLMs (Ollama, llama.cpp, etc.)
- 🔍 **Interactive CLI**: Real-time Q&A about your codebase

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Run the tool
llmlibrarian

# Or specify a directory directly
llmlibrarian ~/my-project
```

## Configuration

### API Configuration

The tool uses OpenAI-compatible APIs. Configure your endpoint:

```bash
# For local Ollama server
export OPENAI_API_BASE="http://localhost:11434/v1"

# For OpenAI
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"
```

### Command Line Options

```bash
llmlibrarian [OPTIONS] [DIRECTORY]

Options:
  --api-base URL          OpenAI-compatible API base URL
  --api-key KEY           API key
  --embedding-model NAME  HuggingFace embedding model (default: all-MiniLM-L6-v2)
  --chunk-size SIZE       Text chunk size (default: 1000)
  --chunk-overlap SIZE    Chunk overlap (default: 200)
  --collection NAME       ChromaDB collection prefix
  -v, --verbose           Enable verbose output
  --no-interactive        Exit after indexing
```

## Interactive Commands

Once in interactive mode:

- **Ask questions**: Type naturally to query your codebase
- `/tools on|off`: Enable/disable AI tool usage (find, grep)
- `/history`: View recent queries
- `/reindex <path>`: Reindex a directory
- `/quit` or `/exit`: Exit the program

## Example Usage

```bash
# Index and explore a Python project
llmlibrarian ~/projects/my-python-app

# Query examples:
🔍 Query: What is the main purpose of this project?
🔍 Query: Find all test files
🔍 Query: Show me the database models
🔍 Query: Search for all TODO comments
```

## Tools Available to AI

The AI has access to system tools:

1. **find_files**: Search for files by name pattern
2. **grep_content**: Search file contents with regex
3. **get_file_info**: Get file metadata and statistics

## Development

### Running Tests

```bash
pytest tests/
pytest tests/test_librarian.py -v
```

### Code Quality

```bash
ruff check src/
mypy src/
```

## Architecture

- **ChromaDB**: Vector database for embeddings
- **LangChain**: Text splitting and document processing
- **Sentence Transformers**: Generate embeddings locally
- **OpenAI API**: Compatible with any LLM server

## Examples

See the `examples/` directory:
- `enhanced_demo.ipynb`: Jupyter notebook demonstrating features
- `turing_way.ipynb`: Original demo notebook

## License

MIT License - see LICENSE file for details.