# AI-Powered Government Scheme Fulfillment Engine - Flutter Frontend

Production-oriented Flutter citizen portal for the backend modules that exist today: authentication, citizen profile, mock DigiLocker, land records, documents, income, community/caste, and dashboard.

The app intentionally does not call scheme recommendation, eligibility, search, applications, notifications, AI recommendation, or admin APIs.

## Backend Endpoints Used

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
- `GET /citizen/dashboard`
- `GET /citizen/profile`
- `GET /citizen/profile/details`
- `PUT /citizen/profile`
- `GET /citizen/income`
- `GET /citizen/caste`
- `GET /citizen/land-records`
- `GET /citizen/documents`
- `GET /digilocker/status`
- `POST /digilocker/sync`
- `GET /digilocker/documents`
- `GET /digilocker/documents/{document_id}`

## Tech Stack

- Flutter with Material 3
- Provider for state management
- Dio with JWT and refresh-token interceptors
- SharedPreferences for token/profile persistence
- Responsive layouts with light and dark themes

## Project Structure

- `lib/core/constants/` - API paths and backend URL selection
- `lib/core/network/` - Dio API service and exception mapping
- `lib/core/services/` - local storage service
- `lib/core/theme/` - Material 3 theme definitions
- `lib/core/widgets/` - buttons, fields, cards, loading/error/empty states
- `lib/models/` - auth, system, citizen, document, land, DigiLocker models
- `lib/repositories/` - backend-facing data access classes
- `lib/providers/` - Auth, App, Dashboard, Citizen, DigiLocker state
- `lib/screens/` - splash, auth, dashboard, profile, documents, DigiLocker, settings
- `lib/routes/` - named route table and protected route wrapper

## Configure Backend URL

By default, Android tries `http://10.80.26.147:8000`, then emulator/local fallbacks. Desktop and web use `http://localhost:8000`.

Override the backend URL at launch:

```bash
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

For a physical Android device, either run:

```bash
adb reverse tcp:8000 tcp:8000
flutter run -d <device-id>
```

or pass your machine LAN URL:

```bash
flutter run --dart-define=API_BASE_URL=http://<host-lan-ip>:8000
```

## Run

```bash
flutter pub get
flutter run
```

## Included Flows

- Splash screen checks `GET /health`, then routes by token state.
- Login and registration store access and refresh tokens.
- Dio attaches `Authorization: Bearer <access_token>` automatically.
- A `401` response triggers `POST /auth/refresh` and retries the request.
- Dashboard displays profile completion, DigiLocker state, documents, land area, income, community, and farmer status.
- Profile, income, caste/community, land records, documents, DigiLocker status/sync, settings, logout, and password change are implemented.

## Verification

Run:

```bash
flutter analyze
flutter test
```
