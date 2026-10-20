import { Link } from "react-router-dom";
import { SignIn } from "@clerk/clerk-react";
import { authUrls } from "../constants/auth";
export default function SignInPage({ clerkEnabled }) {
  return (
    <div className="min-h-screen grid place-items-center p-6 bg-base-200">
      <div>
        {clerkEnabled ? (
          <SignIn
            routing="path"
            path="/sign-in"
            signUpUrl={authUrls.signUp}
            forceRedirectUrl={authUrls.dashboard}
            fallbackRedirectUrl={authUrls.dashboard}
          />
        ) : (
          <div className="section-card max-w-md">
            <p className="eyebrow">Authentication setup</p>
            <h1 className="text-2xl font-bold">Clerk is not configured</h1>
            <p className="text-sm text-base-content/60 mt-3">
              Add VITE_CLERK_PUBLISHABLE_KEY to frontend/.env and restart Vite
              to enable sign-in.
            </p>
            <Link to="/" className="btn btn-primary mt-6">
              Back home
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
