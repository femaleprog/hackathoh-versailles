# Versailles AI Agent with Dual RAG

Un agent conversationnel expert du Château de Versailles utilisant un système RAG dual (Retrieval-Augmented Generation) qui combine des sources textuelles et PDF.

## 🚀 Fonctionnalités

- **Agent conversationnel** avec Mistral AI
- **Système RAG dual** : recherche simultanée dans les textes web et guides PDF
- **Fusion intelligente** des résultats avec citations automatiques
- **Réponses naturelles** avec sources web uniquement

## 📁 Structure du projet

```
src/
├── agent.py                    # Agent principal avec Mistral AI
├── tools/
│   └── rag/
│       ├── dual_rag_fusion.py # Système RAG dual avec fusion Mistral
│       ├── rag_tools.py       # Outils RAG pour l'agent
│       ├── store_vectors.py   # Stockage TxtVector (textes web)
│       ├── pdf_to_pdfvector.py # Stockage PdfVector (guides PDF)
│       └── rag_*.py          # Autres composants RAG
```

## 🔧 Configuration

1. Copier `.env.example` vers `.env`
2. Configurer les clés API :
   ```
   MISTRAL_API_KEY=your_mistral_key
   WEAVIATE_URL=your_weaviate_url
   WEAVIATE_API_KEY=your_weaviate_key
   ```

## 💾 Collections Weaviate

- **TxtVector** : 3,065 documents textuels du site officiel
- **PdfVector** : Pages des guides PDF hackathon

## 🎯 Utilisation

L'agent utilise automatiquement le système dual RAG via `versailles_expert_tool` qui :
1. Recherche dans les deux collections (TxtVector + PdfVector)
2. Fusionne les résultats avec Mistral AI
3. Retourne une réponse naturelle avec sources web uniquement