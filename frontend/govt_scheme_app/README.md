# AI-Powered Government Scheme Fulfillment Engine - Frontend

Flutter frontend for the citizen authentication and profile module.

This app connects only to the backend endpoints that currently exist:

- `GET /health`
- `GET /version`
- `GET /info`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `PUT /auth/profile`
- `PUT /auth/change-password`
- `POST /auth/logout`

It does not call any fake scheme, eligibility, recommendation, application, notification, or admin APIs.

## Tech Stack

- Flutter
- Material 3
- Provider
- Dio
- SharedPreferences

## Project Structure

The frontend is organized under `lib/` with these main areas:

- `core/` - constants, networking, storage, theme, utilities, reusable widgets
- `models/` - request and response models
- `repositories/` - backend data access
- `providers/` - app state management
- `screens/` - splash, auth, home, profile, and settings screens
- `routes/` - named route handling

## Configure Backend URL

The app uses `http://10.80.26.147:8000` first on Android, then falls back to `http://10.0.2.2:8000`, `http://127.0.0.1:8000`, and `http://localhost:8000`. Desktop/web still use `http://localhost:8000`.

To override it, run Flutter with a compile-time define:

```bash
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

If your backend runs on another host or port, replace the value accordingly. For a physical Android device connected over USB debugging, either:

```bash
adb reverse tcp:8000 tcp:8000
flutter run -d <your-device-id>
```

or point `API_BASE_URL` at the host machine's LAN IP, for example `http://10.80.26.147:8000`.

## Run the App

From the Flutter project root:

```bash
flutter pub get
flutter run
```

For a custom backend URL:

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

If Android Studio is launching an emulator, the app will fall back to the emulator-safe host automatically.

## What the App Includes

- Splash screen with backend health check
- Login and registration forms with client-side validation
- JWT token storage and refresh handling
- Protected home screen
- Citizen profile view
- Edit profile screen
- Change password screen
- Logout flow
- Backend status, version, and info display

## Notes

- Authenticated pages are protected by the current session state.
- Access tokens are refreshed automatically when possible.
- If refresh fails, the app clears local session data and returns to login.
- The frontend is ready for future scheme modules once the backend exposes them.

## Testing

Run the smoke test:

```bash
flutter test
```

## Validation

The project currently passes:

- `flutter analyze`
- `flutter test`
