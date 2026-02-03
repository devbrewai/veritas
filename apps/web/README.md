# Veritas Web

Next.js frontend for the Veritas KYC/AML automation platform with Better Auth authentication.

## Quick Start

```bash
# Install dependencies
bun install

# Run development server
bun dev
```

The app will be available at `http://localhost:3000`.

## Prerequisites

- Node.js 18+ or Bun
- PostgreSQL (shared with API via `DATABASE_URL`)

## Environment Variables

Create a `.env.local` file:

```bash
# Database (required - shared with API)
DATABASE_URL=postgres://postgres:postgres@localhost:5432/veritas

# Better Auth (required)
BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_SECRET=your-secret-key-min-32-chars

# Optional
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Authentication

This app uses [Better Auth](https://www.better-auth.com) with the JWT plugin for authentication:

- **Email/Password**: Users register and login with email + password
- **JWT Tokens**: Issued via the `/api/auth/token` endpoint
- **JWKS**: Public keys available at `/api/auth/jwks` for API validation

### Auth Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/auth/sign-up/email` | Register new user |
| `/api/auth/sign-in/email` | Login with email/password |
| `/api/auth/sign-out` | Logout |
| `/api/auth/token` | Get JWT token for API calls |
| `/api/auth/jwks` | JWKS endpoint for token validation |

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home page |
| `/login` | User login |
| `/register` | User registration |

## Project Structure

```
src/
├── app/
│   ├── api/auth/[...all]/   # Better Auth API handler
│   ├── login/               # Login page
│   ├── register/            # Registration page
│   └── page.tsx             # Home page
├── components/
│   ├── auth/                # Auth form components
│   └── ui/                  # shadcn/ui components
└── lib/
    ├── auth.ts              # Better Auth server config
    └── auth-client.ts       # Better Auth React client
```

## Using with the API

1. Register/login to get authenticated
2. Get a JWT token via the auth client
3. Include the token in API requests:

```typescript
import { authClient } from '@/lib/auth-client';

const token = await authClient.token();

const response = await fetch('http://localhost:8000/v1/documents/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData,
});
```

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Auth**: Better Auth with JWT plugin
- **Database**: PostgreSQL (via pg driver)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (Radix primitives)
- **Package Manager**: Bun

## Development

```bash
# Run dev server
bun dev

# Build for production
bun build

# Start production server
bun start

# Lint
bun lint
```
