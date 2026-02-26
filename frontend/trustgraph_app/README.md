# TrustGraph Flutter App

The mobile application for TrustGraph - a trust-weighted startup ecosystem platform.

## Features

- 🔐 **Authentication** - Secure login and registration
- 🔍 **Search** - Find investors, founders, and connectors
- 🤝 **Intro Requests** - Create and manage warm introductions
- 📊 **Path Visualization** - Visualize trust-weighted intro paths
- 👤 **Profile Management** - Manage your profile and trust network
- 🔔 **Real-time Notifications** - Stay updated on intro requests

## Getting Started

### Prerequisites

- Flutter SDK 3.x or higher
- Dart SDK 3.x or higher
- Android Studio / Xcode (for mobile development)

### Installation

1. Install Flutter dependencies:
```bash
cd frontend/trustgraph_app
flutter pub get
```

2. Configure API endpoint:
Edit `lib/core/config/api_config.dart` to point to your backend:
```dart
static const String baseUrl = 'http://your-backend-url:8000';
```

3. Run the app:
```bash
# For development
flutter run

# For specific device
flutter run -d <device-id>

# List available devices
flutter devices
```

### Build for Production

```bash
# Android
flutter build apk --release

# iOS
flutter build ios --release
```

## Project Structure

```
lib/
├── main.dart                   # App entry point
├── app.dart                    # App configuration
├── core/
│   ├── config/                 # Configuration files
│   ├── theme/                  # App theme
│   └── utils/                  # Utilities
├── data/
│   ├── models/                 # Data models
│   ├── repositories/           # Data repositories
│   └── providers/              # API clients
├── features/
│   ├── auth/                   # Authentication
│   ├── home/                   # Home feed
│   ├── search/                 # Search & discovery
│   ├── intros/                 # Intro requests
│   └── profile/                # User profile
└── shared/
    └── widgets/                # Reusable widgets
```

## Key Packages

- **provider** - State management
- **dio** - HTTP client
- **go_router** - Navigation
- **graphview** - Graph visualization
- **flutter_secure_storage** - Secure token storage

## Development

### Running Tests

```bash
flutter test
```

### Code Generation

If using code generation for models:
```bash
flutter pub run build_runner build
```

## API Integration

The app communicates with the TrustGraph backend via REST APIs:

- **Base URL**: `http://localhost:8000` (development)
- **Authentication**: JWT Bearer tokens
- **Main Endpoints**:
  - `/api/v1/users` - User management
  - `/api/v1/intros` - Intro requests
  - `/api/v1/paths/discover` - Path discovery
  - `/api/v1/search/users` - User search

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request
