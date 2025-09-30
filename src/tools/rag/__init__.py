"""
RAG (Retrieval-Augmented Generation) Tools Package
"""

from .rag_system import VersaillesRAG
from .rag_qa_mistral import VersaillesRAGQA
from .store_vectors import VersaillesVectorStore
from .dual_rag_fusion import DualRAGFusion, ask_versailles_dual_rag
from .rag_tools import (
    versailles_search_tool,
    versailles_context_tool,
    versailles_expert_tool,
    versailles_dual_rag_tool,
    search_versailles_knowledge,
    get_versailles_context,
    ask_versailles_expert,
    ask_versailles_expert_legacy
)

__all__ = [
    'VersaillesRAG',
    'VersaillesRAGQA', 
    'VersaillesVectorStore',
    'DualRAGFusion',
    'versailles_search_tool',
    'versailles_context_tool', 
    'versailles_expert_tool',
    'versailles_dual_rag_tool',
    'search_versailles_knowledge',
    'get_versailles_context',
    'ask_versailles_expert',
    'ask_versailles_expert_legacy',
    'ask_versailles_dual_rag'
]
