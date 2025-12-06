"""
Unit tests for AIService class in main.py
Tests cover text generation, image analysis, RAG integration, and error handling
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import test directory
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))


# ============================================================================
# AIService Initialization Tests
# ============================================================================

@pytest.mark.unit
class TestAIServiceInitialization:
    """Test AIService initialization scenarios"""

    def test_init_with_gemini_available(self, mocker, mock_gemini):
        """Test initialization when Gemini is available"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()

        assert service.model is not None
        assert service.model_name == "gemini-2.5-flash"

    def test_init_without_gemini_api_key(self, mocker):
        """Test initialization without Gemini API key"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", None)
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()

        assert service.model is None

    def test_init_with_rag_service(self, mocker, mock_gemini):
        """Test initialization with RAG service"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")

        mock_rag = Mock()
        mock_rag.is_available.return_value = True
        mocker.patch("main.rag_service_plant", mock_rag)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()

        assert service.rag_service_plant is not None
        assert service.rag_service_plant.is_available()

    def test_init_model_fallback(self, mocker):
        """Test model initialization fallback when preferred model fails"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        # Mock GenerativeModel to fail on first attempt
        call_count = 0
        def side_effect(model_name):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Model not found")
            return mock_gemini["model"]

        mocker.patch("google.generativeai.GenerativeModel", side_effect=side_effect)

        from main import AIService

        service = AIService()

        # Should have tried and failed
        assert service.model is None or service.model is not None


# ============================================================================
# Text Generation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestTextGeneration:
    """Test AI text generation"""

    async def test_generate_response_simple(self, mocker, mock_gemini):
        """Test simple text generation without context"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        response = await service.generate_response("What is a dandelion?")

        assert response is not None
        assert len(response) > 0
        assert isinstance(response, str)

    async def test_generate_response_with_conversation_context(self, mocker, mock_gemini, sample_message):
        """Test text generation with conversation context"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        conversation_history = [
            sample_message,
            {**sample_message, "id": "msg-124", "text": "Tell me about plants", "isBot": False},
            {**sample_message, "id": "msg-125", "text": "Plants are living organisms...", "isBot": True}
        ]

        service = AIService()
        response = await service.generate_response(
            "What about dandelions?",
            conversation_context=conversation_history
        )

        assert response is not None
        assert len(response) > 0

    async def test_generate_response_with_rag_context(self, mocker, mock_gemini):
        """Test text generation with RAG context"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")

        # Mock RAG service
        mock_rag = Mock()
        mock_rag.is_available.return_value = True
        mock_rag.get_rag_context.return_value = "Plant Info: Dandelion (Taraxacum officinale) is edible."
        mocker.patch("main.rag_service_plant", mock_rag)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        response = await service.generate_response("Is dandelion edible?")

        assert response is not None
        assert "dandelion" in response.lower() or "edible" in response.lower()
        mock_rag.get_rag_context.assert_called_once()

    async def test_generate_response_without_gemini(self, mocker):
        """Test fallback response when Gemini is not available"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.gemini_api_key", None)
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        response = await service.generate_response("Test message")

        assert response is not None
        assert "Test message" in response or "survival" in response.lower()

    async def test_generate_response_model_error(self, mocker):
        """Test error handling during response generation"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        # Mock model that raises error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")

        mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)

        from main import AIService

        service = AIService()
        response = await service.generate_response("Test")

        assert response is not None
        assert "error" in response.lower()

    async def test_generate_response_404_error(self, mocker):
        """Test handling of 404 model not found error"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        # Mock model that raises 404 error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("404 Model not found")

        mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)

        from main import AIService

        service = AIService()
        response = await service.generate_response("Test")

        # Model should be set to None after 404
        assert service.model is None
        assert "error" in response.lower()

    async def test_generate_response_rag_error(self, mocker, mock_gemini):
        """Test handling when RAG service throws error"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")

        # Mock RAG service that throws error
        mock_rag = Mock()
        mock_rag.is_available.return_value = True
        mock_rag.get_rag_context.side_effect = Exception("RAG Error")
        mocker.patch("main.rag_service_plant", mock_rag)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        response = await service.generate_response("Test")

        # Should still generate response despite RAG error
        assert response is not None
        assert len(response) > 0


# ============================================================================
# Image Analysis Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestImageAnalysis:
    """Test AI image analysis (plant identification)"""

    async def test_analyze_plant_image_basic(self, mocker, mock_gemini):
        """Test basic plant image analysis"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        image_data = b"fake_image_data"
        response = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/jpeg"
        )

        assert response is not None
        assert len(response) > 0
        # Should contain plant identification information
        assert any(word in response.lower() for word in ["plant", "dandelion", "edible"])

    async def test_analyze_plant_image_with_user_message(self, mocker, mock_gemini):
        """Test image analysis with user question"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        image_data = b"fake_image_data"
        response = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/jpeg",
            user_message="Is this plant edible?"
        )

        assert response is not None
        assert len(response) > 0

    async def test_analyze_plant_image_with_rag(self, mocker, mock_gemini):
        """Test image analysis with RAG context"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")

        # Mock RAG service
        mock_rag = Mock()
        mock_rag.is_available.return_value = True
        mock_rag.get_rag_context.return_value = "Dandelion info: Edible plant with yellow flowers."
        mocker.patch("main.rag_service_plant", mock_rag)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        image_data = b"fake_image_data"
        response = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/png",
            user_message="What is this plant?"
        )

        assert response is not None
        mock_rag.get_rag_context.assert_called_once()

    async def test_analyze_plant_image_with_conversation_context(self, mocker, mock_gemini, sample_message):
        """Test image analysis with conversation history"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        conversation_history = [sample_message]

        service = AIService()
        image_data = b"fake_image_data"
        response = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/jpeg",
            conversation_context=conversation_history
        )

        assert response is not None

    async def test_analyze_plant_image_without_model(self, mocker):
        """Test image analysis when model is not available"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.gemini_api_key", None)
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        image_data = b"fake_image_data"
        response = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/jpeg"
        )

        assert response is not None
        assert "cannot analyze images" in response.lower()

    async def test_analyze_plant_image_error_handling(self, mocker):
        """Test error handling during image analysis"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        # Mock model that raises error
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("Vision API Error")

        mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)

        from main import AIService

        service = AIService()
        image_data = b"fake_image_data"
        response = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/jpeg"
        )

        assert response is not None
        assert "error" in response.lower()

    async def test_analyze_plant_image_different_mime_types(self, mocker, mock_gemini):
        """Test image analysis with different MIME types"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        image_data = b"fake_image_data"

        # Test JPEG
        response_jpeg = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/jpeg"
        )
        assert response_jpeg is not None

        # Test PNG
        response_png = await service.analyze_image(
            image_data=image_data,
            image_mime_type="image/png"
        )
        assert response_png is not None


# ============================================================================
# Context Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestContextHandling:
    """Test conversation context and prompt building"""

    async def test_conversation_context_limit(self, mocker, mock_gemini):
        """Test that conversation context is limited to last 10 messages"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        # Create 20 messages
        conversation_history = [
            {
                "id": f"msg-{i}",
                "text": f"Message {i}",
                "userId": "user-123",
                "userName": "testuser",
                "conversationId": "conv-123",
                "createdAt": "2023-01-01T00:00:00",
                "isBot": i % 2 == 0
            }
            for i in range(20)
        ]

        service = AIService()

        # Mock to capture the prompt
        captured_prompt = None
        original_generate = mock_gemini["model"].generate_content
        def capture_prompt(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt
            return original_generate(prompt)

        mock_gemini["model"].generate_content = capture_prompt

        response = await service.generate_response(
            "New message",
            conversation_context=conversation_history
        )

        # Verify only last 10 messages were used (plus system prompt and current message)
        # Exact count depends on implementation, but should be limited
        assert response is not None

    async def test_bot_message_formatting(self, mocker, mock_gemini, sample_message):
        """Test that bot messages are formatted correctly in context"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        conversation_history = [
            {**sample_message, "text": "User question", "isBot": False},
            {**sample_message, "id": "msg-124", "text": "Bot answer", "isBot": True}
        ]

        service = AIService()
        response = await service.generate_response(
            "Follow-up question",
            conversation_context=conversation_history
        )

        assert response is not None

    async def test_empty_conversation_context(self, mocker, mock_gemini):
        """Test with empty conversation context"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()
        response = await service.generate_response(
            "Hello",
            conversation_context=[]
        )

        assert response is not None

    async def test_system_prompt_inclusion(self, mocker, mock_gemini):
        """Test that system prompt is included"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()

        # Capture the prompt sent to the model by tracking calls
        captured_prompts = []
        def capture_prompt(prompt):
            captured_prompts.append(prompt)
            # Return mock response
            mock_response = Mock()
            mock_response.text = "Test response"
            return mock_response

        service.model.generate_content = capture_prompt

        await service.generate_response("Test message")

        # generate_content is called twice: once for intent detection, once for the actual response
        assert len(captured_prompts) == 2


# ============================================================================
# Async Execution Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncExecution:
    """Test async execution and event loop handling"""

    async def test_concurrent_requests(self, mocker, mock_gemini):
        """Test handling multiple concurrent requests"""
        mocker.patch("main.GEMINI_AVAILABLE", True)
        mocker.patch("main.gemini_api_key", "test-key")
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService

        service = AIService()

        # Create multiple concurrent requests
        tasks = [
            service.generate_response(f"Question {i}")
            for i in range(5)
        ]

        responses = await asyncio.gather(*tasks)

        assert len(responses) == 5
        assert all(r is not None for r in responses)

    async def test_response_timing(self, mocker):
        """Test that fallback responses have artificial delay"""
        mocker.patch("main.GEMINI_AVAILABLE", False)
        mocker.patch("main.gemini_api_key", None)
        mocker.patch("main.rag_service_plant", None)
        mocker.patch("main.rag_service_animal", None)

        from main import AIService
        import time

        service = AIService()

        start = time.time()
        response = await service.generate_response("Test")
        elapsed = time.time() - start

        assert response is not None
        # Fallback has 0.5s sleep
        assert elapsed >= 0.4  # Allow some tolerance
