abstract class AIModelInterface {
  bool get isInitialized;
  bool get isLoading;
  Future<bool> initializeModel();
  Future<String> generateResponse(String userInput);
  Future<void> dispose();
}
