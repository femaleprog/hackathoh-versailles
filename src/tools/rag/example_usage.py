#!/usr/bin/env python3
"""
Example usage of the Versailles RAG tools with the agent
"""

import sys
import os
import asyncio

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agent import Agent


async def test_rag_with_agent():
    """Test RAG functionality through the agent"""
    print("=== Testing RAG Tools with Agent ===\n")
    
    try:
        # Initialize the agent
        agent = Agent()
        
        # Test questions about Versailles
        test_questions = [
            "Qui était Louis XIV et quel était son rôle à Versailles?",
            "Peux-tu me parler de la Galerie des Glaces?",
            "Quand le château de Versailles a-t-il été construit?",
            "Que peut-on visiter dans les jardins de Versailles?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"Question {i}: {question}")
            print("-" * 50)
            
            # Get response from agent (non-streaming)
            response = await agent.chat_completion_non_stream(question)
            
            if response and response.get('choices'):
                content = response['choices'][0]['message']['content']
                print(f"Réponse: {content}\n")
                
                # Show tool calls if any
                tool_calls = response['choices'][0]['message'].get('tool_calls', [])
                if tool_calls:
                    print("Outils utilisés:")
                    for tool_call in tool_calls:
                        tool_name = tool_call['function']['name']
                        print(f"- {tool_name}")
            else:
                print("Aucune réponse reçue\n")
            
            print("=" * 60 + "\n")
    
    except Exception as e:
        print(f"Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to run tests"""
    print("Versailles RAG Tools - Agent Integration Test")
    print("=" * 60)
    
    # Note: These tests require proper environment setup
    print("Configuration requise:")
    print("1. MISTRAL_API_KEY dans votre .env")
    print("2. WEAVIATE_URL et WEAVIATE_API_KEY pour RAG")
    print("3. Base de données Weaviate avec les documents Versailles")
    print()
    
    try:
        # Run tests
        asyncio.run(test_rag_with_agent())
        
    except Exception as e:
        print(f"Erreur: {e}")
        print("Assurez-vous que votre environnement est correctement configuré.")


if __name__ == "__main__":
    main()
