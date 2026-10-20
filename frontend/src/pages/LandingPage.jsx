import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Check,
  ShieldCheck,
  Upload,
  Zap,
} from "lucide-react";
export default function LandingPage({ clerkEnabled }) {
  return (
    <div className="min-h-screen">
      <header className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <ShieldCheck size={18} />
          </span>{" "}
          ChurnLab
        </Link>
        <div className="flex items-center gap-3">
          <span className="hidden sm:block text-sm text-base-content/60">
            Research prediction workspace
          </span>
          <Link to="/dashboard" className="btn btn-primary btn-sm">
            Open dashboard <ArrowRight size={15} />
          </Link>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 pt-12 pb-20">
        <div className="hero-grid">
          <div>
            <div className="badge badge-outline mb-6 gap-2">
              <span className="status-dot" /> ML-powered customer insights
            </div>
            <h1 className="hero-title">
              Understand churn <em>before</em> it happens.
            </h1>
            <p className="text-lg text-base-content/65 max-w-xl mt-7 leading-relaxed">
              ChurnLab turns customer attributes into a clear, explainable risk
              estimate using the project's verified Logistic Regression and
              CatBoost ensemble.
            </p>
            <div className="flex flex-wrap gap-3 mt-8">
              <Link to="/predict" className="btn btn-primary">
                Run a prediction <ArrowRight size={17} />
              </Link>
              <Link to="/model" className="btn btn-ghost">
                Explore the model
              </Link>
            </div>
            <p className="text-xs text-base-content/50 mt-5">
              Predictions are estimates for research and decision support—not
              guarantees.
            </p>
          </div>
          <div className="hero-panel">
            <div className="flex justify-between items-start">
              <div>
                <p className="eyebrow">Verified pipeline</p>
                <h2 className="text-2xl font-bold">One workspace, two modes</h2>
              </div>
              <div className="badge badge-success">Ready</div>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-7">
              <div className="p-4 rounded-xl bg-base-200">
                <Zap size={18} className="text-primary mb-5" />
                <p className="font-semibold">Single customer</p>
                <p className="text-xs text-base-content/55 mt-1">
                  19 validated inputs
                </p>
              </div>
              <div className="p-4 rounded-xl bg-base-200">
                <Upload size={18} className="text-primary mb-5" />
                <p className="font-semibold">CSV batches</p>
                <p className="text-xs text-base-content/55 mt-1">
                  Predict at scale
                </p>
              </div>
            </div>
            <div className="divider" />
            <div className="flex gap-3 items-start text-sm">
              <Check className="text-success shrink-0" size={17} />
              <span>
                Feature engineering stays in FastAPI, alongside the saved
                pipelines.
              </span>
            </div>
            <div className="flex gap-3 items-start text-sm mt-3">
              <Check className="text-success shrink-0" size={17} />
              <span>
                Risk bands use the backend's verified probability thresholds.
              </span>
            </div>
          </div>
        </div>
        <div className="grid md:grid-cols-3 gap-5 mt-28">
          <div className="section-card">
            <BarChart3 className="text-primary" />
            <h3 className="font-bold text-lg mt-5">Actionable risk</h3>
            <p className="text-sm text-base-content/60 mt-2">
              See ensemble probability, model signals, and risk classification
              in plain language.
            </p>
          </div>
          <div className="section-card">
            <ShieldCheck className="text-primary" />
            <h3 className="font-bold text-lg mt-5">Validated inputs</h3>
            <p className="text-sm text-base-content/60 mt-2">
              Use the same categorical values and numeric constraints enforced
              by the API.
            </p>
          </div>
          <div className="section-card">
            <Upload className="text-primary" />
            <h3 className="font-bold text-lg mt-5">Batch ready</h3>
            <p className="text-sm text-base-content/60 mt-2">
              Upload the exact required columns and download confirmed
              prediction results.
            </p>
          </div>
        </div>
        <p className="text-xs text-base-content/45 mt-10">
          Authentication{" "}
          {clerkEnabled
            ? "is configured through Clerk."
            : "scaffolding is ready; add VITE_CLERK_PUBLISHABLE_KEY to enable Clerk."}
        </p>
      </main>
    </div>
  );
}
