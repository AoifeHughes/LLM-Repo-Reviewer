import os
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from openai import OpenAI
import hashlib
import json
from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import PyPDF2
from tqdm import tqdm
import subprocess
import shlex

# Suppress tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class Librarian:
    """LLM Librarian using ChromaDB for vector storage and OpenAI API for interactions"""
    
    def __init__(
        self,
        api_base_url: str = "http://localhost:11434/v1",
        api_key: str = "sk-xxxxxxxxxxxxxxxx",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        collection_name: str = "llm_librarian"
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
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Session management
        self.current_session_id = None
        self._start_new_session()
        
        # Tool definitions
        self.tools = self._define_tools()
    
    def _setup_collections(self):
        """Initialize ChromaDB collections"""
        try:
            # Content collection for document chunks
            try:
                self.content_collection = self.chroma_client.get_collection(f"{self.collection_name}_content")
                print(f"✓ Using existing content collection")
            except Exception:
                self.content_collection = self.chroma_client.create_collection(f"{self.collection_name}_content")
                print(f"✓ Created content collection")
            
            # Cache collection for file hashes
            try:
                self.cache_collection = self.chroma_client.get_collection(f"{self.collection_name}_cache")
                print(f"✓ Using existing cache collection")
            except Exception:
                self.cache_collection = self.chroma_client.create_collection(f"{self.collection_name}_cache")
                print(f"✓ Created cache collection")
            
            # Session collection for query history
            try:
                self.session_collection = self.chroma_client.get_collection(f"{self.collection_name}_sessions")
                print(f"✓ Using existing session collection")
            except Exception:
                self.session_collection = self.chroma_client.create_collection(f"{self.collection_name}_sessions")
                print(f"✓ Created session collection")
                
        except Exception as e:
            raise RuntimeError(f"Failed to setup ChromaDB collections: {e}")
    
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
    
    def _update_file_cache(self, file_path: str, file_hash: str, chunk_ids: List[str], metadata: Dict[str, Any]):
        """Update file cache with new hash and chunk references"""
        try:
            cache_data = {
                "file_path": file_path,
                "file_hash": file_hash,
                "last_modified": datetime.now().isoformat(),
                "chunk_ids": chunk_ids,
                "metadata": metadata
            }
            
            cache_id = f"cache_{hashlib.md5(file_path.encode()).hexdigest()}"
            
            # Remove existing cache entry if any
            try:
                self.cache_collection.delete(ids=[cache_id])
            except Exception:
                pass
            
            # Add new cache entry
            self.cache_collection.add(
                documents=[json.dumps(cache_data)],
                metadatas=[{
                    "file_path": file_path,
                    "last_modified": cache_data["last_modified"]
                }],
                ids=[cache_id]
            )
            
        except Exception as e:
            print(f"Error updating cache for {file_path}: {e}")
    
    def _extract_text_from_file(self, file_path: str) -> Optional[str]:
        """Extract text content from various file types"""
        try:
            _, ext = os.path.splitext(file_path.lower())
            
            if ext == '.pdf':
                return self._extract_pdf_text(file_path)
            elif ext in ['.py', '.md', '.txt', '.rst', '.json', '.yml', '.yaml', '.toml', '.cfg', '.ini']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif ext in ['', '.license'] and 'LICENSE' in os.path.basename(file_path).upper():
                with open(file_path, 'r', encoding='utf-8') as f:
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
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
        return text
    
    def process_directory(self, directory_path: str, file_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Process all files in a directory and store in ChromaDB"""
        if not os.path.exists(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")
        
        # Find all files
        all_files = []
        for root, dirs, files in os.walk(directory_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                file_path = os.path.join(root, file)
                if file_pattern:
                    # Use grep to check if file matches pattern
                    if self._file_matches_pattern(file_path, file_pattern):
                        all_files.append(file_path)
                else:
                    all_files.append(file_path)
        
        print(f"Found {len(all_files)} files to process")
        
        # Check cache and determine which files need processing
        files_to_process = []
        cached_files = []
        
        for file_path in all_files:
            if self._check_file_cache(file_path):
                cached_files.append(file_path)
            else:
                files_to_process.append(file_path)
        
        print(f"Using {len(cached_files)} cached files, processing {len(files_to_process)} new/changed files")
        
        # Process new/changed files
        if files_to_process:
            self._process_files(files_to_process, directory_path)
        
        return {
            "total_files": len(all_files),
            "cached_files": len(cached_files),
            "processed_files": len(files_to_process),
            "session_id": self.current_session_id
        }
    
    def _process_files(self, file_paths: List[str], base_directory: str):
        """Process multiple files in parallel"""
        documents = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._process_single_file, fp, base_directory): fp 
                      for fp in file_paths}
            
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
            "directory": os.path.dirname(rel_path)
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
            metadata = {k: v for k, v in chunk.metadata.items() if isinstance(v, (str, int, float, bool))}
            metadatas.append(metadata)
            chunk_ids.append(chunk.metadata["chunk_id"])
        
        # Delete existing chunks for these files
        for file_path in file_chunk_mapping.keys():
            try:
                self.content_collection.delete(where={"source": file_path})
            except Exception:
                pass
        
        # Add new chunks
        self.content_collection.add(
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
            ids=chunk_ids
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
                ["grep", "-l", pattern, file_path],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define tool functions for OpenAI API"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "find_files",
                    "description": "Find files in the indexed directory using the macOS find command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Starting directory path (defaults to current indexed directory)"
                            },
                            "name_pattern": {
                                "type": "string",
                                "description": "File name pattern (e.g., '*.py', 'test_*')"
                            },
                            "type": {
                                "type": "string",
                                "description": "File type: 'f' for files, 'd' for directories",
                                "enum": ["f", "d"]
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum depth to search (default: no limit)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "grep_content",
                    "description": "Search file contents using the macOS grep command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Search pattern (supports regular expressions)"
                            },
                            "path": {
                                "type": "string",
                                "description": "File or directory to search in"
                            },
                            "case_insensitive": {
                                "type": "boolean",
                                "description": "Case insensitive search (default: false)"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Search recursively in directories (default: false)"
                            },
                            "show_line_numbers": {
                                "type": "boolean",
                                "description": "Show line numbers in results (default: true)"
                            }
                        },
                        "required": ["pattern", "path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_file_info",
                    "description": "Get detailed information about a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            }
        ]
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool function and return the result"""
        try:
            if tool_name == "find_files":
                return self._tool_find_files(**arguments)
            elif tool_name == "grep_content":
                return self._tool_grep_content(**arguments)
            elif tool_name == "get_file_info":
                return self._tool_get_file_info(**arguments)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    def _tool_find_files(self, path: str = ".", name_pattern: str = None, type: str = "f", max_depth: int = None) -> str:
        """Execute find command"""
        cmd = ["find", path]
        
        if max_depth:
            cmd.extend(["-maxdepth", str(max_depth)])
        
        if type:
            cmd.extend(["-type", type])
        
        if name_pattern:
            cmd.extend(["-name", name_pattern])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                return f"Found {len(files)} items:\n" + "\n".join(files[:20])  # Limit to 20 results
            else:
                return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _tool_grep_content(self, pattern: str, path: str, case_insensitive: bool = False, 
                           recursive: bool = False, show_line_numbers: bool = True) -> str:
        """Execute grep command"""
        cmd = ["grep"]
        
        if case_insensitive:
            cmd.append("-i")
        if recursive:
            cmd.append("-r")
        if show_line_numbers:
            cmd.append("-n")
        
        cmd.extend([pattern, path])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                return f"Found {len(lines)} matches:\n" + "\n".join(lines[:20])  # Limit to 20 results
            elif result.returncode == 1:
                return "No matches found"
            else:
                return f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _tool_get_file_info(self, file_path: str) -> str:
        """Get file information"""
        try:
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"
            
            stat = os.stat(file_path)
            info = {
                "path": file_path,
                "size": f"{stat.st_size} bytes",
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_file": os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path)
            }
            
            if os.path.isfile(file_path):
                # Try to get line count
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                    info["lines"] = line_count
                except Exception:
                    pass
            
            return json.dumps(info, indent=2)
        except Exception as e:
            return f"Error: {str(e)}"
    
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
                Always provide accurate, helpful responses based on the indexed content."""
            }
        ]
        
        # Add context if available
        if context:
            messages.append({
                "role": "system",
                "content": f"Relevant context from the codebase:\n{context}"
            })
        
        messages.append({
            "role": "user",
            "content": question
        })
        
        # Log query to session
        self._log_to_session({
            "type": "user_query",
            "content": question,
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate response with optional tool use
        if use_tools:
            response = self.client.chat.completions.create(
                model="llama.cpp",  # This will use whatever model the server provides
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            # Handle tool calls if present
            if response.choices[0].message.tool_calls:
                tool_results = self._handle_tool_calls(response.choices[0].message.tool_calls)
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in response.choices[0].message.tool_calls
                    ]
                })
                
                # Add tool results
                messages.extend(tool_results)
                
                # Get final response
                final_response = self.client.chat.completions.create(
                    model="llama.cpp",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                answer = final_response.choices[0].message.content
            else:
                answer = response.choices[0].message.content
        else:
            # Simple response without tools
            response = self.client.chat.completions.create(
                model="llama.cpp",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            answer = response.choices[0].message.content
        
        # Log response
        self._log_to_session({
            "type": "assistant_response",
            "content": answer,
            "timestamp": datetime.now().isoformat()
        })
        
        return answer
    
    def _handle_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        """Execute tool calls and return results"""
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            result = self._execute_tool(function_name, arguments)
            
            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "content": result
            })
        
        return results
    
    def _get_relevant_context(self, query: str, max_chunks: int) -> str:
        """Retrieve relevant context from the vector store"""
        try:
            query_embedding = self.embedding_model.embed_query(query)
            
            results = self.content_collection.query(
                query_embeddings=[query_embedding],
                n_results=max_chunks,
                include=["documents", "metadatas"]
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
                **entry_data
            }
            
            self.session_collection.add(
                documents=[json.dumps(entry)],
                metadatas=[{
                    "session_id": self.current_session_id,
                    "type": entry_data.get("type", "unknown"),
                    "timestamp": entry_data.get("timestamp", datetime.now().isoformat())
                }],
                ids=[entry["entry_id"]]
            )
        except Exception as e:
            print(f"Warning: Error logging to session: {e}")
    
    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session history"""
        try:
            results = self.session_collection.query(
                query_embeddings=None,
                where={"session_id": self.current_session_id},
                n_results=limit
            )
            
            if results["documents"]:
                return [json.loads(doc) for doc in results["documents"][0]]
            return []
            
        except Exception:
            return []