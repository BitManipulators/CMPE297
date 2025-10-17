import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'ai_model_interface.dart';

class AIModelServiceWeb implements AIModelInterface {
  static final AIModelServiceWeb _instance = AIModelServiceWeb._internal();
  factory AIModelServiceWeb() => _instance;
  AIModelServiceWeb._internal();

  bool _isInitialized = false;
  bool _isLoading = false;

  bool get isInitialized => _isInitialized;
  bool get isLoading => _isLoading;

  Future<bool> initializeModel() async {
    if (_isInitialized) return true;

    _isLoading = true;

    try {
      // For web, we'll simulate model initialization
      // In a real implementation, you would load the model here
      await Future.delayed(const Duration(milliseconds: 500));

      _isInitialized = true;
      _isLoading = false;

      debugPrint('AI Model initialized successfully (Web Mode)');
      return true;
    } catch (e) {
      debugPrint('Error initializing AI model: $e');
      _isLoading = false;
      return false;
    }
  }

  Future<String> generateResponse(String userInput) async {
    if (!_isInitialized) {
      await initializeModel();
    }

    if (!_isInitialized) {
      return "I'm sorry, I couldn't initialize the AI model. Please try again later.";
    }

    try {
      // Generate intelligent response based on input
      return await _generateIntelligentResponse(userInput);
    } catch (e) {
      debugPrint('Error generating AI response: $e');
      return "I encountered an error while processing your request. Please try again.";
    }
  }

  Future<String> _generateIntelligentResponse(String userInput) async {
    // Simulate processing time for AI inference
    await Future.delayed(const Duration(milliseconds: 800));

    final input = userInput.toLowerCase();

    // Survival and nature-related responses
    if (input.contains('plant') || input.contains('tree') || input.contains('leaf')) {
      return _getPlantResponse(input);
    } else if (input.contains('animal') || input.contains('wildlife') || input.contains('creature')) {
      return _getAnimalResponse(input);
    } else if (input.contains('survival') || input.contains('emergency') || input.contains('help')) {
      return _getSurvivalResponse(input);
    } else if (input.contains('water') || input.contains('drink') || input.contains('thirsty')) {
      return _getWaterResponse(input);
    } else if (input.contains('food') || input.contains('eat') || input.contains('hungry')) {
      return _getFoodResponse(input);
    } else if (input.contains('shelter') || input.contains('camp') || input.contains('sleep')) {
      return _getShelterResponse(input);
    } else if (input.contains('weather') || input.contains('rain') || input.contains('storm')) {
      return _getWeatherResponse(input);
    } else if (input.contains('navigation') || input.contains('lost') || input.contains('direction')) {
      return _getNavigationResponse(input);
    } else if (input.contains('first aid') || input.contains('injury') || input.contains('hurt')) {
      return _getFirstAidResponse(input);
    } else {
      return _getGeneralResponse(input);
    }
  }

  String _getPlantResponse(String input) {
    final responses = [
      "🌿 Plants are essential for survival! Many edible plants can provide nutrition, but be very careful - some are poisonous. Always follow the rule: 'When in doubt, don't eat it.' Look for plants with simple, recognizable characteristics and avoid anything with milky sap, thorns, or unusual colors.",
      "🌱 For plant identification, look for key features: leaf shape, arrangement, and texture. Common edible plants include dandelions, clover, and cattails. Remember, proper identification is crucial for survival - never consume unknown plants.",
      "🍃 When foraging for plants, start with the most common and easily identifiable species. Dandelions are safe and nutritious, containing vitamins A, C, and K. Always test a small amount first and wait 24 hours before consuming more.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getAnimalResponse(String input) {
    final responses = [
      "🦌 Wildlife can be both a resource and a danger. Large animals like deer and rabbits can provide food, but always respect their space. Never approach wild animals, especially mothers with young. Use your knowledge of animal tracks and behavior for safety.",
      "🐾 Animal tracks can tell you a lot about what's in your area. Look for fresh tracks near water sources. Remember, most animals are more afraid of you than you are of them, but always maintain a safe distance.",
      "🦅 Birds can be excellent indicators of water sources and safe areas. Their flight patterns and calls can help you navigate and find resources. Some birds are also edible, but check local regulations first.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getSurvivalResponse(String input) {
    final responses = [
      "🆘 In any survival situation, remember the Rule of 3s: You can survive 3 minutes without air, 3 hours without shelter in harsh conditions, 3 days without water, and 3 weeks without food. Prioritize accordingly!",
      "⚡ Stay calm and assess your situation. Find or create shelter first, then locate water sources. Signal for help using mirrors, bright colors, or smoke. Make yourself visible and audible to rescuers.",
      "🎯 Your survival priorities should be: 1) Shelter, 2) Water, 3) Fire, 4) Food, 5) Signal for rescue. Focus on one thing at a time and don't panic - clear thinking saves lives.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getWaterResponse(String input) {
    final responses = [
      "💧 Water is your most critical need! Look for flowing water sources like streams and rivers. Avoid stagnant water if possible. Always purify water by boiling for at least 1 minute or using purification tablets.",
      "🌊 Collect rainwater using any available containers. Morning dew on plants can be collected with absorbent cloth. Remember: clear, flowing water is generally safer than still water.",
      "🔍 Signs of water nearby include: green vegetation, animal tracks leading downhill, and the sound of running water. Digging in dry riverbeds might reveal groundwater.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getFoodResponse(String input) {
    final responses = [
      "🍎 Foraging for food requires extreme caution. Start with easily identifiable plants like dandelions, clover, and cattails. Avoid mushrooms unless you're absolutely certain they're safe - many are deadly.",
      "🐟 If near water, fishing can provide protein. Look for shallow areas where fish might gather. Improvise fishing gear using available materials like sticks, string, and hooks made from thorns or wire.",
      "🪲 Insects can be a protein source in survival situations. Grasshoppers, crickets, and certain larvae are edible. Cook them thoroughly and avoid brightly colored insects, which are often poisonous.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getShelterResponse(String input) {
    final responses = [
      "🏠 Your shelter should protect you from wind, rain, and cold. Look for natural shelters like caves, fallen trees, or rock overhangs. If building, use available materials and make it just big enough for your body.",
      "🌲 A simple lean-to shelter can be made with a long branch propped against a tree and covered with leaves, branches, or a tarp. Make sure it's on high ground to avoid flooding.",
      "🔥 Build your shelter near a water source but not too close to avoid flooding. Consider wind direction and position your shelter opening away from prevailing winds.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getWeatherResponse(String input) {
    final responses = [
      "🌤️ Weather awareness is crucial for survival. Watch cloud formations - cumulus clouds often mean fair weather, while dark, towering clouds indicate storms. Red sky at night, sailor's delight; red sky in morning, sailors take warning.",
      "🌧️ If you see storm clouds approaching, seek shelter immediately. Avoid open areas, tall trees, and metal objects during lightning. Stay low and find a depression in the ground if caught in the open.",
      "❄️ In cold weather, focus on staying dry and warm. Wet clothing loses insulation value quickly. Use the layering system: base layer to wick moisture, insulation layer for warmth, and outer layer for protection.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getNavigationResponse(String input) {
    final responses = [
      "🧭 If you're lost, stop and stay put if possible. Use the sun's position to determine direction - it rises in the east and sets in the west. At noon, it's due south in the northern hemisphere.",
      "⭐ At night, use the North Star (Polaris) to find north. It's the last star in the handle of the Little Dipper. In the southern hemisphere, use the Southern Cross constellation.",
      "🌳 Natural navigation signs: moss often grows on the north side of trees, and tree branches are typically longer on the south side. However, these aren't always reliable, so use multiple methods.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getFirstAidResponse(String input) {
    final responses = [
      "🏥 In case of injury, stop any bleeding by applying direct pressure. Clean wounds with clean water if available. Keep injured areas elevated and immobilized. Seek professional medical help as soon as possible.",
      "🩹 For minor cuts and scrapes, clean the area and cover with clean cloth. Watch for signs of infection like redness, swelling, or pus. In survival situations, even small injuries can become serious without proper care.",
      "🚨 For serious injuries, prioritize stopping bleeding and maintaining body temperature. Use the RICE method for sprains: Rest, Ice, Compression, Elevation. Remember, your safety comes first - don't put yourself at risk to help others.",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  String _getGeneralResponse(String input) {
    final responses = [
      "🌿 I'm here to help with survival guidance and nature knowledge! I can assist with plant identification, animal behavior, survival techniques, and outdoor safety. What specific area would you like to learn about?",
      "🏕️ Whether you're planning a camping trip or facing a survival situation, I can provide practical advice on shelter, water, food, and safety. Feel free to ask about any outdoor or nature-related topic!",
      "🔍 I specialize in survival skills and nature identification. Ask me about plants, animals, weather patterns, navigation, or any outdoor safety concerns you might have. I'm here to help keep you safe in the wild!",
    ];
    return responses[DateTime.now().millisecond % responses.length];
  }

  Future<void> dispose() async {
    _isInitialized = false;
    _isLoading = false;
  }
}
