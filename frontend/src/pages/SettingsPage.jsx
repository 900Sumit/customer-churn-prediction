import { useEffect, useState } from "react";
import { CheckCircle2, Monitor } from "lucide-react";
import { health, readiness, apiMessage } from "../services/apiClient";

export default function SettingsPage({ clerkEnabled }) {
  const [status, setStatus] = useState("checking");
  const [message, setMessage] = useState("Checking API health…");
  const [persistence, setPersistence] = useState({ status: "checking", message: "Checking database readiness…" });
  useEffect(() => {
    Promise.all([health(), readiness()])
      .then(([response, readyResponse]) => {
        setStatus(response.data.status === "healthy" ? "healthy" : "error");
        setMessage(
          response.data.status === "healthy"
            ? "FastAPI is healthy and models are loaded."
            : "The API returned an unexpected health state.",
        );
        const ready = readyResponse.data;
        if (ready.status === "ready") {
          setPersistence({ status: "ready", message: "Neon is reachable and authentication configuration is complete." });
        } else if (!ready.database?.configured) {
          setPersistence({ status: "not_ready", message: "Neon persistence is not configured on the backend." });
        } else if (!ready.database?.reachable) {
          setPersistence({ status: "not_ready", message: "Neon is configured but the database connection is unavailable." });
        } else {
          setPersistence({ status: "not_ready", message: "Neon is reachable, but Clerk issuer/audience verification configuration is incomplete." });
        }
      })
      .catch((error) => {
        setStatus("error");
        setMessage(apiMessage(error));
        setPersistence({ status: "not_ready", message: "Readiness could not be checked because the API is unavailable." });
      });
  }, []);
  return (
    <div>
      <div className="mb-8">
        <p className="eyebrow">Workspace settings</p>
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">
          Inspect connected services and account configuration.
        </p>
      </div>
      <div className="grid lg:grid-cols-2 gap-5">
        <div className="section-card">
          <div className="flex gap-3 items-start">
            <Monitor className="text-primary shrink-0" />
            <div>
              <h2 className="text-xl font-bold">Appearance</h2>
              <p className="text-sm text-base-content/60 mt-2">
                Use the single Light, Dark, or System selector in the top
                header. Your choice is saved automatically.
              </p>
            </div>
          </div>
        </div>
        <div className="section-card">
          <h2 className="text-xl font-bold">System status</h2>
          <div className="flex items-start gap-3 mt-5">
            <span
              className={`status-dot mt-1 ${status === "error" ? "bg-error" : "bg-success"}`}
            />
            <div>
              <p className="font-semibold">FastAPI connection</p>
              <p className="text-sm text-base-content/60 mt-1">{message}</p>
            </div>
          </div>
          <div className="divider" />
          <p className="text-sm">
            <b>Authentication:</b>{" "}
            {clerkEnabled
              ? "Clerk is configured. Use the avatar in the header to manage your account or sign out."
              : "Not configured; add a valid VITE_CLERK_PUBLISHABLE_KEY."}
          </p>
          <p className="text-sm mt-3">
            <b>Persistence:</b> {persistence.message}
          </p>
          <div className="flex gap-2 items-center text-xs text-base-content/50 mt-6">
            {/* <CheckCircle2 size={14} /> No secrets are displayed in this */}
            {/* interface. */}
          </div>
        </div>
      </div>
    </div>
  );
}
