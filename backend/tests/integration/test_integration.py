"""
Integration tests for backend services
Tests end-to-end workflows with real or semi-real service interactions
"""
import pytest
from fastapi.testclient import TestClient
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import json
import os

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


# ============================================================================
# Full User Flow Integration Tests
# ============================================================================

@pytest.mark.integration
class TestUserFlowIntegration:
    """Test complete user workflows from registration to messaging"""
    
    def test_complete_user_journey(self, mocker):
        """Test complete user journey: register → create conversation → send message"""
        # Mock external dependencies
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.RAG_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app, conversations, messages_store, users
        
        # Clear storage
        conversations.clear()
        messages_store.clear()
        users.clear()
        
        client = TestClient(app)
        # Step 1: Register two users
        user1_response = client.post("/api/users/register", json={
            "username": "alice",
            "email": "alice@example.com"
        })
        assert user1_response.status_code == 200
        user1_id = user1_response.json()["id"]
        
        user2_response = client.post("/api/users/register", json={
            "username": "bob",
            "email": "bob@example.com"
        })
        assert user2_response.status_code == 200
        user2_id = user2_response.json()["id"]
        
        # Step 2: Create a conversation between them
        conv_response = client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": [user1_id, user2_id]
        })
        assert conv_response.status_code == 200
        conv_id = conv_response.json()["id"]
        
        # Step 3: Verify conversation was created
        get_conv_response = client.get(f"/api/conversations/{conv_id}")
        assert get_conv_response.status_code == 200
        assert len(get_conv_response.json()["participants"]) == 2
        
        # Step 4: Get messages (should be empty)
        messages_response = client.get(f"/api/conversations/{conv_id}/messages")
        assert messages_response.status_code == 200
        assert len(messages_response.json()["messages"]) == 0
        
        # Step 5: Add bot to conversation
        bot_response = client.post(f"/api/conversations/{conv_id}/add-bot")
        assert bot_response.status_code == 200
        assert bot_response.json()["hasBot"] is True
    
    def test_group_conversation_flow(self, mocker):
        """Test group conversation creation and management"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.RAG_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app, conversations, users
        
        conversations.clear()
        users.clear()
        
        client = TestClient(app)
        
        # Register users
        user_ids = []
        for i in range(3):
            response = client.post("/api/users/register", json={
                "username": f"user{i}",
                "email": f"user{i}@example.com"
            })
            user_ids.append(response.json()["id"])
        
        # Create group
        group_response = client.post("/api/conversations", json={
            "name": "Study Group",
            "type": "group",
            "participantIds": user_ids[:2]  # Only first 2 users
        })
        assert group_response.status_code == 200
        group_id = group_response.json()["id"]
        
        # Third user joins group
        join_response = client.post(f"/api/conversations/{group_id}/join", json={
            "user_id": user_ids[2]
        })
        assert join_response.status_code == 200
        assert user_ids[2] in join_response.json()["conversation"]["participants"]
        
        # User leaves group
        leave_response = client.post(f"/api/conversations/{group_id}/leave", json={
            "user_id": user_ids[2]
        })
        assert leave_response.status_code == 200
        assert user_ids[2] not in leave_response.json()["conversation"]["participants"]


# ============================================================================
# RAG Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.requires_credentials
class TestRAGIntegration:
    """Test RAG service integration (requires AWS and Pinecone credentials)"""
    
    def test_rag_service_initialization(self, mocker, sample_plant_json):
        """Test RAG service initialization with real components"""
        # This test requires real credentials
        if not all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("PINECONE_API_KEY")
        ]):
            pytest.skip("AWS and Pinecone credentials not available")
        
        from rag_service import RAGService
        
        service = RAGService(json_file_path=sample_plant_json)
        
        # Verify service components
        assert service.bedrock_runtime is not None or service.pinecone_client is not None
    
    def test_rag_embedding_generation(self, mocker):
        """Test real embedding generation (requires AWS credentials)"""
        if not all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY")
        ]):
            pytest.skip("AWS credentials not available")
        
        from rag_service import RAGService
        
        service = RAGService()
        
        if service.bedrock_runtime:
            embedding = service._generate_embedding("test query", input_type="search_query")
            
            if embedding:
                assert len(embedding) == 1024
                assert all(isinstance(x, float) for x in embedding)
    
    def test_rag_plant_search_integration(self, mocker, sample_plant_json):
        """Test plant search with real vector database (requires credentials)"""
        if not all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("PINECONE_API_KEY")
        ]):
            pytest.skip("Credentials not available")
        
        from rag_service import RAGService
        
        service = RAGService(json_file_path=sample_plant_json)
        
        if service.is_available():
            # Load and index plants
            success = service.load_and_index_plants(sample_plant_json, batch_size=10)
            
            if success:
                # Search for plants
                results = service.search_plants("dandelion", top_k=3)
                assert isinstance(results, list)


# ============================================================================
# AI Service Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.requires_credentials
class TestAIServiceIntegration:
    """Test AI service with real Gemini API (requires API key)"""
    
    @pytest.mark.asyncio
    async def test_gemini_text_generation(self):
        """Test real text generation with Gemini (requires API key)"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not available")
        
        from main import AIService
        
        service = AIService()
        
        if service.model:
            response = await service.generate_response("What is a plant?")
            
            assert response is not None
            assert len(response) > 0
            assert "plant" in response.lower()
    
    @pytest.mark.asyncio
    async def test_gemini_image_analysis(self):
        """Test real image analysis with Gemini Vision (requires API key)"""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not available")
        
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL (Pillow) not installed")
        
        from main import AIService
        
        service = AIService()
        
        if service.model:
            # Create a small test image (1x1 pixel)
            import base64
            import io
            
            img = Image.new('RGB', (1, 1), color='green')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            image_data = img_bytes.getvalue()
            
            response = await service.analyze_plant_image(
                image_data=image_data,
                image_mime_type="image/jpeg",
                user_message="What is this?"
            )
            
            assert response is not None
            assert len(response) > 0


# ============================================================================
# End-to-End Scenario Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenarios:
    """Test complete end-to-end scenarios"""
    
    def test_multi_user_chat_scenario(self, mocker):
        """Test multi-user chat scenario without real AI"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.RAG_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app
        
        client = TestClient(app)
        
        # Create multiple users
        users = []
        for i in range(5):
            response = client.post("/api/users/register", json={
                "username": f"user{i}",
                "email": f"user{i}@test.com"
            })
            users.append(response.json())
        
        # Create group conversation
        group_response = client.post("/api/conversations", json={
            "name": "Team Chat",
            "type": "group",
            "participantIds": [u["id"] for u in users[:3]]
        })
        group_id = group_response.json()["id"]
        
        # Other users join
        for user in users[3:]:
            client.post(f"/api/conversations/{group_id}/join", json={
                "user_id": user["id"]
            })
        
        # Add bot
        client.post(f"/api/conversations/{group_id}/add-bot")
        
        # Verify final state
        conv_response = client.get(f"/api/conversations/{group_id}")
        conversation = conv_response.json()
        
        assert len(conversation["participants"]) == 5
        assert conversation["hasBot"] is True
    
    def test_conversation_lifecycle(self, mocker):
        """Test complete conversation lifecycle"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.RAG_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app
        
        client = TestClient(app)
        
        # Register users
        user1 = client.post("/api/users/register", json={
            "username": "creator", "email": "creator@test.com"
        }).json()
        
        user2 = client.post("/api/users/register", json={
            "username": "member", "email": "member@test.com"
        }).json()
        
        # Create conversation
        conv = client.post("/api/conversations", json={
            "name": "Project Chat",
            "type": "group",
            "participantIds": [user1["id"], user2["id"]]
        }).json()
        
        # Add bot
        client.post(f"/api/conversations/{conv['id']}/add-bot")
        
        # Remove bot
        client.post(f"/api/conversations/{conv['id']}/remove-bot")
        
        # Member leaves
        client.post(f"/api/conversations/{conv['id']}/leave", json={
            "user_id": user2["id"]
        })
        
        # Verify final state
        final_conv = client.get(f"/api/conversations/{conv['id']}").json()
        
        assert user2["id"] not in final_conv["participants"]
        assert final_conv["hasBot"] is False


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Test performance characteristics"""
    
    def test_bulk_user_creation(self, mocker):
        """Test creating many users"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app
        import time
        
        client = TestClient(app)
        
        start = time.time()
        
        # Create 100 users
        for i in range(100):
            client.post("/api/users/register", json={
                "username": f"user{i}",
                "email": f"user{i}@test.com"
            })
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0
    
    def test_bulk_conversation_creation(self, mocker):
        """Test creating many conversations"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app
        import time
        
        client = TestClient(app)
        
        # Create users first
        users = []
        for i in range(10):
            response = client.post("/api/users/register", json={
                "username": f"user{i}",
                "email": f"user{i}@test.com"
            })
            users.append(response.json()["id"])
        
        start = time.time()
        
        # Create 50 conversations
        for i in range(50):
            client.post("/api/conversations", json={
                "name": f"Conv {i}",
                "type": "group",
                "participantIds": users[:2]
            })
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 5.0


# ============================================================================
# Error Recovery Tests
# ============================================================================

@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery and resilience"""
    
    def test_duplicate_conversation_handling(self, mocker):
        """Test system handles duplicate one-to-one conversations"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app
        
        client = TestClient(app)
        
        # Create users
        user1 = client.post("/api/users/register", json={
            "username": "user1", "email": "user1@test.com"
        }).json()["id"]
        
        user2 = client.post("/api/users/register", json={
            "username": "user2", "email": "user2@test.com"
        }).json()["id"]
        
        # Create conversation
        conv1 = client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": [user1, user2]
        }).json()
        
        # Try to create again (different order)
        conv2 = client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": [user2, user1]
        }).json()
        
        # Should return same conversation
        assert conv1["id"] == conv2["id"]
    
    def test_concurrent_operations(self, mocker):
        """Test handling concurrent operations"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.FIREBASE_AVAILABLE", False)
        mocker.patch("main.db", None)
        
        from main import app
        
        client = TestClient(app)
        
        # Create user
        user = client.post("/api/users/register", json={
            "username": "testuser", "email": "test@test.com"
        }).json()
        
        # Create multiple conversations concurrently (simulated)
        conversations = []
        for i in range(10):
            response = client.post("/api/conversations", json={
                "name": f"Conv {i}",
                "type": "group",
                "participantIds": [user["id"]]
            })
            conversations.append(response.json())
        
        # All should succeed
        assert len(conversations) == 10
        assert all(c.get("id") for c in conversations)
