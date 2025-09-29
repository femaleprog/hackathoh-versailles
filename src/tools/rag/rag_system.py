#!/usr/bin/env python3
"""
RAG System for Versailles using LlamaIndex and Weaviate
"""

import os
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import weaviate
from weaviate.classes.init import Auth
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

# Load environment variables
load_dotenv()

class VersaillesRAG:
    """RAG System for Versailles knowledge base"""
    
    def __init__(self, weaviate_url: str = None):
        """
        Initialize the RAG system
        
        Args:
            weaviate_url: URL of your Weaviate cluster (optional, will use env var if not provided)
        """
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        self.embedding_model = None
        self.weaviate_client = None
        self.vector_store = None
        self.index = None
        self.query_engine = None
        
        # Initialize components
        self._setup_embedding_model()
        self._setup_weaviate_client()
        
    def _setup_embedding_model(self):
        """Setup the BGE-M3 embedding model"""
        print("Loading BGE-M3 embedding model...")
        
        # Initialize the embedding model
        embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-m3",
            trust_remote_code=True
        )
        
        # Set global settings
        Settings.embed_model = embed_model
        Settings.chunk_size = 800
        Settings.chunk_overlap = 100
        
        print("✅ Embedding model loaded successfully")
        
    def _setup_weaviate_client(self):
        """Setup Weaviate client and vector store"""
        print("Setting up Weaviate client...")
        
        try:
            # Create Weaviate client (v4 syntax)
            self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=Auth.api_key(self.weaviate_api_key)
            )
            
            # Test connection
            if self.weaviate_client.is_ready():
                print("✅ Weaviate client connected successfully")
            else:
                raise Exception("Weaviate client not ready")
                
            # Setup vector store
            self.vector_store = WeaviateVectorStore(
                weaviate_client=self.weaviate_client,
                index_name="VersaillesKnowledge"
            )
            
        except Exception as e:
            print(f"❌ Error setting up Weaviate: {e}")
            print("Note: Make sure to update the weaviate_url with your actual cluster URL")
            
    def parse_markdown_chunks(self, file_path: str) -> List[Document]:
        """
        Parse the extracted texts markdown file into LlamaIndex documents
        
        Args:
            file_path: Path to the extracted_texts.md file
            
        Returns:
            List of LlamaIndex Document objects
        """
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by chunks (each chunk starts with ##)
            chunks = re.split(r'\n## ', content)
            
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                    
                # Add back the ## for non-first chunks
                if i > 0:
                    chunk = "## " + chunk
                
                # Extract metadata
                lines = chunk.split('\n')
                title = ""
                url = ""
                section = ""
                content_text = ""
                
                for j, line in enumerate(lines):
                    if line.startswith('## '):
                        title = line[3:].strip()
                    elif line.startswith('**URL:**'):
                        url = line.replace('**URL:**', '').strip()
                    elif line.startswith('### '):
                        section = line[4:].strip()
                        # Content starts after the section header
                        content_text = '\n'.join(lines[j+1:]).strip()
                        break
                
                if content_text and title:
                    # Create document with metadata
                    doc = Document(
                        text=content_text,
                        metadata={
                            "title": title,
                            "url": url,
                            "section": section,
                            "source": "Château de Versailles"
                        }
                    )
                    documents.append(doc)
            
            print(f"✅ Parsed {len(documents)} documents from {file_path}")
            return documents
            
        except Exception as e:
            print(f"❌ Error parsing markdown file: {e}")
            return []
    
    def build_index(self, documents: List[Document]):
        """
        Build the vector index from documents
        
        Args:
            documents: List of LlamaIndex Document objects
        """
        if not self.vector_store:
            print("❌ Vector store not initialized")
            return
            
        try:
            print("Building vector index...")
            
            # Create storage context
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            
            # Build index
            self.index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=True
            )
            
            print("✅ Vector index built successfully")
            
        except Exception as e:
            print(f"❌ Error building index: {e}")
    
    def setup_query_engine(self, similarity_top_k: int = 5, similarity_cutoff: float = 0.7):
        """
        Setup the query engine for RAG
        
        Args:
            similarity_top_k: Number of top similar chunks to retrieve
            similarity_cutoff: Minimum similarity score for results
        """
        if not self.index:
            print("❌ Index not built yet")
            return
            
        try:
            # Create retriever
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=similarity_top_k
            )
            
            # Create query engine with post-processor
            self.query_engine = RetrieverQueryEngine(
                retriever=retriever,
                node_postprocessors=[
                    SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)
                ]
            )
            
            print("✅ Query engine setup successfully")
            
        except Exception as e:
            print(f"❌ Error setting up query engine: {e}")
    
    def query(self, question: str) -> str:
        """
        Query the RAG system
        
        Args:
            question: User's question
            
        Returns:
            Answer from the RAG system
        """
        if not self.query_engine:
            return "❌ Query engine not initialized"
            
        try:
            response = self.query_engine.query(question)
            return str(response)
            
        except Exception as e:
            return f"❌ Error during query: {e}"
    
    def get_relevant_chunks(self, question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant chunks for a question without generating an answer
        
        Args:
            question: User's question
            top_k: Number of top chunks to return
            
        Returns:
            List of relevant chunks with metadata
        """
        if not self.index:
            return []
            
        try:
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=top_k
            )
            
            nodes = retriever.retrieve(question)
            
            chunks = []
            for node in nodes:
                chunks.append({
                    "text": node.text,
                    "score": node.score,
                    "metadata": node.metadata
                })
            
            return chunks
            
        except Exception as e:
            print(f"❌ Error retrieving chunks: {e}")
            return []

def main():
    """Main function to demonstrate the RAG system"""
    
    # Initialize RAG system (will use URL from .env file)
    rag = VersaillesRAG()
    
    # Parse documents from extracted texts
    documents = rag.parse_markdown_chunks("extracted_texts.md")
    
    if not documents:
        print("No documents found. Make sure extracted_texts.md exists.")
        return
    
    # Build index
    rag.build_index(documents)
    
    # Setup query engine
    rag.setup_query_engine()
    
    # Example queries
    test_queries = [
        "Qui était Louis XIV?",
        "Que peut-on voir dans la Galerie des Glaces?",
        "Comment visiter le château de Versailles?",
        "Quelle est l'histoire de Marie-Antoinette à Versailles?"
    ]
    
    print("\n" + "="*50)
    print("TESTING RAG SYSTEM")
    print("="*50)
    
    for query in test_queries:
        print(f"\n🔍 Question: {query}")
        print("-" * 40)
        
        # Get relevant chunks
        chunks = rag.get_relevant_chunks(query, top_k=2)
        
        if chunks:
            print("📄 Relevant chunks found:")
            for i, chunk in enumerate(chunks, 1):
                print(f"\n{i}. Score: {chunk['score']:.3f}")
                print(f"   Title: {chunk['metadata'].get('title', 'N/A')}")
                print(f"   Section: {chunk['metadata'].get('section', 'N/A')}")
                print(f"   Text: {chunk['text'][:200]}...")
        else:
            print("❌ No relevant chunks found")
        
        # Generate answer
        answer = rag.query(query)
        print(f"\n💡 Answer: {answer}")
        print("\n" + "="*50)

if __name__ == "__main__":
    main()
