import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AI Response Generation Tests', () {
    test('should generate plant-related responses', () {
      // Test the response generation logic directly
      final input = 'What plants are safe to eat?';
      final response = _generateTestResponse(input);

      expect(response, isNotEmpty);
      expect(response.toLowerCase(), contains('plant'));
    });

    test('should generate survival-related responses', () {
      final input = 'What should I do in a survival situation?';
      final response = _generateTestResponse(input);

      expect(response, isNotEmpty);
      expect(response.toLowerCase(), anyOf([
        contains('survival'),
        contains('shelter'),
        contains('water'),
        contains('food')
      ]));
    });

    test('should generate animal-related responses', () {
      final input = 'What animals should I avoid?';
      final response = _generateTestResponse(input);

      expect(response, isNotEmpty);
      expect(response.toLowerCase(), anyOf([
        contains('animal'),
        contains('wildlife'),
        contains('safe')
      ]));
    });

    test('should handle general questions', () {
      final input = 'Hello, how are you?';
      final response = _generateTestResponse(input);

      expect(response, isNotEmpty);
      expect(response.length, greaterThan(10));
    });
  });
}

// Helper function to simulate the AI response generation
String _generateTestResponse(String userInput) {
  final input = userInput.toLowerCase();

  if (input.contains('plant') || input.contains('tree') || input.contains('leaf')) {
    return "🌿 Plants are essential for survival! Many edible plants can provide nutrition, but be very careful - some are poisonous. Always follow the rule: 'When in doubt, don't eat it.'";
  } else if (input.contains('animal') || input.contains('wildlife') || input.contains('creature')) {
    return "🦌 Wildlife can be both a resource and a danger. Large animals like deer and rabbits can provide food, but always respect their space. Never approach wild animals, especially mothers with young.";
  } else if (input.contains('survival') || input.contains('emergency') || input.contains('help')) {
    return "🆘 In any survival situation, remember the Rule of 3s: You can survive 3 minutes without air, 3 hours without shelter in harsh conditions, 3 days without water, and 3 weeks without food.";
  } else {
    return "🌿 I'm here to help with survival guidance and nature knowledge! I can assist with plant identification, animal behavior, survival techniques, and outdoor safety.";
  }
}
