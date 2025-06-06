# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing and CI/CD.

## Workflows

### 1. `ci.yml` - Main CI Pipeline ⚡
**Triggers:** Push/PR to `main` or `develop` branches

**What it does:**
- Tests across Python 3.8-3.12
- Runs unit tests (no external dependencies)
- Runs integration tests (mocked LLM)
- Runs legacy compatibility tests
- Linting and formatting checks with ruff
- Coverage reporting
- Tests different installation methods

**Duration:** ~5-10 minutes per Python version

### 2. `test.yml` - Comprehensive Testing 🧪
**Triggers:** Push/PR to `main` or `develop` branches

**What it does:**
- Multi-version Python testing
- Comprehensive test suite
- Code quality checks (ruff, mypy)
- Package installation verification
- Coverage reporting with Codecov

**Duration:** ~10-15 minutes per Python version

### 3. `test-with-llm.yml` - LLM Integration Testing 🤖
**Triggers:** Manual only (`workflow_dispatch`)

**What it does:**
- Sets up Ollama service for real LLM testing
- Runs tests that require actual LLM responses
- Optional slow/comprehensive test runs
- Tests with different LLM endpoints

**Duration:** ~20-30 minutes (depending on model download)

## Test Categories

### ✅ **Always Run (No LLM Required)**
- **Unit Tests** (`tests/test_tools.py`, `tests/test_repo_reviewer_core.py`)
  - Tool system functionality
  - Core RepoReviewer features
  - File handling, caching, sessions
  - Error handling

- **Integration Tests** (`tests/test_integration.py`)
  - End-to-end workflows with mocked LLM
  - Tool calling integration
  - Auto-analysis workflow
  - GitHub repository analysis
  - CLI integration

- **Legacy Tests** (`tests/test_repo_reviewer.py`)
  - Backwards compatibility
  - Legacy API support

### 🤖 **Manual Trigger Only (Requires LLM)**
- **Real LLM Tests** (`tests/test_with_llm.py`)
  - Tests with actual LLM responses
  - Performance tests
  - Configuration tests

## Usage

### Running Tests Locally

```bash
# Quick test (unit + integration, no LLM)
python run_tests.py quick

# All tests except LLM
python run_tests.py unit && python run_tests.py integration

# With real LLM (requires local LLM server)
python run_tests.py with-llm

# Full test suite
python run_tests.py all
```

### Manual LLM Testing in GitHub Actions

1. Go to Actions tab in GitHub
2. Select "Tests with Real LLM" workflow
3. Click "Run workflow"
4. Optionally specify:
   - Custom LLM endpoint
   - Whether to run slow tests

### Coverage Reports

Coverage reports are automatically generated and uploaded to:
- **Codecov** (for public visibility)
- **GitHub Artifacts** (downloadable HTML reports)

## Configuration

### Environment Variables
- `TOKENIZERS_PARALLELISM=false` - Disables tokenizer warnings
- `ANTHROPIC_API_KEY` - Not needed for local LLM testing

### Test Markers
- `slow` - Long-running tests (excluded by default)
- `pytest -m "not slow"` - Run only fast tests

### Dependencies
All workflows install the package and its dependencies automatically. No additional setup required.

## Monitoring

### Status Badges
Add these to your README.md:

```markdown
![CI](https://github.com/yourusername/llm-repo-reviewer/workflows/CI/badge.svg)
![Tests](https://github.com/yourusername/llm-repo-reviewer/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/yourusername/llm-repo-reviewer/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/llm-repo-reviewer)
```

### Failure Investigation
1. Check the specific failed job in GitHub Actions
2. Review the test output and error messages
3. For LLM-related failures, check if the service was properly initialized
4. Download coverage reports from artifacts for detailed analysis
