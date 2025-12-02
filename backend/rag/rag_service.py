"""
RAG (Retrieval-Augmented Generation) Service for Plant Information
Uses Pinecone for vector storage and Amazon Bedrock (Cohere) embeddings for semantic search
"""

import json
import os
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import hashlib
import re
import unicodedata

logger = logging.getLogger(__name__)

# Try to import Pinecone
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("Pinecone not available. Install with: pip install pinecone-client")

# Try to import boto3 for Amazon Bedrock
try:
    import boto3
    import botocore.exceptions
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    logger.warning("boto3 not available. Install with: pip install boto3")


class RAGService:
    """RAG service for retrieving plant information using vector search"""

    def __init__(self, json_file_path: Optional[str] = None):
        """Initialize RAG service with Pinecone and Amazon Bedrock (Cohere)"""
        self.pinecone_client = None
        self.index = None
        self.embedding_model = None
        self.index_name = "plant-knowledge-base-bedrock"
        self.dimension = 1024  # Cohere embed-english-v3.0 dimension

        # Local cache for plant data (keyed by scientific_name)
        self.plant_cache: Dict[str, Dict] = {}

        # Local cache for animal data (keyed by scientific_name)
        self.animal_cache: Dict[str, Dict] = {}

        self.json_file_path = json_file_path

        # Load plant data into cache if JSON file path provided
        if json_file_path and os.path.exists(json_file_path):
            self._load_plant_cache(json_file_path)

        # Initialize Amazon Bedrock and Pinecone
        self._initialize_bedrock()
        self._initialize_pinecone()

    @classmethod
    def for_animals(cls, json_file_path: Optional[str] = None):
        """Create RAG service instance configured for animals"""
        instance = cls.__new__(cls)
        instance.pinecone_client = None
        instance.index = None
        instance.embedding_model = None
        instance.index_name = "animal-knowledge-base-bedrock"
        instance.dimension = 1024
        instance.plant_cache = {}
        instance.animal_cache = {}
        instance.json_file_path = json_file_path

        # Load animal data into cache if JSON file path provided
        if json_file_path and os.path.exists(json_file_path):
            instance._load_animal_cache(json_file_path)

        # Initialize Amazon Bedrock and Pinecone
        instance._initialize_bedrock()
        instance._initialize_pinecone()

        return instance

    def _initialize_bedrock(self):
        """Initialize Amazon Bedrock (Cohere) client for embeddings"""
        if BEDROCK_AVAILABLE:
            aws_region = os.getenv("AWS_REGION", "us-west-2")
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if aws_access_key_id and aws_secret_access_key:
                try:
                    self.bedrock_runtime = boto3.client(
                        'bedrock-runtime',
                        region_name=aws_region,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                    )
                    self.embedding_model = "cohere.embed-english-v3"
                    self.aws_region = aws_region
                    logger.info(f"Amazon Bedrock (Cohere) client initialized for embeddings in region {aws_region}")
                except Exception as e:
                    logger.error(f"Failed to initialize Bedrock client: {e}")
                    self.bedrock_runtime = None
            else:
                logger.warning("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY not found. Embeddings will not be available.")
                self.bedrock_runtime = None
        else:
            self.bedrock_runtime = None

    def _initialize_pinecone(self):
        """Initialize Pinecone client and connect to index"""
        if PINECONE_AVAILABLE:
            pinecone_api_key = os.getenv("PINECONE_API_KEY")
            if pinecone_api_key:
                try:
                    self.pinecone_client = Pinecone(api_key=pinecone_api_key)
                    self._initialize_index()
                    logger.info("Pinecone client initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Pinecone: {e}")
                    self.pinecone_client = None
            else:
                logger.warning("PINECONE_API_KEY not found. Pinecone will not be available.")
        else:
            logger.warning("Pinecone library not installed. RAG will not be available.")

    def _initialize_index(self):
        """Initialize or connect to Pinecone index"""
        if not self.pinecone_client:
            return

        try:
            # Check if index exists
            existing_indexes = [idx.name for idx in self.pinecone_client.list_indexes()]

            if self.index_name not in existing_indexes:
                # Create new index
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"Index {self.index_name} created successfully")

            # Connect to index
            self.index = self.pinecone_client.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")

        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {e}")
            self.index = None

    def _load_plant_cache(self, json_file_path: str):
        """Load plant data into local cache for quick retrieval"""
        try:
            logger.info(f"Loading plant data into cache from {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                plants = json.load(f)

            for plant in plants:
                if plant.get("error"):
                    continue
                scientific_name = plant.get("scientific_name", "")
                if scientific_name:
                    self.plant_cache[scientific_name.lower()] = plant

            logger.info(f"Loaded {len(self.plant_cache)} plants into cache")
        except Exception as e:
            logger.error(f"Error loading plant cache: {e}")

    def _load_animal_cache(self, json_file_path: str):
        """Load animal data into local cache for quick retrieval"""
        try:
            logger.info(f"Loading animal data into cache from {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                animals = json.load(f)

            for animal in animals:
                if animal.get("error"):
                    continue
                scientific_name = animal.get("scientific_name", "")
                if scientific_name:
                    self.animal_cache[scientific_name.lower()] = animal

            logger.info(f"Loaded {len(self.animal_cache)} animals into cache")
        except Exception as e:
            logger.error(f"Error loading animal cache: {e}")

    def _generate_embedding(self, text: str, input_type: str = "search_query") -> Optional[List[float]]:
        """
        Generate embedding for text using Amazon Bedrock (Cohere)

        Args:
            text: Text to generate embedding for
            input_type: "search_query" for queries, "search_document" for documents being indexed
        """
        if not self.bedrock_runtime or not text:
            return None

        # Log text preview (first 100 chars) for debugging
        text_preview = text[:100] + "..." if len(text) > 100 else text
        logger.info(f"Generating embedding for {input_type}: {text_preview}")

        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=self.embedding_model,
                body=json.dumps({
                    'texts': [text],  # Cohere requires array format
                    'input_type': input_type
                }),
                contentType='application/json',
                accept='application/json'
            )

            response_body = json.loads(response['body'].read())
            embeddings = response_body.get('embeddings', [])

            if embeddings:
                embedding = embeddings[0]
                logger.info(f"Received embedding: dimension={len(embedding)}, input_type={input_type}")
                return embedding
            logger.warning("Received empty embeddings from Bedrock")
            return None

        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ThrottlingException':
                logger.warning("Bedrock rate limit hit, consider adding retry logic")
            elif error_code == 'ValidationException':
                logger.error(f"Invalid input to Bedrock: {e}")
            else:
                logger.error(f"Bedrock client error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating Bedrock embedding: {e}")
            return None

    def _sanitize_plant_id(self, scientific_name: str) -> str:
        """
        Sanitize plant ID to be ASCII-only for Pinecone compatibility.
        Replaces non-ASCII characters with ASCII equivalents or removes them.
        """
        if not scientific_name:
            return "unknown"

        # Convert to lowercase
        plant_id = scientific_name.lower()

        # Replace common non-ASCII characters with ASCII equivalents
        replacements = {
            '×': 'x',  # Multiplication sign → x
            '×': 'x',  # Different multiplication sign
            'é': 'e',
            'è': 'e',
            'ê': 'e',
            'ë': 'e',
            'à': 'a',
            'á': 'a',
            'â': 'a',
            'ä': 'a',
            'ù': 'u',
            'ú': 'u',
            'û': 'u',
            'ü': 'u',
            'ö': 'o',
            'ó': 'o',
            'ò': 'o',
            'ô': 'o',
            'ç': 'c',
            'ñ': 'n',
            'ß': 'ss',
        }

        for non_ascii, ascii_char in replacements.items():
            plant_id = plant_id.replace(non_ascii, ascii_char)

        # Normalize unicode characters (e.g., convert é to e)
        plant_id = unicodedata.normalize('NFKD', plant_id)

        # Remove any remaining non-ASCII characters
        plant_id = plant_id.encode('ascii', 'ignore').decode('ascii')

        # Replace spaces and other special chars with underscores
        plant_id = re.sub(r'[^a-z0-9_]', '_', plant_id)

        # Remove multiple consecutive underscores
        plant_id = re.sub(r'_+', '_', plant_id)

        # Remove leading/trailing underscores
        plant_id = plant_id.strip('_')

        # Ensure it's not empty
        if not plant_id:
            plant_id = "unknown"

        return plant_id

    def _sanitize_animal_id(self, scientific_name: str) -> str:
        """
        Sanitize animal ID to be ASCII-only for Pinecone compatibility.
        Replaces non-ASCII characters with ASCII equivalents or removes them.
        """
        # Reuse the same sanitization logic as plants
        return self._sanitize_plant_id(scientific_name)

    def _chunk_plant_data(self, plant: Dict) -> List[Dict]:
        """Chunk plant data into smaller pieces for better retrieval"""
        chunks = []

        # Create a comprehensive text representation of the plant
        # Sanitize plant ID to be ASCII-only for Pinecone compatibility
        plant_id = self._sanitize_plant_id(plant.get("scientific_name", ""))

        # Chunk 1: Basic information
        basic_info = f"""
        Scientific Name: {plant.get('scientific_name', 'Unknown')}
        Common Name: {plant.get('common_name', 'Unknown')}
        Family: {plant.get('family', 'Unknown')}
        Genus: {plant.get('genus', 'Unknown')}
        Summary: {plant.get('summary', '')}
        """
        chunks.append({
            "id": f"{plant_id}_basic",
            "text": basic_info.strip(),
            "metadata": {
                "scientific_name": plant.get("scientific_name", ""),
                "common_name": plant.get("common_name", ""),
                "family": plant.get("family", ""),
                "type": "basic_info"
            }
        })

        # Chunk 2: Detailed content (split if too long)
        content = plant.get("content", "")
        if content:
            # Split content into chunks of ~1000 characters
            max_chunk_size = 1000
            content_chunks = []
            words = content.split()
            current_chunk = []
            current_length = 0

            for word in words:
                word_length = len(word) + 1  # +1 for space
                if current_length + word_length > max_chunk_size and current_chunk:
                    content_chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_length = word_length
                else:
                    current_chunk.append(word)
                    current_length += word_length

            if current_chunk:
                content_chunks.append(" ".join(current_chunk))

            # If content is short, use as single chunk
            if len(content_chunks) == 0:
                content_chunks = [content]

            for i, chunk_text in enumerate(content_chunks):
                chunks.append({
                    "id": f"{plant_id}_content_{i}",
                    "text": chunk_text,
                    "metadata": {
                        "scientific_name": plant.get("scientific_name", ""),
                        "common_name": plant.get("common_name", ""),
                        "type": "detailed_content",
                        "chunk_index": i
                    }
                })

        return chunks

    def _chunk_animal_data(self, animal: Dict) -> List[Dict]:
        """Chunk animal data into smaller pieces for better retrieval"""
        chunks = []

        # Create a comprehensive text representation of the animal
        # Sanitize animal ID to be ASCII-only for Pinecone compatibility
        animal_id = self._sanitize_animal_id(animal.get("scientific_name", ""))

        # Chunk 1: Basic information
        basic_info = f"""
        Scientific Name: {animal.get('scientific_name', 'Unknown')}
        Common Name: {animal.get('common_name', 'Unknown')}
        Family: {animal.get('family', 'Unknown')}
        Genus: {animal.get('genus', 'Unknown')}
        Order: {animal.get('order', 'Unknown')}
        Class: {animal.get('class', 'Unknown')}
        Phylum: {animal.get('phylum', 'Unknown')}
        Kingdom: {animal.get('kingdom', 'Unknown')}
        Summary: {animal.get('summary', '')}
        """
        chunks.append({
            "id": f"{animal_id}_basic",
            "text": basic_info.strip(),
            "metadata": {
                "scientific_name": animal.get("scientific_name", ""),
                "common_name": animal.get("common_name", ""),
                "family": animal.get("family", ""),
                "genus": animal.get("genus", ""),
                "order": animal.get("order", ""),
                "class": animal.get("class", ""),
                "phylum": animal.get("phylum", ""),
                "type": "basic_info"
            }
        })

        # Chunk 2: Detailed content (split if too long)
        content = animal.get("content", "")
        if content:
            # Split content into chunks of ~1000 characters
            max_chunk_size = 1000
            content_chunks = []
            words = content.split()
            current_chunk = []
            current_length = 0

            for word in words:
                word_length = len(word) + 1  # +1 for space
                if current_length + word_length > max_chunk_size and current_chunk:
                    content_chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_length = word_length
                else:
                    current_chunk.append(word)
                    current_length += word_length

            if current_chunk:
                content_chunks.append(" ".join(current_chunk))

            # If content is short, use as single chunk
            if len(content_chunks) == 0:
                content_chunks = [content]

            for i, chunk_text in enumerate(content_chunks):
                chunks.append({
                    "id": f"{animal_id}_content_{i}",
                    "text": chunk_text,
                    "metadata": {
                        "scientific_name": animal.get("scientific_name", ""),
                        "common_name": animal.get("common_name", ""),
                        "type": "detailed_content",
                        "chunk_index": i
                    }
                })

        return chunks

    def load_and_index_plants(self, json_file_path: str, batch_size: int = 100) -> bool:
        """Load plant data from JSON and index in Pinecone"""
        if not self.index or not self.bedrock_runtime:
            logger.error("Pinecone index or Bedrock client not available")
            return False

        try:
            logger.info(f"Loading plant data from {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                plants = json.load(f)

            # Also load into cache
            self._load_plant_cache(json_file_path)

            logger.info(f"Loaded {len(plants)} plants. Starting indexing...")

            # Process plants in batches
            vectors_to_upsert = []
            total_indexed = 0

            for plant_idx, plant in enumerate(plants):
                # Skip plants with errors
                if plant.get("error"):
                    continue

                # Chunk the plant data
                chunks = self._chunk_plant_data(plant)

                for chunk in chunks:
                    # Generate embedding using "search_document" input type for indexing
                    embedding = self._generate_embedding(chunk["text"], input_type="search_document")
                    if not embedding:
                        continue

                    # Create vector for Pinecone
                    vector_id = chunk["id"]
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": chunk["metadata"]
                    })

                    # Upsert in batches
                    if len(vectors_to_upsert) >= batch_size:
                        self.index.upsert(vectors=vectors_to_upsert)
                        total_indexed += len(vectors_to_upsert)
                        logger.info(f"Indexed {total_indexed} chunks...")
                        vectors_to_upsert = []

                if (plant_idx + 1) % 100 == 0:
                    logger.info(f"Processed {plant_idx + 1}/{len(plants)} plants...")

            # Upsert remaining vectors
            if vectors_to_upsert:
                self.index.upsert(vectors=vectors_to_upsert)
                total_indexed += len(vectors_to_upsert)

            logger.info(f"Successfully indexed {total_indexed} chunks from {len(plants)} plants")
            return True

        except Exception as e:
            logger.error(f"Error loading and indexing plants: {e}")
            return False

    def load_and_index_animals(self, json_file_path: str, batch_size: int = 100) -> bool:
        """Load animal data from JSON and index in Pinecone"""
        if not self.index or not self.bedrock_runtime:
            logger.error("Pinecone index or Bedrock client not available")
            return False

        try:
            logger.info(f"Loading animal data from {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                animals = json.load(f)

            # Also load into cache
            self._load_animal_cache(json_file_path)

            logger.info(f"Loaded {len(animals)} animals. Starting indexing...")

            # Process animals in batches
            vectors_to_upsert = []
            total_indexed = 0

            for animal_idx, animal in enumerate(animals):
                # Skip animals with errors
                if animal.get("error"):
                    continue

                # Chunk the animal data
                chunks = self._chunk_animal_data(animal)

                for chunk in chunks:
                    # Generate embedding using "search_document" input type for indexing
                    embedding = self._generate_embedding(chunk["text"], input_type="search_document")
                    if not embedding:
                        continue

                    # Create vector for Pinecone
                    vector_id = chunk["id"]
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": chunk["metadata"]
                    })

                    # Upsert in batches
                    if len(vectors_to_upsert) >= batch_size:
                        self.index.upsert(vectors=vectors_to_upsert)
                        total_indexed += len(vectors_to_upsert)
                        logger.info(f"Indexed {total_indexed} chunks...")
                        vectors_to_upsert = []

                if (animal_idx + 1) % 100 == 0:
                    logger.info(f"Processed {animal_idx + 1}/{len(animals)} animals...")

            # Upsert remaining vectors
            if vectors_to_upsert:
                self.index.upsert(vectors=vectors_to_upsert)
                total_indexed += len(vectors_to_upsert)

            logger.info(f"Successfully indexed {total_indexed} chunks from {len(animals)} animals")
            return True

        except Exception as e:
            logger.error(f"Error loading and indexing animals: {e}")
            return False

    def search_plants(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant plant information based on query"""
        if not self.index or not self.bedrock_runtime:
            logger.warning("RAG not available. Returning empty results.")
            return []

        try:
            # Generate embedding for query using "search_query" input type
            query_embedding = self._generate_embedding(query, input_type="search_query")
            if not query_embedding:
                return []

            # Search in Pinecone
            logger.info(f"Querying Pinecone index '{self.index_name}' with query: '{query[:100]}...'")
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )

            logger.info(f"Pinecone query returned {len(results.matches)} matches")

            # Format results
            plant_info = []
            seen_plants = set()

            for match in results.matches:
                metadata = match.metadata
                scientific_name = metadata.get("scientific_name", "")

                # Avoid duplicates - prefer detailed content over basic info
                if scientific_name in seen_plants:
                    continue

                plant_info.append({
                    "scientific_name": scientific_name,
                    "common_name": metadata.get("common_name", ""),
                    "family": metadata.get("family", ""),
                    "text": metadata.get("text", ""),  # This might not be in metadata
                    "score": match.score,
                    "metadata": metadata
                })
                seen_plants.add(scientific_name)
                logger.info(f"Found match: {scientific_name} ({metadata.get('common_name', '')}) - Score: {match.score:.4f}")

            logger.info(f"Returning {len(plant_info)} unique plants from Pinecone")
            return plant_info

        except Exception as e:
            logger.error(f"Error searching plants: {e}")
            return []

    def search_animals(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant animal information based on query"""
        if not self.index or not self.bedrock_runtime:
            logger.warning("RAG not available. Returning empty results.")
            return []

        try:
            # Generate embedding for query using "search_query" input type
            query_embedding = self._generate_embedding(query, input_type="search_query")
            if not query_embedding:
                return []

            # Search in Pinecone
            logger.info(f"Querying Pinecone index '{self.index_name}' with query: '{query[:100]}...'")
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )

            logger.info(f"Pinecone query returned {len(results.matches)} matches")

            # Format results
            animal_info = []
            seen_animals = set()

            for match in results.matches:
                metadata = match.metadata
                scientific_name = metadata.get("scientific_name", "")

                # Avoid duplicates - prefer detailed content over basic info
                if scientific_name in seen_animals:
                    continue

                animal_info.append({
                    "scientific_name": scientific_name,
                    "common_name": metadata.get("common_name", ""),
                    "family": metadata.get("family", ""),
                    "genus": metadata.get("genus", ""),
                    "order": metadata.get("order", ""),
                    "class": metadata.get("class", ""),
                    "phylum": metadata.get("phylum", ""),
                    "text": metadata.get("text", ""),  # This might not be in metadata
                    "score": match.score,
                    "metadata": metadata
                })
                seen_animals.add(scientific_name)
                logger.info(f"Found match: {scientific_name} ({metadata.get('common_name', '')}) - Score: {match.score:.4f}")

            logger.info(f"Returning {len(animal_info)} unique animals from Pinecone")
            return animal_info

        except Exception as e:
            logger.error(f"Error searching animals: {e}")
            return []

    def get_rag_context(self, query: str, top_k: int = 3) -> str:
        """Get formatted RAG context for AI prompt with full plant information"""
        results = self.search_plants(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        context_parts.append("Relevant Plant Information:")

        for i, result in enumerate(results, 1):
            scientific_name = result['scientific_name']
            common_name = result.get('common_name', '')

            # Retrieve full plant data from cache
            plant_data = self.plant_cache.get(scientific_name.lower())

            if plant_data:
                context_parts.append(f"\n--- Plant {i}: {scientific_name} ({common_name}) ---")

                # Add taxonomy
                if plant_data.get('family'):
                    context_parts.append(f"Family: {plant_data['family']}")
                if plant_data.get('genus'):
                    context_parts.append(f"Genus: {plant_data['genus']}")

                # Add summary
                if plant_data.get('summary'):
                    context_parts.append(f"Summary: {plant_data['summary']}")

                # Add detailed content (truncate if too long)
                if plant_data.get('content'):
                    content = plant_data['content']
                    # Limit content to ~2000 characters to avoid token limits
                    if len(content) > 2000:
                        content = content[:2000] + "... [truncated]"
                    context_parts.append(f"Details: {content}")

                # Add Wikipedia URL if available
                if plant_data.get('wikipedia_url'):
                    context_parts.append(f"Source: {plant_data['wikipedia_url']}")
            else:
                # Fallback if plant not in cache
                context_parts.append(f"\n--- Plant {i}: {scientific_name} ({common_name}) ---")
                if result.get('family'):
                    context_parts.append(f"Family: {result['family']}")

        context_parts.append("\n=== END OF PLANT INFORMATION ===\n")
        return "\n".join(context_parts)

    def get_rag_context_animals(self, query: str, top_k: int = 3) -> str:
        """Get formatted RAG context for AI prompt with full animal information"""
        results = self.search_animals(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        context_parts.append("Relevant Animal Information:")

        for i, result in enumerate(results, 1):
            scientific_name = result['scientific_name']
            common_name = result.get('common_name', '')

            # Retrieve full animal data from cache
            animal_data = self.animal_cache.get(scientific_name.lower())

            if animal_data:
                context_parts.append(f"\n--- Animal {i}: {scientific_name} ({common_name}) ---")

                # Add taxonomy
                if animal_data.get('family'):
                    context_parts.append(f"Family: {animal_data['family']}")
                if animal_data.get('genus'):
                    context_parts.append(f"Genus: {animal_data['genus']}")
                if animal_data.get('order'):
                    context_parts.append(f"Order: {animal_data['order']}")
                if animal_data.get('class'):
                    context_parts.append(f"Class: {animal_data['class']}")
                if animal_data.get('phylum'):
                    context_parts.append(f"Phylum: {animal_data['phylum']}")

                # Add summary
                if animal_data.get('summary'):
                    context_parts.append(f"Summary: {animal_data['summary']}")

                # Add detailed content (truncate if too long)
                if animal_data.get('content'):
                    content = animal_data['content']
                    # Limit content to ~2000 characters to avoid token limits
                    if len(content) > 2000:
                        content = content[:2000] + "... [truncated]"
                    context_parts.append(f"Details: {content}")

                # Add Wikipedia URL if available
                if animal_data.get('wikipedia_url'):
                    context_parts.append(f"Source: {animal_data['wikipedia_url']}")
            else:
                # Fallback if animal not in cache
                context_parts.append(f"\n--- Animal {i}: {scientific_name} ({common_name}) ---")
                if result.get('family'):
                    context_parts.append(f"Family: {result['family']}")

        context_parts.append("\n=== END OF ANIMAL INFORMATION ===\n")
        return "\n".join(context_parts)

    def is_available(self) -> bool:
        """Check if RAG service is fully available"""
        return self.index is not None and self.bedrock_runtime is not None

