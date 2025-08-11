"""
LangChain-based RAG Agent for EchoAI voice chat system.

This module implements a RAG system using LangChain with semantic search,
knowledge retrieval, and grounded answer generation capabilities.
"""

import os
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_URL
import shutil

# LangChain imports
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory

# Mistral integration
try:
    from langchain_mistralai import ChatMistralAI
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False

from src.utils import get_settings, get_logger
from src.db.db_operations import DBOperations

logger = get_logger(__name__)
settings = get_settings()

@dataclass
class ReplyCache:
    """Cache entry for semantic reply matching."""
    user_text: str
    response_text: str
    audio_file_path: str
    created_at: str
    similarity_score: float = 0.0

class LangChainRAGAgent:
    """LangChain-based RAG Agent for EchoAI with semantic search and knowledge retrieval."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_operations = DBOperations()
        
        # Initialize embeddings
        self.embeddings = SentenceTransformerEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Initialize vector store
        self.vector_store = self._setup_vector_store()
        
        # Initialize self-info knowledge base
        self.self_info_knowledge_base = self._setup_self_info_knowledge_base()
        
        # Initialize LLMs (Mistral primary, OpenAI fallback)
        self.primary_llm, self.fallback_llm = self._setup_llms()
        
        # Initialize RAG chain
        self.rag_chain = self._setup_rag_chain()
        
        # Initialize reply cache
        self.reply_cache = ReplyCacheManager(self.db_operations, self.vector_store)
        
        # Initialize memory for conversations
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        logger.info("LangChain RAG Agent initialized successfully")
    
    def _setup_vector_store(self):
        """Set up ChromaDB vector store for reply cache."""
        try:
            # Create vector store directory if it doesn't exist
            vector_db_path = "src/db/chroma_db"
            
            # # Delete existing DB as it will be done only once
            # if os.path.exists(vector_db_path):
            #     shutil.rmtree(vector_db_path)
            
            os.makedirs(vector_db_path, exist_ok=True)
            
            vector_store = Chroma(
                persist_directory=vector_db_path,
                embedding_function=self.embeddings,
                collection_name="echoai_reply_cache",
                collection_metadata={"hnsw:space": "cosine"}  # cosine space to get 1.0 = perfect match.
            )
            
            logger.info("ChromaDB vector store initialized for reply cache")
            return vector_store
            
        except Exception as e:
            logger.error(f"Failed to setup vector store: {str(e)}")
            # Return a mock for fallback
            return MockVectorStore()
    
    def _setup_self_info_knowledge_base(self):
        """Set up separate knowledge base for CV/profile/career/personality information."""
        try:
            # Create separate vector store for self-info knowledge
            knowledge_db_path = "src/db/self_info_knowledge"
            
            # Delete existing DB as it will be done only once
            if os.path.exists(knowledge_db_path):
                shutil.rmtree(knowledge_db_path)
                
            os.makedirs(knowledge_db_path, exist_ok=True)
            
            knowledge_base = Chroma(
                persist_directory=knowledge_db_path,
                embedding_function=self.embeddings,
                collection_name="echoai_self_info",
                collection_metadata={"hnsw:space": "cosine"}  # cosine space to get 1.0 = perfect match.
            )
            
            # Load and index self-info data
            self._load_self_info_data(knowledge_base)
            
            logger.info("Self-info knowledge base initialized successfully")
            return knowledge_base
            
        except Exception as e:
            logger.error(f"Failed to setup self-info knowledge base: {str(e)}")
            return None
    
    def _load_self_info_data(self, knowledge_base):
        """Load and index self-info data from JSON file."""
        try:
            self_info_path = "src/documents/self_info.json"
            
            if not os.path.exists(self_info_path):
                logger.warning(f"Self-info file not found: {self_info_path}")
                return
            
            documents = []
            with open(self_info_path, 'r', encoding='utf-8') as file:
                try:
                    # Parse entire JSON file as array
                    data_array = json.load(file)
                    
                    if not isinstance(data_array, list):
                        logger.error("Self-info file should contain a JSON array")
                        return
                    
                    for item_num, data in enumerate(data_array, 1):
                        try:
                            # Create document content combining question and answer
                            content = f"Question: {data.get('question', '')}\nAnswer: {data.get('answer', '')}"
                            
                            # Create metadata - ensure all values are simple types for ChromaDB
                            tags = data.get("tags", [])
                            if isinstance(tags, list):
                                tags = ", ".join(tags) if tags else "none"
                            
                            metadata = {
                                "doc_type": str(data.get("doc_type", "unknown")),
                                "tags": tags,
                                "knowledge_type": "self_info"
                            }
                            
                            # Create LangChain Document
                            doc = Document(
                                page_content=content,
                                metadata=metadata
                            )
                            documents.append(doc)
                            
                        except Exception as e:
                            logger.warning(f"Failed to process item {item_num}: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Failed to parse JSON file: {str(e)}")
                    return
            
            if documents:
                # Add documents to knowledge base
                knowledge_base.add_documents(documents)
                knowledge_base.persist()
                logger.info(f"Loaded {len(documents)} self-info documents into knowledge base")
            else:
                logger.warning("No valid self-info documents found")
                
        except Exception as e:
            logger.error(f"Failed to load self-info data: {str(e)}")
    
    def _setup_llms(self):
        """Set up LLMs with Mistral as primary and OpenAI as fallback."""
        primary_llm = None
        fallback_llm = None
        
        try:
            # Primary: Mistral
            if MISTRAL_AVAILABLE and self.settings.MISTRAL_API_KEY:
                primary_llm = ChatMistralAI(
                    model="mistral-small",
                    mistral_api_key=self.settings.MISTRAL_API_KEY,
                    temperature=0.7,
                    max_tokens=1500
                )
                logger.info("Mistral LLM initialized as primary")
            else:
                logger.warning("Mistral not available or no API key, using OpenAI as primary")
        except Exception as e:
            logger.error(f"Failed to setup Mistral LLM: {str(e)}")
        
        try:
            # Fallback: OpenAI
            fallback_llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                openai_api_key=self.settings.OPENAI_API_KEY,
                max_tokens=1500
            )
            logger.info("OpenAI LLM initialized as fallback")
        except Exception as e:
            logger.error(f"Failed to setup OpenAI LLM: {str(e)}")
            raise Exception("No LLM available - both Mistral and OpenAI failed to initialize")
        
        # Use OpenAI as primary if Mistral failed
        if primary_llm is None:
            primary_llm = fallback_llm
            logger.info("Using OpenAI as both primary and fallback LLM")
        
        return primary_llm, fallback_llm
    
    def _setup_rag_chain(self):
        """Set up RAG chain with custom prompt using self-info knowledge base."""
        try:
            if not self.self_info_knowledge_base:
                logger.warning("Self-info knowledge base not available, using fallback RAG")
                return None
            
            # Custom prompt template for grounded responses using self-info
            prompt_template = """
            You are Ateet’s AI clone — a professional AI engineer and strategic thinker — with access to curated knowledge about Ateet's CV, profile, career, skills, achievements, and personality.

            Your goal:
            - Respond in Ateet’s authentic voice, reflecting his tone, values, and communication style.
            - Adapt the length, tone, and style of your answer based on the intent of the question:

            Intent-based response rules:
            1. If the question is a greeting, casual message, or light check-in:
            - Respond in no more than 1–2 short sentences (max ~20 words).
            - Be friendly, concise, and professional.
            - Do NOT list abilities, background, or capabilities unless explicitly asked.
            2. If the question is about professional, career, or vision topics:
            - Respond in a detailed, structured, and precise manner.
            - Use examples where relevant and ensure clarity.
            3. If the question is technical:
            - Respond with clear, technically accurate, and implementation-ready explanations.
            - Include code snippets or structured steps if relevant.

            Special instruction:
            - If the question requests specific facts not present in the CONTEXT, respond exactly with:
            "I don't have specific information about that in my knowledge base."

            Rules:
            - Never fabricate or assume details outside the CONTEXT.
            - Keep answers relevant — avoid generic or boilerplate introductions unless they directly add value.
            - Always sound like Ateet, not a generic AI assistant.

            ---
            CONTEXT:
            {context}

            QUESTION:
            {question}

            ANSWER:
            """
            
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )
            
            # Create retrieval QA chain using self-info knowledge base
            rag_chain = RetrievalQA.from_chain_type(
                llm=self.primary_llm,
                chain_type="stuff",
                retriever=self.self_info_knowledge_base.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5}  # Get more context for comprehensive responses
                ),
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            logger.info("RAG chain initialized with self-info knowledge base")
            return rag_chain
            
        except Exception as e:
            logger.error(f"Failed to setup RAG chain: {str(e)}")
            return None
    
    async def process_query(self, user_text: str, session_id: str = None) -> Dict[str, Any]:
        """
        Process user query through LangChain RAG pipeline.
        
        Args:
            user_text: User input text
            session_id: Session identifier
            
        Returns:
            Dict with response and metadata
        """
        try:
            start_time = time.time()
            
            # Step 1: Check reply cache for semantic similarity
            cached_reply = await self.reply_cache.find_similar_reply(user_text)
            if cached_reply and cached_reply.similarity_score >= 0.85:
                logger.info(f"Found cached reply with similarity {cached_reply.similarity_score:.3f}")
                return {
                    "response_text": cached_reply.response_text,
                    "audio_file_path": cached_reply.audio_file_path,
                    "cached": True,
                    "similarity_score": cached_reply.similarity_score,
                    "source": "cache",
                    "processing_time": time.time() - start_time
                }
            
            # Step 2: Check if we have relevant self-info knowledge
            if self.self_info_knowledge_base:
                try:
                    # Search self-info knowledge base
                    knowledge_docs = self.self_info_knowledge_base.similarity_search(user_text, k=3)
                    
                    if knowledge_docs and len(knowledge_docs) > 0:
                        # Use RAG chain for grounded response from self-info
                        try:
                            rag_response = self.rag_chain({"query": user_text})
                            response_text = rag_response["result"]
                            source_docs = rag_response.get("source_documents", [])
                            
                            return {
                                "response_text": response_text,
                                "cached": False,
                                "source": "rag_self_info",
                                "knowledge_used": True,
                                "source_documents": len(source_docs),
                                "processing_time": time.time() - start_time
                            }
                        except Exception as rag_error:
                            logger.error(f"RAG chain failed, using fallback LLM: {str(rag_error)}")
                            response = await self._direct_llm_response(user_text, use_fallback=True)
                            return {
                                "response_text": response,
                                "cached": False,
                                "source": "llm_fallback",
                                "knowledge_used": False,
                                "rag_error": str(rag_error),
                                "processing_time": time.time() - start_time
                            }
                    else:
                        # No relevant self-info knowledge found
                        logger.info("No relevant self-info knowledge found, using direct LLM")
                        response = await self._direct_llm_response(user_text)
                        return {
                            "response_text": response,
                            "cached": False,
                            "source": "llm_direct",
                            "knowledge_used": False,
                            "processing_time": time.time() - start_time
                        }
                        
                except Exception as knowledge_error:
                    logger.error(f"Self-info knowledge search failed: {str(knowledge_error)}")
                    # Fall back to direct LLM
                    response = await self._direct_llm_response(user_text)
                    return {
                        "response_text": response,
                        "cached": False,
                        "source": "llm_fallback",
                        "knowledge_used": False,
                        "knowledge_error": str(knowledge_error),
                        "processing_time": time.time() - start_time
                    }
            else:
                # Self-info knowledge base not available, use direct LLM
                logger.warning("Self-info knowledge base not available, using direct LLM")
                response = await self._direct_llm_response(user_text)
                return {
                    "response_text": response,
                    "cached": False,
                    "source": "llm_direct",
                    "knowledge_used": False,
                    "processing_time": time.time() - start_time
                }
            
        except Exception as e:
            logger.error(f"LangChain RAG query processing failed: {str(e)}")
            # Final fallback to direct LLM
            try:
                response = await self._direct_llm_response(user_text, use_fallback=True)
                return {
                    "response_text": response,
                    "cached": False,
                    "source": "error_fallback",
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
            except Exception as fallback_error:
                return {
                    "response_text": "I encountered an error processing your request. Please try again.",
                    "cached": False,
                    "source": "error",
                    "error": str(e),
                    "fallback_error": str(fallback_error),
                    "processing_time": time.time() - start_time
                }
    
    async def _direct_llm_response(self, user_text: str, use_fallback: bool = False) -> str:
        """Generate direct LLM response when no knowledge is available."""
        try:
            # Choose LLM based on use_fallback flag
            llm_to_use = self.fallback_llm if use_fallback and self.fallback_llm else self.primary_llm
            
            # Use LangChain LLM directly
            response = llm_to_use.invoke(user_text)
            
            # Extract content from response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Direct LLM response failed: {str(e)}")
            # Final fallback to LLM service
            try:
                from src.services.llm_service import llm_service
                result = await llm_service.generate_response(user_text)
                return result.get("text", "I apologize, but I couldn't generate a response.")
            except Exception as service_error:
                logger.error(f"LLM service fallback failed: {str(service_error)}")
                return "I apologize, but I encountered an error generating a response."
    
    async def store_interaction(self, user_text: str, response_text: str, audio_file_path: str):
        """Store successful interaction in reply cache."""
        await self.reply_cache.store_reply(user_text, response_text, audio_file_path)
    
    def add_knowledge(self, texts: List[str], metadatas: List[Dict] = None):
        """Add knowledge to the self-info knowledge base."""
        try:
            if not self.self_info_knowledge_base:
                logger.warning("Self-info knowledge base not available")
                return
            
            # Split texts if they're too long
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            
            documents = []
            for i, text in enumerate(texts):
                chunks = text_splitter.split_text(text)
                for chunk in chunks:
                    metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                    metadata["knowledge_type"] = "self_info"
                    documents.append(Document(page_content=chunk, metadata=metadata))
            
            # Add to self-info knowledge base
            self.self_info_knowledge_base.add_documents(documents)
            self.self_info_knowledge_base.persist()
            
            logger.info(f"Added {len(documents)} documents to self-info knowledge base")
            
        except Exception as e:
            logger.error(f"Failed to add knowledge: {str(e)}")
    
    def add_self_info_knowledge(self, cv_data: Dict[str, Any]):
        """Add structured CV/profile data to the self-info knowledge base."""
        try:
            if not self.self_info_knowledge_base:
                logger.warning("Self-info knowledge base not available")
                return
            
            # Parse structured CV data
            content_parts = []
            
            if "personal_info" in cv_data:
                personal = cv_data["personal_info"]
                content_parts.append(f"Personal Information: {personal.get('name', 'N/A')} - {personal.get('title', 'N/A')}")
                if personal.get('summary'):
                    content_parts.append(f"Summary: {personal['summary']}")
            
            if "experience" in cv_data:
                exp_parts = ["Experience:"]
                for exp in cv_data["experience"]:
                    exp_parts.append(f"- {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration', 'N/A')})")
                    if exp.get('description'):
                        exp_parts.append(f"  {exp['description']}")
                content_parts.append("\n".join(exp_parts))
            
            if "skills" in cv_data:
                skills = ", ".join(cv_data["skills"]) if isinstance(cv_data["skills"], list) else str(cv_data["skills"])
                content_parts.append(f"Skills: {skills}")
            
            if "education" in cv_data:
                edu_parts = ["Education:"]
                for edu in cv_data["education"]:
                    edu_parts.append(f"- {edu.get('degree', 'N/A')} from {edu.get('institution', 'N/A')} ({edu.get('year', 'N/A')})")
                content_parts.append("\n".join(edu_parts))
            
            if "personality" in cv_data:
                personality = ", ".join(cv_data["personality"]) if isinstance(cv_data["personality"], list) else str(cv_data["personality"])
                content_parts.append(f"Personality: {personality}")
            
            content = "\n\n".join(content_parts)
            
            # Create metadata
            metadata = {
                "doc_type": "cv_profile",
                "tags": "cv,profile,career,personality",
                "knowledge_type": "self_info"
            }
            
            # Create and add document
            doc = Document(page_content=content, metadata=metadata)
            self.self_info_knowledge_base.add_documents([doc])
            self.self_info_knowledge_base.persist()
            
            logger.info("Added custom CV profile to self-info knowledge base")
            
        except Exception as e:
            logger.error(f"Failed to add self-info knowledge: {str(e)}")

class ReplyCacheManager:
    """Manages semantic reply cache for fast audio reuse."""
    
    def __init__(self, db_operations: DBOperations, vector_store: Chroma):
        self.db = db_operations
        self.vector_store = vector_store
        self.similarity_threshold = 0.85
        self._ensure_cache_table()
    
    def _ensure_cache_table(self):
        """Ensure reply cache table exists."""
        try:
            #self.db.conn.execute("DROP TABLE IF EXISTS reply_cache;")
            self.db.conn.execute("""
                CREATE TABLE IF NOT EXISTS reply_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    audio_file_path TEXT NOT NULL,
                    text_hash TEXT NOT NULL,
                    vector_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(text_hash)
                )
            """)
            self.db.conn.commit()
            logger.info("Reply cache table ensured")
        except Exception as e:
            logger.error(f"Failed to create reply cache table: {str(e)}")
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()
    
    async def find_similar_reply(self, user_text: str) -> Optional[ReplyCache]:
        """Find semantically similar cached reply."""
        try:
            # First check for exact hash match
            text_hash = self._get_text_hash(user_text)
            cursor = self.db.conn.execute(
                "SELECT user_text, response_text, audio_file_path, created_at FROM reply_cache WHERE text_hash = ?",
                (text_hash,)
            )
            exact_match = cursor.fetchone()
            
            if exact_match:
                return ReplyCache(
                    user_text=exact_match[0],
                    response_text=exact_match[1],
                    audio_file_path=exact_match[2],
                    created_at=exact_match[3],
                    similarity_score=1.0
                )
            
            # Semantic search using vector store
            try:
                docs = self.vector_store.similarity_search_with_score(user_text, k=3)
                if docs:
                    best_doc, distance = docs[0]  # distance in [0, 2] for cosine
                    cos_sim = 1 - distance                 # cosine similarity in [-1, 1]
                    sim_0_1 = (cos_sim + 1) / 2           # map to [0, 1] for UI/thresholds
                    sim_percent = round(sim_0_1 * 100, 2) # 0–100%
                    
                    if sim_percent  >= self.similarity_threshold:
                        # Find the cached reply for this document
                        original_text = best_doc.metadata.get('original_text', best_doc.page_content)
                        cursor = self.db.conn.execute(
                            "SELECT user_text, response_text, audio_file_path, created_at FROM reply_cache WHERE user_text = ?",
                            (original_text,)
                        )
                        match = cursor.fetchone()
                        if match:
                            return ReplyCache(
                                user_text=match[0],
                                response_text=match[1],
                                audio_file_path=match[2],
                                created_at=match[3],
                                similarity_score=sim_percent
                            )
            except Exception as e:
                logger.warning(f"Semantic search in cache failed: {str(e)}")
            
            return None
            
        except Exception as e:
            logger.error(f"Similar reply search failed: {str(e)}")
            return None
    
    async def store_reply(self, user_text: str, response_text: str, audio_file_path: str):
        """
        Store new reply in SQLite + Chroma vector store with a deterministic vector_id.
        - Deterministic ID lets you upsert + delete cleanly without metadata searches.
        - Uses SQLite ON CONFLICT to keep one row per text_hash.
        """
        try:
            text_hash = self._get_text_hash(user_text)

            # Stable ID per unique text_hash (change namespace if you prefer)
            vector_id = str(uuid5(NAMESPACE_URL, text_hash))

            # Build LangChain Document
            doc = Document(
                page_content=user_text,
                metadata={
                    "original_text": user_text,
                    "response_text": response_text,
                    "audio_file_path": audio_file_path,
                    "type": "reply_cache",
                },
            )

            # Ensure no duplicate in Chroma (ignore errors if not present)
            try:
                self.vector_store.delete(ids=[vector_id])
            except Exception:
                pass

            # Insert into Chroma with OUR id (important!)
            returned_ids = self.vector_store.add_documents([doc], ids=[vector_id])
            # returned_ids is a list[str]; sanity check
            if not returned_ids or returned_ids[0] != vector_id:
                logger.warning("Chroma returned unexpected id; proceeding with our vector_id")

            # Persist if backend supports it (Chroma does)
            if hasattr(self.vector_store, "persist"):
                self.vector_store.persist()

            # Upsert into SQLite (requires UNIQUE(text_hash))
            self.db.conn.execute(
                """
                INSERT INTO reply_cache (user_text, response_text, audio_file_path, text_hash, vector_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(text_hash) DO UPDATE SET
                    user_text     = excluded.user_text,
                    response_text = excluded.response_text,
                    audio_file_path = excluded.audio_file_path,
                    vector_id     = excluded.vector_id
                """,
                (user_text, response_text, audio_file_path, text_hash, vector_id),
            )
            self.db.conn.commit()

            logger.info(f"Stored reply in cache: hash={text_hash}, vector_id={vector_id}")

            return vector_id

        except Exception as e:
            # Rollback any partial SQL work
            try:
                self.db.conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to store reply in cache: {e}")
            raise

class MockVectorStore:
    """Mock vector store for fallback."""
    
    def __init__(self):
        self.docs = []
    
    def similarity_search(self, query: str, k: int = 3) -> List:
        return []
    
    def similarity_search_with_score(self, query: str, k: int = 3) -> List:
        return []
    
    def add_documents(self, documents):
        pass
    
    def persist(self):
        pass
    
    def as_retriever(self, **kwargs):
        return MockRetriever()

class MockRetriever:
    """Mock retriever for fallback."""
    
    def get_relevant_documents(self, query: str) -> List:
        return []

# Global RAG agent instance
rag_agent = LangChainRAGAgent()