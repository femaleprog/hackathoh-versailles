#!/usr/bin/env python3
"""
RAG-powered QA system using Mistral AI and Weaviate
"""

import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import weaviate
from weaviate.classes.init import Auth
from mistralai import Mistral

# Load environment variables
load_dotenv()

class VersaillesRAGQA:
    """RAG-powered QA system for Versailles using Mistral AI"""
    
    def __init__(self):
        """Initialize the RAG QA system"""
        self.weaviate_url = os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.collection_name = "TxtVector"
        
        self.embedding_model = None
        self.weaviate_client = None
        self.mistral_client = None
        
        # Initialize components
        self._setup_embedding_model()
        self._setup_weaviate_client()
        self._setup_mistral_client()
        
    def _setup_embedding_model(self):
        """Setup the BGE-M3 embedding model"""
        print("Loading BGE-M3 embedding model...")
        self.embedding_model = SentenceTransformer("BAAI/bge-m3")
        print("✅ Embedding model loaded successfully")
        
    def _setup_weaviate_client(self):
        """Setup Weaviate client"""
        print("Setting up Weaviate client...")
        
        try:
            self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=Auth.api_key(self.weaviate_api_key)
            )
            
            if self.weaviate_client.is_ready():
                print("✅ Weaviate client connected successfully")
            else:
                raise Exception("Weaviate client not ready")
                
        except Exception as e:
            print(f"❌ Error setting up Weaviate: {e}")
            raise
    
    def _setup_mistral_client(self):
        """Setup Mistral AI client"""
        print("Setting up Mistral AI client...")
        
        try:
            self.mistral_client = Mistral(api_key=self.mistral_api_key)
            print("✅ Mistral AI client setup successfully")
            
        except Exception as e:
            print(f"❌ Error setting up Mistral AI: {e}")
            raise
    
    def retrieve_relevant_chunks(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from Weaviate
        
        Args:
            query: User's question
            limit: Number of chunks to retrieve
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search for relevant chunks
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                return_metadata=["distance"]
            )
            
            chunks = []
            for obj in response.objects:
                chunks.append({
                    "content": obj.properties["content"],
                    "url": obj.properties["url"],
                    "title": obj.properties["title"],
                    "section": obj.properties["section"],
                    "distance": obj.metadata.distance
                })
            
            return chunks
            
        except Exception as e:
            print(f"❌ Error retrieving chunks: {e}")
            return []
    
    def generate_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Generate answer using Mistral AI with retrieved context
        
        Args:
            question: User's question
            context_chunks: Retrieved relevant chunks
            
        Returns:
            Generated answer
        """
        try:
            # Prepare context from chunks
            context_parts = []
            for i, chunk in enumerate(context_chunks, 1):
                context_parts.append(f"""
Source {i}:
Title: {chunk['title']}
Section: {chunk['section']}
URL: {chunk['url']}
Content: {chunk['content']}
""")
            
            context = "\n".join(context_parts)
            
            # Create prompt
            system_prompt = """Tu es un assistant expert du Château de Versailles. Tu réponds aux questions en français en utilisant uniquement les informations fournies dans le contexte. 

Instructions:
1. Réponds en français de manière claire et précise
2. Utilise uniquement les informations du contexte fourni
3. Si l'information n'est pas dans le contexte, dis "Je n'ai pas trouvé cette information dans ma base de connaissances"
4. Cite les sources quand c'est pertinent
5. Sois informatif mais concis"""

            user_prompt = f"""Contexte:
{context}

Question: {question}

Réponse:"""

            # Generate response using Mistral
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.mistral_client.chat.complete(
                model="mistral-medium-latest",
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            return f"Erreur lors de la génération de la réponse: {e}"
    
    def ask(self, question: str, num_chunks: int = 5, show_sources: bool = True) -> Dict[str, Any]:
        """
        Ask a question and get an answer with sources
        
        Args:
            question: User's question
            num_chunks: Number of relevant chunks to retrieve
            show_sources: Whether to show source information
            
        Returns:
            Dictionary with answer and sources
        """
        print(f"🔍 Question: {question}")
        print("-" * 50)
        
        # Retrieve relevant chunks
        chunks = self.retrieve_relevant_chunks(question, limit=num_chunks)
        
        if not chunks:
            return {
                "answer": "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question.",
                "sources": []
            }
        
        # Generate answer
        answer = self.generate_answer(question, chunks)
        
        result = {
            "question": question,
            "answer": answer,
            "sources": chunks
        }
        
        # Display results
        print(f"💡 Réponse: {answer}")
        
        if show_sources:
            print(f"\n📚 Sources utilisées ({len(chunks)} chunks):")
            for i, chunk in enumerate(chunks, 1):
                print(f"\n{i}. {chunk['title']} - {chunk['section']}")
                print(f"   Distance: {chunk['distance']:.4f}")
                print(f"   URL: {chunk['url']}")
                print(f"   Extrait: {chunk['content'][:150]}...")
        
        return result
    
    def interactive_qa(self):
        """Interactive Q&A session"""
        print("\n" + "="*60)
        print("🏰 SYSTÈME DE Q&A INTERACTIF - CHÂTEAU DE VERSAILLES")
        print("="*60)
        print("Posez vos questions sur le Château de Versailles!")
        print("Tapez 'quit' pour quitter.\n")
        
        while True:
            try:
                question = input("❓ Votre question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("Au revoir! 👋")
                    break
                
                if not question:
                    continue
                
                print()
                result = self.ask(question)
                print("\n" + "="*60 + "\n")
                
            except KeyboardInterrupt:
                print("\n\nAu revoir! 👋")
                break
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    def close(self):
        """Close connections"""
        if self.weaviate_client:
            self.weaviate_client.close()

def main():
    """Main function to test the RAG QA system"""
    
    # Initialize RAG QA system
    qa_system = VersaillesRAGQA()
    
    try:
        # Test questions
        test_questions = [
            "Qui était Louis XIV?",
            "Que peut-on voir dans la Galerie des Glaces?",
            "Comment visiter le château de Versailles?",
            "Quelle est l'histoire de Marie-Antoinette à Versailles?",
            "Quels sont les jardins du château?",
            "Quand le château a-t-il été construit?"
        ]
        
        print("\n" + "="*60)
        print("🧪 TEST DU SYSTÈME RAG QA")
        print("="*60)
        
        for question in test_questions:
            result = qa_system.ask(question, num_chunks=3, show_sources=False)
            print("\n" + "="*60 + "\n")
        
        # Start interactive session
        qa_system.interactive_qa()
        
    finally:
        qa_system.close()

if __name__ == "__main__":
    main()
