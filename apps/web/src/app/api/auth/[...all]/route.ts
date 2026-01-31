/**
 * Better Auth API route handler.
 *
 * This catch-all route handles all auth-related API requests:
 * - POST /api/auth/sign-up/email - User registration
 * - POST /api/auth/sign-in/email - User login
 * - GET /api/auth/session - Get current session
 * - GET /api/auth/jwks - JSON Web Key Set for JWT validation
 * - GET /api/auth/token - Get JWT token for API calls
 */

import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { POST, GET } = toNextJsHandler(auth);
