import contextlib
import hashlib
import json
import os
import subprocess
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

import chromadb
import git
import pypdf
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
from tqdm import tqdm

from .analysis_template import REPORT_TEMPLATE
from .health_assessment import HEALTH_ANALYSIS_QUESTIONS, HealthAssessment
from .quality_scorer import HealthScores, QualityScorer
from .repo_editor import RepoEditor
from .repo_indexer import RepoIndexer
from .template_manager import TemplateManager
from .tools import default_registry as tool_registry

# Suppress tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class RepoHealthAnalyzer:
    """AI-powered repository health analysis and quality assessment tool using ChromaDB for vector storage and OpenAI API for interactions"""

    def __init__(
        self,
        api_base_url: str = "http://localhost:11434/v1",
        api_key: str = "sk-xxxxxxxxxxxxxxxx",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        collection_name: str = "llm_librarian",
    ):
        # Initialize OpenAI client
        self.client = OpenAI(base_url=api_base_url, api_key=api_key)

        # Initialize ChromaDB
        self.chroma_client = chromadb.Client()
        self.collection_name = collection_name

        # Initialize collections
        self._setup_collections()

        # Initialize embedding model
        self.embedding_model = HuggingFaceEmbeddings(model_name=embedding_model_name)

        # Text splitter configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )

        # Session management
        self.current_session_id = None
        self._start_new_session()

        # Initialize health analysis components
        self.repo_indexer = RepoIndexer()
        self.quality_scorer = QualityScorer()
        self.repo_editor = RepoEditor()
        self.template_manager = TemplateManager()
        self.health_assessment = HealthAssessment()

        # Tool registry
        self.tool_registry = tool_registry
        self.tools = self.tool_registry.get_openai_functions()

    def _setup_collections(self):
        """Initialize ChromaDB collections"""
        try:
            # Content collection for document chunks
            try:
                self.content_collection = self.chroma_client.get_collection(
                    f"{self.collection_name}_content"
                )
                print("✓ Using existing content collection")
            except Exception:
                self.content_collection = self.chroma_client.create_collection(
                    f"{self.collection_name}_content"
                )
                print("✓ Created content collection")

            # Cache collection for file hashes
            try:
                self.cache_collection = self.chroma_client.get_collection(
                    f"{self.collection_name}_cache"
                )
                print("✓ Using existing cache collection")
            except Exception:
                self.cache_collection = self.chroma_client.create_collection(
                    f"{self.collection_name}_cache"
                )
                print("✓ Created cache collection")

            # Session collection for query history
            try:
                self.session_collection = self.chroma_client.get_collection(
                    f"{self.collection_name}_sessions"
                )
                print("✓ Using existing session collection")
            except Exception:
                self.session_collection = self.chroma_client.create_collection(
                    f"{self.collection_name}_sessions"
                )
                print("✓ Created session collection")

        except Exception as e:
            msg = f"Failed to setup ChromaDB collections: {e}"
            raise RuntimeError(msg)

    def _start_new_session(self):
        """Start a new query session"""
        self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"Started new session: {self.current_session_id}")

    def _get_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return None

    def _check_file_cache(self, file_path: str) -> bool:
        """Check if file is cached and unchanged"""
        try:
            current_hash = self._get_file_hash(file_path)
            if not current_hash:
                return False

            cache_id = f"cache_{hashlib.md5(file_path.encode()).hexdigest()}"
            results = self.cache_collection.get(ids=[cache_id])

            if results["documents"] and len(results["documents"]) > 0:
                cached_data = json.loads(results["documents"][0])
                return cached_data.get("file_hash") == current_hash
            return False

        except Exception:
            return False

    def _update_file_cache(
        self,
        file_path: str,
        file_hash: str,
        chunk_ids: List[str],
        metadata: Dict[str, Any],
    ):
        """Update file cache with new hash and chunk references"""
        try:
            cache_data = {
                "file_path": file_path,
                "file_hash": file_hash,
                "last_modified": datetime.now().isoformat(),
                "chunk_ids": chunk_ids,
                "metadata": metadata,
            }

            cache_id = f"cache_{hashlib.md5(file_path.encode()).hexdigest()}"

            # Remove existing cache entry if any
            with contextlib.suppress(Exception):
                self.cache_collection.delete(ids=[cache_id])

            # Add new cache entry
            self.cache_collection.add(
                documents=[json.dumps(cache_data)],
                metadatas=[
                    {
                        "file_path": file_path,
                        "last_modified": cache_data["last_modified"],
                    }
                ],
                ids=[cache_id],
            )

        except Exception as e:
            print(f"Error updating cache for {file_path}: {e}")

    def _extract_text_from_file(self, file_path: str) -> Optional[str]:
        """Extract text content from various file types"""
        try:
            _, ext = os.path.splitext(file_path.lower())

            if ext == ".pdf":
                return self._extract_pdf_text(file_path)
            if ext in [
                ".py",
                ".md",
                ".txt",
                ".rst",
                ".json",
                ".yml",
                ".yaml",
                ".toml",
                ".cfg",
                ".ini",
            ] or (ext in ["", ".license"] and "LICENSE" in os.path.basename(file_path).upper()):
                with open(file_path, encoding="utf-8") as f:
                    return f.read()
            else:
                return None

        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return None

    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
        return text

    def _get_git_tracked_files(self, directory_path: str) -> List[str]:
        """Get list of git-tracked files in the directory"""
        try:
            # Check if directory is a git repository
            repo = git.Repo(directory_path)

            # Get all tracked files
            tracked_files = []
            for item in repo.index.entries:
                file_path = os.path.join(directory_path, item[0])
                # Only include files that exist and we can process
                if os.path.isfile(file_path):
                    tracked_files.append(file_path)

            return tracked_files

        except (git.exc.InvalidGitRepositoryError, git.exc.GitError):
            # Fallback to regular file discovery if not a git repo
            print("⚠️  Not a git repository, falling back to all files")
            return self._get_all_files_fallback(directory_path)

    def _get_all_files_fallback(self, directory_path: str) -> List[str]:
        """Fallback method to get all files when not in a git repository"""
        all_files = []
        for root, dirs, files in os.walk(directory_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ["__pycache__", "node_modules", "venv", "env"]
            ]

            for file in files:
                if file.startswith("."):
                    continue
                file_path = os.path.join(root, file)
                all_files.append(file_path)

        return all_files

    def process_directory(
        self, directory_path: str, file_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process all files in a directory and store in ChromaDB"""
        if not os.path.exists(directory_path):
            msg = f"Directory not found: {directory_path}"
            raise ValueError(msg)

        # Get git-tracked files only
        all_files = self._get_git_tracked_files(directory_path)

        # Apply file pattern filter if specified
        if file_pattern:
            filtered_files = []
            for file_path in all_files:
                if self._file_matches_pattern(file_path, file_pattern):
                    filtered_files.append(file_path)
            all_files = filtered_files

        print(f"Found {len(all_files)} git-tracked files to process")

        # Check cache and determine which files need processing
        files_to_process = []
        cached_files = []

        for file_path in all_files:
            if self._check_file_cache(file_path):
                cached_files.append(file_path)
            else:
                files_to_process.append(file_path)

        print(
            f"Using {len(cached_files)} cached files, processing {len(files_to_process)} new/changed files"
        )

        # Process new/changed files
        if files_to_process:
            self._process_files(files_to_process, directory_path)

        return {
            "total_files": len(all_files),
            "cached_files": len(cached_files),
            "processed_files": len(files_to_process),
            "session_id": self.current_session_id,
        }

    def _process_files(self, file_paths: List[str], base_directory: str):
        """Process multiple files in parallel"""
        documents = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._process_single_file, fp, base_directory): fp
                for fp in file_paths
            }

            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
                result = future.result()
                if result:
                    documents.append(result)

        if documents:
            self._store_documents(documents)

    def _process_single_file(self, file_path: str, base_directory: str) -> Optional[Document]:
        """Process a single file and return a Document object"""
        text = self._extract_text_from_file(file_path)
        if not text:
            return None

        # Create metadata
        rel_path = os.path.relpath(file_path, base_directory)
        metadata = {
            "source": file_path,
            "filename": os.path.basename(file_path),
            "relative_path": rel_path,
            "file_type": os.path.splitext(file_path)[1],
            "directory": os.path.dirname(rel_path),
        }

        return Document(page_content=text, metadata=metadata)

    def _store_documents(self, documents: List[Document]):
        """Store documents in ChromaDB after splitting into chunks"""
        all_chunks = []
        file_chunk_mapping = {}

        # Split documents into chunks
        for doc in documents:
            chunks = self.text_splitter.split_documents([doc])
            file_path = doc.metadata["source"]
            chunk_ids = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"chunk_{hashlib.md5((file_path + str(i)).encode()).hexdigest()}"
                chunk.metadata["chunk_id"] = chunk_id
                chunk.metadata["chunk_index"] = i
                chunk_ids.append(chunk_id)
                all_chunks.append(chunk)

            file_chunk_mapping[file_path] = chunk_ids

        if not all_chunks:
            return

        print(f"Storing {len(all_chunks)} chunks from {len(documents)} documents...")

        # Generate embeddings
        chunk_texts = [chunk.page_content for chunk in all_chunks]
        embeddings = self.embedding_model.embed_documents(chunk_texts)

        # Prepare data for ChromaDB
        metadatas = []
        chunk_ids = []

        for chunk in all_chunks:
            metadata = {
                k: v for k, v in chunk.metadata.items() if isinstance(v, (str, int, float, bool))
            }
            metadatas.append(metadata)
            chunk_ids.append(chunk.metadata["chunk_id"])

        # Delete existing chunks for these files
        for file_path in file_chunk_mapping:
            with contextlib.suppress(Exception):
                self.content_collection.delete(where={"source": file_path})

        # Add new chunks
        self.content_collection.add(
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
            ids=chunk_ids,
        )

        # Update cache
        for file_path, chunk_ids in file_chunk_mapping.items():
            file_hash = self._get_file_hash(file_path)
            if file_hash:
                doc = next(d for d in documents if d.metadata["source"] == file_path)
                self._update_file_cache(file_path, file_hash, chunk_ids, doc.metadata)

        print(f"✓ Successfully stored {len(all_chunks)} chunks")

    def _file_matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file content matches pattern using grep"""
        try:
            result = subprocess.run(
                ["grep", "-l", pattern, file_path], capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def register_tool(self, tool) -> None:
        """Register a new tool with the tool registry"""
        self.tool_registry.register(tool)
        # Update the tools list for OpenAI
        self.tools = self.tool_registry.get_openai_functions()

    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool from the tool registry"""
        self.tool_registry.unregister(tool_name)
        # Update the tools list for OpenAI
        self.tools = self.tool_registry.get_openai_functions()

    def list_tools(self) -> List[str]:
        """Get a list of all registered tool names"""
        return self.tool_registry.list_tools()

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool function using the tool registry"""
        return self.tool_registry.execute_tool(tool_name, arguments)

    def query(self, question: str, max_chunks: int = 5, use_tools: bool = True) -> str:
        """Query the indexed content and get an AI-generated response"""
        # Get relevant context from vector store
        context = self._get_relevant_context(question, max_chunks)

        # Prepare messages for chat
        messages = [
            {
                "role": "system",
                "content": """You are a helpful AI assistant with access to an indexed codebase.
                You can search through the code and documentation to answer questions.
                When appropriate, use the available tools to find specific files or search for patterns.
                Always provide accurate, helpful responses based on the indexed content.""",
            }
        ]

        # Add context if available
        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant context from the codebase:\n{context}",
                }
            )

        messages.append({"role": "user", "content": question})

        # Log query to session
        self._log_to_session(
            {
                "type": "user_query",
                "content": question,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Generate response with optional tool use
        if use_tools:
            response = self.client.chat.completions.create(
                model="llama.cpp",  # This will use whatever model the server provides
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000,
            )

            # Handle tool calls if present
            if response.choices[0].message.tool_calls:
                tool_results = self._handle_tool_calls(response.choices[0].message.tool_calls)

                # Add assistant message with tool calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in response.choices[0].message.tool_calls
                        ],
                    }
                )

                # Add tool results
                messages.extend(tool_results)

                # Get final response
                final_response = self.client.chat.completions.create(
                    model="llama.cpp",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000,
                )

                answer = final_response.choices[0].message.content
            else:
                answer = response.choices[0].message.content
        else:
            # Simple response without tools
            response = self.client.chat.completions.create(
                model="llama.cpp", messages=messages, temperature=0.7, max_tokens=1000
            )
            answer = response.choices[0].message.content

        # Log response
        self._log_to_session(
            {
                "type": "assistant_response",
                "content": answer,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return answer

    def _handle_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        """Execute tool calls and return results"""
        results = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            result = self._execute_tool(function_name, arguments)

            results.append({"tool_call_id": tool_call.id, "role": "tool", "content": result})

        return results

    def _get_relevant_context(self, query: str, max_chunks: int) -> str:
        """Retrieve relevant context from the vector store"""
        try:
            query_embedding = self.embedding_model.embed_query(query)

            results = self.content_collection.query(
                query_embeddings=[query_embedding],
                n_results=max_chunks,
                include=["documents", "metadatas"],
            )

            if not results["documents"][0]:
                return ""

            context_parts = []
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                source = metadata.get("filename", "Unknown")
                context_parts.append(f"[{source}]\n{doc}")

            return "\n\n---\n\n".join(context_parts)

        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""

    def _log_to_session(self, entry_data: Dict[str, Any]):
        """Log an entry to the current session"""
        try:
            entry = {
                "session_id": self.current_session_id,
                "entry_id": str(uuid.uuid4()),
                **entry_data,
            }

            self.session_collection.add(
                documents=[json.dumps(entry)],
                metadatas=[
                    {
                        "session_id": self.current_session_id,
                        "type": entry_data.get("type", "unknown"),
                        "timestamp": entry_data.get("timestamp", datetime.now().isoformat()),
                    }
                ],
                ids=[entry["entry_id"]],
            )
        except Exception as e:
            print(f"Warning: Error logging to session: {e}")

    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session history"""
        try:
            results = self.session_collection.query(
                query_embeddings=None,
                where={"session_id": self.current_session_id},
                n_results=limit,
            )

            if results["documents"]:
                return [json.loads(doc) for doc in results["documents"][0]]
            return []

        except Exception:
            return []

    def analyze_repository_health(
        self,
        directory_path: str,
        output_file: str = "health_report.md",
        include_llm_analysis: bool = True,
        generate_missing_files: bool = False,
        context_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive repository health analysis.

        Args:
            directory_path: Path to repository to analyze
            output_file: Output file for health report
            include_llm_analysis: Whether to include detailed LLM analysis
            generate_missing_files: Whether to generate missing standard files
            context_overrides: Additional context for file generation

        Returns:
            Dictionary with health analysis results
        """
        print("\n🏥 Starting repository health analysis...")

        # Ensure directory is indexed for RAG functionality
        self.process_directory(directory_path)

        # Step 1: Comprehensive repository indexing
        print("📊 Indexing repository metadata...")
        repo_metadata = self.repo_indexer.index_repository(directory_path)

        # Step 2: Calculate health scores
        print("⚕️ Calculating health scores...")
        health_scores = self.quality_scorer.calculate_health_scores(repo_metadata)

        # Step 3: Generate findings and recommendations
        print("🔍 Generating findings and recommendations...")
        findings = self.quality_scorer.generate_findings(repo_metadata, health_scores)
        recommendations = self.quality_scorer.generate_recommendations(
            repo_metadata, health_scores, findings
        )

        # Step 4: Optional LLM-based detailed analysis
        llm_analysis = {}
        if include_llm_analysis:
            print("🤖 Performing detailed LLM analysis...")
            llm_analysis = self._perform_llm_health_analysis()

        # Step 5: Generate missing files if requested
        missing_files_results = []
        if generate_missing_files:
            print("📝 Generating missing repository files...")
            context = context_overrides or {}
            missing_files_results = self.repo_editor.generate_missing_files(
                directory_path, repo_metadata, context, dry_run=False
            )

        # Step 6: Generate comprehensive health report
        print("📋 Generating health report...")
        report_content = self.health_assessment.generate_health_report(
            repo_metadata=repo_metadata,
            health_scores=health_scores,
            findings=findings,
            recommendations=recommendations,
            llm_analysis=llm_analysis,
        )

        # Write report to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        # Prepare results
        results = {
            "health_scores": health_scores.to_dict(),
            "findings": findings.to_dict(),
            "recommendations": recommendations,
            "repo_metadata": repo_metadata,
            "llm_analysis": llm_analysis,
            "missing_files_generated": missing_files_results,
            "report_file": output_file,
            "overall_grade": self._calculate_health_grade(health_scores.overall),
        }

        print(f"✅ Health analysis complete! Overall score: {health_scores.overall}/100")
        print(f"📄 Report saved to: {output_file}")

        return results

    def _perform_llm_health_analysis(self) -> Dict[str, str]:
        """Perform detailed LLM analysis for each health category."""
        analysis_results = {}
        total_questions = len(HEALTH_ANALYSIS_QUESTIONS)

        with tqdm(total=total_questions, desc="LLM Analysis") as pbar:
            for category, question in HEALTH_ANALYSIS_QUESTIONS.items():
                pbar.set_description(f"Analyzing: {category}")
                try:
                    answer = self.query(question, use_tools=True, max_context_chunks=20)
                    analysis_results[category] = answer
                except Exception as e:
                    analysis_results[category] = f"Error during analysis: {e!s}"
                pbar.update(1)

        return analysis_results

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

    def suggest_improvements(
        self, directory_path: str, focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Suggest specific improvements for repository health.

        Args:
            directory_path: Path to repository
            focus_areas: Optional list of areas to focus on (documentation, security, etc.)

        Returns:
            Dictionary with improvement suggestions
        """
        # Get repository metadata and health scores
        repo_metadata = self.repo_indexer.index_repository(directory_path)
        health_scores = self.quality_scorer.calculate_health_scores(repo_metadata)

        # Get file improvement suggestions
        file_improvements = self.repo_editor.suggest_file_improvements(
            directory_path, repo_metadata, health_scores
        )

        # Filter by focus areas if specified
        if focus_areas:
            file_improvements = [
                imp for imp in file_improvements if imp.get("category") in focus_areas
            ]

        # Get missing files
        missing_files = self.template_manager.get_missing_files(directory_path, repo_metadata)

        return {
            "health_scores": health_scores.to_dict(),
            "file_improvements": file_improvements,
            "missing_files": missing_files,
            "priority_actions": self._get_priority_actions(
                health_scores, file_improvements, missing_files
            ),
        }

    def _get_priority_actions(
        self,
        health_scores: HealthScores,
        file_improvements: List[Dict[str, Any]],
        missing_files: List[str],
    ) -> List[str]:
        """Get prioritized list of actions to take."""
        actions = []

        # Critical actions based on scores
        if health_scores.security < 50:
            actions.append("🚨 CRITICAL: Address security vulnerabilities immediately")

        if health_scores.overall < 40:
            actions.append("🚨 CRITICAL: Repository health is severely compromised")

        # High priority actions
        if "README.md" in missing_files:
            actions.append("🔴 HIGH: Create README.md file")

        if "SECURITY.md" in missing_files and health_scores.security < 70:
            actions.append("🔴 HIGH: Add security policy (SECURITY.md)")

        if health_scores.testing < 50:
            actions.append("🔴 HIGH: Improve test coverage")

        # Medium priority actions
        critical_improvements = [imp for imp in file_improvements if imp.get("priority") == "high"]
        for imp in critical_improvements[:3]:  # Top 3
            actions.append(f"🟡 MEDIUM: {imp.get('title', 'Unknown improvement')}")

        return actions[:10]  # Limit to top 10 actions

    def generate_missing_files(
        self,
        directory_path: str,
        file_types: Optional[List[str]] = None,
        context_overrides: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> List[Dict[str, str]]:
        """
        Generate missing repository files.

        Args:
            directory_path: Path to repository
            file_types: Optional list of specific file types to generate
            context_overrides: Additional context for template generation
            dry_run: If True, don't actually create files

        Returns:
            List of generated files with their status
        """
        repo_metadata = self.repo_indexer.index_repository(directory_path)

        # Get missing files
        missing_files = self.template_manager.get_missing_files(directory_path, repo_metadata)

        # Filter by file types if specified
        if file_types:
            missing_files = [f for f in missing_files if any(ft in f for ft in file_types)]

        # Generate files
        context = context_overrides or {}
        return self.repo_editor.generate_missing_files(
            directory_path, repo_metadata, context, dry_run
        )

    def auto_analyze(self, directory_path: str, output_file: str = "analysis_report.md") -> str:
        """Perform comprehensive codebase analysis and generate a report"""
        print("\n🔍 Starting automated codebase analysis...")

        # First, ensure the directory is indexed
        stats = self.process_directory(directory_path)

        # Gather project statistics
        project_stats = self._gather_project_stats(directory_path)

        # Run analysis questions
        analysis_results = {}
        total_questions = len(HEALTH_ANALYSIS_QUESTIONS)

        with tqdm(total=total_questions, desc="Analyzing codebase") as pbar:
            for key, question in HEALTH_ANALYSIS_QUESTIONS.items():
                pbar.set_description(f"Analyzing: {key}")
                try:
                    answer = self.query(question, use_tools=True)
                    analysis_results[key] = answer
                except Exception as e:
                    analysis_results[key] = f"Error during analysis: {e!s}"
                pbar.update(1)

        # Create the report
        print("\n📝 Generating report...")
        report_content = self._create_report(directory_path, stats, project_stats, analysis_results)

        # Write report to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"✅ Analysis complete! Report saved to: {output_file}")
        return output_file

    def _gather_project_stats(self, directory_path: str) -> Dict[str, Any]:
        """Gather basic project statistics"""
        stats = {
            "languages": Counter(),
            "file_types": Counter(),
            "total_files": 0,
            "dependencies": [],
            "loc_estimate": 0,
        }

        # Get git-tracked files and gather stats
        tracked_files = self._get_git_tracked_files(directory_path)

        for file_path in tracked_files:
            file_name = os.path.basename(file_path)
            _, ext = os.path.splitext(file_name.lower())

            stats["total_files"] += 1
            if ext:
                stats["file_types"][ext] += 1

                # Language detection
                if ext in [".py"]:
                    stats["languages"]["Python"] += 1
                elif ext in [".js", ".jsx"]:
                    stats["languages"]["JavaScript"] += 1
                elif ext in [".ts", ".tsx"]:
                    stats["languages"]["TypeScript"] += 1
                elif ext in [".java"]:
                    stats["languages"]["Java"] += 1
                elif ext in [".cpp", ".cc", ".cxx"]:
                    stats["languages"]["C++"] += 1
                elif ext in [".c"]:
                    stats["languages"]["C"] += 1
                elif ext in [".rs"]:
                    stats["languages"]["Rust"] += 1
                elif ext in [".go"]:
                    stats["languages"]["Go"] += 1
                elif ext in [".rb"]:
                    stats["languages"]["Ruby"] += 1
                elif ext in [".php"]:
                    stats["languages"]["PHP"] += 1
                elif ext in [".swift"]:
                    stats["languages"]["Swift"] += 1
                elif ext in [".kt"]:
                    stats["languages"]["Kotlin"] += 1

            # Estimate lines of code for text files
            if ext in [
                ".py",
                ".js",
                ".ts",
                ".java",
                ".cpp",
                ".c",
                ".rs",
                ".go",
                ".rb",
                ".php",
            ]:
                try:
                    with open(file_path, encoding="utf-8") as f:
                        stats["loc_estimate"] += sum(1 for line in f if line.strip())
                except Exception:
                    pass

        # Look for dependency files
        dependency_files = [
            "requirements.txt",
            "package.json",
            "Cargo.toml",
            "pom.xml",
            "build.gradle",
            "pyproject.toml",
        ]
        for dep_file in dependency_files:
            dep_path = os.path.join(directory_path, dep_file)
            if os.path.exists(dep_path):
                stats["dependencies"].append(dep_file)

        return stats

    def _create_report(
        self,
        directory_path: str,
        stats: Dict[str, Any],
        project_stats: Dict[str, Any],
        analysis_results: Dict[str, str],
    ) -> str:
        """Create the final markdown report"""

        # Create report from template
        return REPORT_TEMPLATE.format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            project_path=directory_path,
            total_files=stats.get("total_files", 0),
            primary_languages=(
                ", ".join(
                    f"{lang} ({count})" for lang, count in project_stats["languages"].most_common(3)
                )
                if project_stats["languages"]
                else "Not detected"
            ),
            file_types=(
                ", ".join(
                    f"{ext} ({count})" for ext, count in project_stats["file_types"].most_common(8)
                )
                if project_stats["file_types"]
                else "Not analyzed"
            ),
            loc_estimate=(
                f"~{project_stats['loc_estimate']:,}"
                if project_stats["loc_estimate"] > 0
                else "Not calculated"
            ),
            purpose=analysis_results.get("purpose", "Analysis not available"),
            languages=analysis_results.get("languages", "Analysis not available"),
            dependencies=analysis_results.get("dependencies", "Analysis not available"),
            architecture=analysis_results.get("architecture", "Analysis not available"),
            components=analysis_results.get("components", "Analysis not available"),
            testing=analysis_results.get("testing", "Analysis not available"),
            code_quality=analysis_results.get("code_quality", "Analysis not available"),
            documentation=analysis_results.get("documentation", "Analysis not available"),
            build_tools=analysis_results.get("build_tools", "Analysis not available"),
            ci_cd=analysis_results.get("ci_cd", "Analysis not available"),
            config=analysis_results.get("config", "Analysis not available"),
            security=analysis_results.get("security", "Analysis not available"),
        )

    @staticmethod
    def clone_github_repo(github_url: str, target_dir: str = "reviewing") -> str:
        """Clone a GitHub repository to a local directory for analysis"""
        import re
        import shutil

        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)

        # Extract repo name from URL
        repo_name_match = re.search(r"github\.com/[^/]+/([^/]+?)(?:\.git)?/?$", github_url)
        if not repo_name_match:
            msg = f"Invalid GitHub URL: {github_url}"
            raise ValueError(msg)

        repo_name = repo_name_match.group(1)
        local_path = os.path.join(target_dir, repo_name)

        # Remove existing directory if it exists
        if os.path.exists(local_path):
            print(f"🗑️  Removing existing directory: {local_path}")
            shutil.rmtree(local_path)

        # Clone the repository
        print(f"📥 Cloning repository: {github_url}")
        try:
            git.Repo.clone_from(github_url, local_path)
            print(f"✅ Repository cloned to: {local_path}")
            return local_path
        except git.exc.GitError as e:
            msg = f"Failed to clone repository: {e}"
            raise RuntimeError(msg)

    def analyze_github_repo(self, github_url: str, output_file: Optional[str] = None) -> str:
        """Clone a GitHub repo and perform analysis"""
        # Clone the repository
        local_path = self.clone_github_repo(github_url)

        # Generate output filename if not provided
        if output_file is None:
            repo_name = os.path.basename(local_path)
            output_file = f"{repo_name}_analysis_report.md"

        # Run auto-analysis
        return self.auto_analyze(local_path, output_file)
