#!/usr/bin/env python3
"""
RAG Tools for Agent Integration
Wrapper functions to make RAG functionality available to the agent.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from .rag_qa_mistral import VersaillesRAGQA
from .dual_rag_fusion import DualRAGFusion, ask_versailles_dual_rag


# Global RAG QA instance
_rag_qa_instance: Optional[VersaillesRAGQA] = None
_dual_rag_instance: Optional[DualRAGFusion] = None


def get_rag_qa_instance() -> VersaillesRAGQA:
    """Get or create the global RAG QA instance."""
    global _rag_qa_instance
    if _rag_qa_instance is None:
        _rag_qa_instance = VersaillesRAGQA()
    return _rag_qa_instance


def get_dual_rag_instance() -> DualRAGFusion:
    """Get or create the global dual RAG instance."""
    global _dual_rag_instance
    if _dual_rag_instance is None:
        _dual_rag_instance = DualRAGFusion()
    return _dual_rag_instance


def search_versailles_knowledge(question: str, num_sources: int = 3) -> str:
    """
    Search the Versailles knowledge base for information relevant to a question.
    
    Args:
        question: The question to search for
        num_sources: Number of source documents to retrieve (default: 3)
        
    Returns:
        A formatted string with the answer and sources
    """
    try:
        qa_system = get_rag_qa_instance()
        
        # Get the answer with sources
        result = qa_system.ask(question, num_chunks=num_sources, show_sources=False)
        
        if result.get('answer'):
            # Format the response for the agent
            response = f"**Answer:** {result['answer']}\n\n"
            
            if result.get('sources'):
                response += "**Sources:**\n"
                for i, source in enumerate(result['sources'], 1):
                    title = source.get('title', 'Unknown')
                    section = source.get('section', 'Unknown')
                    distance = source.get('distance', 0)
                    url = source.get('url', '')
                    
                    response += f"{i}. **{title}** - {section}\n"
                    response += f"   Relevance: {1-distance:.3f}\n"
                    if url:
                        response += f"   URL: {url}\n"
                    response += "\n"
            
            return response
        else:
            return "Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question sur Versailles."
            
    except Exception as e:
        return f"Erreur lors de la recherche dans la base de connaissances Versailles: {str(e)}"


def get_versailles_context(question: str, max_chunks: int = 5) -> str:
    """
    Get relevant context from Versailles knowledge base without generating an answer.
    Useful for providing context to the LLM for further processing.
    
    Args:
        question: The question or topic to get context for
        max_chunks: Maximum number of context chunks to retrieve
        
    Returns:
        Formatted context string
    """
    try:
        qa_system = get_rag_qa_instance()
        
        # Get relevant chunks without generating an answer
        chunks = qa_system.retrieve_relevant_chunks(question, limit=max_chunks)
        
        if not chunks:
            return "Aucun contexte pertinent trouvé dans la base de connaissances Versailles."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            title = chunk.get('title', 'Document inconnu')
            section = chunk.get('section', 'Section inconnue')
            content = chunk.get('content', '')
            distance = chunk.get('distance', 0)
            
            context_part = f"**Source {i}: {title} - {section}**\n"
            context_part += f"Pertinence: {1-distance:.3f}\n"
            context_part += f"Contenu: {content[:300]}{'...' if len(content) > 300 else ''}\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
        
    except Exception as e:
        return f"Erreur lors de la récupération du contexte Versailles: {str(e)}"


def ask_versailles_expert(question: str) -> str:
    """
    Ask a question to the Versailles expert system using DUAL RAG FUSION.
    This function searches both text and PDF collections and fuses results with Mistral AI.
    
    Args:
        question: Question about Versailles (in French or English)
        
    Returns:
        Expert answer fused from both text and PDF sources
    """
    try:
        # Use the new dual RAG fusion system
        return ask_versailles_dual_rag(question, txt_limit=3, pdf_limit=2)
            
    except Exception as e:
        return f"Erreur du système expert Versailles: {str(e)}"


def ask_versailles_expert_legacy(question: str) -> str:
    """
    Legacy function - Ask a question to the Versailles expert system (text only).
    This function combines retrieval and generation for comprehensive answers.
    
    Args:
        question: Question about Versailles (in French or English)
        
    Returns:
        Expert answer about Versailles with source citations
    """
    try:
        qa_system = get_rag_qa_instance()
        
        # Get comprehensive answer
        result = qa_system.ask(question, num_chunks=5, show_sources=False)
        
        if result.get('answer'):
            answer = result['answer']
            sources = result.get('sources', [])
            
            # Add source information
            if sources:
                answer += f"\n\n**Sources consultées ({len(sources)} documents):**\n"
                for i, source in enumerate(sources[:3], 1):  # Show top 3 sources
                    title = source.get('title', 'Document')
                    section = source.get('section', '')
                    if section:
                        answer += f"- {title}: {section}\n"
                    else:
                        answer += f"- {title}\n"
            
            return answer
        else:
            return "Je n'ai pas pu trouver d'informations spécifiques sur ce sujet dans ma base de connaissances sur Versailles."
            
    except Exception as e:
        return f"Erreur du système expert Versailles: {str(e)}"


# Tool functions for the agent
def versailles_search_tool(question: str, num_sources: int = 3) -> str:
    """Tool function for searching Versailles knowledge base."""
    return search_versailles_knowledge(question, num_sources)


def versailles_context_tool(question: str, max_chunks: int = 5) -> str:
    """Tool function for getting Versailles context."""
    return get_versailles_context(question, max_chunks)


def versailles_expert_tool(question: str) -> str:
    """Tool function for asking the Versailles expert using DUAL RAG FUSION."""
    return ask_versailles_expert(question)


def versailles_dual_rag_tool(question: str, txt_limit: int = 3, pdf_limit: int = 2) -> str:
    """
    Tool function for dual RAG fusion system.
    Searches both text and PDF collections and fuses results with Mistral AI.
    
    Args:
        question: Question about Versailles
        txt_limit: Number of text sources to retrieve
        pdf_limit: Number of PDF sources to retrieve
        
    Returns:
        Fused answer from both collections
    """
    return ask_versailles_dual_rag(question, txt_limit, pdf_limit)
