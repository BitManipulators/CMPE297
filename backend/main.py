"""
FastAPI Backend Server for Multi-User Chat with AI Support
Supports WebSocket for real-time messaging and /bot command to add AI to conversations
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import json
import uuid
from datetime import datetime
from pydantic import BaseModel
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests as http_requests
import base64
import re

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Gemini AI imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    # Configure Gemini API key from environment variable
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        logger.info("Gemini AI configured successfully")
    else:
        GEMINI_AVAILABLE = False
        logger.warning("GEMINI_API_KEY not found in environment variables. Gemini AI will not be available.")
except ImportError as e:
    GEMINI_AVAILABLE = False
    gemini_api_key = None
    logger.warning(f"Gemini AI not available. Import error: {e}")

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    FIREBASE_AVAILABLE = True
except ImportError as e:
    FIREBASE_AVAILABLE = False
    print(f"Firebase not available, using in-memory storage. Import error: {e}")

# RAG Service imports
try:
    import sys
    # Add rag directory to path
    rag_dir = Path(__file__).parent / "rag"
    sys.path.insert(0, str(rag_dir))
    from rag_service import RAGService
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    logger.warning(f"RAG service not available. Import error: {e}")

# Set the path that NGINX is stripping off
BACKEND_ROOT_PATH = "/backend"

app = FastAPI(
    title="IntoTheWild Chat API",
    root_path=BACKEND_ROOT_PATH
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Flutter app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (fallback if Firebase not configured)
active_connections: Dict[str, WebSocket] = {}
conversations: Dict[str, Dict] = {}
messages_store: Dict[str, List[Dict]] = {}
users: Dict[str, Dict] = {}

# Firebase initialization
db = None

# Initialize Firebase if available
if FIREBASE_AVAILABLE:
    try:
        # Check if Firebase is already initialized (prevents error on reload)
        try:
            firebase_admin.get_app()
            logger.info("Firebase already initialized")
        except ValueError:
            # Firebase not initialized yet, so initialize it
            import os
            import json
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            cred_path = os.path.join(script_dir, "serviceAccountKey.json")
            cred = credentials.Certificate(cred_path)

            # Read storageBucket from the service account key file
            storage_bucket = None
            try:
                with open(cred_path, 'r') as f:
                    service_account_data = json.load(f)
                    storage_bucket = service_account_data.get('storageBucket')
            except Exception as e:
                logger.warning(f"Could not read storageBucket from service account key: {e}")

            # Initialize Firebase with storage bucket if available
            if storage_bucket:
                firebase_admin.initialize_app(cred, {
                    'storage_bucket': storage_bucket
                })
                logger.info(f"Firebase initialized successfully with storage bucket: {storage_bucket}")
            else:
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized successfully (storage bucket not found in service account key)")

        db = firestore.client()
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}")
        db = None

# Pydantic models
class User(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    googleId: Optional[str] = None
    picture: Optional[str] = None
    createdAt: Optional[str] = None
    lastLoginAt: Optional[str] = None


class Message(BaseModel):
    id: str
    text: str
    userId: str
    userName: str
    conversationId: str
    createdAt: str
    isBot: bool = False
    imageUrl: Optional[str] = None
    type: str = "text"


class Conversation(BaseModel):
    id: str
    name: Optional[str] = None
    type: str  # "one_to_one" or "group"
    participants: List[str]
    createdAt: str
    hasBot: bool = False


class CreateConversationRequest(BaseModel):
    name: Optional[str] = None
    type: str  # "one_to_one" or "group"
    participantIds: List[str]


class RegisterUserRequest(BaseModel):
    username: str
    email: Optional[str] = None


# Database helper functions
async def save_message(message: Dict):
    """Save message to database (Firebase or in-memory)"""
    if db:
        # Save to Firebase
        db.collection("messages").add(message)
    else:
        # In-memory storage
        conv_id = message["conversationId"]
        if conv_id not in messages_store:
            messages_store[conv_id] = []
        messages_store[conv_id].append(message)


async def get_messages(conversation_id: str, limit: int = 50) -> List[Dict]:
    """Get messages from database"""
    if db:
        # Get from Firebase
        messages_ref = db.collection("messages").where("conversationId", "==", conversation_id)
        messages_ref = messages_ref.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit)
        docs = messages_ref.stream()
        return [doc.to_dict() for doc in docs]
    else:
        # In-memory storage
        return messages_store.get(conversation_id, [])


async def save_conversation(conversation: Dict):
    """Save conversation to database"""
    if db:
        db.collection("conversations").document(conversation["id"]).set(conversation)
    else:
        conversations[conversation["id"]] = conversation


async def get_conversation(conversation_id: str) -> Optional[Dict]:
    """Get conversation from database"""
    if db:
        doc = db.collection("conversations").document(conversation_id).get()
        return doc.to_dict() if doc.exists else None
    else:
        return conversations.get(conversation_id)


async def update_conversation(conversation_id: str, updates: Dict):
    """Update conversation in database"""
    if db:
        db.collection("conversations").document(conversation_id).update(updates)
    else:
        if conversation_id in conversations:
            conversations[conversation_id].update(updates)


async def find_conversation_by_participants(participant_ids: List[str], conversation_type: str = "one_to_one") -> Optional[Dict]:
    """Find existing conversation with exact same participants (for one-to-one conversations)"""
    participant_set = set(participant_ids)

    if db:
        # Query Firebase for conversations with these participants
        convs_ref = db.collection("conversations").where("type", "==", conversation_type)
        docs = convs_ref.stream()
        for doc in docs:
            conv = doc.to_dict()
            if conv and set(conv.get("participants", [])) == participant_set:
                return conv
        return None
    else:
        # In-memory storage
        for conv in conversations.values():
            if conv.get("type") == conversation_type and set(conv.get("participants", [])) == participant_set:
                return conv
        return None


# Initialize RAG Services (Plant and Animal)
rag_service_plant = None
rag_service_animal = None

if RAG_AVAILABLE:
    script_dir = Path(__file__).parent

    # Initialize Plant RAG Service
    try:
        plant_json_path = script_dir / "rag" / "plantae_wikipedia_content.json"
        rag_service_plant = RAGService(json_file_path=str(plant_json_path) if plant_json_path.exists() else None)
        if rag_service_plant.is_available():
            logger.info("Plant RAG service initialized successfully")
        else:
            logger.warning("Plant RAG service initialized but not fully available (missing API keys)")
    except Exception as e:
        logger.error(f"Failed to initialize Plant RAG service: {e}")
        rag_service_plant = None

    # Initialize Animal RAG Service
    try:
        animal_json_path = script_dir / "rag" / "animalia_wikipedia_content.json"
        if animal_json_path.exists():
            rag_service_animal = RAGService.for_animals(json_file_path=str(animal_json_path))
            if rag_service_animal.is_available():
                logger.info("Animal RAG service initialized successfully")
            else:
                logger.warning("Animal RAG service initialized but not fully available (missing API keys)")
        else:
            logger.warning(f"Animal data file not found: {animal_json_path}")
    except Exception as e:
        logger.error(f"Failed to initialize Animal RAG service: {e}")
        rag_service_animal = None

# AI Service (shared AI for all users)
class AIService:
    """Shared AI service that generates responses using Gemini AI with RAG support"""

    def __init__(self):
        """Initialize the AI service with Gemini model"""
        self.model = None
        self.model_name = None
        self.rag_service_plant = rag_service_plant
        self.rag_service_animal = rag_service_animal
        if GEMINI_AVAILABLE and gemini_api_key:
            # Try different model names in order of preference
            # gemini-1.5-flash is faster and more cost-effective
            # gemini-1.5-pro is more capable but slower
            model_names = ['gemini-2.5-flash']

            for model_name in model_names:
                try:
                    logger.info(f"Attempting to initialize Gemini model: {model_name}")
                    self.model = genai.GenerativeModel(model_name)
                    self.model_name = model_name
                    logger.info(f"Gemini AI model '{model_name}' initialized successfully")
                    break
                except Exception as e:
                    logger.warning(f"Failed to initialize Gemini model '{model_name}': {e}")
                    self.model = None
                    continue

            if not self.model:
                logger.error("Failed to initialize any Gemini model. AI will use fallback responses.")

    async def _detect_query_intent(self, query: str) -> Dict[str, bool]:
        """
        Detect if query is about plants, animals/insects, or both using LLM.
        Returns dict with flags for each domain.
        Falls back to default ambiguous classification if LLM is unavailable.
        """
        # If Gemini model is not available, default to ambiguous (search both)
        if not self.model:
            logger.warning("Gemini model not available for intent detection, defaulting to ambiguous")
            return {
                'is_animal': False,
                'is_plant': False,
                'is_both': False,
                'is_ambiguous': True
            }

        try:
            # Construct prompt for intent classification
            intent_prompt = f"""You are a query classifier for a wildlife knowledge base. Classify the following user query to determine if it's about animals/insects/wildlife, plants/flora, both domains, or ambiguous/unclear.

Query: "{query}"

Respond with ONLY a valid JSON object in this exact format (no markdown, no code blocks, just the JSON):
{{
  "is_animal": true or false,
  "is_plant": true or false,
  "is_both": true or false,
  "is_ambiguous": true or false
}}

Classification Rules:
- If query mentions specific animals (bears, lions, birds, insects, mammals, reptiles, etc.) or animal-related terms → is_animal: true
- If query mentions specific plants (trees, flowers, mushrooms, herbs, etc.) or plant-related terms → is_plant: true
- If query clearly mentions both animals and plants → is_both: true, is_animal: true, is_plant: true
- If query is unclear, too general, or could be either → is_ambiguous: true
- Only one of is_both or is_ambiguous should be true (not both)
- If query is clearly about animals, set is_animal: true and is_ambiguous: false
- If query is clearly about plants, set is_plant: true and is_ambiguous: false

Examples:
- "where can I find grizzly bears?" → {{"is_animal": true, "is_plant": false, "is_both": false, "is_ambiguous": false}}
- "what plants are edible?" → {{"is_animal": false, "is_plant": true, "is_both": false, "is_ambiguous": false}}
- "what animals and plants live in forests?" → {{"is_animal": true, "is_plant": true, "is_both": true, "is_ambiguous": false}}
- "tell me about nature" → {{"is_animal": false, "is_plant": false, "is_both": false, "is_ambiguous": true}}

Now classify this query:"""

            # Generate response using Gemini
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(intent_prompt)
            )

            # Extract text from response
            response_text = response.text.strip() if response.text else ""

            if not response_text:
                logger.warning("Empty response from LLM for intent detection, defaulting to ambiguous")
                return {
                    'is_animal': False,
                    'is_plant': False,
                    'is_both': False,
                    'is_ambiguous': True
                }

            # Clean up response text (remove markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON response
            try:
                intent_result = json.loads(response_text)

                # Validate the response structure
                required_keys = ['is_animal', 'is_plant', 'is_both', 'is_ambiguous']
                if not all(key in intent_result for key in required_keys):
                    logger.warning(f"Invalid intent detection response structure: {intent_result}, defaulting to ambiguous")
                    return {
                        'is_animal': False,
                        'is_plant': False,
                        'is_both': False,
                        'is_ambiguous': True
                    }

                # Ensure boolean values
                intent_result = {
                    'is_animal': bool(intent_result.get('is_animal', False)),
                    'is_plant': bool(intent_result.get('is_plant', False)),
                    'is_both': bool(intent_result.get('is_both', False)),
                    'is_ambiguous': bool(intent_result.get('is_ambiguous', False))
                }

                logger.info(f"LLM intent detection result: {intent_result}")
                return intent_result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM intent detection response: {e}")
                logger.error(f"Response text: {response_text}")
                # Default to ambiguous on parse error
                return {
                    'is_animal': False,
                    'is_plant': False,
                    'is_both': False,
                    'is_ambiguous': True
                }

        except Exception as e:
            logger.error(f"Error in LLM-based intent detection: {e}")
            # Default to ambiguous on any error
            return {
                'is_animal': False,
                'is_plant': False,
                'is_both': False,
                'is_ambiguous': True
            }

    async def generate_response(self, user_message: str, conversation_context: List[Dict] = None) -> str:
        """
        Generate AI response using Gemini AI.

        Args:
            user_message: The user's message
            conversation_context: List of previous messages for context

        Returns:
            AI-generated response string
        """
        # If Gemini is not available, fall back to mock response
        if not self.model:
            logger.warning("Gemini model not available, using fallback response")
            responses = [
                f"I understand you said: {user_message}. Let me help you with survival guidance.",
                "That's an interesting question about survival. Here's what I think...",
                "Based on your message, I'd recommend considering the following survival tips...",
                "I can help you with that! In survival situations, it's important to...",
            ]
            await asyncio.sleep(0.5)
            return responses[hash(user_message) % len(responses)]

        try:
            # Build conversation history for context
            prompt_parts = []

            # Add system context for plant and animal identification and information
            system_prompt = """You are a helpful AI assistant specialized in:
- Plant identification, edibility, medicinal uses, and outdoor plant knowledge
- Animal identification (including insects, mammals, birds, reptiles, etc.)
- Wildlife behavior, habitats, and safety information
- Survival knowledge about both flora and fauna

CRITICAL INSTRUCTION - INFORMATION SOURCING:
You MUST ONLY use information provided in the "Relevant Plant Information" or "Relevant Animal Information" sections below.
- DO NOT use any information from your training data or prior knowledge
- DO NOT make up or infer information that is not explicitly stated in the provided context
- If the provided information does not contain the answer, you MUST say "I don't have specific information about this" or similar
- You can only answer questions about plants/animals that appear in the provided context sections
- If asked about something not in the context, politely decline and suggest the user provide more details or check other sources

CRITICAL RESPONSE FORMATTING:
- DO NOT start responses with phrases like "Based on the information I have", "Based on the information in my knowledge base", "According to my knowledge base", "Based on the provided information", or any similar prefacing phrases
- DO NOT mention "knowledge base", "information I have", "provided information", or similar phrases in your responses
- Start your responses directly with the answer or information
- Answer naturally as if you are an expert sharing knowledge directly
- Example of what NOT to say: "Based on the information I have, here are some plants..."
- Example of what TO say: "Here are some plants that can be used for natural insect repellent:"

Your primary role is to help users learn about:
PLANTS: Identifying plants, determining edibility, medicinal uses, safety warnings
ANIMALS/INSECTS: Identifying species, behavior, habitats, safety (venomous/poisonous), ecological roles

IMPORTANT SAFETY GUIDELINES:
PLANTS:
- Always emphasize that users should NEVER consume plants without 100% certainty of identification
- Warn about lookalike plants that might be toxic
- Recommend consulting with local experts or field guides

ANIMALS/INSECTS:
- Warn about venomous, poisonous, or dangerous species
- Provide safety guidelines for encounters
- Distinguish between harmful and beneficial species (e.g., beneficial insects vs pests)

When in doubt, advise users to err on the side of caution and consult experts.

Keep your responses accurate, informative, and safety-focused. Be friendly and educational.
ALWAYS base your answers ONLY on the information provided in the context sections below."""
            prompt_parts.append(system_prompt)

            # Detect query intent to determine which domain(s) to search
            intent = await self._detect_query_intent(user_message)
            logger.info(f"Query intent detected: {intent} for message: '{user_message[:100]}...'")

            # Get RAG context based on intent
            rag_context = ""
            if self.rag_service_plant or self.rag_service_animal:
                try:
                    plant_context = ""
                    animal_context = ""

                    # Search only relevant domain(s) based on intent
                    if intent['is_both'] or intent['is_ambiguous']:
                        # Search both domains
                        logger.info("Searching both plant and animal RAG services")
                        if self.rag_service_plant and self.rag_service_plant.is_available():
                            plant_context = self.rag_service_plant.get_rag_context(user_message, top_k=2)
                            logger.info(f"Plant RAG context retrieved (length: {len(plant_context)} chars):\n{plant_context[:500]}...")

                        if self.rag_service_animal and self.rag_service_animal.is_available():
                            animal_context = self.rag_service_animal.get_rag_context_animals(user_message, top_k=2)
                            logger.info(f"Animal RAG context retrieved (length: {len(animal_context)} chars):\n{animal_context[:500]}...")

                        # Combine both contexts
                        if plant_context and animal_context:
                            rag_context = plant_context + "\n\n" + animal_context
                        elif plant_context:
                            rag_context = plant_context
                        elif animal_context:
                            rag_context = animal_context

                    elif intent['is_animal']:
                        # Only search animal index
                        logger.info("Searching animal RAG service only")
                        if self.rag_service_animal and self.rag_service_animal.is_available():
                            animal_context = self.rag_service_animal.get_rag_context_animals(user_message, top_k=3)
                            rag_context = animal_context
                            logger.info(f"Animal RAG context retrieved (length: {len(animal_context)} chars):\n{animal_context[:500]}...")

                    elif intent['is_plant']:
                        # Only search plant index
                        logger.info("Searching plant RAG service only")
                        if self.rag_service_plant and self.rag_service_plant.is_available():
                            plant_context = self.rag_service_plant.get_rag_context(user_message, top_k=3)
                            rag_context = plant_context
                            logger.info(f"Plant RAG context retrieved (length: {len(plant_context)} chars):\n{plant_context[:500]}...")

                    if rag_context:
                        logger.info(f"Final RAG context (total length: {len(rag_context)} chars) will be added to prompt")
                        prompt_parts.append("\n" + "="*80)
                        prompt_parts.append("KNOWLEDGE BASE CONTEXT - USE ONLY THIS INFORMATION:")
                        prompt_parts.append("="*80)
                        prompt_parts.append(rag_context)
                        prompt_parts.append("="*80)
                        prompt_parts.append("\nCRITICAL INSTRUCTIONS:")
                        prompt_parts.append("- Answer the user's question using ONLY the information provided in the 'KNOWLEDGE BASE CONTEXT' section above")
                        prompt_parts.append("- If the answer is not in the provided context, say: 'I don't have specific information about this. Please provide more details or consult other sources.'")
                        prompt_parts.append("- DO NOT use any information from your training data that is not in the provided context")
                        prompt_parts.append("- DO NOT start responses with phrases like 'Based on the information I have', 'Based on the information in my knowledge base', 'According to my knowledge base', 'Based on the provided information', or any similar prefacing phrases")
                        prompt_parts.append("- DO NOT mention 'knowledge base', 'information I have', 'provided information', or similar phrases in your responses")
                        prompt_parts.append("- Start your responses directly with the answer or information - answer naturally as if you are an expert sharing knowledge directly")
                        prompt_parts.append("- If the context is empty or doesn't contain relevant information, you must decline to answer based on prior knowledge")
                    else:
                        logger.warning("No RAG context retrieved for query")
                        prompt_parts.append("\n" + "="*80)
                        prompt_parts.append("NO KNOWLEDGE BASE CONTEXT AVAILABLE")
                        prompt_parts.append("="*80)
                        prompt_parts.append("\nIMPORTANT: No relevant information was found for this query.")
                        prompt_parts.append("You must inform the user that you don't have specific information about this topic.")
                        prompt_parts.append("DO NOT make up answers or use prior training knowledge.")
                        prompt_parts.append("Answer naturally without mentioning 'knowledge base' or similar phrases.")
                except Exception as e:
                    logger.error(f"Error getting RAG context: {e}")

            # Add conversation context if available
            if conversation_context:
                # Reverse to get chronological order (oldest first)
                context_messages = conversation_context[::-1]
                for msg in context_messages[-10:]:  # Use last 10 messages for context
                    text = msg.get("text", "")
                    is_bot = msg.get("isBot", False)
                    if text:
                        if is_bot:
                            prompt_parts.append(f"Assistant: {text}")
                        else:
                            user_name = msg.get("userName", "User")
                            prompt_parts.append(f"{user_name}: {text}")

            # Add current user message
            prompt_parts.append(f"User: {user_message}")
            prompt_parts.append("Assistant:")

            # Join prompt parts with newlines for better formatting
            full_prompt = "\n".join(prompt_parts)

            # Generate response using Gemini
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(full_prompt)
            )

            # Extract text from response
            ai_response = response.text.strip() if response.text else "I'm sorry, I couldn't generate a response. Please try again."

            logger.info(f"Generated AI response for message: {user_message[:50]}...")
            return ai_response

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating AI response: {e}")

            # Check if it's a model not found error
            if "404" in error_msg or "not found" in error_msg.lower():
                logger.error(f"Model '{self.model_name}' not available. Please check your API key permissions or try a different model.")
                # Mark model as unavailable for future requests
                self.model = None

            # Fallback response on error
            return f"I apologize, but I encountered an error processing your message. Please try again. Your message was: {user_message[:100]}"

    async def analyze_image(self, image_data: bytes, image_mime_type: str, user_message: str = "", conversation_context: List[Dict] = None) -> str:
        """
        Analyze plant image using Gemini Vision API (using gemini-2.5-flash).

        Args:
            image_data: Raw image bytes
            image_mime_type: MIME type (e.g., 'image/jpeg', 'image/png')
            user_message: Optional user message/question about the image
            conversation_context: List of previous messages for context

        Returns:
            AI-generated plant identification and information
        """
        if not self.model:
            logger.warning("Gemini model not available, using fallback response")
            return "I'm sorry, but I cannot analyze images right now. Please ensure the AI service is properly configured."

        try:
            # STEP 1: First, identify the scientific name using LLM's visual recognition
            scientific_name = "UNKNOWN"  # Initialize with default value
            try:
                logger.info("Image analysis - Step 1: Identifying scientific name from image using LLM")
                identification_prompt = """Look at this image and identify ONLY the scientific name (binomial nomenclature) of the plant or animal shown.

CRITICAL INSTRUCTIONS:
- Provide ONLY the scientific name in the format: "Genus species" (e.g., "Azadirachta indica")
- If you cannot identify it, respond with: "UNKNOWN"
- Do NOT provide any other information, just the scientific name or UNKNOWN
- If it's clearly a plant, provide the plant scientific name
- If it's clearly an animal/insect, provide the animal scientific name
- If uncertain, try to provide the most likely scientific name

Respond with ONLY the scientific name or UNKNOWN:"""

                # Prepare image for identification (Gemini accepts raw bytes)
                image_part_identification = {
                    "mime_type": image_mime_type,
                    "data": image_data
                }

                # Get identification from LLM
                loop = asyncio.get_event_loop()
                identification_response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content([identification_prompt, image_part_identification])
                )

                scientific_name = identification_response.text.strip() if identification_response.text else "UNKNOWN"
                # Clean up the response (remove quotes, extra text)
                scientific_name = scientific_name.replace('"', '').replace("'", '').strip()
                # Extract just the scientific name if LLM added extra text
                scientific_name_match = re.search(r'([A-Z][a-z]+(?:\s+[a-z]+)+)', scientific_name)
                if scientific_name_match:
                    scientific_name = scientific_name_match.group(1)

                logger.info(f"Image analysis - Identified scientific name: {scientific_name}")
            except Exception as e:
                logger.error(f"Error during scientific name identification: {e}")
                scientific_name = "UNKNOWN"  # Fallback to UNKNOWN if identification fails

            # Build prompt parts for final analysis
            prompt_parts = []

            # System prompt for plant and animal identification
            system_prompt = """You are an expert specializing in analyzing images of plants, animals, and insects found in the wild.

CRITICAL INSTRUCTION - INFORMATION SOURCING:
You MUST ONLY use information provided in the "Relevant Plant Information" or "Relevant Animal Information" sections below.
- DO NOT use any information from your training data or prior knowledge for detailed information
- DO NOT make up or infer information that is not explicitly stated in the provided context
- The scientific name has already been identified from the image
- You MUST use ONLY the information from the provided context to answer questions
- If the provided information does not contain details about the identified species, you MUST say "I don't have specific information about this"

CRITICAL RESPONSE FORMATTING:
- DO NOT start responses with phrases like "Based on the information I have", "Based on the information in my knowledge base", "According to my knowledge base", "Based on the provided information", or any similar prefacing phrases
- DO NOT mention "knowledge base", "information I have", "provided information", or similar phrases in your responses
- Start your responses directly with the answer or information
- Answer naturally as if you are an expert sharing knowledge directly

When analyzing images, provide:

FOR PLANTS:
1. Plant name (common name and scientific name - already identified)
2. Key identifying features visible in the image
3. Edibility status (edible/poisonous/unknown) - ONLY from provided context, BE VERY CAUTIOUS
4. Safety warnings about lookalike plants or toxic parts - ONLY from provided context
5. Medicinal uses (if any and if known) - ONLY from provided context
6. Habitat and growing conditions - ONLY from provided context

FOR ANIMALS/INSECTS:
1. Species name (common name and scientific name - already identified)
2. Key identifying features visible in the image
3. Safety status (venomous/poisonous/harmless) - ONLY from provided context, BE VERY CAUTIOUS
4. Behavior and habitat information - ONLY from provided context
5. Ecological role (beneficial/pest/predator/prey) - ONLY from provided context
6. Safety warnings about bites, stings, or dangerous encounters - ONLY from provided context

CRITICAL SAFETY GUIDELINES:
PLANTS:
- NEVER state a plant is edible unless you are HIGHLY confident AND the information is in the provided context
- Always warn about potential lookalike toxic plants (if mentioned in context)

ANIMALS/INSECTS:
- Warn about venomous, poisonous, or dangerous species (if mentioned in context)
- Distinguish between harmful and beneficial species (if mentioned in context)
- Provide safety guidelines for encounters (if mentioned in context)

GENERAL:
- Recommend consulting local experts or field guides
- When in doubt, advise users to err on the side of caution
- If the image is unclear or doesn't show a plant/animal/insect, say so
- If the identified species is not in the provided context, clearly state that you don't have information about it
- Answer naturally without mentioning "knowledge base" or similar phrases

Be accurate, informative, and prioritize safety above all else."""
            prompt_parts.append(system_prompt)

            # Add the identified scientific name to the prompt
            if scientific_name and scientific_name.upper() != "UNKNOWN":
                prompt_parts.append(f"\nIDENTIFIED SPECIES: {scientific_name}")
                prompt_parts.append("Use the provided context below to provide information about this species.")

            # STEP 2: Search RAG using the identified scientific name
            plant_context = ""
            animal_context = ""
            rag_context = ""

            if scientific_name and scientific_name.upper() != "UNKNOWN" and (self.rag_service_plant or self.rag_service_animal):
                try:
                    logger.info(f"Image analysis - Step 2: Searching RAG with scientific name: {scientific_name}")

                    # Try both plant and animal indexes with the scientific name
                    if self.rag_service_plant and self.rag_service_plant.is_available():
                        plant_context = self.rag_service_plant.get_rag_context(scientific_name, top_k=3)
                        logger.info(f"Image analysis - Plant RAG context retrieved (length: {len(plant_context)} chars):\n{plant_context[:500]}...")

                    if self.rag_service_animal and self.rag_service_animal.is_available():
                        animal_context = self.rag_service_animal.get_rag_context_animals(scientific_name, top_k=3)
                        logger.info(f"Image analysis - Animal RAG context retrieved (length: {len(animal_context)} chars):\n{animal_context[:500]}...")

                    # Combine contexts
                    if plant_context and animal_context:
                        rag_context = plant_context + "\n\n" + animal_context
                    elif plant_context:
                        rag_context = plant_context
                    elif animal_context:
                        rag_context = animal_context

                    if rag_context:
                        logger.info(f"Image analysis - Final RAG context (total length: {len(rag_context)} chars) will be added to prompt")
                        prompt_parts.append("\n" + "="*80)
                        prompt_parts.append("KNOWLEDGE BASE CONTEXT - USE ONLY THIS INFORMATION:")
                        prompt_parts.append("="*80)
                        prompt_parts.append(rag_context)
                        prompt_parts.append("="*80)
                        prompt_parts.append("\nCRITICAL INSTRUCTIONS:")
                        prompt_parts.append("- The scientific name has been identified as: " + scientific_name)
                        prompt_parts.append("- Use ONLY the information provided in the 'KNOWLEDGE BASE CONTEXT' section above to answer all questions")
                        prompt_parts.append("- DO NOT use any information from your training data that is not in the provided context")
                        prompt_parts.append("- If the identified species is not in the provided context, say: 'I can identify this as " + scientific_name + ", but I don't have specific detailed information about it.'")
                        prompt_parts.append("- DO NOT start responses with phrases like 'Based on the information I have', 'Based on the information in my knowledge base', 'According to my knowledge base', 'Based on the provided information', or any similar prefacing phrases")
                        prompt_parts.append("- DO NOT mention 'knowledge base', 'information I have', 'provided information', or similar phrases in your responses")
                        prompt_parts.append("- Start your responses directly with the answer or information - answer naturally as if you are an expert sharing knowledge directly")
                    else:
                        logger.warning(f"Image analysis - No RAG context found for scientific name: {scientific_name}")
                        prompt_parts.append("\n" + "="*80)
                        prompt_parts.append("NO KNOWLEDGE BASE CONTEXT AVAILABLE")
                        prompt_parts.append("="*80)
                        prompt_parts.append(f"\nIMPORTANT: The species was identified as {scientific_name}, but no relevant information was found for this scientific name.")
                        prompt_parts.append("You must inform the user that you can identify the species but don't have detailed information about it.")
                        prompt_parts.append("DO NOT make up detailed answers or use prior training knowledge.")
                        prompt_parts.append("Answer naturally without mentioning 'knowledge base' or similar phrases.")
                except Exception as e:
                    logger.error(f"Error getting RAG context: {e}")
            else:
                # No RAG services available or scientific name is UNKNOWN
                if scientific_name.upper() == "UNKNOWN":
                    logger.warning("Image analysis - Could not identify scientific name, proceeding without RAG context")
                    prompt_parts.append("\n" + "="*80)
                    prompt_parts.append("NO SPECIES IDENTIFICATION")
                    prompt_parts.append("="*80)
                    prompt_parts.append("\nIMPORTANT: Could not identify the scientific name from the image.")
                    prompt_parts.append("You can describe what you see in the image, but you cannot provide detailed information without identification.")
                elif not (self.rag_service_plant or self.rag_service_animal):
                    logger.warning("Image analysis - RAG services not available")
                    prompt_parts.append("\n" + "="*80)
                    prompt_parts.append("RAG SERVICES NOT AVAILABLE")
                    prompt_parts.append("="*80)
                    prompt_parts.append(f"\nIMPORTANT: The species was identified as {scientific_name}, but RAG services are not available.")
                    prompt_parts.append("You must inform the user that you can identify the species but don't have detailed information available.")

            # Add conversation context if available
            if conversation_context:
                context_messages = conversation_context[::-1]
                for msg in context_messages[-5:]:
                    text = msg.get("text", "")
                    is_bot = msg.get("isBot", False)
                    if text:
                        if is_bot:
                            prompt_parts.append(f"Assistant: {text}")
                        else:
                            user_name = msg.get("userName", "User")
                            prompt_parts.append(f"{user_name}: {text}")

            # Add user message/question if provided
            if user_message:
                prompt_parts.append(f"User: {user_message}")
            else:
                prompt_parts.append("User: Please identify this plant, animal, or insect and provide information about it.")

            prompt_parts.append("Assistant:")

            # Prepare image part for Gemini Vision (for final analysis)
            image_part = {
                "mime_type": image_mime_type,
                "data": image_data
            }

            # Combine image and prompt (Gemini Vision requires image first, then text)
            content_parts = [image_part] + prompt_parts

            # Generate response using Gemini Vision (same model, just with image input)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(content_parts)
            )

            # Extract text from response
            ai_response = response.text.strip() if response.text else "I'm sorry, I couldn't analyze this image. Please try again."

            logger.info(f"Generated image analysis response")
            return ai_response

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error analyzing image: {e}")

            if "404" in error_msg or "not found" in error_msg.lower():
                logger.error(f"Model '{self.model_name}' not available for vision. Please check your API key permissions.")
                self.model = None

            return f"I apologize, but I encountered an error analyzing the image. Please try again. Error: {str(e)[:100]}"


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_conversations: Dict[str, List[str]] = {}  # userId -> [conversationIds]

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")

    async def broadcast_to_conversation(self, message: dict, conversation_id: str, exclude_user: str = None):
        """Broadcast message to all users in a conversation"""
        conversation = await get_conversation(conversation_id)
        if not conversation:
            return

        participants = conversation.get("participants", [])
        for user_id in participants:
            if user_id != exclude_user and user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {user_id}: {e}")


manager = ConnectionManager()
ai_service = AIService()  # Initialize with Gemini AI


@app.get("/")
async def root():
    return {"message": "IntoTheWild Chat API", "status": "running"}


@app.post("/api/rag/index-plants")
async def index_plants():
    """Index plant data from JSON into Pinecone vector database"""
    if not RAG_AVAILABLE or not rag_service_plant:
        raise HTTPException(status_code=503, detail="RAG service not available")

    if not rag_service_plant.is_available():
        raise HTTPException(
            status_code=503,
            detail="RAG service not fully configured. Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and PINECONE_API_KEY environment variables."
        )

    try:
        # Get the path to the plant data JSON file
        script_dir = Path(__file__).parent
        json_file_path = script_dir / "rag" / "plantae_wikipedia_content.json"

        if not json_file_path.exists():
            raise HTTPException(status_code=404, detail=f"Plant data file not found: {json_file_path}")

        logger.info("Starting plant indexing process...")
        success = rag_service_plant.load_and_index_plants(str(json_file_path))

        if success:
            return {
                "message": "Plants indexed successfully",
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to index plants. Check logs for details.")

    except Exception as e:
        logger.error(f"Error indexing plants: {e}")
        raise HTTPException(status_code=500, detail=f"Error indexing plants: {str(e)}")


@app.post("/api/rag/index-animals")
async def index_animals():
    """Index animal data from JSON into Pinecone vector database"""
    if not RAG_AVAILABLE or not rag_service_animal:
        raise HTTPException(status_code=503, detail="Animal RAG service not available")

    if not rag_service_animal.is_available():
        raise HTTPException(
            status_code=503,
            detail="RAG service not fully configured. Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and PINECONE_API_KEY environment variables."
        )

    try:
        # Get the path to the animal data JSON file
        script_dir = Path(__file__).parent
        json_file_path = script_dir / "rag" / "animalia_wikipedia_content.json"

        if not json_file_path.exists():
            raise HTTPException(status_code=404, detail=f"Animal data file not found: {json_file_path}")

        logger.info("Starting animal indexing process...")
        success = rag_service_animal.load_and_index_animals(str(json_file_path))

        if success:
            return {
                "message": "Animals indexed successfully",
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to index animals. Check logs for details.")

    except Exception as e:
        logger.error(f"Error indexing animals: {e}")
        raise HTTPException(status_code=500, detail=f"Error indexing animals: {str(e)}")


@app.get("/api/rag/status")
async def rag_status():
    """Get RAG service status for both plant and animal services"""
    if not RAG_AVAILABLE:
        return {
            "available": False,
            "message": "RAG service not available"
        }

    plant_status = {
        "available": rag_service_plant.is_available() if rag_service_plant else False,
        "index_name": rag_service_plant.index_name if rag_service_plant else None,
        "data_source": "Pinecone vector database"
    }

    animal_status = {
        "available": rag_service_animal.is_available() if rag_service_animal else False,
        "index_name": rag_service_animal.index_name if rag_service_animal else None,
        "animals_indexed": "N/A"  # Cache removed, all data in Pinecone
    }

    return {
        "plant": plant_status,
        "animal": animal_status,
        "message": "RAG services status"
    }

@app.get("/api/rag/test")
async def test_rag():
    """Test RAG service connectivity for both plant and animal services"""
    results = {
        "bedrock": {
            "available": False,
            "model": None,
            "test_embedding": None
        },
        "pinecone_plant": {
            "available": False,
            "index_name": None,
            "vector_count": None
        },
        "pinecone_animal": {
            "available": False,
            "index_name": None,
            "vector_count": None
        }
    }

    # Test Bedrock (using plant service as reference, both use same Bedrock)
    test_service = rag_service_plant or rag_service_animal
    if test_service and test_service.bedrock_runtime:
        try:
            test_embedding = test_service._generate_embedding("test", input_type="search_query")
            results["bedrock"] = {
                "available": True,
                "model": test_service.embedding_model,
                "test_embedding": f"Generated ({len(test_embedding)} dimensions)" if test_embedding else "Failed"
            }
        except Exception as e:
            results["bedrock"]["error"] = str(e)

    # Test Pinecone Plant Index
    if rag_service_plant and rag_service_plant.index:
        try:
            stats = rag_service_plant.index.describe_index_stats()
            results["pinecone_plant"] = {
                "available": True,
                "index_name": rag_service_plant.index_name,
                "vector_count": stats.total_vector_count,
                "dimension": stats.dimension
            }
        except Exception as e:
            results["pinecone_plant"]["error"] = str(e)

    # Test Pinecone Animal Index
    if rag_service_animal and rag_service_animal.index:
        try:
            stats = rag_service_animal.index.describe_index_stats()
            results["pinecone_animal"] = {
                "available": True,
                "index_name": rag_service_animal.index_name,
                "vector_count": stats.total_vector_count,
                "dimension": stats.dimension
            }
        except Exception as e:
            results["pinecone_animal"]["error"] = str(e)

    return results

@app.post("/api/users/register")
async def register_user(request: RegisterUserRequest):
    """Register a new user"""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "createdAt": datetime.utcnow().isoformat()
    }

    # Save to database
    if db:
        db.collection("users").document(user_id).set(user)
    else:
        users[user_id] = user

    return user


@app.post("/api/auth/google")
async def google_auth(request: dict = Body(...)):
    """Authenticate user with Google OAuth"""
    id_token_str = request.get("idToken")
    access_token_str = request.get("accessToken")

    # Handle None, empty string, or missing values
    id_token_str = id_token_str if id_token_str and str(id_token_str).strip() else None
    access_token_str = access_token_str if access_token_str and str(access_token_str).strip() else None

    if not id_token_str and not access_token_str:
        raise HTTPException(status_code=400, detail="ID token or access token is required")

    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID environment variable."
            )

        # Try to use ID token first (preferred method)
        if id_token_str:
            # Verify the ID token
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
            # Extract user info from ID token
            google_id = idinfo.get("sub")
            email = idinfo.get("email")
            name = idinfo.get("name", email.split("@")[0] if email else "User")
            picture = idinfo.get("picture")
        elif access_token_str:
            # Fallback: Use access token to get user info from Google API
            userinfo_response = http_requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token_str}"}
            )
            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid access token"
                )
            userinfo = userinfo_response.json()
            google_id = userinfo.get("id")
            email = userinfo.get("email")
            name = userinfo.get("name", email.split("@")[0] if email else "User")
            picture = userinfo.get("picture")
        else:
            raise HTTPException(status_code=400, detail="ID token or access token is required")

        # Check if user exists (by email or Google ID)
        user = None
        user_id = None

        if db:
            # Check Firebase for existing user
            users_ref = db.collection("users")
            # Try to find by email first
            if email:
                email_query = users_ref.where("email", "==", email).limit(1).stream()
                for doc in email_query:
                    user = doc.to_dict()
                    user_id = doc.id
                    break

            # If not found, try to find by Google ID
            if not user:
                google_id_query = users_ref.where("googleId", "==", google_id).limit(1).stream()
                for doc in google_id_query:
                    user = doc.to_dict()
                    user_id = doc.id
                    break
        else:
            # In-memory: search by email or Google ID
            for uid, u in users.items():
                if u.get("email") == email or u.get("googleId") == google_id:
                    user = u.copy()
                    user_id = uid
                    break

        # Create or update user
        if user:
            # Update user info
            updates = {
                "email": email,
                "username": name,
                "googleId": google_id,
                "picture": picture,
                "lastLoginAt": datetime.utcnow().isoformat()
            }
            if db:
                db.collection("users").document(user_id).update(updates)
            else:
                users[user_id].update(updates)
            user.update(updates)
            user["id"] = user_id
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            user = {
                "id": user_id,
                "username": name,
                "email": email,
                "googleId": google_id,
                "picture": picture,
                "createdAt": datetime.utcnow().isoformat(),
                "lastLoginAt": datetime.utcnow().isoformat()
            }

            if db:
                db.collection("users").document(user_id).set(user)
            else:
                users[user_id] = user

        return user

    except ValueError as e:
        # Invalid token
        logger.error(f"Invalid Google token: {e}")
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user information"""
    if db:
        doc = db.collection("users").document(user_id).get()
        return doc.to_dict() if doc.exists else None
    else:
        return users.get(user_id)


@app.post("/api/conversations")
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation (1-to-1 or group) or return existing one-to-one conversation"""
    # For one-to-one conversations, check if a conversation already exists between these participants
    if request.type == "one_to_one" and len(request.participantIds) == 2:
        existing_conv = await find_conversation_by_participants(request.participantIds, "one_to_one")
        if existing_conv:
            logger.info(f"Found existing one-to-one conversation: {existing_conv['id']}")
            return existing_conv

    # Create new conversation
    conversation_id = str(uuid.uuid4())
    conversation = {
        "id": conversation_id,
        "name": request.name,
        "type": request.type,
        "participants": request.participantIds,
        "createdAt": datetime.utcnow().isoformat(),
        "hasBot": False
    }

    await save_conversation(conversation)

    # If it's a group, broadcast to all connected users so they can see it
    if request.type == "group":
        group_created_message = {
            "type": "group_created",
            "conversation": conversation
        }
        # Broadcast to all connected users
        for user_id in manager.active_connections.keys():
            await manager.send_personal_message(group_created_message, user_id)

    return conversation


@app.get("/api/conversations/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    """Get conversation details"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/conversations/{conversation_id}/messages")
async def get_messages_endpoint(conversation_id: str, limit: int = 50):
    """Get messages for a conversation"""
    messages = await get_messages(conversation_id, limit)
    return {"messages": messages}


@app.post("/api/images/upload")
async def upload_image(
    imageBase64: str = Body(..., description="Base64 encoded image"),
    imageMimeType: str = Body(..., description="MIME type of the image (e.g., image/jpeg)"),
    conversationId: str = Body(..., description="Conversation ID for organizing images")
):
    """Upload image to Firebase Storage and return download URL"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(imageBase64)

        # Generate unique filename
        file_extension = "jpg"
        if "png" in imageMimeType:
            file_extension = "png"
        elif "webp" in imageMimeType:
            file_extension = "webp"
        elif "gif" in imageMimeType:
            file_extension = "gif"

        filename = f"chat_images/{conversationId}/{uuid.uuid4()}.{file_extension}"

        if FIREBASE_AVAILABLE and db:
            try:
                # Get Firebase Storage bucket
                bucket = storage.bucket()
                blob = bucket.blob(filename)

                # Upload image data
                blob.upload_from_string(image_data, content_type=imageMimeType)

                # Make the blob publicly accessible
                blob.make_public()

                # Get public URL
                image_url = blob.public_url

                logger.info(f"Image uploaded successfully: {filename}")
                return {"imageUrl": image_url, "success": True}
            except Exception as e:
                logger.error(f"Firebase Storage upload failed: {e}")
                # Fallback: return data URL if Firebase Storage fails
                data_url = f"data:{imageMimeType};base64,{imageBase64}"
                return {"imageUrl": data_url, "success": False, "error": str(e)}
        else:
            # Fallback: return data URL if Firebase not available
            logger.warning("Firebase Storage not available, returning data URL")
            data_url = f"data:{imageMimeType};base64,{imageBase64}"
            return {"imageUrl": data_url, "success": False, "error": "Firebase Storage not configured"}

    except Exception as e:
        logger.error(f"Image upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@app.get("/api/conversations")
async def get_all_conversations(user_id: Optional[str] = Query(None, description="User ID to filter conversations")):
    """Get all conversations. For groups, return all groups. For one-to-one, return only user's conversations."""

    if db:
        # Get all conversations from Firebase
        convs_ref = db.collection("conversations")
        docs = convs_ref.stream()
        all_convs = [doc.to_dict() for doc in docs]
    else:
        # In-memory storage
        all_convs = list(conversations.values())

    # Filter: return all groups, but only one-to-one conversations where user is a participant
    if user_id:
        filtered_convs = [
            conv for conv in all_convs
            if conv.get("type") == "group" or (conv.get("type") == "one_to_one" and user_id in conv.get("participants", []))
        ]
    else:
        # If no user_id provided, return all groups only
        filtered_convs = [conv for conv in all_convs if conv.get("type") == "group"]

    return {"conversations": filtered_convs}


@app.post("/api/conversations/{conversation_id}/join")
async def join_group(conversation_id: str, user_id: str = Body(..., embed=True)):
    """Join a group conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("type") != "group":
        raise HTTPException(status_code=400, detail="Can only join group conversations")

    participants = conversation.get("participants", [])
    if user_id in participants:
        return {"message": "Already a member of this group", "conversation": conversation}

    # Add user to participants
    participants.append(user_id)
    await update_conversation(conversation_id, {"participants": participants})

    # Update local conversation object
    conversation["participants"] = participants

    # Broadcast join event to all group members
    join_message = {
        "type": "user_joined_group",
        "conversationId": conversation_id,
        "userId": user_id,
        "conversation": conversation
    }
    await manager.broadcast_to_conversation(join_message, conversation_id)

    return {"message": "Successfully joined group", "conversation": conversation}


@app.post("/api/conversations/{conversation_id}/leave")
async def leave_group(conversation_id: str, user_id: str = Body(..., embed=True)):
    """Leave a group conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("type") != "group":
        raise HTTPException(status_code=400, detail="Can only leave group conversations")

    participants = conversation.get("participants", [])
    if user_id not in participants:
        raise HTTPException(status_code=400, detail="User is not a member of this group")

    # Remove user from participants
    participants = [p for p in participants if p != user_id]
    await update_conversation(conversation_id, {"participants": participants})

    # Update local conversation object
    conversation["participants"] = participants

    # Broadcast leave event to all group members
    leave_message = {
        "type": "user_left_group",
        "conversationId": conversation_id,
        "userId": user_id,
        "conversation": conversation
    }
    await manager.broadcast_to_conversation(leave_message, conversation_id)

    return {"message": "Successfully left group", "conversation": conversation}


@app.post("/api/conversations/{conversation_id}/add-bot")
async def add_bot_to_conversation(conversation_id: str):
    """Add AI bot to a conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("hasBot"):
        return {"message": "Bot already in conversation", "hasBot": True}

    await update_conversation(conversation_id, {"hasBot": True})

    # Notify all participants
    bot_message = {
        "type": "bot_added",
        "conversationId": conversation_id,
        "message": "AI Bot has been added to the conversation",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_conversation(bot_message, conversation_id)

    return {"message": "Bot added successfully", "hasBot": True}


@app.post("/api/conversations/{conversation_id}/remove-bot")
async def remove_bot_from_conversation(conversation_id: str):
    """Remove AI bot from a conversation"""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not conversation.get("hasBot"):
        return {"message": "Bot not in conversation", "hasBot": False}

    await update_conversation(conversation_id, {"hasBot": False})

    # Notify all participants
    bot_message = {
        "type": "bot_removed",
        "conversationId": conversation_id,
        "message": "AI Bot has been removed from the conversation",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_conversation(bot_message, conversation_id)

    return {"message": "Bot removed successfully", "hasBot": False}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time messaging"""
    await manager.connect(websocket, user_id)

    # Ping interval in seconds
    PING_INTERVAL = 30
    last_pong_time = asyncio.get_event_loop().time()

    async def send_ping():
        """Send periodic ping to keep connection alive"""
        nonlocal last_pong_time
        while True:
            try:
                await asyncio.sleep(PING_INTERVAL)

                # Check if we've received a pong recently
                current_time = asyncio.get_event_loop().time()
                time_since_pong = current_time - last_pong_time

                if time_since_pong > PING_INTERVAL * 2:
                    logger.warning(f"No pong received from {user_id} for {time_since_pong}s - closing connection")
                    await websocket.close()
                    break

                # Send ping
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.debug(f"Ping sent to user {user_id}")
            except Exception as e:
                logger.error(f"Error sending ping to {user_id}: {e}")
                break

    # Start ping task
    ping_task = asyncio.create_task(send_ping())

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            # Handle pong response - update last pong time and send acknowledgment
            if message_type == "pong":
                last_pong_time = asyncio.get_event_loop().time()
                logger.debug(f"Pong received from user {user_id}")
                # Send acknowledgment back so client knows server is alive
                await websocket.send_json({
                    "type": "pong_ack",
                    "timestamp": datetime.utcnow().isoformat()
                })
                continue

            # Handle ping from client
            if message_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.debug(f"Pong sent to user {user_id}")
                continue

            if message_type == "send_message":
                # Handle new message
                message_text = data.get("text", "").strip()
                conversation_id = data.get("conversationId")

                if not message_text or not conversation_id:
                    continue

                # Check if user is a participant in the conversation
                conversation = await get_conversation(conversation_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    continue

                participants = conversation.get("participants", [])
                if user_id not in participants:
                    logger.warning(f"User {user_id} is not a participant in conversation {conversation_id}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "You are not a member of this conversation. Please join the group first."
                    }, user_id)
                    continue

                # Check for /bot command
                if message_text.startswith("/bot"):
                    # Extract the query part (everything after "/bot")
                    query_part = message_text[4:].strip()  # Remove "/bot" and any leading/trailing spaces

                    # Add bot to conversation if not already added
                    if not conversation.get("hasBot"):
                        await update_conversation(conversation_id, {"hasBot": True})

                        # Send notification
                        notification = {
                            "type": "bot_added",
                            "conversationId": conversation_id,
                            "message": "AI Bot has been added to the conversation",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await manager.broadcast_to_conversation(notification, conversation_id)

                    # If there's a query after "/bot", process it as a message to the bot
                    if query_part:
                        # Update message_text to be the query part for bot processing
                        message_text = query_part
                        # Continue to normal message flow below, which will trigger bot response
                    else:
                        # Just "/bot" with no query, so just add bot and stop
                        continue

                # Check for /chat command
                if message_text == "/chat":
                    # Remove bot from conversation
                    if conversation.get("hasBot"):
                        await update_conversation(conversation_id, {"hasBot": False})

                        # Send notification
                        notification = {
                            "type": "bot_removed",
                            "conversationId": conversation_id,
                            "message": "AI Bot has been removed from the conversation",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await manager.broadcast_to_conversation(notification, conversation_id)
                    continue

                # Create message
                message = {
                    "id": str(uuid.uuid4()),
                    "text": message_text,
                    "userId": user_id,
                    "userName": data.get("userName", "User"),
                    "conversationId": conversation_id,
                    "createdAt": datetime.utcnow().isoformat(),
                    "isBot": False,
                    "type": "text"
                }

                # Include clientMessageId if provided (for matching optimistic messages)
                client_message_id = data.get("clientMessageId")
                if client_message_id:
                    message["clientMessageId"] = client_message_id

                # Save message
                await save_message(message)

                # Broadcast to conversation participants
                await manager.broadcast_to_conversation({
                    "type": "new_message",
                    "message": message
                }, conversation_id, exclude_user=user_id)

                # Send confirmation to sender (include clientMessageId for matching)
                confirmation_message = {
                    "type": "message_sent",
                    "message": message
                }
                await manager.send_personal_message(confirmation_message, user_id)

                # Check if bot is in conversation and generate response
                conversation = await get_conversation(conversation_id)
                if conversation and conversation.get("hasBot"):
                    # Get recent messages for context
                    recent_messages = await get_messages(conversation_id, limit=10)

                    # Generate AI response
                    ai_response_text = await ai_service.generate_response(message_text, recent_messages)

                    # Create bot message
                    bot_message = {
                        "id": str(uuid.uuid4()),
                        "text": ai_response_text,
                        "userId": "bot",
                        "userName": "AI Bot",
                        "conversationId": conversation_id,
                        "createdAt": datetime.utcnow().isoformat(),
                        "isBot": True,
                        "type": "text"
                    }

                    # Save bot message
                    await save_message(bot_message)

                    # Broadcast bot response
                    await manager.broadcast_to_conversation({
                        "type": "new_message",
                        "message": bot_message
                    }, conversation_id)

            elif message_type == "send_image":
                # Handle image message
                conversation_id = data.get("conversationId")
                image_url = data.get("imageUrl")  # Preferred: Firebase Storage URL
                image_base64 = data.get("imageBase64")  # Fallback: base64 data
                image_mime_type = data.get("imageMimeType", "image/jpeg")
                user_message = data.get("text", "").strip()  # Optional text with image

                if not conversation_id:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Conversation ID is required"
                    }, user_id)
                    continue

                # Check if user is a participant
                conversation = await get_conversation(conversation_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    continue

                participants = conversation.get("participants", [])
                if user_id not in participants:
                    logger.warning(f"User {user_id} is not a participant in conversation {conversation_id}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "You are not a member of this conversation."
                    }, user_id)
                    continue

                try:
                    # If imageUrl is provided, use it directly (already uploaded to Firebase Storage)
                    # Otherwise, if imageBase64 is provided, upload it first
                    if image_url:
                        # Image already uploaded, use the provided URL
                        final_image_url = image_url
                    elif image_base64:
                        # Upload base64 image to Firebase Storage
                        try:
                            # Decode base64 image
                            image_data = base64.b64decode(image_base64)

                            # Generate unique filename
                            file_extension = "jpg"
                            if "png" in image_mime_type:
                                file_extension = "png"
                            elif "webp" in image_mime_type:
                                file_extension = "webp"
                            elif "gif" in image_mime_type:
                                file_extension = "gif"

                            filename = f"chat_images/{conversation_id}/{uuid.uuid4()}.{file_extension}"

                            if FIREBASE_AVAILABLE and db:
                                try:
                                    # Get Firebase Storage bucket
                                    bucket = storage.bucket()
                                    blob = bucket.blob(filename)

                                    # Upload image data
                                    blob.upload_from_string(image_data, content_type=image_mime_type)

                                    # Make the blob publicly accessible
                                    blob.make_public()

                                    # Get public URL
                                    final_image_url = blob.public_url
                                    logger.info(f"Image uploaded to Firebase Storage: {filename}")
                                except Exception as e:
                                    logger.error(f"Firebase Storage upload failed: {e}")
                                    # Fallback to data URL
                                    final_image_url = f"data:{image_mime_type};base64,{image_base64}"
                            else:
                                # Fallback to data URL if Firebase not available
                                final_image_url = f"data:{image_mime_type};base64,{image_base64}"
                        except Exception as e:
                            logger.error(f"Error processing image: {e}")
                            await manager.send_personal_message({
                                "type": "error",
                                "message": f"Failed to process image: {str(e)}"
                            }, user_id)
                            continue
                    else:
                        await manager.send_personal_message({
                            "type": "error",
                            "message": "Either imageUrl or imageBase64 is required"
                        }, user_id)
                        continue

                    # Create image message with Firebase Storage URL or data URL
                    image_message = {
                        "id": str(uuid.uuid4()),
                        "text": user_message if user_message else "📷 Image",
                        "userId": user_id,
                        "userName": data.get("userName", "User"),
                        "conversationId": conversation_id,
                        "createdAt": datetime.utcnow().isoformat(),
                        "isBot": False,
                        "type": "image",
                        "imageUrl": final_image_url  # Firebase Storage URL or data URL fallback
                    }

                    # Include clientMessageId if provided
                    client_message_id = data.get("clientMessageId")
                    if client_message_id:
                        image_message["clientMessageId"] = client_message_id

                    # Save message
                    await save_message(image_message)

                    # Broadcast to conversation participants
                    await manager.broadcast_to_conversation({
                        "type": "new_message",
                        "message": image_message
                    }, conversation_id, exclude_user=user_id)

                    # Send confirmation to sender
                    await manager.send_personal_message({
                        "type": "message_sent",
                        "message": image_message
                    }, user_id)

                    # If bot is in conversation, analyze the image
                    conversation = await get_conversation(conversation_id)
                    if conversation and conversation.get("hasBot"):
                        # Get recent messages for context
                        recent_messages = await get_messages(conversation_id, limit=10)

                        # Analyze image with Gemini Vision
                        analysis_text = await ai_service.analyze_image(
                            image_data=image_data,
                            image_mime_type=image_mime_type,
                            user_message=user_message if user_message else "",
                            conversation_context=recent_messages
                        )

                        # Create bot response message
                        bot_message = {
                            "id": str(uuid.uuid4()),
                            "text": analysis_text,
                            "userId": "bot",
                            "userName": "AI Bot",
                            "conversationId": conversation_id,
                            "createdAt": datetime.utcnow().isoformat(),
                            "isBot": True,
                            "type": "text"
                        }

                        # Save bot message
                        await save_message(bot_message)

                        # Broadcast bot response
                        await manager.broadcast_to_conversation({
                            "type": "new_message",
                            "message": bot_message
                        }, conversation_id)

                except Exception as e:
                    logger.error(f"Error processing image message: {e}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Error processing image: {str(e)}"
                    }, user_id)

            elif message_type == "join_conversation":
                # User joining a conversation
                conversation_id = data.get("conversationId")
                if conversation_id:
                    # Send recent messages
                    recent_messages = await get_messages(conversation_id, limit=50)
                    await manager.send_personal_message({
                        "type": "conversation_history",
                        "conversationId": conversation_id,
                        "messages": recent_messages
                    }, user_id)

            elif message_type == "get_all_groups":
                # User requesting all available groups
                # Get all conversations from database
                if db:
                    convs_ref = db.collection("conversations")
                    docs = convs_ref.stream()
                    all_convs = [doc.to_dict() for doc in docs]
                else:
                    all_convs = list(conversations.values())

                # Filter: return all groups, but only one-to-one conversations where user is a participant
                filtered_convs = [
                    conv for conv in all_convs
                    if conv.get("type") == "group" or (conv.get("type") == "one_to_one" and user_id in conv.get("participants", []))
                ]

                await manager.send_personal_message({
                    "type": "all_groups",
                    "conversations": filtered_convs
                }, user_id)

    except WebSocketDisconnect:
        ping_task.cancel()
        manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        ping_task.cancel()
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

