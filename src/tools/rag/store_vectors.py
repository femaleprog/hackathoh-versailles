#!/usr/bin/env python3
"""
Store Versailles chunks as vectors in Weaviate
"""

import os
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
import uuid
from tqdm import tqdm

# Load environment variables
load_dotenv()

class VersaillesVectorStore:
    """Store Versailles knowledge chunks as vectors in Weaviate"""
    
    def __init__(self):
        """Initialize the vector store"""
        self.weaviate_url = os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        self.collection_name = "TxtVector"
        self.embedding_model = None
        self.weaviate_client = None
        
        # Initialize components
        self._setup_embedding_model()
        self._setup_weaviate_client()
        self._setup_collection()
        
    def _setup_embedding_model(self):
        """Setup the BGE-M3 embedding model"""
        print("Loading BGE-M3 embedding model...")
        self.embedding_model = SentenceTransformer("BAAI/bge-m3")
        print("✅ Embedding model loaded successfully")
        
    def _setup_weaviate_client(self):
        """Setup Weaviate client"""
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
                
        except Exception as e:
            print(f"❌ Error setting up Weaviate: {e}")
            raise
    
    def _setup_collection(self):
        """Setup or create the TxtVector collection"""
        print(f"Setting up collection: {self.collection_name}")
        
        try:
            # Check if collection exists
            if self.weaviate_client.collections.exists(self.collection_name):
                print(f"Collection {self.collection_name} already exists")
                # Check if it has data
                collection = self.weaviate_client.collections.get(self.collection_name)
                total_objects = collection.aggregate.over_all(total_count=True).total_count
                print(f"Current objects in collection: {total_objects}")
                
                if total_objects > 0:
                    print("Collection has data, skipping recreation")
                    return
                else:
                    print("Collection is empty, will populate it")
            else:
                # Create new collection
                self.weaviate_client.collections.create(
                    name=self.collection_name,
                    vectorizer_config=Configure.Vectorizer.none(),  # We'll provide our own vectors
                    properties=[
                        Property(name="content", data_type=DataType.TEXT),
                        Property(name="url", data_type=DataType.TEXT),
                        Property(name="title", data_type=DataType.TEXT),
                        Property(name="section", data_type=DataType.TEXT),
                    ]
                )
                print(f"✅ Collection {self.collection_name} created successfully")
            
        except Exception as e:
            print(f"❌ Error setting up collection: {e}")
            raise
    
    def parse_markdown_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse the extracted texts markdown file into chunks
        
        Args:
            file_path: Path to the extracted_texts.md file
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by chunks (each chunk starts with ##)
            raw_chunks = re.split(r'\n## ', content)
            
            for i, chunk in enumerate(raw_chunks):
                if not chunk.strip():
                    continue
                    
                # Add back the ## for non-first chunks
                if i > 0:
                    chunk = "## " + chunk
                
                # Extract metadata and content
                lines = chunk.split('\n')
                title = ""
                url = ""
                section = ""
                content_lines = []
                
                parsing_content = False
                
                for line in lines:
                    if line.startswith('## '):
                        title = line[3:].strip()
                        content_lines.append(line)  # Include title in content
                    elif line.startswith('**URL:**'):
                        url = line.replace('**URL:**', '').strip()
                        # Don't include URL line in content
                    elif line.startswith('### '):
                        section = line[4:].strip()
                        content_lines.append(line)  # Include section in content
                        parsing_content = True
                    elif parsing_content and line.strip():
                        content_lines.append(line)
                
                # Join content (excluding URL line)
                content_text = '\n'.join(content_lines).strip()
                
                if content_text and title:
                    chunk_data = {
                        "content": content_text,
                        "url": url,
                        "title": title,
                        "section": section
                    }
                    chunks.append(chunk_data)
            
            print(f"✅ Parsed {len(chunks)} chunks from {file_path}")
            return chunks
            
        except Exception as e:
            print(f"❌ Error parsing markdown file: {e}")
            return []
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    
    def store_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Store chunks with their embeddings in Weaviate
        
        Args:
            chunks: List of chunk dictionaries
        """
        if not chunks:
            print("No chunks to store")
            return
        
        print(f"Storing {len(chunks)} chunks in Weaviate...")
        
        try:
            # Get the collection
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            # Prepare texts for embedding
            texts = [chunk["content"] for chunk in chunks]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            
            # Prepare data for batch insert
            objects = []
            for i, chunk in enumerate(chunks):
                obj = {
                    "properties": {
                        "content": chunk["content"],
                        "url": chunk["url"],
                        "title": chunk["title"],
                        "section": chunk["section"]
                    },
                    "vector": embeddings[i]
                }
                objects.append(obj)
            
            # Batch insert
            print("Inserting objects into Weaviate...")
            with collection.batch.dynamic() as batch:
                for obj in tqdm(objects, desc="Inserting chunks"):
                    batch.add_object(
                        properties=obj["properties"],
                        vector=obj["vector"]
                    )
            
            print(f"✅ Successfully stored {len(chunks)} chunks in collection {self.collection_name}")
            
            # Verify insertion
            total_objects = collection.aggregate.over_all(total_count=True).total_count
            print(f"📊 Total objects in collection: {total_objects}")
            
        except Exception as e:
            print(f"❌ Error storing chunks: {e}")
            raise
    
    def test_search(self, query: str, limit: int = 3):
        """
        Test search functionality
        
        Args:
            query: Search query
            limit: Number of results to return
        """
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                return_metadata=["distance"]
            )
            
            print(f"\n🔍 Search results for: '{query}'")
            print("-" * 50)
            
            for i, obj in enumerate(response.objects, 1):
                print(f"\n{i}. Distance: {obj.metadata.distance:.4f}")
                print(f"   Title: {obj.properties['title']}")
                print(f"   Section: {obj.properties['section']}")
                print(f"   URL: {obj.properties['url']}")
                print(f"   Content: {obj.properties['content'][:200]}...")
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
    
    def close(self):
        """Close the Weaviate client"""
        if self.weaviate_client:
            self.weaviate_client.close()

def main():
    """Main function to store vectors"""
    
    # Initialize vector store
    store = VersaillesVectorStore()
    
    try:
        # Use the correct path to extracted_texts.md
        markdown_file = "/Users/yongkangzou/Desktop/Hackathons/Datacraft Hackathon/Versaille Hackathon/extracted_texts.md"
        
        # Parse chunks from extracted texts
        chunks = store.parse_markdown_chunks(markdown_file)
        
        if not chunks:
            print("No chunks found. Make sure extracted_texts.md exists.")
            return
        
        # Check if collection already has data
        collection = store.weaviate_client.collections.get(store.collection_name)
        total_objects = collection.aggregate.over_all(total_count=True).total_count
        
        if total_objects > 0:
            print(f"✅ TxtVector collection already has {total_objects} objects")
            print("Skipping embedding process")
        else:
            print("TxtVector collection is empty, proceeding with embedding...")
            # Store chunks as vectors
            store.store_chunks(chunks)
        
        # Test search functionality
        test_queries = [
            "Louis XIV",
            "Galerie des Glaces",
            "Marie-Antoinette",
            "jardins de Versailles"
        ]
        
        print("\n" + "="*60)
        print("TESTING SEARCH FUNCTIONALITY")
        print("="*60)
        
        for query in test_queries:
            store.test_search(query, limit=2)
            print("\n" + "="*60)
        
    finally:
        # Close connection
        store.close()

if __name__ == "__main__":
    main()
