#!/usr/bin/env python3
"""
Dual RAG Fusion System
Combines TxtVector and PdfVector search results using Mistral AI for fusion
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import weaviate
from weaviate.classes.init import Auth
from llama_index.llms.mistralai import MistralAI

# Load environment variables
load_dotenv()

class DualRAGFusion:
    """Dual RAG system that searches both TxtVector and PdfVector collections and fuses results"""
    
    def __init__(self):
        """Initialize the dual RAG fusion system"""
        self.weaviate_url = os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        
        self.embedding_model = None
        self.weaviate_client = None
        self.mistral_llm = None
        
        # Collection names
        self.txt_collection = "TxtVector"
        self.pdf_collection = "PdfVector"
        
        # Initialize components
        self._setup_embedding_model()
        self._setup_weaviate_client()
        self._setup_mistral_llm()
    
    def _setup_embedding_model(self):
        """Setup the BGE-M3 embedding model"""
        print("Loading BGE-M3 embedding model...")
        self.embedding_model = SentenceTransformer("BAAI/bge-m3")
        print("✅ Embedding model loaded successfully")
    
    def _setup_weaviate_client(self):
        """Setup Weaviate client"""
        if not self.weaviate_url or not self.weaviate_api_key:
            raise ValueError("Weaviate credentials not found in environment")
        
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
    
    def _setup_mistral_llm(self):
        """Setup Mistral AI LLM for fusion"""
        if not self.mistral_api_key:
            raise ValueError("Mistral API key not found in environment")
        
        try:
            self.mistral_llm = MistralAI(
                model="mistral-medium-latest",
                api_key=self.mistral_api_key
            )
            print("✅ Mistral AI LLM initialized successfully")
        except Exception as e:
            print(f"❌ Error setting up Mistral LLM: {e}")
            raise
    
    def search_collection(self, query: str, collection_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search a specific collection for relevant documents
        
        Args:
            query: Search query
            collection_name: Name of the collection to search
            limit: Number of results to return
            
        Returns:
            List of search results with metadata
        """
        try:
            collection = self.weaviate_client.collections.get(collection_name)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                return_metadata=["distance"]
            )
            
            results = []
            for obj in response.objects:
                result = {
                    "content": obj.properties.get("content", ""),
                    "title": obj.properties.get("title", ""),
                    "section": obj.properties.get("section", ""),
                    "url": obj.properties.get("url", ""),
                    "distance": obj.metadata.distance,
                    "relevance": 1 - obj.metadata.distance,
                    "source_type": "text" if collection_name == self.txt_collection else "pdf"
                }
                
                # Add PDF-specific metadata if available
                if collection_name == self.pdf_collection:
                    result["page_number"] = obj.properties.get("page_number", 0)
                    result["pdf_filename"] = obj.properties.get("pdf_filename", "")
                
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching {collection_name}: {e}")
            return []
    
    def dual_search(self, query: str, txt_limit: int = 3, pdf_limit: int = 3) -> Dict[str, Any]:
        """
        Search both TxtVector and PdfVector collections
        
        Args:
            query: Search query
            txt_limit: Number of results from TxtVector
            pdf_limit: Number of results from PdfVector
            
        Returns:
            Dictionary containing results from both collections
        """
        print(f"🔍 Searching both collections for: '{query}'")
        
        # Search TxtVector collection
        txt_results = self.search_collection(query, self.txt_collection, txt_limit)
        print(f"📄 Found {len(txt_results)} results in TxtVector")
        
        # Search PdfVector collection
        pdf_results = self.search_collection(query, self.pdf_collection, pdf_limit)
        print(f"📋 Found {len(pdf_results)} results in PdfVector")
        
        return {
            "query": query,
            "txt_results": txt_results,
            "pdf_results": pdf_results,
            "total_results": len(txt_results) + len(pdf_results)
        }
    
    def format_results_for_fusion(self, search_results: Dict[str, Any]) -> str:
        """
        Format search results for Mistral AI fusion
        
        Args:
            search_results: Results from dual_search
            
        Returns:
            Formatted string for LLM processing
        """
        formatted = f"Question: {search_results['query']}\n\n"
        
        # Format TxtVector results
        if search_results['txt_results']:
            formatted += "=== SOURCES TEXTUELLES ===\n"
            for i, result in enumerate(search_results['txt_results'], 1):
                formatted += f"\nSource Texte {i} (Pertinence: {result['relevance']:.3f}):\n"
                formatted += f"Titre: {result['title']}\n"
                formatted += f"Section: {result['section']}\n"
                formatted += f"Contenu: {result['content'][:500]}{'...' if len(result['content']) > 500 else ''}\n"
                if result['url']:
                    formatted += f"URL: {result['url']}\n"
        
        # Format PdfVector results
        if search_results['pdf_results']:
            formatted += "\n=== SOURCES PDF ===\n"
            for i, result in enumerate(search_results['pdf_results'], 1):
                formatted += f"\nSource PDF {i} (Pertinence: {result['relevance']:.3f}):\n"
                formatted += f"Fichier: {result.get('pdf_filename', 'Unknown')}\n"
                formatted += f"Page: {result.get('page_number', 'Unknown')}\n"
                formatted += f"Contenu: {result['content'][:500]}{'...' if len(result['content']) > 500 else ''}\n"
        
        return formatted
    
    def fuse_results_with_mistral(self, search_results: Dict[str, Any]) -> str:
        """
        Use Mistral AI to fuse and synthesize results from both collections
        
        Args:
            search_results: Results from dual_search
            
        Returns:
            Fused and synthesized answer
        """
        if not search_results['txt_results'] and not search_results['pdf_results']:
            return "Je n'ai trouvé aucune information pertinente dans les deux bases de connaissances pour répondre à votre question."
        
        # Format results for the LLM
        formatted_results = self.format_results_for_fusion(search_results)
        
        # Create fusion prompt
        fusion_prompt = f"""Tu es un expert du Château de Versailles. Tu dois analyser et fusionner les informations pour répondre à la question de l'utilisateur.

INSTRUCTIONS CRITIQUES:
1. Analyse toutes les sources fournies (textuelles et PDF)
2. Synthétise les informations en une réponse cohérente et complète
3. Privilégie les informations les plus pertinentes (score de pertinence élevé)
4. Si les sources se complètent, combine-les intelligemment
5. Si les sources se contredisent, mentionne-le et explique
6. **IMPORTANT**: Ne mentionne PAS les sources PDF dans ta réponse
7. **IMPORTANT**: Utilise les informations des PDF mais ne les cite pas
8. **IMPORTANT**: Seules les sources web avec URLs doivent être mentionnées
9. Réponds en français de manière claire et naturelle

FORMAT DE RÉPONSE:
- Réponse directe et naturelle à la question
- Pas de citations dans le texte principal
- Les URLs seront ajoutées automatiquement à la fin

SOURCES DISPONIBLES:
{formatted_results}

RÉPONSE NATURELLE (sans citations dans le texte):"""

        try:
            # Generate fused response using Mistral
            response = self.mistral_llm.complete(fusion_prompt)
            fused_answer = response.text.strip()
            
            # Add metadata about sources used
            source_info = self._generate_source_summary(search_results)
            
            return f"{fused_answer}\n\n{source_info}"
            
        except Exception as e:
            print(f"❌ Error during Mistral fusion: {e}")
            return f"Erreur lors de la fusion des résultats: {str(e)}"
    
    def _generate_source_summary(self, search_results: Dict[str, Any]) -> str:
        """Generate a simple summary with only web URLs (no PDF mentions)"""
        # Only show text sources with URLs
        if not search_results['txt_results']:
            return ""
        
        # Filter text sources that have URLs
        sources_with_urls = [result for result in search_results['txt_results'] if result.get('url')]
        
        if not sources_with_urls:
            return ""
        
        summary = "\n**Sources:**\n"
        for result in sources_with_urls:
            if result['url']:
                summary += f"- {result['url']}\n"
        
        return summary
    
    def ask(self, question: str, txt_limit: int = 3, pdf_limit: int = 3) -> Dict[str, Any]:
        """
        Main method to ask a question using dual RAG fusion
        
        Args:
            question: User's question
            txt_limit: Number of results from TxtVector
            pdf_limit: Number of results from PdfVector
            
        Returns:
            Dictionary with fused answer and metadata
        """
        try:
            # Search both collections
            search_results = self.dual_search(question, txt_limit, pdf_limit)
            
            # Fuse results using Mistral AI
            fused_answer = self.fuse_results_with_mistral(search_results)
            
            return {
                "question": question,
                "answer": fused_answer,
                "txt_sources": len(search_results['txt_results']),
                "pdf_sources": len(search_results['pdf_results']),
                "total_sources": search_results['total_results'],
                "raw_results": search_results
            }
            
        except Exception as e:
            return {
                "question": question,
                "answer": f"Erreur lors du traitement de votre question: {str(e)}",
                "txt_sources": 0,
                "pdf_sources": 0,
                "total_sources": 0,
                "error": str(e)
            }
    
    def close(self):
        """Close connections"""
        if self.weaviate_client:
            self.weaviate_client.close()

# Global instance
_dual_rag_instance: Optional[DualRAGFusion] = None

def get_dual_rag_instance() -> DualRAGFusion:
    """Get or create the global dual RAG instance"""
    global _dual_rag_instance
    if _dual_rag_instance is None:
        _dual_rag_instance = DualRAGFusion()
    return _dual_rag_instance

def ask_versailles_dual_rag(question: str, txt_limit: int = 3, pdf_limit: int = 3) -> str:
    """
    Ask a question using the dual RAG fusion system
    
    Args:
        question: User's question about Versailles
        txt_limit: Number of text sources to retrieve
        pdf_limit: Number of PDF sources to retrieve
        
    Returns:
        Fused answer from both text and PDF sources
    """
    try:
        dual_rag = get_dual_rag_instance()
        result = dual_rag.ask(question, txt_limit, pdf_limit)
        return result["answer"]
    except Exception as e:
        return f"Erreur du système RAG dual: {str(e)}"

def main():
    """Test the dual RAG fusion system"""
    dual_rag = DualRAGFusion()
    
    test_questions = [
        "Quels sont les horaires d'ouverture du château de Versailles?",
        "Comment visiter la Galerie des Glaces?",
        "Que peut-on voir dans les jardins de Versailles?",
        "Quels sont les tarifs des billets?"
    ]
    
    print("=== Test du Système RAG Dual avec Fusion ===\n")
    
    for question in test_questions:
        print(f"🔍 Question: {question}")
        print("-" * 50)
        
        result = dual_rag.ask(question)
        
        print(f"📊 Sources: {result['txt_sources']} texte(s) + {result['pdf_sources']} PDF(s)")
        print(f"💡 Réponse fusionnée:\n{result['answer']}")
        print("\n" + "="*60 + "\n")
    
    dual_rag.close()

if __name__ == "__main__":
    main()
