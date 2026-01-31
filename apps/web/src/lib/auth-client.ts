/**
 * Better Auth client configuration.
 *
 * Used in client components to interact with the auth API.
 */

import { createAuthClient } from "better-auth/react";
import { jwtClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  baseURL: "http://localhost:3000",
  plugins: [jwtClient()],
});

// Export commonly used hooks and functions
export const {
  signIn,
  signUp,
  signOut,
  useSession,
  getSession,
} = authClient;

// Export the token getter for API calls
export const getToken = async () => {
  const token = await authClient.token();
  return token.data?.token;
};
