import os
import re
import io
import math
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Union, List, Tuple, Set, Dict, Literal
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pdf2image import convert_from_path
from sentence_transformers import CrossEncoder
from database import Connection, Immigrants, LawPersonnel, Functions
from documents_gateway import DocumentsGateway
from .config import (
    SPEED_OPTIMIZED_CONFIG,
    ACCURACY_OPTIMIZED_CONFIG,
    BALANCED_CONFIG,
    LARGE_SCALE_CONFIG,
    DEVELOPMENT_CONFIG,
)

load_dotenv()

db_func = Functions()
docs = DocumentsGateway()

class ProcessError(BaseException):
    desc: str


class RAGApplication:
    CONFIGS = {
        "speed": SPEED_OPTIMIZED_CONFIG,
        "accuracy": ACCURACY_OPTIMIZED_CONFIG,
        "balanced": BALANCED_CONFIG,
        "large_scale": LARGE_SCALE_CONFIG,
        "development": DEVELOPMENT_CONFIG,
    }

    def __init__(
        self,
        rag_config: Literal[
            "speed", "accuracy", "balanced", "large_scale", "development"
        ] = "balanced",
    ):
        self.db = Connection(database_actor="postgresql+psycopg")
        self.connection_string = self.db.connection_string

        self.rag_config = self.CONFIGS.get(rag_config, BALANCED_CONFIG)

        self.embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.rag_config.chunk_size,
            chunk_overlap=self.rag_config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.batch_size = self.rag_config.batch_size

        # Optional cross-encoder for re-ranking (can be disabled for speed)
        self.cross_encoder = None
        if self.rag_config.enable_cross_encoder:
            print("RAG: Initializing Cross-Encoder model for re-ranking...")
            self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            print("RAG: Cross-Encoder model initialized.")

        # Cache for vector stores and collection names
        self._vector_store_cache = {} if self.rag_config.enable_caching else None
        self._collection_name_cache = {} if self.rag_config.enable_caching else None

        print("OptimizedRAGApplication initialized successfully.")

    def _get_user_class(self, username: str) -> Tuple[
        Union[Immigrants, LawPersonnel, None],
        Literal["immigrant", "law_personnel", None],
    ]:
        """Helper to fetch user or law personnel class."""
        user = db_func.get_immigrant(username)
        if user:
            return user, "immigrant"
        lawyer = db_func.get_lawpersonnel(username)
        if lawyer:
            return lawyer, lawyer.personnel_type
        raise ModuleNotFoundError(f"User or Lawyer '{username}' not found in database.")

    def _get_collection_name_cached(self, username: str) -> str:
        """Helper method for collection name generation with optional caching."""
        if (
            self.rag_config.enable_caching
            and self._collection_name_cache
            and username in self._collection_name_cache
        ):
            return self._collection_name_cache[username]

        account_type = self._get_user_class(username)[1]

        if not account_type:
            print(f"Cannot determine account type for '{username}'.")
            return None

        safe_username = re.sub(r"[^a-zA-Z0-9_]", "_", username.lower())
        collection_name = f"{account_type}_rag_{safe_username}"
        if self.rag_config.enable_caching and self._collection_name_cache is not None:
            self._collection_name_cache[username] = collection_name
        return collection_name

    def _get_collection_name(self, username: str) -> str:
        """Main collection name method with conditional caching."""
        if self.rag_config.enable_caching:
            return self._get_collection_name_cached(username)
        else:
            account_type = self._get_user_class(username)[1]
            if not account_type:
                print(f"Cannot determine account type for '{username}'.")
                return None

            safe_username = re.sub(r"[^a-zA-Z0-9_]", "_", username.lower())
            return f"{account_type}_rag_{safe_username}"

    def get_vector_store(self, username: str) -> Union[PGVector, None]:
        """Get or create vector store with caching."""
        if (
            self.rag_config.enable_caching
            and self._vector_store_cache
            and username in self._vector_store_cache
        ):
            return self._vector_store_cache[username]

        collection_name = self._get_collection_name(username)
        if not collection_name:
            return None

        try:
            store = PGVector(
                embeddings=self.embeddings,
                collection_name=collection_name,
                connection_string=self.connection_string,
            )
            if self.rag_config.enable_caching and self._vector_store_cache is not None:
                self._vector_store_cache[username] = store
            print(
                f"RAG: Vector store interface ready for user: {username} (Collection: {collection_name})"
            )
            return store
        except Exception as e:
            print(
                f"RAG Error: Could not get vector store for {username}: {e}",
            )
            return None

    def _perform_retrieval(
        self,
        vector_store: PGVector,
        query: str,
        k: int,
        filter_dict: Optional[Dict] = None,
    ) -> List[Document]:
        """Performs the multi-stage retrieval: vector search -> reranking."""
        try:
            initial_k = min(
                self.rag_config.max_initial_candidates,
                self.rag_config.default_top_k * self.rag_config.initial_candidate_multiplier,
            )
            retriever = vector_store.as_retriever(
                search_kwargs={"k": initial_k, "filter": filter_dict}
            )
            initial_docs = retriever.invoke(query)

            if not initial_docs:
                return []

            if not self.cross_encoder:
                return initial_docs[:k]

            passage_query_pairs = [(doc.page_content, query) for doc in initial_docs]
            scores = self.cross_encoder.predict(passage_query_pairs)

            doc_scores = sorted(
                zip(initial_docs, scores), key=lambda x: x[1], reverse=True
            )

            return [doc for doc, score in doc_scores[:k]]
        except Exception as e:
            print(f"Error during retrieval stage: {e}")
            return []

    def _retrieve_from_specific_files(
        self, vector_store: PGVector, query: str, file_urls: List[str], top_k: int
    ) -> List[Document]:
        all_file_docs = []
        with ThreadPoolExecutor(max_workers=self.rag_config.max_workers) as executor:
            future_to_url = {
                executor.submit(
                    self._perform_retrieval,
                    vector_store,
                    query,
                    top_k,
                    {"original_url": url},
                ): url
                for url in file_urls
            }
            for future in as_completed(future_to_url):
                try:
                    docs = future.result()
                    all_file_docs.extend(docs)
                except Exception as e:
                    raise FileNotFoundError(
                        desc=f"Error retrieving from URL {future_to_url[future]}: {e}"
                    )

        if len(all_file_docs) > 1 and self.cross_encoder:
            passage_query_pairs = [(doc.page_content, query) for doc in all_file_docs]
            scores = self.cross_encoder.predict(passage_query_pairs)
            doc_scores = sorted(
                zip(all_file_docs, scores), key=lambda x: x[1], reverse=True
            )
            return [doc for doc, _ in doc_scores[:top_k]]
        return all_file_docs[:top_k]

    def _format_context(self, docs: List[Document], header_template: str) -> str:
        # Implementation from previous version
        context_str = ""
        for doc in docs:
            source_name = "User Profile"
            if "original_url" in doc.metadata:
                try:
                    source_name = os.path.basename(
                        urlparse(doc.metadata["original_url"]).path
                    )
                except Exception:
                    source_name = doc.metadata.get("source", "Unknown File")
            elif "source" in doc.metadata:
                source_name = doc.metadata["source"].replace("_", " ").title()

            header = header_template.format(source=source_name)
            context_str += f"\n{header}\n{doc.page_content}\n"
        return context_str

    def retrieve_hybrid_context(
        self,
        username: str,
        query: str,
        file_urls: Optional[List[str]] = None,
        top_k_files: int = 5,
        top_k_general: int = 3,
    ) -> str:
        # This is the advanced retrieval logic from the previous step
        vector_store = self.get_vector_store(username)
        if not vector_store:
            return "Error: Could not access user's information store."

        file_context = ""
        general_context = ""

        # Step 1: Prioritize uploaded files
        if file_urls:
            file_docs = self._retrieve_from_specific_files(
                vector_store, query, file_urls, top_k=top_k_files
            )
            if file_docs:
                file_context = self._format_context(
                    file_docs, "--- Context from Uploaded Document: {source} ---"
                )

        # Step 2: Enhance with general context
        general_filter = {"original_url": {"$nin": file_urls}} if file_urls else None
        general_docs = self._perform_retrieval(
            vector_store, query, k=top_k_general, filter_dict=general_filter
        )
        if general_docs:
            general_context = self._format_context(
                general_docs, "--- Background Context from Your History: {source} ---"
            )

        final_context = f"{file_context}\n\n{general_context}".strip()

        return final_context or "No relevant information found."

    def _calculate_content_hash(self, content: str, metadata: dict) -> str:
        """Calculate hash for content deduplication."""
        hash_input = (
            f"{content}_{metadata.get('source', '')}_{metadata.get('original_url', '')}"
        )
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _check_hash_exists(
        self, vector_store: PGVector, content_hash: str, source: str
    ) -> bool:
        """Check if content hash already exists in vector store."""
        if not vector_store or not content_hash:
            return False
        try:
            results = vector_store.similarity_search(
                query="*", k=1, filter={"content_hash": content_hash, "source": source}
            )
            return len(results) > 0
        except Exception as e:
            print(f"Hash check failed for {content_hash}: {e}")
            return False

    def _get_existing_file_urls(self, vector_store: PGVector) -> Set[str]:
        """Get all existing file URLs from vector store."""
        existing_urls = set()
        if not vector_store:
            return existing_urls
        try:
            # Use a more efficient query if possible
            docs = vector_store.similarity_search(query="*", k=10000)
            for doc in docs:
                if doc.metadata and "original_url" in doc.metadata:
                    existing_urls.add(doc.metadata["original_url"])
            print(f"Found {len(existing_urls)} existing file URLs in vector store.")
        except Exception as e:
            raise FileNotFoundError(
                f"Error fetching existing file URLs: {e}"
            )
        return existing_urls

    def _get_image_description(self, image_bytes: bytes, filename: str) -> str:
        """Get AI description of image with optimized prompt."""
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        try:
            print(f"RAG: Getting vision description for: {filename}")
            response = self.openai_client.chat.completions.create(
                model=self.rag_config.vision_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a forensic document analyst. Provide exhaustive visual descriptions without assumptions.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image and provide a highly detailed description for legal/immigration context. Transcribe all text verbatim. Describe all visual elements precisely.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": self.rag_config.vision_detail,
                                },
                            },
                        ],
                    },
                ],
                max_tokens=self.rag_config.vision_max_tokens,
                temperature=self.rag_config.vision_temperature,
            )
            description = response.choices[0].message.content
            print(f"RAG: Received description for {filename} (Length: {len(description)})")
            return description.strip() if description else ""
        except Exception as e:
            print(
                f"RAG Error: Failed to get AI description for {filename}: {e}"
            )
            return f"Image file: {filename}. Failed to get AI description."

    def _process_file_batch(
        self, username: str, file_urls: List[str]
    ) -> Tuple[List[Document], int, bool]:
        """Process a batch of files with parallel processing where possible."""
        docs_for_indexing = []
        processed_files_count = 0
        errors_occurred = False

        # Process files sequentially for now (can be optimized with threading for I/O)
        for https_url in file_urls:
            try:
                file_data = docs.download_file(https_url)
                if not file_data or "filename" not in file_data:
                    print(f"RAG: Failed to download file: {https_url}")
                    errors_occurred = True
                    continue

                filename = file_data["filename"]
                content_type = file_data.get("content_type", "")
                content_docs = []
                source = None

                # Process different file types
                if content_type.startswith("text/") and file_data.get("content"):
                    source = "uploaded_text"
                    chunks = self.text_splitter.split_text(file_data["content"])
                    for i, chunk_text in enumerate(chunks):
                        content_hash = self._calculate_content_hash(
                            chunk_text, {"source": source}
                        )
                        content_docs.append(
                            Document(
                                page_content=chunk_text,
                                metadata={
                                    "chunk_index": i,
                                    "content_nature": "text",
                                    "content_hash": content_hash,
                                },
                            )
                        )

                elif content_type.startswith("image/") and file_data.get("image_data"):
                    source = "uploaded_image"
                    description = self._get_image_description(
                        file_data["image_data"], filename
                    )
                    if description:
                        full_content = (
                            f"Image file: {filename}\nAI Description:\n{description}"
                        )
                        chunks = self.text_splitter.split_text(full_content)
                        for i, chunk_text in enumerate(chunks):
                            content_hash = self._calculate_content_hash(
                                chunk_text, {"source": source}
                            )
                            content_docs.append(
                                Document(
                                    page_content=chunk_text,
                                    metadata={
                                        "chunk_index": i,
                                        "content_nature": "image_description",
                                        "content_hash": content_hash,
                                    },
                                )
                            )

                elif content_type == "application/pdf" and file_data.get("filepath"):
                    source = "uploaded_document"
                    try:
                        images = convert_from_path(file_data["filepath"])
                        full_pdf_description = ""
                        for page_num, image in enumerate(images):
                            img_byte_arr = io.BytesIO()
                            image.save(img_byte_arr, format="PNG")
                            img_bytes = img_byte_arr.getvalue()
                            description = self._get_image_description(
                                img_bytes, f"{filename}-page-{page_num+1}"
                            )
                            full_pdf_description += (
                                f"\n\n--- Page {page_num+1} ---\n{description}"
                            )

                        if full_pdf_description:
                            full_content = f"PDF Document: {filename}\nAI-Generated Summary:\n{full_pdf_description}"
                            chunks = self.text_splitter.split_text(full_content)
                            for i, chunk_text in enumerate(chunks):
                                content_hash = self._calculate_content_hash(
                                    chunk_text, {"source": source}
                                )
                                content_docs.append(
                                    Document(
                                        page_content=chunk_text,
                                        metadata={
                                            "chunk_index": i,
                                            "content_nature": "pdf_description",
                                            "content_hash": content_hash,
                                        },
                                    )
                                )
                    except Exception as pdf_e:
                        print(
                            f"RAG Error: Failed to process PDF {filename}: {pdf_e}"
                        )
                        errors_occurred = True

                # Add metadata to all docs
                if content_docs:
                    for doc in content_docs:
                        doc.metadata.update(
                            {
                                "source": source,
                                "original_url": https_url,
                                "user": username,
                            }
                        )
                    docs_for_indexing.extend(content_docs)
                    processed_files_count += 1
                    print(
                        f"RAG: Processed '{filename}' into {len(content_docs)} chunks"
                    )

            except Exception as e:
                print(
                    f"RAG Error: Processing file {https_url}: {e}", exc_info=True
                )
                errors_occurred = True

        return docs_for_indexing, processed_files_count, errors_occurred

    def _process_user_data_sources(self, username: str) -> List[Document]:
        """Process KYC, profile, and message data into documents."""
        docs_to_add = []

        try:
            user_class, account_type = self._get_user_class(username)
            if not user_class:
                print(f"User '{username}' not found for data processing")
                return docs_to_add

            user_data = {
                k: v for k, v in user_class.extract_data().items() if v is not None
            }
            if user_data:
                profile_content = f"User Profile for {username}:\n"
                for key, value in user_data.items():
                    profile_content += f"{key}: {value}\n"

                content_hash = self._calculate_content_hash(
                    profile_content, {"source": "user_profile"}
                )
                docs_to_add.append(
                    Document(
                        page_content=profile_content,
                        metadata={
                            "source": "user_profile",
                            "user": username,
                            "content_nature": "profile",
                            "content_hash": content_hash,
                        },
                    )
                )

            # Process KYC data (if available)
            if account_type == "immigrant":
                try:
                    kyc_data = db_func.get_immigrant_kyc(user_class.email)
                    if kyc_data:
                        kyc_content = f"KYC Information for {username}:\n"
                        for key, value in kyc_data.items():
                            kyc_content += f"{key}: {value}\n"

                        content_hash = self._calculate_content_hash(
                            kyc_content, {"source": "kyc_summary"}
                        )
                        docs_to_add.append(
                            Document(
                                page_content=kyc_content,
                                metadata={
                                    "source": "kyc_summary",
                                    "user": username,
                                    "content_nature": "kyc",
                                    "content_hash": content_hash,
                                },
                            )
                        )
                except Exception as kyc_e:
                    raise Exception(
                        f"Error processing KYC data for {username}: {kyc_e}"
                    )

            # Process message history (if available)
            try:
                messages = db_func.retrieve_user_messages(user_email=user_class.email, user_type=account_type)
                if messages:
                    message_content = f"Recent Messages for {username}:\n"
                    for i, msg in enumerate(messages[-20:]):  # Last 20 messages
                        message_content += f"Message {i+1}: {msg}\n"

                    content_hash = self._calculate_content_hash(
                        message_content, {"source": "message_history"}
                    )
                    docs_to_add.append(
                        Document(
                            page_content=message_content,
                            metadata={
                                "source": "message_history",
                                "user": username,
                                "content_nature": "messages",
                                "content_hash": content_hash,
                            },
                        )
                    )
            except Exception as msg_e:

                print(
                    f"No message processing available for {username}: {msg_e}"
                )

        except Exception as e:
            raise ProcessError(desc=f"Error processing user data sources for {username}: {e}")

        return docs_to_add

    def setup_or_update_all_sources(
        self, username: str, force_refresh: bool = False
    ) -> bool:
        """Efficiently sync all data sources for the user."""
        vector_store = self.get_vector_store(username)
        if not vector_store:
            return False

        print(f"RAG: Starting optimized sync for user: {username}")
        all_docs_to_add = []

        # Process user data (profile, KYC, messages)
        user_docs = self._process_user_data_sources(username)
        all_docs_to_add.extend(user_docs)
        user_class, account_type = self._get_user_class(username)
        if not user_class:
            print(f"RAG: Cannot find user '{username}' in database.")
            return False
        # Process files
        try:
            existing_files = (
                set() if force_refresh else self._get_existing_file_urls(vector_store)
            )
            if account_type == "immigrant":
                s3_files = docs.retrieve_all_immigrant_files(username)
            else:
                s3_files = docs.retrieve_all_lawpersonnel_files(
                    username, user_class.personnel_type
                )

            if s3_files:
                files_to_process = [
                    url for url in s3_files if url not in existing_files
                ]
                if files_to_process:
                    print(f"Processing {len(files_to_process)} new files...")
                    file_docs, processed_count, errors = self._process_file_batch(
                        username, files_to_process
                    )
                    all_docs_to_add.extend(file_docs)

                    if errors:
                        print(f"Some file processing errors occurred for {username}")
                else:
                    print("No new files to process")
        except Exception as e:
            print(f"Error processing files for {username}: {e}")

        # Batch add documents
        if all_docs_to_add:
            try:
                total_docs = len(all_docs_to_add)
                num_batches = math.ceil(total_docs / self.batch_size)

                print(f"Adding {total_docs} documents in {num_batches} batches")

                for i in range(num_batches):
                    start_idx = i * self.batch_size
                    end_idx = min((i + 1) * self.batch_size, total_docs)
                    batch_docs = all_docs_to_add[start_idx:end_idx]

                    print(
                        f"Processing batch {i+1}/{num_batches} ({len(batch_docs)} docs)"
                    )
                    vector_store.add_documents(batch_docs)

                print(f"RAG: Successfully synced {total_docs} documents for {username}")
                return True

            except Exception as e:
                print(f"RAG: Failed to add documents for {username}: {e}")
                return False
        else:
            print(f"RAG: No new documents to sync for {username}")
            return True

    def _generate_hypothetical_answer(self, query: str) -> str:
        try:
            response = self.openai_client.chat.completions.create(
                model=self.rag_config.hyde_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Generate a concise, hypothetical answer to improve document retrieval. This will not be shown to the user.",
                    },
                    {"role": "user", "content": query},
                ],
                temperature=self.rag_config.hyde_temperature,
                max_tokens=self.rag_config.hyde_max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"RAG HyDE: Could not generate hypothetical answer: {e}")
            return query  # Fallback to original query

    def retrieve_context(
        self,
        username: str,
        query: str,
        top_k: int = None,
        use_hyde: bool = True,
        sources: List[str] = None,
    ) -> str:
        if top_k is None:
            top_k = self.rag_config.default_top_k

        print(
            f"RAG: Starting optimized retrieval for '{username}' with query: '{query}'"
        )

        vector_store = self.get_vector_store(username)
        if not vector_store:
            return "Error: Could not access user's information store."

        # Use HyDE for better retrieval if enabled
        search_query = query
        if use_hyde:
            search_query = self._generate_hypothetical_answer(query)

        # Get initial candidates
        initial_k = min(
            self.rag_config.max_initial_candidates,
            top_k * self.rag_config.initial_candidate_multiplier,
        )

        try:
            if sources:
                # Search within specific sources
                all_docs = []
                for source in sources:
                    source_docs = vector_store.similarity_search(
                        search_query,
                        k=initial_k // len(sources),
                        filter={"source": source},
                    )
                    all_docs.extend(source_docs)
                candidate_docs = all_docs
            else:
                # Search all sources
                candidate_docs = vector_store.similarity_search(
                    search_query, k=initial_k
                )

            if not candidate_docs:
                print(f"RAG: No documents found for query: '{query}'")
                return "No relevant information found."

            # Re-rank with cross-encoder if available
            if self.cross_encoder and len(candidate_docs) > top_k:
                sentence_pairs = [[query, doc.page_content] for doc in candidate_docs]
                scores = self.cross_encoder.predict(sentence_pairs)
                scored_docs = sorted(
                    zip(scores, candidate_docs), key=lambda x: x[0], reverse=True
                )
                top_documents = [doc for score, doc in scored_docs[:top_k]]
            else:
                top_documents = candidate_docs[:top_k]

            # Format response
            formatted_context = "Relevant Background Information:\n" + "=" * 40 + "\n"

            docs_by_source = {}
            for doc in top_documents:
                source = doc.metadata.get("source", "unknown")
                if source not in docs_by_source:
                    docs_by_source[source] = []
                docs_by_source[source].append(doc)

            for source, docs in docs_by_source.items():
                source_label = source.replace("_", " ").title()
                original_url = docs[0].metadata.get("original_url", "")
                source_info = (
                    f"{source_label} ({original_url})" if original_url else source_label
                )

                formatted_context += f"\n--- Context from: {source_info} ---\n"
                for doc in docs:
                    formatted_context += doc.page_content + "\n"
                formatted_context += f"--- End Context from: {source_label} ---\n"

            print(
                f"RAG: Retrieved {len(top_documents)} chunks from {len(docs_by_source)} sources"
            )
            return formatted_context.strip()

        except Exception as e:
            print(f"RAG Error during retrieval for '{username}': {e}", exc_info=True)
            return f"Error retrieving context: {str(e)}"

    def retrieve_specific_files(
        self, username: str, file_urls: List[str], query: str, k_per_file: int = 3
    ) -> str:
        """Retrieve context from specific files only."""
        vector_store = self.get_vector_store(username)
        if not vector_store:
            return "Error: Could not access user's information store."

        all_relevant_docs = []

        for file_url in file_urls:
            try:
                file_docs = vector_store.similarity_search(
                    query, k=k_per_file, filter={"original_url": file_url}
                )
                all_relevant_docs.extend(file_docs)
            except Exception as e:
                print(f"Error retrieving from file {file_url}: {e}")

        if not all_relevant_docs:
            return "No relevant information found in specified files."

        # Format response
        formatted_context = (
            "Relevant Information from Specified Files:\n" + "=" * 40 + "\n"
        )

        docs_by_file = {}
        for doc in all_relevant_docs:
            file_url = doc.metadata.get("original_url", "unknown")
            if file_url not in docs_by_file:
                docs_by_file[file_url] = []
            docs_by_file[file_url].append(doc)

        for file_url, docs in docs_by_file.items():
            filename = file_url.split("/")[-1] if "/" in file_url else file_url
            formatted_context += f"\n--- From File: {filename} ({file_url}) ---\n"
            for doc in docs:
                formatted_context += doc.page_content + "\n"

        return formatted_context.strip()

    def delete_store(self, username: str) -> bool:
        """Delete entire vector store for user."""
        try:
            vector_store = self.get_vector_store(username)
            if vector_store:
                vector_store.delete_collection()
                # Clear cache
                if self.rag_config.enable_caching:
                    if (
                        self._vector_store_cache
                        and username in self._vector_store_cache
                    ):
                        del self._vector_store_cache[username]
                    if (
                        self._collection_name_cache
                        and username in self._collection_name_cache
                    ):
                        del self._collection_name_cache[username]
                print(f"RAG: Successfully deleted store for {username}")
                return True
        except Exception as e:
            raise ProcessError(desc=f"RAG: Failed to delete store for {username}: {e}")
        return False

    def delete_by_source(self, username: str, sources: List[str]) -> bool:
        """Delete documents by source type."""
        vector_store = self.get_vector_store(username)
        if not vector_store:
            return False

        try:
            for source in sources:
                # This would need to be implemented based on your PGVector version
                vector_store.delete(filter={"source": source})
                print(f"Attempted to delete source '{source}' for user '{username}'")
            return True
        except Exception as e:
            print(f"Error deleting sources {sources} for {username}: {e}")
            return False

    def get_store_stats(self, username: str) -> Dict:
        """Get statistics about the user's vector store."""
        vector_store = self.get_vector_store(username)
        if not vector_store:
            return {"error": "Vector store not available"}

        try:
            # Get sample documents to analyze
            sample_docs = vector_store.similarity_search("*", k=1000)

            stats = {
                "total_documents": len(sample_docs),
                "sources": {},
                "content_types": {},
            }

            for doc in sample_docs:
                source = doc.metadata.get("source", "unknown")
                content_nature = doc.metadata.get("content_nature", "unknown")

                stats["sources"][source] = stats["sources"].get(source, 0) + 1
                stats["content_types"][content_nature] = (
                    stats["content_types"].get(content_nature, 0) + 1
                )

            return stats
        except Exception as e:
            print(f"Error getting stats for {username}: {e}")
            return {"error": str(e)}

    def update_config(self, new_config_name: str = None, **config_overrides) -> bool:
        try:
            if new_config_name:
                if new_config_name in self.CONFIGS:
                    self.rag_config = self.CONFIGS[new_config_name]
                    print(f"Switched to {new_config_name} configuration")
                else:
                    print(f"Unknown config name: {new_config_name}")
                    return False

            if config_overrides:
                for key, value in config_overrides.items():
                    if hasattr(self.rag_config, key):
                        setattr(self.rag_config, key, value)
                        print(f"Updated config {key} to {value}")
                    else:
                        print(f"Unknown config parameter: {key}")

            self._update_components_from_config()
            return True

        except Exception as e:
            print(f"Error updating config: {e}")
            return False

    def _update_components_from_config(self):
        """Update components that depend on configuration."""
        # Update text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.rag_config.chunk_size,
            chunk_overlap=self.rag_config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

        # Update batch size
        self.batch_size = self.rag_config.batch_size

        # Update cross-encoder if needed
        if self.rag_config.enable_cross_encoder and self.cross_encoder is None:
            print("Loading cross-encoder due to config change...")
            self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        elif (
            not self.rag_config.enable_cross_encoder and self.cross_encoder is not None
        ):
            print("Disabling cross-encoder due to config change...")
            self.cross_encoder = None

        # Update caching
        if not self.rag_config.enable_caching:
            self._vector_store_cache = None
            self._collection_name_cache = None
        elif self._vector_store_cache is None:
            self._vector_store_cache = {}
            self._collection_name_cache = {}
