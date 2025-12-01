"""
Unit tests for conversation management in main.py
Tests conversation CRUD, participant management, and bot operations
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture
def client(mocker):
    """Create test client with mocked dependencies"""
    mocker.patch("main.GEMINI_AVAILABLE", False)
    mocker.patch("main.FIREBASE_AVAILABLE", False)
    mocker.patch("main.RAG_AVAILABLE", False)
    mocker.patch("main.db", None)
    mocker.patch("main.rag_service", None)
    
    from main import app, conversations, messages_store
    # Clear in-memory storage before each test
    conversations.clear()
    messages_store.clear()
    
    return TestClient(app)
    return


# ============================================================================
# Create Conversation Tests
# ============================================================================

@pytest.mark.unit
class TestCreateConversation:
    """Test conversation creation"""
    
    def test_create_group_conversation(self, client):
        """Test creating a group conversation"""
        response = client.post(
            "/api/conversations",
            json={
                "name": "Test Group",
                "type": "group",
                "participantIds": ["user-1", "user-2", "user-3"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Group"
        assert data["type"] == "group"
        assert len(data["participants"]) == 3
        assert data["hasBot"] is False
        assert "id" in data
        assert "createdAt" in data
    
    def test_create_one_to_one_conversation(self, client):
        """Test creating a one-to-one conversation"""
        response = client.post(
            "/api/conversations",
            json={
                "name": None,
                "type": "one_to_one",
                "participantIds": ["user-1", "user-2"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "one_to_one"
        assert len(data["participants"]) == 2
    
    def test_create_duplicate_one_to_one(self, client):
        """Test that duplicate one-to-one conversations return existing"""
        # Create first conversation
        response1 = client.post(
            "/api/conversations",
            json={
                "type": "one_to_one",
                "participantIds": ["user-1", "user-2"]
            }
        )
        conv1_id = response1.json()["id"]
        
        # Try to create same conversation
        response2 = client.post(
            "/api/conversations",
            json={
                "type": "one_to_one",
                "participantIds": ["user-2", "user-1"]  # Different order
            }
        )
        
        assert response2.status_code == 200
        conv2_id = response2.json()["id"]
        assert conv1_id == conv2_id  # Should return same conversation
    
    def test_create_conversation_with_firebase(self, client, mocker, mock_firestore):
        """Test conversation creation with Firebase"""
        mocker.patch("main.db", mock_firestore)
        
        response = client.post(
            "/api/conversations",
            json={
                "name": "Firebase Group",
                "type": "group",
                "participantIds": ["user-1", "user-2"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Firebase Group"


# ============================================================================
# Get Conversation Tests
# ============================================================================

@pytest.mark.unit
class TestGetConversation:
    """Test getting conversation details"""
    
    def test_get_existing_conversation(self, client):
        """Test getting an existing conversation"""
        # Create conversation first
        create_response = client.post(
            "/api/conversations",
            json={
                "name": "Test Chat",
                "type": "group",
                "participantIds": ["user-1", "user-2"]
            }
        )
        conv_id = create_response.json()["id"]
        
        # Get conversation
        response = client.get(f"/api/conversations/{conv_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert data["name"] == "Test Chat"
    
    def test_get_nonexistent_conversation(self, client):
        """Test getting a non-existent conversation"""
        response = client.get("/api/conversations/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Get All Conversations Tests
# ============================================================================

@pytest.mark.unit
class TestGetAllConversations:
    """Test getting all conversations"""
    
    def test_get_all_conversations_no_filter(self, client):
        """Test getting all conversations without user filter"""
        # Create some conversations
        client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": ["user-1", "user-3"]
        })
        
        response = client.get("/api/conversations")
        
        assert response.status_code == 200
        data = response.json()
        # Without user_id, should only return groups
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["type"] == "group"
    
    def test_get_all_conversations_with_user_filter(self, client):
        """Test getting conversations filtered by user"""
        # Create conversations
        client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": ["user-1", "user-3"]
        })
        client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": ["user-2", "user-3"]
        })
        
        response = client.get("/api/conversations?user_id=user-1")
        
        assert response.status_code == 200
        data = response.json()
        # Should return group + one-to-one where user-1 is participant
        assert len(data["conversations"]) == 2
    
    def test_get_all_conversations_user_not_participant(self, client):
        """Test filtering excludes conversations where user is not participant"""
        client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": ["user-2", "user-3"]
        })
        
        response = client.get("/api/conversations?user_id=user-1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 0


# ============================================================================
# Join/Leave Group Tests
# ============================================================================

@pytest.mark.unit
class TestJoinLeaveGroup:
    """Test joining and leaving group conversations"""
    
    def test_join_group_success(self, client):
        """Test successfully joining a group"""
        # Create group
        create_response = client.post("/api/conversations", json={
            "name": "Public Group",
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        # Join group
        response = client.post(
            f"/api/conversations/{conv_id}/join",
            json={"user_id": "user-3"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user-3" in data["conversation"]["participants"]
    
    def test_join_group_already_member(self, client):
        """Test joining group when already a member"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        # Try to join when already member
        response = client.post(
            f"/api/conversations/{conv_id}/join",
            json={"user_id": "user-1"}
        )
        
        assert response.status_code == 200
        assert "already" in response.json()["message"].lower()
    
    def test_join_nonexistent_group(self, client):
        """Test joining non-existent group"""
        response = client.post(
            "/api/conversations/nonexistent-id/join",
            json={"user_id": "user-1"}
        )
        
        assert response.status_code == 404
    
    def test_join_one_to_one_conversation(self, client):
        """Test that joining one-to-one conversations is not allowed"""
        create_response = client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/conversations/{conv_id}/join",
            json={"user_id": "user-3"}
        )
        
        assert response.status_code == 400
        assert "group" in response.json()["detail"].lower()
    
    def test_leave_group_success(self, client):
        """Test successfully leaving a group"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2", "user-3"]
        })
        conv_id = create_response.json()["id"]
        
        # Leave group
        response = client.post(
            f"/api/conversations/{conv_id}/leave",
            json={"user_id": "user-3"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user-3" not in data["conversation"]["participants"]
    
    def test_leave_group_not_member(self, client):
        """Test leaving group when not a member"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/conversations/{conv_id}/leave",
            json={"user_id": "user-99"}
        )
        
        assert response.status_code == 400
        assert "not a member" in response.json()["detail"].lower()
    
    def test_leave_one_to_one_conversation(self, client):
        """Test that leaving one-to-one conversations is not allowed"""
        create_response = client.post("/api/conversations", json={
            "type": "one_to_one",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/conversations/{conv_id}/leave",
            json={"user_id": "user-1"}
        )
        
        assert response.status_code == 400


# ============================================================================
# Bot Management Tests
# ============================================================================

@pytest.mark.unit
class TestBotManagement:
    """Test adding and removing bot from conversations"""
    
    def test_add_bot_to_conversation(self, client):
        """Test adding bot to a conversation"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.post(f"/api/conversations/{conv_id}/add-bot")
        
        assert response.status_code == 200
        data = response.json()
        assert data["hasBot"] is True
        
        # Verify conversation updated
        conv_response = client.get(f"/api/conversations/{conv_id}")
        assert conv_response.json()["hasBot"] is True
    
    def test_add_bot_already_present(self, client):
        """Test adding bot when already present"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1"]
        })
        conv_id = create_response.json()["id"]
        
        # Add bot first time
        client.post(f"/api/conversations/{conv_id}/add-bot")
        
        # Try to add again
        response = client.post(f"/api/conversations/{conv_id}/add-bot")
        
        assert response.status_code == 200
        assert "already" in response.json()["message"].lower()
    
    def test_add_bot_to_nonexistent_conversation(self, client):
        """Test adding bot to non-existent conversation"""
        response = client.post("/api/conversations/nonexistent-id/add-bot")
        
        assert response.status_code == 404
    
    def test_remove_bot_from_conversation(self, client):
        """Test removing bot from conversation"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1", "user-2"]
        })
        conv_id = create_response.json()["id"]
        
        # Add bot first
        client.post(f"/api/conversations/{conv_id}/add-bot")
        
        # Remove bot
        response = client.post(f"/api/conversations/{conv_id}/remove-bot")
        
        assert response.status_code == 200
        data = response.json()
        assert data["hasBot"] is False
    
    def test_remove_bot_not_present(self, client):
        """Test removing bot when not present"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.post(f"/api/conversations/{conv_id}/remove-bot")
        
        assert response.status_code == 200
        assert "not in conversation" in response.json()["message"].lower()


# ============================================================================
# Messages Tests
# ============================================================================

@pytest.mark.unit
class TestMessages:
    """Test message retrieval"""
    
    def test_get_messages_empty_conversation(self, client):
        """Test getting messages from empty conversation"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.get(f"/api/conversations/{conv_id}/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
    
    def test_get_messages_with_limit(self, client):
        """Test getting messages with limit parameter"""
        create_response = client.post("/api/conversations", json={
            "type": "group",
            "participantIds": ["user-1"]
        })
        conv_id = create_response.json()["id"]
        
        response = client.get(f"/api/conversations/{conv_id}/messages?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data


# ============================================================================
# Database Helper Function Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestDatabaseHelpers:
    """Test database helper functions"""
    
    async def test_save_message_in_memory(self, mocker):
        """Test saving message to in-memory storage"""
        mocker.patch("main.db", None)
        from main import save_message, messages_store
        
        messages_store.clear()
        
        message = {
            "id": "msg-1",
            "text": "Hello",
            "conversationId": "conv-1",
            "userId": "user-1"
        }
        
        await save_message(message)
        
        assert "conv-1" in messages_store
        assert len(messages_store["conv-1"]) == 1
        assert messages_store["conv-1"][0]["id"] == "msg-1"
    
    async def test_get_messages_in_memory(self, mocker):
        """Test getting messages from in-memory storage"""
        mocker.patch("main.db", None)
        from main import get_messages, messages_store
        
        messages_store["conv-1"] = [
            {"id": "msg-1", "text": "Hello"},
            {"id": "msg-2", "text": "World"}
        ]
        
        messages = await get_messages("conv-1")
        
        assert len(messages) == 2
    
    async def test_save_conversation_in_memory(self, mocker):
        """Test saving conversation to in-memory storage"""
        mocker.patch("main.db", None)
        from main import save_conversation, conversations
        
        conversations.clear()
        
        conversation = {
            "id": "conv-1",
            "name": "Test",
            "type": "group"
        }
        
        await save_conversation(conversation)
        
        assert "conv-1" in conversations
        assert conversations["conv-1"]["name"] == "Test"
    
    async def test_update_conversation_in_memory(self, mocker):
        """Test updating conversation in in-memory storage"""
        mocker.patch("main.db", None)
        from main import update_conversation, conversations
        
        conversations["conv-1"] = {
            "id": "conv-1",
            "name": "Old Name",
            "hasBot": False
        }
        
        await update_conversation("conv-1", {"hasBot": True})
        
        assert conversations["conv-1"]["hasBot"] is True
    
    async def test_find_conversation_by_participants(self, mocker):
        """Test finding conversation by participant set"""
        mocker.patch("main.db", None)
        from main import find_conversation_by_participants, conversations
        
        conversations.clear()
        conversations["conv-1"] = {
            "id": "conv-1",
            "type": "one_to_one",
            "participants": ["user-1", "user-2"]
        }
        conversations["conv-2"] = {
            "id": "conv-2",
            "type": "one_to_one",
            "participants": ["user-1", "user-3"]
        }
        
        # Find with same participants (different order)
        result = await find_conversation_by_participants(["user-2", "user-1"], "one_to_one")
        
        assert result is not None
        assert result["id"] == "conv-1"
    
    async def test_find_conversation_no_match(self, mocker):
        """Test finding conversation when no match exists"""
        mocker.patch("main.db", None)
        from main import find_conversation_by_participants, conversations
        
        conversations.clear()
        
        result = await find_conversation_by_participants(["user-1", "user-2"], "one_to_one")
        
        assert result is None
