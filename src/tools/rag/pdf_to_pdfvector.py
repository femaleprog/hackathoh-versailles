#!/usr/bin/env python3
"""
PDF to PdfVector Pipeline
Process PDF files page by page and store in PdfVector collection using GME embeddings
"""

import os
import fitz  # PyMuPDF
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from tqdm import tqdm
import re

# Load environment variables
load_dotenv()

class PDFVectorProcessor:
    """Process PDF files page by page and store in PdfVector collection"""
    
    def __init__(self):
        """Initialize the PDF vector processor"""
        self.weaviate_url = os.getenv("WEAVIATE_URL")
        self.weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
        self.collection_name = "PdfVector"
        self.embedding_model = None
        self.weaviate_client = None
        
        # PDF file paths
        self.pdf_files = [
            "/Users/yongkangzou/Desktop/Hackathons/Datacraft Hackathon/Versaille Hackathon/data/Fiche_tips_hackathon_versailles.pdf",
            "/Users/yongkangzou/Desktop/Hackathons/Datacraft Hackathon/Versaille Hackathon/data/Livret-Hackathon_ChâteauDeVersailles.pdf"
        ]
        
        # Initialize components
        self._setup_embedding_model()
        self._setup_weaviate_client()
        self._setup_collection()
    
    def _setup_embedding_model(self):
        """Setup the BGE-M3 embedding model (GME)"""
        print("Loading BGE-M3 (GME) embedding model...")
        self.embedding_model = SentenceTransformer("BAAI/bge-m3")
        print("✅ GME embedding model loaded successfully")
    
    def _setup_weaviate_client(self):
        """Setup Weaviate client"""
        print("Setting up Weaviate client...")
        
        if not self.weaviate_url or not self.weaviate_api_key:
            print("❌ Weaviate credentials not found")
            print("Please set WEAVIATE_URL and WEAVIATE_API_KEY in your .env file")
            return
        
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
        """Setup or create the PdfVector collection"""
        print(f"Setting up collection: {self.collection_name}")
        
        try:
            # Check if collection exists
            if self.weaviate_client.collections.exists(self.collection_name):
                print(f"Collection {self.collection_name} already exists")
                # Check if it has data
                collection = self.weaviate_client.collections.get(self.collection_name)
                total_objects = collection.aggregate.over_all(total_count=True).total_count
                print(f"Current objects in PdfVector collection: {total_objects}")
                
                if total_objects > 0:
                    print("Collection has data, will add new PDF pages to existing collection")
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
                        Property(name="page_number", data_type=DataType.INT),
                        Property(name="pdf_filename", data_type=DataType.TEXT),
                    ]
                )
                print(f"✅ Collection {self.collection_name} created successfully")
            
        except Exception as e:
            print(f"❌ Error setting up collection: {e}")
            raise
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep French accents and common punctuation
        text = re.sub(r'[^\w\s\-.,;:!?()[\]{}"\'/àâäéèêëïîôöùûüÿç]', ' ', text)
        
        # Normalize spacing
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_pdf_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from each page of a PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of page dictionaries
        """
        pages = []
        pdf_filename = Path(pdf_path).name
        
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}")
            return []
        
        try:
            print(f"Processing PDF: {pdf_filename}")
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text from page
                text = page.get_text()
                
                if text and text.strip():
                    # Clean the text
                    cleaned_text = self.clean_text(text)
                    
                    if cleaned_text and len(cleaned_text) > 20:  # Skip very short texts
                        page_data = {
                            "content": cleaned_text,
                            "title": f"{pdf_filename} - Page {page_num + 1}",
                            "section": f"Page {page_num + 1}",
                            "url": f"file://{pdf_path}#page={page_num + 1}",
                            "page_number": page_num + 1,
                            "pdf_filename": pdf_filename
                        }
                        pages.append(page_data)
                else:
                    print(f"⚠️ Page {page_num + 1} has no extractable text")
            
            doc.close()
            print(f"✅ Extracted {len(pages)} pages from {pdf_filename}")
            return pages
            
        except Exception as e:
            print(f"❌ Error processing PDF {pdf_filename}: {e}")
            return []
    
    def check_existing_pages(self, pdf_filename: str) -> List[int]:
        """
        Check which pages from a PDF are already in the collection
        
        Args:
            pdf_filename: Name of the PDF file
            
        Returns:
            List of existing page numbers
        """
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            # Query for existing pages from this PDF
            response = collection.query.fetch_objects(
                where={
                    "path": ["pdf_filename"],
                    "operator": "Equal",
                    "valueText": pdf_filename
                },
                limit=1000  # Assume no PDF has more than 1000 pages
            )
            
            existing_pages = [obj.properties.get("page_number", 0) for obj in response.objects]
            return existing_pages
            
        except Exception as e:
            print(f"⚠️ Error checking existing pages: {e}")
            return []
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate GME embeddings for texts"""
        print("Generating GME embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    
    def store_pages(self, pages: List[Dict[str, Any]]):
        """
        Store PDF pages with their embeddings in Weaviate
        
        Args:
            pages: List of page dictionaries
        """
        if not pages:
            print("No pages to store")
            return
        
        print(f"Storing {len(pages)} PDF pages in Weaviate...")
        
        try:
            # Get the collection
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            # Prepare texts for embedding
            texts = [page["content"] for page in pages]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            
            # Prepare data for batch insert
            objects = []
            for i, page in enumerate(pages):
                obj = {
                    "properties": {
                        "content": page["content"],
                        "url": page["url"],
                        "title": page["title"],
                        "section": page["section"],
                        "page_number": page["page_number"],
                        "pdf_filename": page["pdf_filename"]
                    },
                    "vector": embeddings[i]
                }
                objects.append(obj)
            
            # Batch insert
            print("Inserting PDF pages into Weaviate...")
            with collection.batch.dynamic() as batch:
                for obj in tqdm(objects, desc="Inserting pages"):
                    batch.add_object(
                        properties=obj["properties"],
                        vector=obj["vector"]
                    )
            
            print(f"✅ Successfully stored {len(pages)} PDF pages in collection {self.collection_name}")
            
            # Verify insertion
            total_objects = collection.aggregate.over_all(total_count=True).total_count
            print(f"📊 Total objects in PdfVector collection: {total_objects}")
            
        except Exception as e:
            print(f"❌ Error storing pages: {e}")
            raise
    
    def process_all_pdfs(self):
        """Process all PDF files"""
        all_pages = []
        
        for pdf_path in self.pdf_files:
            pdf_filename = Path(pdf_path).name
            print(f"\n📄 Processing: {pdf_filename}")
            
            # Check existing pages
            existing_pages = self.check_existing_pages(pdf_filename)
            if existing_pages:
                print(f"Found {len(existing_pages)} existing pages for {pdf_filename}")
            
            # Extract pages from PDF
            pages = self.extract_pdf_pages(pdf_path)
            
            # Filter out already existing pages
            new_pages = []
            for page in pages:
                if page["page_number"] not in existing_pages:
                    new_pages.append(page)
                else:
                    print(f"Skipping existing page {page['page_number']}")
            
            if new_pages:
                print(f"Found {len(new_pages)} new pages to process")
                all_pages.extend(new_pages)
            else:
                print(f"All pages from {pdf_filename} already exist in collection")
        
        return all_pages
    
    def test_search(self, query: str, limit: int = 3):
        """Test search functionality on PdfVector collection"""
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
            
            print(f"\n🔍 PDF Search results for: '{query}'")
            print("-" * 50)
            
            for i, obj in enumerate(response.objects, 1):
                print(f"\n{i}. Distance: {obj.metadata.distance:.4f}")
                print(f"   PDF: {obj.properties['pdf_filename']}")
                print(f"   Page: {obj.properties['page_number']}")
                print(f"   Title: {obj.properties['title']}")
                print(f"   Content: {obj.properties['content'][:200]}...")
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
    
    def run_pipeline(self):
        """Run the complete PDF processing pipeline"""
        print("🚀 Starting PDF to PdfVector Pipeline...")
        
        # Process all PDFs
        pages = self.process_all_pdfs()
        
        if not pages:
            print("✅ No new PDF pages to process")
        else:
            # Store pages as vectors
            self.store_pages(pages)
        
        # Test search functionality
        test_queries = [
            "horaires",
            "billets",
            "visite",
            "château",
            "jardins"
        ]
        
        print("\n" + "="*60)
        print("TESTING PDF SEARCH FUNCTIONALITY")
        print("="*60)
        
        for query in test_queries:
            self.test_search(query, limit=2)
            print("\n" + "="*40)
        
        print("✅ PDF Pipeline completed successfully!")
        return True
    
    def close(self):
        """Close the Weaviate client"""
        if self.weaviate_client:
            self.weaviate_client.close()

def main():
    """Main function"""
    processor = PDFVectorProcessor()
    
    print("=== PDF to PdfVector Pipeline ===")
    print("Processing PDF files:")
    for pdf_path in processor.pdf_files:
        print(f"  - {Path(pdf_path).name}")
    print()
    
    try:
        success = processor.run_pipeline()
        
        if success:
            print("\n🎉 PDF processing completed successfully!")
            print("📊 PdfVector collection is ready for RAG queries")
        else:
            print("\n❌ PDF processing failed")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        processor.close()

if __name__ == "__main__":
    main()
