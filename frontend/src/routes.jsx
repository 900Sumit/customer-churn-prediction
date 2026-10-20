import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/Layout";
import LandingPage from "./pages/LandingPage";
import DashboardPage from "./pages/DashboardPage";
import SinglePredictionPage from "./pages/SinglePredictionPage";
import BatchPredictionPage from "./pages/BatchPredictionPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import HistoryPage from "./pages/HistoryPage";
import ModelPage from "./pages/ModelPage";
import SettingsPage from "./pages/SettingsPage";
import NotFoundPage from "./pages/NotFoundPage";
import SignInPage from "./pages/SignInPage";
import SignUpPage from "./pages/SignUpPage";
import { SignedIn, SignedOut } from "@clerk/clerk-react";
function Protected({ children, clerkEnabled }) {
  if (!clerkEnabled) return children;
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" replace />
      </SignedOut>
    </>
  );
}
export default function AppRoutes({ clerkEnabled }) {
  return (
    <Routes>
      <Route path="/" element={<LandingPage clerkEnabled={clerkEnabled} />} />
      <Route
        path="/sign-in/*"
        element={<SignInPage clerkEnabled={clerkEnabled} />}
      />
      <Route
        path="/sign-up/*"
        element={<SignUpPage clerkEnabled={clerkEnabled} />}
      />
      <Route
        element={
          <Protected clerkEnabled={clerkEnabled}>
            <AppLayout clerkEnabled={clerkEnabled} />
          </Protected>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/predict" element={<SinglePredictionPage />} />
        <Route path="/batch" element={<BatchPredictionPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/model" element={<ModelPage />} />
        <Route
          path="/settings"
          element={<SettingsPage clerkEnabled={clerkEnabled} />}
        />
      </Route>
      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
