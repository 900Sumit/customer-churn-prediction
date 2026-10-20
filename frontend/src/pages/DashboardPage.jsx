import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, FileSpreadsheet, Sparkles } from "lucide-react";
import { Stat, Empty } from "../components/common";
import { usePredictions } from "../context/PredictionContext";
import { getAnalytics } from "../services/apiClient";

export default function DashboardPage() {
  const { records } = usePredictions();
  const [databaseMetrics, setDatabaseMetrics] = useState(null);
  useEffect(() => {
    getAnalytics().then((response) => setDatabaseMetrics(response.data)).catch(() => setDatabaseMetrics(null));
  }, []);
  const churn = records.filter(
    (record) => record.Ensemble_Prediction === "Churn",
  ).length;
  const total = databaseMetrics?.total ?? records.length;
  const displayedChurn = databaseMetrics?.churn ?? churn;
  const displayedNonChurn = databaseMetrics?.non_churn ?? total - churn;
  const rate = databaseMetrics?.churn_rate ?? (total ? (churn / total) * 100 : 0);

  return (
    <div>
      <div className="flex flex-wrap justify-between gap-5 items-end mb-8">
        <div>
          <p className="eyebrow">Workspace overview</p>
          <h1 className="page-title">Good morning, researcher.</h1>
          <p className="page-subtitle">
            Run predictions and inspect your model-backed results.
          </p>
        </div>
        <div className="flex gap-3">
          <Link to="/predict" className="btn btn-primary btn-sm">
            <Sparkles size={16} /> Single prediction
          </Link>
          <Link to="/batch" className="btn btn-outline btn-sm">
            <FileSpreadsheet size={16} /> CSV batch
          </Link>
        </div>
      </div>
      <div className="alert alert-info mb-5 text-sm">
        {databaseMetrics
          ? "Dashboard metrics use persistent Neon history for this signed-in user. Recent activity below is session-only."
          : "Persistent analytics is unavailable. Dashboard metrics are based on successful predictions in this browser session and reset when the page reloads."}
      </div>
      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <Stat label="Total predictions" value={total} />
        <Stat label="Churn predictions" value={displayedChurn} />
        <Stat label="Non-churn predictions" value={displayedNonChurn} />
        <Stat
          label="Churn rate"
          value={total ? `${rate.toFixed(1)}%` : "—"}
          hint={databaseMetrics ? "From persistent history" : total ? "From current session" : "Run a prediction to begin"}
        />
      </div>
      <div className="grid lg:grid-cols-5 gap-5 mt-5">
        <div className="section-card lg:col-span-3">
          <div className="flex justify-between">
            <div>
              <p className="eyebrow">Session-only activity</p>
              <h2 className="text-xl font-bold">Recent prediction activity</h2>
            </div>
            <Link to="/analytics" className="btn btn-ghost btn-sm">
              Analytics <ArrowRight size={15} />
            </Link>
          </div>
          {total === 0 ? (
            <Empty
              title="No predictions in this session"
              text="Run a single prediction or process a CSV to populate real session activity."
            />
          ) : (
            <div className="mt-5 space-y-3">
              {records.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  className="flex justify-between items-center p-3 rounded-lg bg-base-200"
                >
                  <div>
                    <p className="font-semibold text-sm">{item.source}</p>
                    <p className="text-xs text-base-content/55">
                      {new Date(item.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`badge ${item.Ensemble_Prediction === "Churn" ? "badge-error" : "badge-success"}`}
                    >
                      {item.Ensemble_Prediction}
                    </span>
                    <p className="text-xs mt-1">
                      {item.Ensemble_Churn_Probability}% probability
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="section-card lg:col-span-2">
          <p className="eyebrow">Quick start</p>
          <h2 className="text-xl font-bold">Choose a workflow</h2>
          <div className="space-y-3 mt-5">
            <Link
              to="/predict"
              className="flex justify-between items-center p-4 rounded-xl bg-base-200 hover:bg-base-300"
            >
              <span>
                <b className="block">Score one customer</b>
                <small className="text-base-content/55">
                  Guided 19-field form
                </small>
              </span>
              <ArrowRight size={17} />
            </Link>
            <Link
              to="/batch"
              className="flex justify-between items-center p-4 rounded-xl bg-base-200 hover:bg-base-300"
            >
              <span>
                <b className="block">Score a CSV</b>
                <small className="text-base-content/55">
                  Process many records
                </small>
              </span>
              <ArrowRight size={17} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
