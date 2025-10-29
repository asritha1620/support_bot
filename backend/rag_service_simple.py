import os
import pandas as pd
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json
import pickle
import google.generativeai as genai

# Load environment variables
load_dotenv()


class Document:
    """Simple document class to replace LangChain Document"""
    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


class SimpleTextSplitter:
    """Simple text splitter to replace LangChain RecursiveCharacterTextSplitter"""
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks"""
        split_docs = []
        for doc in documents:
            chunks = self._split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    new_metadata = doc.metadata.copy()
                    new_metadata['chunk_index'] = i
                    split_docs.append(Document(page_content=chunk, metadata=new_metadata))
        return split_docs
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Try to find a good break point
            break_point = end
            for i in range(end - 1, start + self.chunk_size // 2, -1):
                if text[i] in ['.', '\n', '!', '?']:
                    break_point = i + 1
                    break
            
            chunks.append(text[start:break_point])
            start = break_point - self.chunk_overlap
            if start < 0:
                start = 0
        
        return chunks


class SimpleFAISS:
    """Simple FAISS wrapper to replace LangChain FAISS"""
    def __init__(self, embeddings_model: SentenceTransformer, documents: List[Document] = None):
        self.embeddings_model = embeddings_model
        self.documents = documents or []
        self.index = None
        self._build_index()
    
    def _build_index(self):
        """Build FAISS index from documents"""
        if not self.documents:
            return
        
        # Get embeddings for all documents
        texts = [doc.page_content for doc in self.documents]
        embeddings = self.embeddings_model.encode(texts, convert_to_numpy=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype(np.float32))
    
    def add_documents(self, documents: List[Document]):
        """Add new documents to the index"""
        self.documents.extend(documents)
        self._build_index()  # Rebuild index with all documents
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """Search for similar documents"""
        if not self.index or not self.documents:
            return []
        
        # Get query embedding
        query_embedding = self.embeddings_model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                results.append({
                    'document': self.documents[idx],
                    'score': float(score),
                    'reasons': ['Semantic similarity']
                })
        
        return results
    
    def save_local(self, path: str):
        """Save index and documents to disk"""
        os.makedirs(path, exist_ok=True)
        
        if self.index:
            faiss.write_index(self.index, os.path.join(path, 'index.faiss'))
        
        with open(os.path.join(path, 'documents.pkl'), 'wb') as f:
            pickle.dump(self.documents, f)
    
    @classmethod
    def load_local(cls, path: str, embeddings_model: SentenceTransformer):
        """Load index and documents from disk"""
        instance = cls(embeddings_model)
        
        index_path = os.path.join(path, 'index.faiss')
        docs_path = os.path.join(path, 'documents.pkl')
        
        if os.path.exists(index_path):
            instance.index = faiss.read_index(index_path)
        
        if os.path.exists(docs_path):
            with open(docs_path, 'rb') as f:
                instance.documents = pickle.load(f)
        
        return instance
    
    @classmethod
    def from_documents(cls, documents: List[Document], embeddings_model: SentenceTransformer):
        """Create FAISS index from documents"""
        return cls(embeddings_model, documents)


class SimpleGeminiChat:
    """Simple Gemini chat wrapper"""
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def invoke(self, prompt: str) -> str:
        """Generate response from Gemini"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            return "I'm sorry, I'm having trouble generating a response right now."


class RAGService:
    def __init__(self):
        self.sessions = {}  # Store session-specific data
        self.embeddings_model = None
        self.llm = None
        self.system_prompt = ("""
You are a Support Engineer Helper AI. Your role is to assist the human Support Engineer (me) in diagnosing, troubleshooting, and suggesting fixes for support tickets in our eCommerce platform. I will use your guidance to actually perform the fixes.

Instructions:
--Be friendly, patient, and professional.
--Ask relevant follow-up questions in a short and crisp way, using no more than 3 bullet points.
--Explain technical solutions clearly, step-by-step, without assuming prior technical knowledge. Use 3 bullet points or fewer for resolution steps whenever possible.
--Use a polite, conversational tone but remain focused and precise.
--Always consider the user's previous messages in the thread.
--If a previous ticket or error has been discussed, use that context to tailor your suggestions.
--If a ticket ID or customer name is given, keep that reference until the issue is resolved.
--Retain category-specific history (like "PAY502" errors being payment gateway timeouts).
--Use historical ticket data, known error code mappings, resolution playbooks, and escalation paths to provide solutions.
--If the exact error code is detected, respond with:
    --"As per existing history tickets, here are the resolution steps you can try to fix the problem:"
--Then provide no more than 3 bullet points outlining the steps from the documented history.
--When the user provides resolution steps, respond with:
    --"Thank you for providing the resolution steps, I learnt a new thing today."
--If an issue is unknown or requires human intervention, say so clearly and recommend escalation.
--When referring to logs, files, or configurations, use realistic paths (e.g., /var/logs/payment/, /config/orders.yaml).
--Ask clarifying questions briefly, for example:
    --"Can you share the full error message?"
    --"Did this happen at checkout or order confirmation?"
    --"Any recent changes to config or server?"
--Provide options concisely:
    --"Do you want to check logs or restart the service?"
--Summarize steps clearly, with no more than 3 bullet points:
    --Example:
        --Check logs in /var/logs/payment/
        --Update config file payment.yaml
        --Restart payment service
--For L1 issues: Focus on quick fixes like cache clear, network reset, retry, UI checks.
--For L2 issues: Guide through deeper analysis like log checks, config edits, API testing.
--For known L3 tickets: Mention backend/dev team involvement.
--Use bold or code style to highlight file paths, config keys, or API endpoints.
--If the solution is lengthy, provide a brief summary at the end.
--Strictly avoid answering:
    --General knowledge questions (geography, history, etc.)
    --Jokes, trivia, or personal questions
    --Anything unrelated to support engineering
--If an unrelated query is detected, respond with:
    --"I'm designed to assist with technical support issues. Please let me know how I can help you with a support-related question."
--Do not provide unrelated information even if the user insists.
{context}
    """)
        self.setup_models()
    
    def setup_models(self):
        """Initialize the embeddings and LLM models"""
        try:
            # Setup sentence-transformers embeddings
            try:
                self.embeddings_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                print("Embeddings model initialized successfully")
            except Exception as e:
                print(f"Failed to initialize embeddings: {e}")
                self.embeddings_model = None
            
            # Setup Gemini LLM
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                print("Warning: GEMINI_API_KEY not found. LLM functionality will be limited.")
                self.llm = None
            else:
                try:
                    self.llm = SimpleGeminiChat(gemini_api_key)
                    print("Gemini LLM initialized successfully")
                except Exception as e:
                    print(f"Failed to initialize Gemini: {e}")
                    self.llm = None

            print("RAG Service initialized successfully")
            
        except Exception as e:
            print(f"Error initializing RAG service: {str(e)}")
            raise
    
    def load_excel_data(self, file_path: str) -> List[Document]:
        """Load and process Excel file into documents"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            documents = []
            file_name = os.path.basename(file_path)
            
            # Convert each row to a document
            for idx, row in df.iterrows():
                content = ""
                metadata = {"row_index": idx, "source": file_name}
                
                for col in df.columns:
                    if pd.notna(row[col]):
                        content += f"{col}: {row[col]}\n"
                        metadata[col] = str(row[col])
                
                if content.strip():
                    documents.append(Document(
                        page_content=content.strip(),
                        metadata=metadata
                    ))
            
            # Create column summaries
            for col in df.columns:
                col_data = df[col].dropna()
                if not col_data.empty:
                    content = f"Column: {col}\n"
                    content += f"Data type: {col_data.dtype}\n"
                    content += f"Sample values: {', '.join(map(str, col_data.head(10).tolist()))}\n"
                    content += f"Total non-null values: {len(col_data)}"
                    
                    documents.append(Document(
                        page_content=content,
                        metadata={"column": col, "source": file_name, "type": "column_summary"}
                    ))
            
            return documents
            
        except Exception as e:
            print(f"Error loading Excel file: {str(e)}")
            return []
    
    def _fallback_keyword_search(self, question: str, documents: List[Document], limit: int = 5) -> List[Dict]:
        """Fallback keyword search when semantic search is unavailable"""
        question_words = question.lower().split()
        relevant_tickets = []
        
        for doc in documents[:20]:  # Search first 20 documents
            if doc.metadata.get('type') == 'column_summary':
                continue
            content_lower = doc.page_content.lower()
            score = sum(1 for word in question_words if len(word) > 2 and word in content_lower)
            if score > 0:
                relevant_tickets.append({
                    'document': doc,
                    'score': score,
                    'reasons': ['Keyword match']
                })
        
        relevant_tickets.sort(key=lambda x: x['score'], reverse=True)
        return relevant_tickets[:limit]
    
    def create_vectorstore(self, documents: List[Document]) -> SimpleFAISS:
        """Create FAISS vectorstore from documents"""
        try:
            if not documents:
                raise ValueError("No documents to process")
            
            if not self.embeddings_model:
                raise ValueError("Embeddings model not available")
            
            # Split documents into smaller chunks
            text_splitter = SimpleTextSplitter(chunk_size=500, chunk_overlap=50)
            split_docs = text_splitter.split_documents(documents)
            
            # Create vectorstore
            vectorstore = SimpleFAISS.from_documents(split_docs, self.embeddings_model)
            
            return vectorstore
        except Exception as e:
            print(f"Error creating vectorstore: {str(e)}")
            raise
    
    def save_vectorstore(self, vectorstore: SimpleFAISS, session_id: str) -> bool:
        """Save FAISS vectorstore to disk for persistence"""
        try:
            persist_dir = f"vectorstores/{session_id}"
            vectorstore.save_local(persist_dir)
            print(f"Saved vectorstore for session {session_id}")
            return True
        except Exception as e:
            print(f"Error saving vectorstore: {e}")
            return False
    
    def load_vectorstore(self, session_id: str) -> Optional[SimpleFAISS]:
        """Load FAISS vectorstore from disk"""
        try:
            if not self.embeddings_model:
                return None
            
            persist_dir = f"vectorstores/{session_id}"
            if os.path.exists(persist_dir):
                vectorstore = SimpleFAISS.load_local(persist_dir, self.embeddings_model)
                print(f"Loaded vectorstore for session {session_id}")
                return vectorstore
            else:
                print(f"No saved vectorstore found for session {session_id}")
                return None
        except Exception as e:
            print(f"Error loading vectorstore: {e}")
            return None
    
    async def process_file(self, file_path: str, session_id: str) -> bool:
        """Process Excel file and setup RAG for session with FAISS vectorstore"""
        try:
            # Check if vectorstore already exists for this session
            existing_vectorstore = self.load_vectorstore(session_id)
            if existing_vectorstore:
                print(f"Found existing vectorstore for session {session_id}")
                # Load documents from file and add to existing vectorstore
                documents = self.load_excel_data(file_path)
                if not documents:
                    return False
                
                try:
                    existing_vectorstore.add_documents(documents)
                    self.save_vectorstore(existing_vectorstore, session_id)
                    print(f"Updated existing vectorstore with {len(documents)} new documents")
                except Exception as e:
                    print(f"Failed to update existing vectorstore: {e}, creating new one")
                    existing_vectorstore = self.create_vectorstore(documents)
                    self.save_vectorstore(existing_vectorstore, session_id)
                
                # Store in session
                self.sessions[session_id] = {
                    "documents": documents,
                    "vectorstore": existing_vectorstore,
                    "file_path": file_path
                }
                return True
            
            # Load documents
            documents = self.load_excel_data(file_path)
            if not documents:
                return False
            
            # Create FAISS vectorstore for semantic search
            try:
                vectorstore = self.create_vectorstore(documents)
                self.save_vectorstore(vectorstore, session_id)
                print(f"Created and saved FAISS vectorstore with {len(documents)} documents")
            except Exception as e:
                print(f"Failed to create vectorstore: {e}, falling back to document storage only")
                vectorstore = None
            
            # Store in session
            self.sessions[session_id] = {
                "documents": documents,
                "vectorstore": vectorstore,
                "file_path": file_path
            }
            
            return True
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            return False
    
    async def append_file(self, file_path: str, session_id: str) -> bool:
        """Append Excel file data to an existing session with FAISS update"""
        try:
            if session_id not in self.sessions:
                return False
            
            # Load new documents
            new_documents = self.load_excel_data(file_path)
            if not new_documents:
                return False
            
            # Append to existing documents
            self.sessions[session_id]["documents"].extend(new_documents)
            
            # Update FAISS vectorstore if it exists
            if self.sessions[session_id].get("vectorstore"):
                try:
                    # Add new documents to existing vectorstore
                    self.sessions[session_id]["vectorstore"].add_documents(new_documents)
                    self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                    print(f"Updated FAISS vectorstore with {len(new_documents)} new documents")
                except Exception as e:
                    print(f"Failed to update vectorstore: {e}, recreating...")
                    try:
                        # Recreate vectorstore with all documents
                        all_documents = self.sessions[session_id]["documents"]
                        self.sessions[session_id]["vectorstore"] = self.create_vectorstore(all_documents)
                        self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                        print(f"Recreated FAISS vectorstore with {len(all_documents)} total documents")
                    except Exception as e2:
                        print(f"Failed to recreate vectorstore: {e2}")
                        self.sessions[session_id]["vectorstore"] = None
            else:
                # Try to create vectorstore if it doesn't exist
                try:
                    all_documents = self.sessions[session_id]["documents"]
                    self.sessions[session_id]["vectorstore"] = self.create_vectorstore(all_documents)
                    self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                    print(f"Created FAISS vectorstore for existing session with {len(all_documents)} documents")
                except Exception as e:
                    print(f"Failed to create vectorstore for existing session: {e}")
            
            # Update file path to indicate multiple files
            current_path = self.sessions[session_id].get("file_path", "")
            if isinstance(current_path, str) and current_path:
                self.sessions[session_id]["file_paths"] = [current_path, file_path]
            elif isinstance(current_path, list):
                current_path.append(file_path)
                self.sessions[session_id]["file_paths"] = current_path
            else:
                self.sessions[session_id]["file_paths"] = [file_path]
            
            print(f"Appended {len(new_documents)} documents to session {session_id}")
            return True
            
        except Exception as e:
            print(f"Error appending file: {str(e)}")
            return False
    
    async def query(self, question: str, session_id: str) -> Dict[str, Any]:
        """Query the RAG system for support ticket resolution"""
        try:
            if session_id not in self.sessions:
                return {"error": "Session not found"}

            documents = self.sessions[session_id]["documents"]
            vectorstore = self.sessions[session_id].get("vectorstore")

            # Try semantic search first if vectorstore is available
            relevant_docs = []
            if vectorstore and self.embeddings_model:
                try:
                    search_results = vectorstore.similarity_search(question, k=5)
                    for result in search_results:
                        if result['document'].metadata.get('type') != 'column_summary':
                            relevant_docs.append({
                                "content": result['document'].page_content[:300] + "..." if len(result['document'].page_content) > 300 else result['document'].page_content,
                                "metadata": result['document'].metadata,
                                "relevance_score": result['score'],
                                "match_reasons": result['reasons']
                            })
                    print(f"Found {len(relevant_docs)} relevant documents using semantic search")
                except Exception as e:
                    print(f"Semantic search failed: {e}, falling back to keyword search")
                    search_results = self._fallback_keyword_search(question, documents, 5)
                    for result in search_results:
                        relevant_docs.append({
                            "content": result['document'].page_content[:300] + "..." if len(result['document'].page_content) > 300 else result['document'].page_content,
                            "metadata": result['document'].metadata,
                            "relevance_score": result['score'],
                            "match_reasons": result['reasons']
                        })
            else:
                # Fallback to keyword search
                search_results = self._fallback_keyword_search(question, documents, 5)
                for result in search_results:
                    relevant_docs.append({
                        "content": result['document'].page_content[:300] + "..." if len(result['document'].page_content) > 300 else result['document'].page_content,
                        "metadata": result['document'].metadata,
                        "relevance_score": result['score'],
                        "match_reasons": result['reasons']
                    })

            # Generate response using LLM if available
            if self.llm is not None:
                # Create context from relevant documents
                context = ""
                if relevant_docs:
                    context = "\n\nRelevant ticket history:\n"
                    for i, doc in enumerate(relevant_docs[:3]):  # Top 3 most relevant
                        context += f"\n--- Ticket {i+1} ---\n{doc['content']}\n"

                prompt = f"""{self.system_prompt}

{context}

USER QUERY: "{question}"

Provide a helpful response based on the ticket history and your knowledge. If this is a support query, reference similar past tickets where relevant."""

                try:
                    response = self.llm.invoke(prompt)
                    confidence = "High" if len(relevant_docs) >= 3 else "Medium" if len(relevant_docs) >= 1 else "Low"
                    return {
                        "answer": f"**Confidence: {confidence}**\n\n{response}",
                        "sources": relevant_docs
                    }
                except Exception as e:
                    print(f"LLM query failed: {e}")
                    # Fallback to simple response
            
            # Fallback response when LLM is not available
            if relevant_docs:
                answer = "Based on similar past tickets, here are some relevant resolutions:\n\n"
                for i, doc in enumerate(relevant_docs[:2]):
                    answer += f"**Ticket {i+1}:**\n{doc['content']}\n\n"
                answer += "Please review these similar cases for potential solutions."
            else:
                answer = "I couldn't find specific tickets matching your query. Could you provide more details about the issue you're experiencing?"

            return {
                "answer": answer,
                "sources": relevant_docs
            }
            
        except Exception as e:
            return {"error": f"Error during query: {str(e)}"}
    
    async def add_resolution(self, session_id: str, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new resolution to the session's ticket data"""
        try:
            if session_id not in self.sessions:
                return {"error": "Session not found"}

            # Normalize the data
            normalized_data = {
                'error_code': resolution_data.get('error_code', 'N/A'),
                'module': resolution_data.get('module', 'General'),
                'ticket_level': resolution_data.get('ticket_level', 'L2'),
                'description': resolution_data.get('description', '').strip(),
                'resolution': resolution_data.get('resolution', resolution_data.get('resolution_steps', '')).strip()
            }

            # Validate required fields
            if not normalized_data['description'] or not normalized_data['resolution']:
                return {"error": "Missing required fields: description and resolution are required"}

            # Create a new document from the resolution data
            new_document = Document(
                page_content=f"""
Ticket Level: {normalized_data['ticket_level']}
Module: {normalized_data['module']}
Error Code: {normalized_data['error_code']}
Description: {normalized_data['description']}
Resolution: {normalized_data['resolution']}
Added: {datetime.now().isoformat()}
""".strip(),
                metadata={
                    "row_index": len(self.sessions[session_id]["documents"]),  # Next available index
                    "source": "user_added_resolution",
                    "type": "manual_entry",
                    "ticket_level": normalized_data['ticket_level'],
                    "module": normalized_data['module'],
                    "error_code": normalized_data['error_code'],
                    "added_at": datetime.now().isoformat()
                }
            )

            # Add to session documents
            self.sessions[session_id]["documents"].append(new_document)

            # Update vectorstore if it exists
            if self.sessions[session_id].get("vectorstore"):
                try:
                    self.sessions[session_id]["vectorstore"].add_documents([new_document])
                    self.save_vectorstore(self.sessions[session_id]["vectorstore"], session_id)
                    print(f"Updated vectorstore with new resolution")
                except Exception as e:
                    print(f"Failed to update vectorstore with new resolution: {e}")

            print(f"Added new resolution to session {session_id}: {normalized_data['description'][:50]}...")

            return {
                "success": True,
                "message": "Resolution added successfully",
                "document_count": len(self.sessions[session_id]["documents"])
            }

        except Exception as e:
            print(f"Error adding resolution: {str(e)}")
            return {"error": f"Error adding resolution: {str(e)}"}
    
    async def cleanup_session(self, session_id: str):
        """Clean up session data"""
        if session_id in self.sessions:
            del self.sessions[session_id]