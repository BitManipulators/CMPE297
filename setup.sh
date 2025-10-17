#!/bin/bash

echo "🌿 Setting up IntoTheWild Flutter App..."

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    echo "❌ Flutter is not installed. Please install Flutter first:"
    echo "   Visit: https://flutter.dev/docs/get-started/install"
    echo "   Or use: brew install --cask flutter"
    exit 1
fi

echo "✅ Flutter found: $(flutter --version | head -n 1)"

# Check Flutter doctor
echo "🔍 Running Flutter doctor..."
flutter doctor

# Get dependencies
echo "📦 Getting Flutter dependencies..."
flutter pub get

# Generate code (if needed)
echo "🔧 Generating code..."
flutter packages pub run build_runner build --delete-conflicting-outputs

# Check for any issues
echo "🔍 Running Flutter analyze..."
flutter analyze

echo "✅ Setup complete!"
echo ""
echo "To run the app:"
echo "  flutter run"
echo ""
echo "To run on a specific device:"
echo "  flutter devices"
echo "  flutter run -d <device-id>"