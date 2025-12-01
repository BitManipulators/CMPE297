"""
Pytest configuration and shared fixtures for backend tests
"""
import pytest
import sys
import os
from pathlib import Path
from typing import Dict, Generator
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime
from collections import defaultdict
import json

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ============================================================================
# Mock Environment Variables
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def mock_env_vars():
    """Set up mock environment variables for all tests"""
    os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id.apps.googleusercontent.com"
    os.environ["GEMINI_API_KEY"] = "test-gemini-api-key"
    os.environ["AWS_ACCESS_KEY_ID"] = "test-aws-access-key"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test-aws-secret-key"
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["PINECONE_API_KEY"] = "test-pinecone-api-key"
    yield
    # Cleanup after all tests
    for key in ["GOOGLE_CLIENT_ID", "GEMINI_API_KEY", "AWS_ACCESS_KEY_ID", 
                "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "PINECONE_API_KEY"]:
        os.environ.pop(key, None)


# ============================================================================
# Sample Test Data
# ============================================================================

@pytest.fixture
def sample_user() -> Dict:
    """Sample user data"""
    return {
        "id": "user-123",
        "username": "testuser",
        "email": "testuser@example.com",
        "googleId": "google-123",
        "picture": "https://example.com/photo.jpg",
        "createdAt": "2023-01-01T00:00:00",
        "lastLoginAt": "2023-01-01T00:00:00"
    }


@pytest.fixture
def sample_conversation() -> Dict:
    """Sample conversation data"""
    return {
        "id": "conv-123",
        "name": "Test Chat",
        "type": "group",
        "participants": ["user-123", "user-456"],
        "createdAt": "2023-01-01T00:00:00",
        "hasBot": False
    }


@pytest.fixture
def sample_message() -> Dict:
    """Sample message data"""
    return {
        "id": "msg-123",
        "text": "Hello, world!",
        "userId": "user-123",
        "userName": "testuser",
        "conversationId": "conv-123",
        "createdAt": "2023-01-01T00:00:00",
        "isBot": False,
        "type": "text"
    }


@pytest.fixture
def sample_plant_data() -> Dict:
    """Sample plant data for RAG testing"""
    return {
        "scientific_name": "Taraxacum officinale",
        "common_name": "Common Dandelion",
        "family": "Asteraceae",
        "genus": "Taraxacum",
        "summary": "A common flowering plant native to temperate regions.",
        "content": "The common dandelion is a herbaceous perennial plant. All parts of the plant are edible. "
                  "The leaves can be eaten raw in salads or cooked. The roots can be roasted and used as a coffee substitute.",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Taraxacum_officinale"
    }


@pytest.fixture
def sample_plant_json(sample_plant_data, tmp_path) -> str:
    """Create a temporary JSON file with plant data"""
    json_file = tmp_path / "test_plants.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump([sample_plant_data], f)
    return str(json_file)


# ============================================================================
# Mock Firebase
# ============================================================================

class MockFirestoreDocument:
    """Mock Firestore document reference"""
    def __init__(self, data: Dict = None, exists: bool = True):
        self._data = data or {}
        self.exists = exists
        self.id = data.get("id", "mock-id") if data else "mock-id"
    
    def to_dict(self):
        return self._data
    
    def get(self):
        return self
    
    def set(self, data: Dict):
        """Set document data"""
        self._data = data
        self.exists = True
        return self
    
    def update(self, data: Dict):
        """Update document data"""
        self._data.update(data)
        return self


class MockFirestoreCollection:
    """Mock Firestore collection"""
    def __init__(self):
        self._documents: Dict[str, MockFirestoreDocument] = {}
        self._query_results = []
    
    def document(self, doc_id: str):
        """Get or create document reference"""
        if doc_id not in self._documents:
            self._documents[doc_id] = MockFirestoreDocument({"id": doc_id}, exists=False)
        return self._documents[doc_id]
    
    def add(self, data: Dict):
        """Add a document"""
        doc_id = data.get("id", f"auto-{len(self._documents)}")
        doc = MockFirestoreDocument(data)
        self._documents[doc_id] = doc
        return (None, doc)
    
    def where(self, field: str, op: str, value):
        """Mock where query"""
        query = MockFirestoreQuery(self._documents, field, op, value)
        return query
    
    def stream(self):
        """Stream all documents"""
        return iter(self._documents.values())
    
    def set_document(self, doc_id: str, data: Dict):
        """Helper to set a document for testing"""
        self._documents[doc_id] = MockFirestoreDocument(data, exists=True)


class MockFirestoreQuery:
    """Mock Firestore query"""
    def __init__(self, documents: Dict, field: str, op: str, value):
        self._documents = documents
        self._filters = [(field, op, value)]
        self._limit_count = None
        self._order_field = None
        self._order_direction = None
    
    def where(self, field: str, op: str, value):
        """Add filter"""
        self._filters.append((field, op, value))
        return self
    
    def limit(self, count: int):
        """Limit results"""
        self._limit_count = count
        return self
    
    def order_by(self, field: str, direction=None):
        """Order results"""
        self._order_field = field
        self._order_direction = direction
        return self
    
    def stream(self):
        """Execute query and return results"""
        results = []
        for doc in self._documents.values():
            data = doc.to_dict()
            matches = True
            for field, op, value in self._filters:
                if op == "==":
                    if data.get(field) != value:
                        matches = False
                        break
            if matches:
                results.append(doc)
        
        if self._limit_count:
            results = results[:self._limit_count]
        
        return iter(results)


class MockFirestoreClient:
    """Mock Firestore client"""
    def __init__(self):
        self._collections: Dict[str, MockFirestoreCollection] = {}
    
    def collection(self, name: str):
        """Get or create collection"""
        if name not in self._collections:
            self._collections[name] = MockFirestoreCollection()
        return self._collections[name]


@pytest.fixture
def mock_firestore():
    """Mock Firestore client"""
    return MockFirestoreClient()


@pytest.fixture
def mock_firebase_admin(mocker, mock_firestore):
    """Mock Firebase Admin SDK"""
    mock_firebase = mocker.patch("firebase_admin.initialize_app")
    mock_credentials = mocker.patch("firebase_admin.credentials.Certificate")
    mock_firestore_client = mocker.patch("firebase_admin.firestore.client", return_value=mock_firestore)
    
    return {
        "initialize_app": mock_firebase,
        "credentials": mock_credentials,
        "firestore": mock_firestore
    }


# ============================================================================
# Mock Google OAuth
# ============================================================================

@pytest.fixture
def mock_google_auth(mocker):
    """Mock Google OAuth verification"""
    mock_verify = mocker.patch("google.oauth2.id_token.verify_oauth2_token")
    mock_verify.return_value = {
        "sub": "google-123",
        "email": "testuser@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg"
    }
    return mock_verify


@pytest.fixture
def mock_google_userinfo(mocker):
    """Mock Google userinfo API"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "google-123",
        "email": "testuser@example.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg"
    }
    mock_get = mocker.patch("requests.get", return_value=mock_response)
    return mock_get


# ============================================================================
# Mock Gemini AI
# ============================================================================

class MockGeminiResponse:
    """Mock Gemini API response"""
    def __init__(self, text: str):
        self.text = text


class MockGeminiModel:
    """Mock Gemini GenerativeModel"""
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
    
    def generate_content(self, prompt):
        """Mock content generation"""
        if isinstance(prompt, list):
            # Vision API call (with image)
            return MockGeminiResponse(
                "This appears to be a dandelion (Taraxacum officinale). "
                "The yellow flowers and serrated leaves are characteristic. "
                "This plant is edible, but ensure proper identification before consumption."
            )
        else:
            # Text generation
            if "dandelion" in prompt.lower():
                return MockGeminiResponse(
                    "Dandelions are edible plants. The leaves can be used in salads, "
                    "and the roots can be roasted as a coffee substitute."
                )
            return MockGeminiResponse("I can help you with plant identification and information.")


@pytest.fixture
def mock_gemini(mocker):
    """Mock Google Gemini AI"""
    mock_genai = mocker.patch("google.generativeai.configure")
    mock_model_class = mocker.patch("google.generativeai.GenerativeModel", return_value=MockGeminiModel())
    return {
        "configure": mock_genai,
        "GenerativeModel": mock_model_class,
        "model": MockGeminiModel()
    }


# ============================================================================
# Mock AWS Bedrock
# ============================================================================

@pytest.fixture
def mock_bedrock(mocker):
    """Mock AWS Bedrock client"""
    mock_client = Mock()
    
    # Mock embedding generation
    def mock_invoke_model(**kwargs):
        response = Mock()
        # Cohere embedding dimension is 1024
        response_body = json.dumps({
            "embeddings": [[0.1] * 1024]
        })
        response.__getitem__ = lambda self, key: Mock(read=lambda: response_body.encode())
        return response
    
    mock_client.invoke_model = mock_invoke_model
    mock_boto3 = mocker.patch("boto3.client", return_value=mock_client)
    
    return mock_client


# ============================================================================
# Mock Pinecone
# ============================================================================

class MockPineconeIndex:
    """Mock Pinecone index"""
    def __init__(self, name: str):
        self.name = name
        self._vectors: Dict[str, Dict] = {}
        # Create Mock objects for methods that need call tracking
        self.upsert = Mock(side_effect=self._upsert_impl)
        self.query = Mock(side_effect=self._query_impl)
        self.describe_index_stats = Mock(side_effect=self._describe_stats_impl)
    
    def _upsert_impl(self, vectors: list):
        """Mock upsert operation"""
        for vector in vectors:
            self._vectors[vector["id"]] = vector
        return {"upserted_count": len(vectors)}
    
    def _query_impl(self, vector: list, top_k: int = 5, include_metadata: bool = False):
        """Mock query operation"""
        # Return mock matches
        matches = []
        for i, (vec_id, vec_data) in enumerate(list(self._vectors.items())[:top_k]):
            match = Mock()
            match.id = vec_id
            match.score = 0.9 - (i * 0.1)
            match.metadata = vec_data.get("metadata", {})
            matches.append(match)
        
        result = Mock()
        result.matches = matches
        return result
    
    def _describe_stats_impl(self):
        """Mock index stats"""
        stats = Mock()
        stats.total_vector_count = len(self._vectors)
        stats.dimension = 1024
        return stats
class MockPineconeIndexInfo:
    """Mock Pinecone index info"""
    def __init__(self, name: str):
        self.name = name


@pytest.fixture
def mock_pinecone(mocker):
    """Mock Pinecone client"""
    mock_index = MockPineconeIndex("test-index")
    
    # Mock the list response with proper attributes and iterable
    class MockIndexList:
        def __init__(self):
            self.indexes = [MockPineconeIndexInfo("test-index")]
        
        def __iter__(self):
            """Make the list iterable"""
            return iter(self.indexes)
    
    mock_client = Mock()
    mock_client.list_indexes.return_value = MockIndexList()
    mock_client.create_index = Mock()
    mock_client.Index.return_value = mock_index
    
    # Patch at both module level and import level
    mock_pinecone_class = mocker.patch("pinecone.Pinecone", return_value=mock_client)
    mocker.patch("rag_service.Pinecone", return_value=mock_client)
    mock_serverless = mocker.patch("pinecone.ServerlessSpec")
    mocker.patch("rag_service.ServerlessSpec", return_value=Mock())
    
    return {
        "client": mock_client,
        "index": mock_index,
        "Pinecone": mock_pinecone_class,
        "ServerlessSpec": mock_serverless
    }


# ============================================================================
# Mock WebSocket
# ============================================================================

@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    return ws


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    # Import will be done in individual test files to avoid circular imports
    return TestClient


# ============================================================================
# Time Mocking
# ============================================================================

@pytest.fixture
def frozen_time():
    """Frozen time for deterministic testing"""
    from freezegun import freeze_time
    with freeze_time("2023-01-01 12:00:00"):
        yield datetime(2023, 1, 1, 12, 0, 0)

# ============================================================================
# Pytest Hooks for Test File Summary
# ============================================================================

def pytest_sessionstart(session):
    session.file_results = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0, "total": 0})

def pytest_runtest_makereport(item, call):
    if call.when == "call":
        file_path = item.fspath.strpath
        session_results = item.session.file_results[file_path]
        session_results["total"] += 1
        if call.excinfo is None:
            session_results["passed"] += 1
        elif call.excinfo.errisinstance(item.config.getoption("skip_exceptions")):
            session_results["skipped"] += 1
        else:
            session_results["failed"] += 1

def pytest_sessionfinish(session):
    print("\n--- Test File Summary ---")
    for file_path, results in session.file_results.items():
        print(f"File: {file_path}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Total: {results['total']}")
        print("-" * 30)