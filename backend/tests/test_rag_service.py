"""
Unit tests for RAG Service (rag_service.py)
Tests cover Pinecone, AWS Bedrock, embedding generation, plant indexing, and search
"""
import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import botocore.exceptions

# Add rag directory to path
backend_dir = Path(__file__).parent.parent
rag_dir = backend_dir / "rag"
sys.path.insert(0, str(rag_dir))

from rag_service import RAGService


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
class TestRAGServiceInitialization:
    """Test RAG service initialization scenarios"""
    
    def test_init_without_credentials(self, mocker):
        """Test initialization without AWS/Pinecone credentials"""
        mocker.patch.dict('os.environ', {}, clear=True)
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        
        assert service.bedrock_runtime is None
        assert service.pinecone_client is None
        assert not service.is_available()
    
    def test_init_with_aws_credentials(self, mocker, mock_bedrock):
        """Test initialization with AWS credentials"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'AWS_REGION': 'us-west-2'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        
        assert service.bedrock_runtime is not None
        assert service.embedding_model == "cohere.embed-english-v3"
    
    def test_init_with_pinecone_credentials(self, mocker, mock_pinecone):
        """Test initialization with Pinecone credentials"""
        mocker.patch.dict('os.environ', {
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", False)
        
        service = RAGService()
        
        assert service.pinecone_client is not None
        assert service.index is not None
    
    def test_init_with_json_file(self, mocker, sample_plant_json, mock_bedrock, mock_pinecone):
        """Test initialization with plant data JSON file"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService(json_file_path=sample_plant_json)
        
        assert len(service.plant_cache) > 0
        assert "taraxacum officinale" in service.plant_cache
    
    def test_init_with_nonexistent_json_file(self, mocker, mock_bedrock, mock_pinecone):
        """Test initialization with nonexistent JSON file"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService(json_file_path="/nonexistent/path.json")
        
        assert len(service.plant_cache) == 0


# ============================================================================
# Plant ID Sanitization Tests
# ============================================================================

@pytest.mark.unit
class TestPlantIDSanitization:
    """Test ASCII sanitization for plant IDs"""
    
    def test_sanitize_basic_name(self, mocker, mock_bedrock, mock_pinecone):
        """Test sanitization of basic plant name"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service._sanitize_plant_id("Taraxacum officinale")
        
        assert result == "taraxacum_officinale"
        assert result.isascii()
    
    def test_sanitize_name_with_multiplication_sign(self, mocker, mock_bedrock, mock_pinecone):
        """Test sanitization of plant name with × (multiplication sign)"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service._sanitize_plant_id("Mentha × piperita")
        
        assert result == "mentha_x_piperita"
        assert result.isascii()
        assert "×" not in result
    
    def test_sanitize_name_with_accents(self, mocker, mock_bedrock, mock_pinecone):
        """Test sanitization of plant name with accented characters"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service._sanitize_plant_id("Caféier arabica")
        
        assert result == "cafeier_arabica"
        assert result.isascii()
    
    def test_sanitize_empty_name(self, mocker, mock_bedrock, mock_pinecone):
        """Test sanitization of empty plant name"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service._sanitize_plant_id("")
        
        assert result == "unknown"
    
    def test_sanitize_name_with_special_chars(self, mocker, mock_bedrock, mock_pinecone):
        """Test sanitization with various special characters"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service._sanitize_plant_id("Plant's \"Name\" (variant)")
        
        assert result.isascii()
        assert '"' not in result
        assert '(' not in result
        assert ')' not in result


# ============================================================================
# Embedding Generation Tests
# ============================================================================

@pytest.mark.unit
class TestEmbeddingGeneration:
    """Test AWS Bedrock embedding generation"""
    
    def test_generate_embedding_success(self, mocker, mock_bedrock):
        """Test successful embedding generation"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        embedding = service._generate_embedding("test query", input_type="search_query")
        
        assert embedding is not None
        assert len(embedding) == 1024  # Cohere dimension
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_embedding_different_input_types(self, mocker, mock_bedrock):
        """Test embedding generation with different input types"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        
        # Test search_query type
        query_embedding = service._generate_embedding("query", input_type="search_query")
        assert query_embedding is not None
        
        # Test search_document type
        doc_embedding = service._generate_embedding("document", input_type="search_document")
        assert doc_embedding is not None
    
    def test_generate_embedding_empty_text(self, mocker, mock_bedrock):
        """Test embedding generation with empty text"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        embedding = service._generate_embedding("", input_type="search_query")
        
        assert embedding is None
    
    def test_generate_embedding_throttling_exception(self, mocker):
        """Test handling of Bedrock throttling exception"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Mock boto3 client with throttling error
        mock_client = Mock()
        error_response = {'Error': {'Code': 'ThrottlingException'}}
        mock_client.invoke_model.side_effect = botocore.exceptions.ClientError(
            error_response, 'invoke_model'
        )
        mocker.patch("boto3.client", return_value=mock_client)
        
        service = RAGService()
        embedding = service._generate_embedding("test", input_type="search_query")
        
        assert embedding is None
    
    def test_generate_embedding_without_bedrock(self, mocker):
        """Test embedding generation when Bedrock is not available"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", False)
        
        service = RAGService()
        embedding = service._generate_embedding("test", input_type="search_query")
        
        assert embedding is None


# ============================================================================
# Plant Data Chunking Tests
# ============================================================================

@pytest.mark.unit
class TestPlantDataChunking:
    """Test plant data chunking for indexing"""
    
    def test_chunk_plant_data_basic(self, mocker, sample_plant_data, mock_bedrock, mock_pinecone):
        """Test basic plant data chunking"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        chunks = service._chunk_plant_data(sample_plant_data)
        
        assert len(chunks) >= 1
        assert chunks[0]["id"].endswith("_basic")
        assert "scientific_name" in chunks[0]["metadata"]
        assert sample_plant_data["scientific_name"] in chunks[0]["text"]
    
    def test_chunk_plant_data_with_long_content(self, mocker, mock_bedrock, mock_pinecone):
        """Test chunking with long content (should split)"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        plant_data = {
            "scientific_name": "Test Plant",
            "common_name": "Test",
            "family": "Testaceae",
            "content": "word " * 1500  # Create very long content
        }
        
        service = RAGService()
        chunks = service._chunk_plant_data(plant_data)
        
        # Should have basic chunk + multiple content chunks
        assert len(chunks) > 1
        content_chunks = [c for c in chunks if "content" in c["id"]]
        assert len(content_chunks) > 0
    
    def test_chunk_plant_data_without_content(self, mocker, mock_bedrock, mock_pinecone):
        """Test chunking plant data without detailed content"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        plant_data = {
            "scientific_name": "Minimal Plant",
            "common_name": "Minimal",
            "family": "Minimalaceae"
        }
        
        service = RAGService()
        chunks = service._chunk_plant_data(plant_data)
        
        # Should only have basic chunk
        assert len(chunks) == 1
        assert chunks[0]["id"].endswith("_basic")


# ============================================================================
# Plant Indexing Tests
# ============================================================================

@pytest.mark.unit
class TestPlantIndexing:
    """Test plant data loading and indexing"""
    
    def test_load_and_index_plants_success(self, mocker, sample_plant_json, mock_bedrock, mock_pinecone):
        """Test successful plant indexing"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service.load_and_index_plants(sample_plant_json)
        
        assert result is True
        assert len(service.plant_cache) > 0
        assert mock_pinecone["index"].upsert.called
    
    def test_load_and_index_plants_without_pinecone(self, mocker, sample_plant_json, mock_bedrock):
        """Test indexing without Pinecone available"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        result = service.load_and_index_plants(sample_plant_json)
        
        assert result is False
    
    def test_load_and_index_plants_invalid_json(self, mocker, tmp_path, mock_bedrock, mock_pinecone):
        """Test indexing with invalid JSON file"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Create invalid JSON file
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("not valid json")
        
        service = RAGService()
        result = service.load_and_index_plants(str(invalid_json))
        
        assert result is False
    
    def test_load_and_index_plants_with_errors(self, mocker, tmp_path, mock_bedrock, mock_pinecone):
        """Test indexing plants with error entries"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Create JSON with error entry
        plants = [
            {"error": "Plant not found"},
            {"scientific_name": "Valid Plant", "common_name": "Valid", "family": "Validaceae"}
        ]
        json_file = tmp_path / "plants_with_errors.json"
        with open(json_file, 'w') as f:
            json.dump(plants, f)
        
        service = RAGService()
        result = service.load_and_index_plants(str(json_file))
        
        assert result is True
        # Only valid plant should be indexed
        assert len(service.plant_cache) == 1
    
    def test_load_and_index_plants_batch_processing(self, mocker, tmp_path, mock_bedrock, mock_pinecone):
        """Test batch processing during indexing"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Create multiple plants to test batching
        plants = [
            {
                "scientific_name": f"Plant {i}",
                "common_name": f"Common {i}",
                "family": "Testaceae",
                "content": "Short content"
            }
            for i in range(5)
        ]
        json_file = tmp_path / "multiple_plants.json"
        with open(json_file, 'w') as f:
            json.dump(plants, f)
        
        service = RAGService()
        result = service.load_and_index_plants(str(json_file), batch_size=2)
        
        assert result is True
        # Verify upsert was called multiple times for batching
        assert mock_pinecone["index"].upsert.call_count >= 1


# ============================================================================
# Plant Search Tests
# ============================================================================

@pytest.mark.unit
class TestPlantSearch:
    """Test plant search functionality"""
    
    def test_search_plants_success(self, mocker, sample_plant_data, mock_bedrock, mock_pinecone):
        """Test successful plant search"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Set up mock index with plant data
        mock_pinecone["index"]._vectors = {
            "taraxacum_officinale_basic": {
                "metadata": {
                    "scientific_name": "Taraxacum officinale",
                    "common_name": "Common Dandelion",
                    "family": "Asteraceae"
                }
            }
        }
        
        service = RAGService()
        results = service.search_plants("dandelion", top_k=5)
        
        assert len(results) > 0
        assert results[0]["scientific_name"] == "Taraxacum officinale"
        assert "score" in results[0]
    
    def test_search_plants_without_pinecone(self, mocker, mock_bedrock):
        """Test search without Pinecone available"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        results = service.search_plants("dandelion", top_k=5)
        
        assert results == []
    
    def test_search_plants_empty_query(self, mocker, mock_bedrock, mock_pinecone):
        """Test search with empty query"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        results = service.search_plants("", top_k=5)
        
        assert results == []
    
    def test_search_plants_deduplication(self, mocker, mock_bedrock, mock_pinecone):
        """Test that duplicate plants are filtered"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Mock index to return duplicate entries
        mock_pinecone["index"]._vectors = {
            "plant_basic": {"metadata": {"scientific_name": "Test Plant", "common_name": "Test"}},
            "plant_content_0": {"metadata": {"scientific_name": "Test Plant", "common_name": "Test"}},
            "plant_content_1": {"metadata": {"scientific_name": "Test Plant", "common_name": "Test"}}
        }
        
        service = RAGService()
        results = service.search_plants("test plant", top_k=5)
        
        # Should only return one result despite multiple chunks
        assert len(results) == 1


# ============================================================================
# RAG Context Generation Tests
# ============================================================================

@pytest.mark.unit
class TestRAGContext:
    """Test RAG context generation for AI prompts"""
    
    def test_get_rag_context_success(self, mocker, sample_plant_data, sample_plant_json, mock_bedrock, mock_pinecone):
        """Test successful RAG context generation"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService(json_file_path=sample_plant_json)
        
        # Mock search results
        mock_pinecone["index"]._vectors = {
            "taraxacum_officinale_basic": {
                "metadata": {
                    "scientific_name": "Taraxacum officinale",
                    "common_name": "Common Dandelion",
                    "family": "Asteraceae"
                }
            }
        }
        
        context = service.get_rag_context("dandelion", top_k=3)
        
        assert len(context) > 0
        assert "Relevant Plant Information" in context
        assert "Taraxacum officinale" in context
        assert "Common Dandelion" in context
    
    def test_get_rag_context_with_full_plant_data(self, mocker, sample_plant_data, sample_plant_json, mock_bedrock, mock_pinecone):
        """Test context includes full plant data from cache"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService(json_file_path=sample_plant_json)
        
        # Mock search results
        mock_pinecone["index"]._vectors = {
            "taraxacum_officinale_basic": {
                "metadata": {
                    "scientific_name": "Taraxacum officinale",
                    "common_name": "Common Dandelion"
                }
            }
        }
        
        context = service.get_rag_context("dandelion", top_k=1)
        
        # Should include summary, content, and other details from cache
        assert "Summary:" in context or "Details:" in context
        assert "Asteraceae" in context  # Family from cached data
    
    def test_get_rag_context_empty_results(self, mocker, mock_bedrock, mock_pinecone):
        """Test context generation with no search results"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        mock_pinecone["index"]._vectors = {}  # No results
        
        context = service.get_rag_context("nonexistent plant", top_k=3)
        
        assert context == ""
    
    def test_get_rag_context_content_truncation(self, mocker, tmp_path, mock_bedrock, mock_pinecone):
        """Test that very long content is truncated"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Create plant with very long content
        long_plant = {
            "scientific_name": "Long Plant",
            "common_name": "Long",
            "family": "Longaceae",
            "content": "word " * 3000  # Very long content
        }
        json_file = tmp_path / "long_plant.json"
        with open(json_file, 'w') as f:
            json.dump([long_plant], f)
        
        service = RAGService(json_file_path=str(json_file))
        
        mock_pinecone["index"]._vectors = {
            "long_plant_basic": {
                "metadata": {
                    "scientific_name": "Long Plant",
                    "common_name": "Long"
                }
            }
        }
        
        context = service.get_rag_context("long plant", top_k=1)
        
        # Should include truncation marker
        assert "[truncated]" in context or len(context) < len(long_plant["content"])


# ============================================================================
# Service Availability Tests
# ============================================================================

@pytest.mark.unit
class TestServiceAvailability:
    """Test service availability checks"""
    
    def test_is_available_with_all_services(self, mocker, mock_bedrock, mock_pinecone):
        """Test availability when all services are configured"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        
        assert service.is_available() is True
    
    def test_is_available_without_bedrock(self, mocker, mock_pinecone):
        """Test availability without Bedrock"""
        mocker.patch.dict('os.environ', {
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", False)
        
        service = RAGService()
        
        assert service.is_available() is False
    
    def test_is_available_without_pinecone(self, mocker, mock_bedrock):
        """Test availability without Pinecone"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        
        assert service.is_available() is False
    
    def test_is_available_without_any_service(self, mocker):
        """Test availability without any services"""
        mocker.patch.dict('os.environ', {}, clear=True)
        mocker.patch("rag_service.PINECONE_AVAILABLE", False)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", False)
        
        service = RAGService()
        
        assert service.is_available() is False


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
class TestRAGServiceErrorHandling:
    """Test error handling in RAG service"""
    
    def test_load_plant_cache_with_corrupt_json(self, mocker, tmp_path, mock_bedrock, mock_pinecone):
        """Test loading plant cache with corrupt JSON"""
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        # Create corrupt JSON file
        corrupt_json = tmp_path / "corrupt.json"
        corrupt_json.write_text("{invalid json")
        
        service = RAGService()
        service._load_plant_cache(str(corrupt_json))
        
        # Should handle gracefully
        assert len(service.plant_cache) == 0
    
    def test_pinecone_index_creation_failure(self, mocker):
        """Test handling of Pinecone index creation failure"""
        mocker.patch.dict('os.environ', {
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", False)
        
        # Mock Pinecone client that raises exception
        mock_client = Mock()
        mock_client.list_indexes.side_effect = Exception("Connection failed")
        mocker.patch("pinecone.Pinecone", return_value=mock_client)
        
        service = RAGService()
        
        # Should handle gracefully
        assert service.index is None
    
    def test_search_with_exception(self, mocker, mock_bedrock, mock_pinecone):
        """Test search handling when Pinecone query raises exception"""
        mocker.patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'PINECONE_API_KEY': 'test-pinecone-key'
        })
        mocker.patch("rag_service.PINECONE_AVAILABLE", True)
        mocker.patch("rag_service.BEDROCK_AVAILABLE", True)
        
        service = RAGService()
        
        # Mock index query to raise exception
        mock_pinecone["index"].query = Mock(side_effect=Exception("Query failed"))
        
        results = service.search_plants("test query", top_k=5)
        
        # Should return empty list on error
        assert results == []
