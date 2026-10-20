import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider, useAuth } from "@clerk/clerk-react";
import App from "./App";
import { ThemeProvider } from "./context/ThemeContext";
import { PredictionProvider } from "./context/PredictionContext";
import "./styles/index.css";
import { setTokenGetter } from "./services/apiClient";
import { authUrls } from "./constants/auth";

const key = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY?.trim();
// The value in .env.example is intentionally a placeholder. Do not mount
// Clerk until a real publishable key is configured, otherwise Clerk throws
// before React can render the application.
const clerkEnabled = Boolean(key && /^(pk_test_|pk_live_)/.test(key));
const app = (
  <BrowserRouter>
    <ThemeProvider>
      <PredictionProvider>
        <App clerkEnabled={clerkEnabled} />
      </PredictionProvider>
    </ThemeProvider>
  </BrowserRouter>
);

function AuthTokenBridge({ children }) {
  const { getToken } = useAuth();
  setTokenGetter(getToken);
  return children;
}

createRoot(document.getElementById("root")).render(
  clerkEnabled ? (
    <ClerkProvider
      publishableKey={key}
      signInUrl={authUrls.signIn}
      signUpUrl={authUrls.signUp}
      signInForceRedirectUrl={authUrls.dashboard}
      signUpForceRedirectUrl={authUrls.dashboard}
      signInFallbackRedirectUrl={authUrls.dashboard}
      signUpFallbackRedirectUrl={authUrls.dashboard}
      afterSignOutUrl={authUrls.landing}
      allowedRedirectOrigins={[authUrls.origin]}
    >
      <AuthTokenBridge>{app}</AuthTokenBridge>
    </ClerkProvider>
  ) : (
    app
  ),
);
