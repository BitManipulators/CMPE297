"""
Script to index plant data into Pinecone vector database
Run this script once to populate the Pinecone index with plant embeddings
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add rag directory to path
script_dir = Path(__file__).parent
rag_dir = script_dir / "rag"
sys.path.insert(0, str(rag_dir))

from rag_service import RAGService

def main():
    """Main function to index plants"""
    logger.info("Starting plant indexing script...")

    # Check for required environment variables
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        logger.error("AWS_ACCESS_KEY_ID not found in environment variables")
        logger.error("Please set AWS_ACCESS_KEY_ID in your .env file or environment")
        return False

    if not os.getenv("AWS_SECRET_ACCESS_KEY"):
        logger.error("AWS_SECRET_ACCESS_KEY not found in environment variables")
        logger.error("Please set AWS_SECRET_ACCESS_KEY in your .env file or environment")
        return False

    if not os.getenv("PINECONE_API_KEY"):
        logger.error("PINECONE_API_KEY not found in environment variables")
        logger.error("Please set PINECONE_API_KEY in your .env file or environment")
        return False

    # Initialize RAG service
    json_file_path = script_dir / "rag" / "all_plants_streaming.json"

    if not json_file_path.exists():
        logger.error(f"Plant data file not found: {json_file_path}")
        return False

    logger.info(f"Initializing RAG service...")
    rag_service = RAGService(json_file_path=str(json_file_path))

    if not rag_service.is_available():
        logger.error("RAG service is not available. Please check your API keys.")
        return False

    logger.info("RAG service initialized successfully")
    logger.info(f"Index name: {rag_service.index_name}")
    logger.info(f"Starting to index plants from: {json_file_path}")

    # Index plants
    success = rag_service.load_and_index_plants(str(json_file_path), batch_size=100)

    if success:
        logger.info("=" * 60)
        logger.info("SUCCESS: Plants indexed successfully!")
        logger.info(f"Total plants cached: {len(rag_service.plant_cache)}")
        logger.info("=" * 60)
        return True
    else:
        logger.error("FAILED: Error indexing plants. Check logs above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

