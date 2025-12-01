# Backend Testing Guide

This directory contains comprehensive unit and integration tests for the IntoTheWild backend services.

## Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and test configuration
├── test_rag_service.py           # RAG service unit tests (156 tests)
├── test_ai_service.py            # AIService class unit tests
├── test_auth.py                  # Authentication & user management tests
├── test_conversations.py         # Conversation CRUD tests
├── test_websocket.py             # WebSocket handler tests
└── integration/
    ├── __init__.py
    └── test_integration.py       # End-to-end integration tests
```

## Setup

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

## Running Tests

### Run All Tests
```bash
cd backend
pytest
```

### Run Only Unit Tests
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Run Specific Test File
```bash
pytest tests/test_rag_service.py
pytest tests/test_ai_service.py
pytest tests/test_auth.py
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run with Verbose Output
```bash
pytest -v
```

### Run Specific Test Class or Function
```bash
pytest tests/test_rag_service.py::TestRAGServiceInitialization
pytest tests/test_ai_service.py::TestTextGeneration::test_generate_response_simple
```

## Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.unit` - Unit tests with mocked dependencies (fast)
- `@pytest.mark.integration` - Integration tests with real services (slower)
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.requires_credentials` - Tests requiring external service credentials

### Run Tests by Marker
```bash
# Only fast unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Only tests requiring credentials
pytest -m requires_credentials
```

## Environment Variables for Integration Tests

Integration tests can run with real services if credentials are provided:

```bash
# For RAG integration tests
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export AWS_REGION="us-west-2"
export PINECONE_API_KEY="your-pinecone-key"

# For AI service integration tests
export GEMINI_API_KEY="your-gemini-key"

# For authentication tests
export GOOGLE_CLIENT_ID="your-google-client-id"

# For Firebase tests (optional)
# Ensure serviceAccountKey.json exists in backend/
```

**Note:** Integration tests will automatically skip if credentials are not available.

## Mocking Strategy

### External Services Mocked in Unit Tests

All unit tests use mocks for external dependencies:

1. **Firebase/Firestore** - MockFirestoreClient in `conftest.py`
2. **Google OAuth** - Mocked token verification
3. **Gemini AI** - MockGeminiModel with predictable responses
4. **AWS Bedrock** - Mocked embedding generation
5. **Pinecone** - MockPineconeIndex for vector operations
6. **WebSocket** - AsyncMock for connection testing

### Shared Fixtures (`conftest.py`)

- `mock_env_vars` - Mock environment variables
- `sample_user`, `sample_conversation`, `sample_message` - Test data
- `sample_plant_data`, `sample_plant_json` - Plant data for RAG tests
- `mock_firestore` - Complete Firestore mock with collections
- `mock_google_auth` - Google OAuth token verification
- `mock_gemini` - Gemini AI model mock
- `mock_bedrock` - AWS Bedrock embedding mock
- `mock_pinecone` - Pinecone vector database mock
- `mock_websocket` - WebSocket connection mock
