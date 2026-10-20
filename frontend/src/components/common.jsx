import { AlertCircle, CheckCircle2, LoaderCircle, Inbox } from "lucide-react";
export function Loading({ text = "Loading…" }) {
  return (
    <div className="flex items-center gap-3 py-10 justify-center text-base-content/60">
      <LoaderCircle className="animate-spin" size={20} />
      {text}
    </div>
  );
}
export function Empty({
  title = "Nothing here yet",
  text = "Completed results will appear here once they are available.",
}) {
  return (
    <div className="empty-state">
      <Inbox size={28} />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
export function ErrorState({ text }) {
  return (
    <div className="alert alert-error">
      <AlertCircle size={18} />
      <span>{text}</span>
    </div>
  );
}
export function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function ResultCard({ result }) {
  const churn = result.Ensemble_Prediction === "Churn";
  return (
    <div className={`result-card ${churn ? "result-danger" : "result-safe"}`}>
      <div>
        <p className="eyebrow">Ensemble prediction</p>
        <h2>{result.Ensemble_Prediction}</h2>
        <p className="text-base-content/70">
          Estimated risk: {result.Risk_Level}
        </p>
      </div>
      <div className="text-right">
        <p className="metric-xl">{result.Ensemble_Churn_Probability}%</p>
        <p className="text-sm text-base-content/60">churn probability</p>
      </div>
    </div>
  );
}
export function Stat({ label, value, hint }) {
  return (
    <div className="stat-card">
      <p className="eyebrow">{label}</p>
      <p className="metric">{value}</p>
      {hint && <p className="text-sm text-base-content/60">{hint}</p>}
    </div>
  );
}
