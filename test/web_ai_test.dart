import 'package:flutter_test/flutter_test.dart';
import 'package:into_the_wild/services/ai_model_service_web.dart';

void main() {
  group('Web AI Model Service Tests', () {
    late AIModelServiceWeb aiModelService;

    setUp(() {
      aiModelService = AIModelServiceWeb();
    });

    test('should initialize model service', () async {
      expect(aiModelService.isInitialized, false);
      expect(aiModelService.isLoading, false);
    });

    test('should generate plant-related responses', () async {
      final response = await aiModelService.generateResponse('What plants are safe to eat?');
      expect(response, isNotEmpty);
      expect(response.toLowerCase(), contains('plant'));
    });

    test('should generate survival-related responses', () async {
      final response = await aiModelService.generateResponse('What should I do in a survival situation?');
      expect(response, isNotEmpty);
      expect(response.toLowerCase(), anyOf([
        contains('survival'),
        contains('shelter'),
        contains('water'),
        contains('food')
      ]));
    });

    test('should generate animal-related responses', () async {
      final response = await aiModelService.generateResponse('What animals should I avoid?');
      expect(response, isNotEmpty);
      expect(response.toLowerCase(), anyOf([
        contains('animal'),
        contains('wildlife'),
        contains('safe')
      ]));
    });

    test('should handle general questions', () async {
      final response = await aiModelService.generateResponse('Hello, how are you?');
      expect(response, isNotEmpty);
      expect(response.length, greaterThan(10));
    });
  });
}
