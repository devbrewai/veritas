/**
 * Better Auth server configuration.
 *
 * This configures authentication with:
 * - Email/password authentication
 * - JWT plugin for API token generation
 * - PostgreSQL database (shared with FastAPI backend)
 */

import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || "postgres://postgres:postgres@localhost:5432/veritas",
});

export const auth = betterAuth({
  baseURL: process.env.BETTER_AUTH_URL || "http://localhost:3000",
  database: pool,
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
  },
  plugins: [
    jwt({
      // JWT configuration
      // Uses EdDSA (Ed25519) by default - most secure
      jwt: {
        expirationTime: "7d", // 7 day expiry
      },
    }),
  ],
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // Update session every 24 hours
  },
  trustedOrigins: [
    "http://localhost:3000",
    "http://localhost:8000", // FastAPI backend
  ],
});

export type Session = typeof auth.$Infer.Session;
