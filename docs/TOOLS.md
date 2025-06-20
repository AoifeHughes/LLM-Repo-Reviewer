# 🔧 Tools Documentation

The Repository Health Analyzer provides a comprehensive suite of tools that enable the AI to perform detailed repository analysis. These tools are organized into three main categories: Health Analysis Tools, File System Tools, and the underlying Tool Registry system.

## 🏗️ Tool Architecture

```mermaid
graph TB
    subgraph "LLM Integration"
        A[OpenAI Function Calling]
        B[Tool Registry]
        C[Tool Execution Engine]
    end

    subgraph "Health Analysis Tools"
        D[AnalyzeRepositoryHealthTool<br/>🏥 Complete Assessment]
        E[CheckDocumentationQualityTool<br/>📚 Documentation Review]
        F[SuggestImprovementsTool<br/>💡 Recommendations]
        G[GenerateMissingFilesTool<br/>📝 File Creation]
    end

    subgraph "File System Tools"
        H[FindFilesTool<br/>🔍 File Search]
        I[GrepContentTool<br/>📖 Content Search]
        J[GetFileInfoTool<br/>ℹ️ File Metadata]
    end

    subgraph "Core Components"
        K[Repository Indexer<br/>📁 Metadata Extraction]
        L[Quality Scorer<br/>⚡ Health Scoring]
        M[Template Manager<br/>🛠️ File Generation]
        N[ChromaDB<br/>💾 Vector Storage]
    end

    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I
    C --> J

    D --> K
    D --> L
    E --> K
    F --> L
    F --> M
    G --> M

    H --> N
    I --> N
    J --> N
```

## 🏥 Health Analysis Tools

These specialized tools provide comprehensive repository assessment capabilities that the LLM can invoke to analyze different aspects of repository health.

### 1. AnalyzeRepositoryHealthTool

**Purpose**: Performs complete health assessment with detailed scoring across all 6 categories.

**Function Schema**:
```json
{
  "name": "analyze_repository_health",
  "description": "Perform comprehensive health analysis of a repository and return detailed scores",
  "parameters": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository to analyze"
      },
      "analysis_depth": {
        "type": "string",
        "enum": ["quick", "standard", "deep"],
        "description": "Depth of analysis to perform",
        "default": "standard"
      },
      "focus_areas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Specific areas to focus on (documentation, security, testing, etc.)",
        "default": []
      }
    },
    "required": ["repo_path"]
  }
}
```

**Analysis Workflow**:
```mermaid
flowchart TD
    A[Tool Invocation] --> B[Index Repository<br/>📁 Structure Analysis]
    B --> C[Calculate Health Scores<br/>⚡ 6-Category Assessment]
    C --> D[Generate Findings<br/>🔍 Critical/High/Medium/Low]
    D --> E[Create Recommendations<br/>💡 Actionable Items]
    E --> F{Analysis Depth}

    F -->|Quick| G[Basic Summary<br/>- Overall Score<br/>- Critical Issues<br/>- Top Recommendations]
    F -->|Standard| H[Detailed Analysis<br/>- Full Score Breakdown<br/>- All Findings<br/>- Priority Recommendations]
    F -->|Deep| I[Comprehensive Report<br/>- Repository Statistics<br/>- Language Distribution<br/>- Security Details<br/>- Detailed Metrics]

    G --> J[Return Formatted Result]
    H --> J
    I --> J
```

**Example Usage**:
```python
# LLM can call this tool during conversation
result = analyze_repository_health(
    repo_path="/path/to/repo",
    analysis_depth="deep",
    focus_areas=["security", "testing"]
)
```

### 2. CheckDocumentationQualityTool

**Purpose**: Specialized assessment of documentation quality and completeness.

**Function Schema**:
```json
{
  "name": "check_documentation_quality",
  "description": "Analyze README, API docs, and project documentation quality",
  "parameters": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository",
        "default": "."
      },
      "check_completeness": {
        "type": "boolean",
        "description": "Check for missing documentation files",
        "default": true
      },
      "language_specific": {
        "type": "boolean",
        "description": "Include language-specific documentation recommendations",
        "default": true
      }
    },
    "required": ["repo_path"]
  }
}
```

**Documentation Assessment Process**:
```mermaid
flowchart LR
    A[Repository Path] --> B[README Analysis<br/>📄 Quality Scoring]
    A --> C[Documentation Files<br/>📚 Completeness Check]
    A --> D[Code Comments<br/>💬 Ratio Analysis]
    A --> E[Language Detection<br/>🔍 Primary Language]

    B --> F[README Score<br/>0-100 based on:<br/>- Sections completeness<br/>- Code examples<br/>- Links and badges]

    C --> G[Standard Docs Check<br/>- CHANGELOG<br/>- CONTRIBUTING<br/>- API docs<br/>- INSTALL]

    D --> H[Comment Ratio<br/>Comments / Total Lines<br/>Per file type]

    E --> I[Language-Specific Recs<br/>- Python: docstrings, Sphinx<br/>- JavaScript: JSDoc<br/>- Rust: /// comments<br/>- Java: JavaDoc]

    F --> J[Comprehensive Report]
    G --> J
    H --> J
    I --> J
```

### 3. SuggestImprovementsTool

**Purpose**: Generate actionable improvement suggestions based on health assessment.

**Function Schema**:
```json
{
  "name": "suggest_improvements",
  "description": "Generate actionable improvement suggestions for repository health",
  "parameters": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository",
        "default": "."
      },
      "priority_areas": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Areas to prioritize (security, documentation, testing, etc.)",
        "default": []
      },
      "include_templates": {
        "type": "boolean",
        "description": "Include information about available templates",
        "default": true
      }
    },
    "required": ["repo_path"]
  }
}
```

**Improvement Generation Flow**:
```mermaid
flowchart TD
    A[Repository Analysis] --> B[Health Score Calculation]
    B --> C[Missing Files Detection]
    C --> D[File Improvement Analysis]
    D --> E[Priority Classification]

    E --> F[🚨 Critical Actions<br/>- Security Score < 50<br/>- Missing README<br/>- Overall Score < 40]

    E --> G[📝 Missing Files<br/>- Standard files not found<br/>- Template availability<br/>- Generation priority]

    E --> H[🔧 File Improvements<br/>- Existing file enhancements<br/>- Quality improvements<br/>- Best practice alignment]

    E --> I[📊 Category Recommendations<br/>- Security improvements<br/>- Documentation gaps<br/>- Testing enhancements<br/>- CI/CD automation]

    F --> J[Prioritized Action Plan]
    G --> J
    H --> J
    I --> J
```

### 4. GenerateMissingFilesTool

**Purpose**: Create templates for missing standard repository files.

**Function Schema**:
```json
{
  "name": "generate_missing_files",
  "description": "Create templates for missing standard repository files",
  "parameters": {
    "type": "object",
    "properties": {
      "repo_path": {
        "type": "string",
        "description": "Path to the repository",
        "default": "."
      },
      "file_types": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Specific file types to generate (README, CONTRIBUTING, etc.)",
        "default": []
      },
      "customize_for_language": {
        "type": "boolean",
        "description": "Customize templates for the repository's primary language",
        "default": true
      },
      "dry_run": {
        "type": "boolean",
        "description": "Preview what would be generated without creating files",
        "default": true
      }
    },
    "required": ["repo_path"]
  }
}
```

**Template Generation System**:
```mermaid
flowchart TD
    A[Repository Path] --> B[Language Detection<br/>🔍 Primary Language]
    A --> C[Missing Files Analysis<br/>📄 Standard File Check]
    A --> D[Repository Metadata<br/>📊 Structure & Info]

    B --> E[Language Context<br/>- Test commands<br/>- Lint commands<br/>- Package manager<br/>- Framework specifics]

    C --> F[Template Selection<br/>- README.md<br/>- CONTRIBUTING.md<br/>- SECURITY.md<br/>- LICENSE<br/>- CI workflows<br/>- Issue templates]

    D --> G[Project Context<br/>- Repository name<br/>- Description<br/>- Author info<br/>- URLs]

    E --> H[Jinja2 Template Engine<br/>🛠️ Context Rendering]
    F --> H
    G --> H

    H --> I{Dry Run?}
    I -->|Yes| J[Preview Results<br/>📋 File list & sizes]
    I -->|No| K[Create Files<br/>✅ Write to filesystem]

    J --> L[Generation Report]
    K --> L
```

## 📁 File System Tools

These tools provide the AI with precise file system access capabilities for detailed repository exploration.

### 1. FindFilesTool

**Purpose**: Search for files by name patterns using glob syntax.

```mermaid
graph LR
    A[Pattern Query] --> B[Glob Search<br/>🔍 File Name Matching]
    B --> C[Filter Results<br/>📋 Relevance Scoring]
    C --> D[Sort by Modification<br/>⏰ Most Recent First]
    D --> E[Return File Paths<br/>📄 Absolute Paths]
```

**Example Patterns**:
- `**/*.py` - All Python files
- `**/test_*.py` - All test files
- `src/**/*.ts` - TypeScript files in src
- `*.md` - Markdown files in root
- `**/*config*` - Configuration files

### 2. GrepContentTool

**Purpose**: Search file contents using regular expressions.

```mermaid
graph LR
    A[Regex Pattern] --> B[Content Search<br/>🔍 Text Matching]
    B --> C[Include Filter<br/>📂 File Type Restriction]
    C --> D[Match Results<br/>📄 Files with Matches]
    D --> E[Sort by Modification<br/>⏰ Recent First]
```

**Example Patterns**:
- `TODO|FIXME|HACK` - Technical debt markers
- `password|secret|api_key` - Potential secrets
- `def\s+test_.*` - Python test functions
- `class\s+\w+Test` - Test classes
- `@Injectable|@Component` - Angular decorators

### 3. GetFileInfoTool

**Purpose**: Retrieve detailed metadata and statistics for files.

```mermaid
graph TB
    A[File Path] --> B[File System Stats<br/>📊 Size, Modified, Permissions]
    A --> C[Content Analysis<br/>📄 Lines, Characters, Type]
    A --> D[Git Information<br/>🌿 Last Commit, Author]

    B --> E[File Metadata Report<br/>📋 Comprehensive Info]
    C --> E
    D --> E
```

**Information Provided**:
- File size and last modified date
- Line count and character count
- File type and encoding
- Git blame information
- Directory structure context

## 🔄 Tool Registry System

The tool registry manages all available tools and provides the interface between the LLM and tool implementations.

### Registry Architecture

```mermaid
graph TB
    subgraph "Tool Registry Core"
        A[Tool Registry<br/>🗂️ Central Manager]
        B[Tool Registration<br/>📝 Add/Remove Tools]
        C[OpenAI Function Schema<br/>📋 Function Definitions]
        D[Tool Execution<br/>⚙️ Safe Invocation]
    end

    subgraph "Tool Categories"
        E[Health Tools<br/>🏥 4 Analysis Tools]
        F[File System Tools<br/>📁 3 Search Tools]
        G[Custom Tools<br/>🔧 Extensible System]
    end

    subgraph "LLM Integration"
        H[Function Calling<br/>🤖 Tool Selection]
        I[Parameter Validation<br/>✅ Input Checking]
        J[Result Processing<br/>📤 Output Formatting]
    end

    A --> B
    A --> C
    A --> D

    B --> E
    B --> F
    B --> G

    C --> H
    D --> I
    I --> J
```

### Tool Registration Process

```python
# Tools are automatically registered at startup
from .tools.health_tools import health_tools
from .tools.file_tools import file_tools

# Registry maintains tool instances
registry = ToolRegistry()
for tool in health_tools + file_tools:
    registry.register(tool)

# OpenAI function schemas are generated automatically
functions = registry.get_openai_functions()
```

### Function Calling Flow

```mermaid
sequenceDiagram
    participant U as User Query
    participant L as LLM
    participant R as Tool Registry
    participant T as Tool Instance
    participant S as System/Files

    U->>L: "Analyze repository security"
    L->>R: Call analyze_repository_health
    R->>T: Execute with parameters
    T->>S: Access repository files
    S->>T: Return file data
    T->>R: Processed results
    R->>L: Tool response
    L->>U: Analysis with findings
```

## 🛠️ Tool Development

### Creating Custom Tools

Tools implement the `BaseTool` interface:

```python
from .base import BaseTool

class CustomAnalysisTool(BaseTool):
    name = "custom_analysis"
    description = "Perform custom repository analysis"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Repository path"
                }
            },
            "required": ["repo_path"]
        }

    def execute(self, **kwargs) -> str:
        # Tool implementation
        return "Analysis results"
```

### Tool Integration

```python
# Register custom tool
analyzer = RepoHealthAnalyzer()
analyzer.register_tool(CustomAnalysisTool())

# Tool becomes available to LLM
# User: "Run custom analysis on this repo"
# LLM: *calls custom_analysis tool automatically*
```

## 📊 Tool Performance

### Execution Metrics

| Tool Category | Average Execution Time | Memory Usage | Typical Output Size |
|---------------|------------------------|--------------|-------------------|
| Health Analysis | 2-5 seconds | 50-100MB | 5-50KB text |
| Documentation Check | 1-2 seconds | 10-20MB | 2-10KB text |
| File Search | 0.1-0.5 seconds | 5-10MB | 1-5KB text |
| Content Grep | 0.5-2 seconds | 10-30MB | 2-20KB text |

### Optimization Features

- **Caching**: Results cached in ChromaDB for repeated queries
- **Indexing**: Repository metadata pre-indexed for fast access
- **Streaming**: Large results can be streamed for better UX
- **Parallelization**: Multiple tools can execute concurrently
- **Timeouts**: All tool executions have configurable timeouts

## 🔍 Tool Usage Examples

### Health Analysis Scenario

```
User: "Analyze the security of this Python project"

LLM Decision Making:
1. Detects security focus requirement
2. Calls analyze_repository_health with focus_areas=["security"]
3. Calls check_documentation_quality for security docs
4. Calls suggest_improvements with priority_areas=["security"]

Tool Execution:
- analyze_repository_health: Scans for vulnerabilities, secrets, policies
- check_documentation_quality: Looks for SECURITY.md, security sections
- suggest_improvements: Generates security-focused recommendations

Result: Comprehensive security assessment with specific action items
```

### File Generation Scenario

```
User: "This repository is missing standard community files"

LLM Decision Making:
1. Calls analyze_repository_health for overview
2. Calls generate_missing_files with dry_run=true
3. Based on results, asks user for confirmation
4. Calls generate_missing_files with dry_run=false

Tool Execution:
- Identifies missing: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
- Generates language-appropriate templates
- Creates files with project-specific context

Result: Repository enhanced with standard community health files
```

## 🚨 Error Handling

### Tool Execution Safety

```mermaid
flowchart TD
    A[Tool Call Request] --> B[Parameter Validation<br/>✅ Type & Required Checks]
    B --> C[Security Validation<br/>🔒 Path Traversal Protection]
    C --> D[Timeout Protection<br/>⏰ Execution Limits]
    D --> E[Tool Execution<br/>⚙️ Actual Work]
    E --> F[Exception Handling<br/>🛡️ Error Capture]
    F --> G[Result Sanitization<br/>🧹 Output Cleaning]
    G --> H[Return to LLM<br/>📤 Safe Response]

    B -->|Invalid| I[Parameter Error<br/>❌ Clear Error Message]
    C -->|Security Risk| J[Security Error<br/>🚫 Access Denied]
    D -->|Timeout| K[Timeout Error<br/>⏱️ Execution Halted]
    F -->|Exception| L[Runtime Error<br/>⚠️ Graceful Failure]
```

### Common Error Scenarios

1. **File Not Found**: Graceful handling with suggestions
2. **Permission Denied**: Clear error with resolution steps
3. **Timeout**: Partial results with continuation options
4. **Memory Limits**: Streaming or chunked processing
5. **Invalid Patterns**: Pattern validation with examples

---

The tool system forms the backbone of the Repository Health Analyzer's intelligent analysis capabilities, providing the LLM with precise, safe, and powerful repository exploration abilities.
