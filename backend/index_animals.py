"""
Script to index animal data into Pinecone vector database
Run this script once to populate the Pinecone index with animal embeddings
Checks if plant index exists and skips plant indexing, only indexes animals
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

def check_plant_index_exists(pinecone_client) -> bool:
    """Check if plant-knowledge-base-bedrock index already exists in Pinecone"""
    if not pinecone_client:
        return False

    try:
        existing_indexes = [idx.name for idx in pinecone_client.list_indexes()]
        plant_index_name = "plant-knowledge-base-bedrock"
        exists = plant_index_name in existing_indexes
        if exists:
            logger.info(f"Plant index '{plant_index_name}' already exists in Pinecone. Skipping plant indexing.")
        else:
            logger.info(f"Plant index '{plant_index_name}' not found. This script will only index animals.")
        return exists
    except Exception as e:
        logger.warning(f"Error checking for plant index: {e}")
        return False

def main():
    """Main function to index animals"""
    logger.info("Starting animal indexing script...")

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

    # Check if plant index exists
    try:
        from pinecone import Pinecone
        pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        plant_index_exists = check_plant_index_exists(pinecone_client)
        if plant_index_exists:
            logger.info("Plant index found. Proceeding with animal indexing only.")
    except Exception as e:
        logger.warning(f"Could not check for plant index: {e}. Proceeding with animal indexing.")

    # Initialize RAG service for animals
    json_file_path = script_dir / "rag" / "animalia_wikipedia_content.json"

    if not json_file_path.exists():
        logger.error(f"Animal data file not found: {json_file_path}")
        return False

    logger.info(f"Initializing RAG service for animals...")
    # Create RAG service with animal index name
    rag_service = RAGService.for_animals(json_file_path=str(json_file_path))

    if not rag_service.is_available():
        logger.error("RAG service is not available. Please check your API keys.")
        return False

    logger.info("RAG service initialized successfully")
    logger.info(f"Index name: {rag_service.index_name}")
    logger.info(f"Starting to index animals from: {json_file_path}")

    # Index animals
    success = rag_service.load_and_index_animals(str(json_file_path), batch_size=100)

    if success:
        logger.info("=" * 60)
        logger.info("SUCCESS: Animals indexed successfully!")
        logger.info(f"Total animals cached: {len(rag_service.animal_cache)}")
        logger.info("=" * 60)
        return True
    else:
        logger.error("FAILED: Error indexing animals. Check logs above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
