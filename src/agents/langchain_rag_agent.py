"""
LangChain-based RAG Agent for EchoAI voice chat system.

This module implements a RAG system using LangChain with semantic search,
knowledge retrieval, and grounded answer generation capabilities.
"""

import os
import re
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_URL
import shutil  # noqa: F401 — kept for ReplyCacheManager compatibility

from src.constants import ChromaCollection

# LangChain imports

from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain.retrievers import EnsembleRetriever
from langchain_core.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.memory import ConversationBufferMemory

# Mistral integration (fallback)
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
        
        # Initialize embeddings (shared singleton — avoids reloading the model)
        from src.knowledge.self_info_vectorstore import _get_embeddings
        self.embeddings = _get_embeddings()
        
        # Initialize vector store
        self.vector_store = self._setup_vector_store()
        
        # Initialize self-info knowledge bases (persistent, no destructive rebuild)
        try:
            from src.knowledge.self_info_vectorstore import get_self_info_store
            stores = get_self_info_store()
            self.self_info_facts_store = stores.facts
            self.self_info_evidence_store = stores.evidence
            self.self_info_knowledge_base = True  # flag for availability
        except Exception as e:
            logger.error(f"Failed to load self-info store: {e}")
            self.self_info_facts_store = None
            self.self_info_evidence_store = None
            self.self_info_knowledge_base = None
        
        # Initialize LLMs (DeepSeek primary, Mistral fallback)
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
            # Create vector store directory if it doesn't exist # Ateet move to supabase
            vector_db_path = self.settings.REPLY_CACHE_CHROMA_DIR
            
            os.makedirs(vector_db_path, exist_ok=True)
            
            vector_store = Chroma(
                persist_directory=vector_db_path,
                embedding_function=self.embeddings,
                collection_name=ChromaCollection.REPLY_CACHE,
                collection_metadata={"hnsw:space": "cosine"}  # cosine space to get 1.0 = perfect match.
            )
            
            logger.info("ChromaDB vector store initialized for reply cache")
            return vector_store
            
        except Exception as e:
            logger.error(f"Failed to setup vector store: {str(e)}")
            # Return a mock for fallback
            return MockVectorStore()
    
    # NOTE: _setup_self_info_knowledge_base and _load_self_info_data removed.
    # Knowledge base is now managed by src.knowledge.self_info_vectorstore (persistent, upsert-based).
    
    def _rebuild_self_info_stores(self):
        """Force rebuild self-info stores when HNSW index is corrupted."""
        try:
            import shutil
            from pathlib import Path
            from src.knowledge.self_info_vectorstore import build_or_update_self_info_store

            persist_dir = Path(self.settings.SELF_INFO_CHROMA_DIR)
            if persist_dir.exists():
                logger.warning("Deleting corrupted self-info store at %s", persist_dir)
                shutil.rmtree(persist_dir)

            stores = build_or_update_self_info_store()
            self.self_info_facts_store = stores.facts
            self.self_info_evidence_store = stores.evidence
            self.self_info_knowledge_base = True

            # Re-create the RAG chain with fresh retrievers
            self.rag_chain = self._setup_rag_chain()

            logger.info("Self-info stores rebuilt successfully after HNSW corruption")
        except Exception as e:
            logger.error(f"Failed to rebuild self-info stores: {e}")
            self.self_info_facts_store = None
            self.self_info_evidence_store = None
            self.self_info_knowledge_base = None
            self.rag_chain = None

    
    def _setup_llms(self):
        """Set up LLMs with DeepSeek as primary and Mistral as fallback."""
        primary_llm = None
        fallback_llm = None
        
        try:
            # Primary: DeepSeek (via OpenAI-compatible API)
            if self.settings.DEEPSEEK_API_KEY:
                primary_llm = ChatOpenAI(
                    model=self.settings.DEEPSEEK_MODEL,
                    openai_api_key=self.settings.DEEPSEEK_API_KEY,
                    openai_api_base=self.settings.DEEPSEEK_API_BASE,
                    temperature=self.settings.LLM_TEMPERATURE,
                    max_tokens=1500
                )
                logger.info("DeepSeek LLM initialized as primary")
            else:
                logger.warning("DeepSeek API key not available, will try Mistral as primary")
        except Exception as e:
            logger.error(f"Failed to setup DeepSeek LLM: {str(e)}")
        
        try:
            # Fallback: Mistral
            if MISTRAL_AVAILABLE and self.settings.MISTRAL_API_KEY:
                fallback_llm = ChatMistralAI(
                    model=self.settings.MISTRAL_MODEL,
                    mistral_api_key=self.settings.MISTRAL_API_KEY,
                    temperature=self.settings.LLM_TEMPERATURE,
                    max_tokens=1500
                )
                logger.info("Mistral LLM initialized as fallback")
            else:
                logger.warning("Mistral not available or no API key for fallback")
        except Exception as e:
            logger.error(f"Failed to setup Mistral LLM: {str(e)}")
        
        # If neither initialized, raise
        if primary_llm is None and fallback_llm is None:
            raise Exception("No LLM available - both DeepSeek and Mistral failed to initialize")
        
        # Use fallback as primary if DeepSeek failed
        if primary_llm is None:
            primary_llm = fallback_llm
            logger.info("Using Mistral as both primary and fallback LLM")
        
        return primary_llm, fallback_llm
    
    def _setup_rag_chain(self):
        """Set up RAG chain with custom prompt using merged facts + evidence knowledge base."""
        try:
            if not self.self_info_knowledge_base:
                logger.warning("Self-info knowledge base not available, using fallback RAG")
                return None
            
            # Custom prompt template for grounded responses using self-info
            prompt_template = """
            IDENTITY (non-negotiable):
            You are Ateet Vatan's AI clone. You speak as Ateet — always in the first person ("I", "my", "me").
            You are NOT DeepSeek, Mistral, ChatGPT, or any other AI assistant.
            You must NEVER reveal, mention, or hint at the underlying AI model or company powering you.
            If asked "who are you" or "tell me about yourself", answer ONLY with facts about Ateet from the CONTEXT below.

            ROLE:
            You are a professional AI engineer and strategic thinker with access to curated knowledge about Ateet's CV, profile, career, skills, achievements, and personality.

            GOAL:
            - Respond in Ateet's authentic voice, reflecting his tone, values, and communication style.
            - Adapt the length, tone, and style of your answer based on the intent of the question:

            QUERY INTERPRETATION (critical):
            - Users may type short phrases, keywords, or misspelled words instead of full questions.
            - ALWAYS interpret the user's INTENT behind their input. For example:
              * "work experiance" or "work experience" → the user wants to know about Ateet's work/employment history
              * "skills" → the user wants to know about Ateet's technical skills
              * "projects" → the user wants to know about Ateet's projects
              * "education" → the user wants to know about Ateet's education
            - Treat short keyword queries the same as full questions — find relevant info in the CONTEXT and answer.
            - Ignore spelling mistakes in the user's query and focus on INTENT.

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

            CRITICAL — Anti-hallucination:
            - NEVER invent, guess, or fabricate project names, company names, or product names. Use ONLY the exact names that appear in the CONTEXT.
            - If the CONTEXT mentions a project called "ApplyBots", refer to it as "ApplyBots" — do NOT rename it to something else.
            - Every proper noun (project name, company name, tool name) in your answer MUST come from the CONTEXT verbatim.

            Special instruction:
            - If partial information is available in the CONTEXT, synthesize the best answer from what is available.
            - ONLY say "I don't have specific information about that in my knowledge base." if the CONTEXT contains ABSOLUTELY NOTHING related to the user's intent. If ANYTHING in the CONTEXT is relevant, use it to form an answer.

            Rules:
            - Always respond in English, regardless of the language of the question.
            - Never fabricate or assume details outside the CONTEXT.
            - Keep answers relevant — avoid generic or boilerplate introductions unless they directly add value.
            - Always sound like Ateet, not a generic AI assistant.
            - NEVER say "I'm an AI assistant" or "I'm DeepSeek" or similar. You ARE Ateet's digital twin.

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
            
            # Create merged retriever from facts + evidence stores
            # Higher k values to surface more relevant chunks including project names
            facts_retriever = self.self_info_facts_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 6}
            )
            evidence_retriever = self.self_info_evidence_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            merged_retriever = EnsembleRetriever(
                retrievers=[facts_retriever, evidence_retriever],
                weights=[0.6, 0.4]  # Favor facts (explicit Q&A) over evidence (raw docs)
            )
            
            # Create retrieval QA chain using merged retriever
            rag_chain = RetrievalQA.from_chain_type(
                llm=self.primary_llm,
                chain_type="stuff",
                retriever=merged_retriever,
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            logger.info("RAG chain initialized with merged facts + evidence retriever")
            return rag_chain
            
        except Exception as e:
            logger.error(f"Failed to setup RAG chain: {str(e)}")
            return None
    
    # -----------------------------------------------------------------------
    # Query expansion for short / misspelled inputs
    # Regex rules + LLM fallback live in src.agents.query_expansions
    # -----------------------------------------------------------------------

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
            if cached_reply and cached_reply.similarity_score >= 0.95:
                logger.info(f"Found cached reply with similarity {cached_reply.similarity_score:.3f}")
                return {
                    "response_text": cached_reply.response_text,
                    "audio_file_path": cached_reply.audio_file_path,
                    "cached": True,
                    "similarity_score": cached_reply.similarity_score,
                    "source": "cache",
                    "processing_time": time.time() - start_time
                }
            
            # Step 2: Always try RAG chain when knowledge base is available.
            # The RAG chain's EnsembleRetriever (k=6+5) handles short,
            # misspelled, or ambiguous queries far better than a low-k
            # pre-flight similarity_search gate.
            if self.self_info_knowledge_base and self.rag_chain:
                try:
                    # Handle corrupted HNSW index by attempting a quick probe
                    try:
                        self.self_info_facts_store.similarity_search(user_text, k=1)
                    except Exception as hnsw_err:
                        if "hnsw" in str(hnsw_err).lower() or "Nothing found on disk" in str(hnsw_err):
                            logger.warning("HNSW index corrupted, rebuilding self-info store...")
                            self._rebuild_self_info_stores()
                        else:
                            raise

                    # Expand short/ambiguous queries into full questions for
                    # better embedding-based retrieval.  The RAG prompt still
                    # receives the *original* user_text, but the retriever
                    # sees the expanded version so it pulls richer context.
                    from src.agents.query_expansions import expand_query
                    retrieval_query = await expand_query(
                        user_text, llm=self.primary_llm
                    )

                    rag_response = self.rag_chain.invoke({"query": retrieval_query})
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
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # Choose LLM based on use_fallback flag
            llm_to_use = self.fallback_llm if use_fallback and self.fallback_llm else self.primary_llm
            
            # System message to keep the model in-character as Ateet
            system_msg = SystemMessage(content=(
                "You are Ateet Vatan's AI clone — his digital twin. "
                "Always speak as Ateet in the first person. "
                "You are NOT DeepSeek, Mistral, ChatGPT, or any other AI assistant. "
                "Never reveal or mention the underlying AI model powering you. "
                "If you don't know something about Ateet, say: "
                "'I don't have specific information about that in my knowledge base.' "
                "Always respond in English."
            ))
            human_msg = HumanMessage(content=user_text)
            
            response = llm_to_use.invoke([system_msg, human_msg])
            
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
            if not self.self_info_facts_store:
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
            
            # Add to self-info facts store
            self.self_info_facts_store.add_documents(documents)
            self.self_info_facts_store.persist()
            
            logger.info(f"Added {len(documents)} documents to self-info knowledge base")
            
        except Exception as e:
            logger.error(f"Failed to add knowledge: {str(e)}")
    
    def add_self_info_knowledge(self, cv_data: Dict[str, Any]):
        """Add structured CV/profile data to the self-info knowledge base."""
        try:
            if not self.self_info_facts_store:
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
            self.self_info_facts_store.add_documents([doc])
            self.self_info_facts_store.persist()
            
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
            
            return None # TODO: For now disabeling this feature need to be tested.
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

# ---------------------------------------------------------------------------
# Lazy singleton — avoids blocking Uvicorn startup with heavy init work
# ---------------------------------------------------------------------------
_rag_agent: Optional[LangChainRAGAgent] = None


def get_rag_agent() -> LangChainRAGAgent:
    """Return the global RAG agent, creating it on first call."""
    global _rag_agent  # noqa: PLW0603
    if _rag_agent is None:
        logger.info("Initializing LangChain RAG Agent (first access)...")
        _rag_agent = LangChainRAGAgent()
    return _rag_agent