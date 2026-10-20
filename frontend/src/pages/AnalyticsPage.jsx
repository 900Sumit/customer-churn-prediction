import { useEffect, useMemo, useState } from "react";
import { BarChart3, Database, LineChart as LineIcon, PieChart as PieIcon } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Empty, Stat } from "../components/common";
import { usePredictions } from "../context/PredictionContext";
import { getAnalytics } from "../services/apiClient";

const COLORS = ["#d05b48", "#2c8b6c", "#d69e2e"];

export default function AnalyticsPage() {
  const { records } = usePredictions();
  const [databaseMetrics, setDatabaseMetrics] = useState(null);

  useEffect(() => {
    getAnalytics()
      .then((response) => setDatabaseMetrics(response.data))
      .catch(() => setDatabaseMetrics(null));
  }, []);

  const sessionMetrics = useMemo(() => {
    const churn = records.filter((item) => item.Ensemble_Prediction === "Churn").length;
    const total = records.length;
    const averageProbability = total
      ? records.reduce((sum, item) => sum + Number(item.Ensemble_Churn_Probability || 0), 0) / total
      : 0;
    return {
      total,
      churn,
      non_churn: total - churn,
      churn_rate: total ? (churn / total) * 100 : 0,
      average_probability: averageProbability,
      risk_distribution: ["Low Risk", "Medium Risk", "High Risk"].map((risk_level) => ({
        risk_level,
        count: records.filter((item) => item.Risk_Level === risk_level).length,
      })),
      source_distribution: ["single", "csv"].map((source) => ({
        source,
        count: records.filter((item) => item.source === (source === "single" ? "Single prediction" : "CSV batch")).length,
      })),
      date_trends: [],
      segment_analysis: [],
      feature_importance: [],
      evaluation_metrics: { available: false, message: "Evaluation metrics are not available for session-only data." },
    };
  }, [records]);

  const display = databaseMetrics || sessionMetrics;
  const isPersistent = Boolean(databaseMetrics);
  const riskData = (display.risk_distribution || []).map((item) => ({
    name: item.risk_level?.replace(" Risk", "") || "Unknown",
    value: Number(item.count || 0),
  }));
  const sourceData = (display.source_distribution || []).map((item) => ({
    name: item.source === "csv" ? "CSV batch" : "Single",
    predictions: Number(item.count || 0),
  }));
  const trendData = display.date_trends || [];
  const segments = display.segment_analysis || [];
  const featureImportance = display.feature_importance || [];
  const total = Number(display.total || 0);
  const churn = Number(display.churn || 0);
  const nonChurn = Number(display.non_churn || 0);
  const averageProbability = Number(display.average_probability || 0);

  return (
    <div>
      <div className="mb-8">
        <p className="eyebrow">Evidence-led reporting</p>
        <h1 className="page-title">Analytics</h1>
        <p className="page-subtitle">
          {isPersistent
            ? "Persistent prediction history for the signed-in user."
            : "Session-only prediction results while persistent analytics is unavailable."}
        </p>
      </div>
      <div className={`alert ${isPersistent ? "alert-info" : "alert-warning"} mb-5`}>
        <Database size={18} />
        <span>
          {isPersistent
            ? "Analytics loaded from Neon; all figures below use the same persistent dataset."
            : "Neon analytics is unavailable. The figures below are session-only and clear on refresh; they are not combined with database data."}
        </span>
      </div>
      {total === 0 ? (
        <div className="section-card">
          <Empty title="No predictions to analyse yet" text="Run a single prediction or process a CSV batch, then return here to see real churn distribution, risk bands, trends, segments, and model summaries." />
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <Stat label="Predictions analysed" value={total} />
            <Stat label="Churn predictions" value={churn} />
            <Stat label="Non-churn predictions" value={nonChurn} />
            <Stat label="Churn rate" value={`${Number(display.churn_rate || 0).toFixed(1)}%`} hint={`${averageProbability.toFixed(1)}% average probability`} />
          </div>

          <div className="grid lg:grid-cols-2 gap-5 mt-5">
            <div className="section-card">
              <div className="flex gap-3 items-center mb-4"><PieIcon className="text-primary" /><div><p className="eyebrow">Risk composition</p><h2 className="text-xl font-bold">Risk-level distribution</h2></div></div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart><Pie data={riskData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={92} paddingAngle={3}>{riskData.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="section-card">
              <div className="flex gap-3 items-center mb-4"><BarChart3 className="text-primary" /><div><p className="eyebrow">Outcome summary</p><h2 className="text-xl font-bold">Churn vs non-churn</h2></div></div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[{ name: "Churn", count: churn }, { name: "No churn", count: nonChurn }]}><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#2c8b6c" radius={[6, 6, 0, 0]} /></BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-5 mt-5">
            <div className="section-card">
              <div className="flex gap-3 items-center mb-4"><LineIcon className="text-primary" /><div><p className="eyebrow">Date-wise trend</p><h2 className="text-xl font-bold">Prediction activity</h2></div></div>
              {trendData.length ? <div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={trendData}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Line type="monotone" dataKey="churn" stroke="#d05b48" name="Churn" /><Line type="monotone" dataKey="non_churn" stroke="#2c8b6c" name="No churn" /></LineChart></ResponsiveContainer></div> : <p className="text-sm text-base-content/60">Date trends require persistent history. Session-only trends are intentionally not fabricated.</p>}
            </div>
            <div className="section-card">
              <p className="eyebrow">Prediction sources</p><h2 className="text-xl font-bold">Workflow usage</h2>
              <div className="h-64 mt-4"><ResponsiveContainer width="100%" height="100%"><BarChart data={sourceData}><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="predictions" fill="#4a7aa8" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-5 mt-5">
            <div className="section-card">
              <p className="eyebrow">Customer segments</p><h2 className="text-xl font-bold">Contract segment analysis</h2>
              {segments.length ? <div className="table-wrap mt-4"><table className="table table-zebra"><thead><tr><th>Segment</th><th>Total</th><th>Churn</th><th>Avg. probability</th></tr></thead><tbody>{segments.map((segment) => <tr key={segment.segment}><td>{segment.segment}</td><td>{segment.total}</td><td>{segment.churn}</td><td>{Number(segment.average_probability || 0).toFixed(1)}%</td></tr>)}</tbody></table></div> : <p className="text-sm text-base-content/60">Segment analysis is unavailable for session-only data.</p>}
            </div>
            <div className="section-card">
              <p className="eyebrow">Model evaluation</p>
              <h2 className="text-xl font-bold">Benchmark Evaluation</h2>
              {display.evaluation_metrics?.available && display.evaluation_metrics?.data?.models ? (
                <div className="mt-4 space-y-3">
                  <div className="text-xs text-base-content/70 flex flex-wrap justify-between gap-2">
                    <span><strong>Dataset:</strong> {display.evaluation_metrics.data.dataset}</span>
                    <span><strong>Test Holdout:</strong> {display.evaluation_metrics.data.test_samples} samples</span>
                  </div>
                  <div className="table-wrap">
                    <table className="table table-zebra table-sm">
                      <thead>
                        <tr>
                          <th>Model</th>
                          <th>Accuracy</th>
                          <th>Precision</th>
                          <th>Recall</th>
                          <th>F1-Score</th>
                          <th>ROC-AUC</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(display.evaluation_metrics.data.models).map(([key, m]) => (
                          <tr key={key} className={key === "ensemble" ? "font-semibold bg-base-200/50" : ""}>
                            <td className="capitalize">{key.replace("_", " ")}</td>
                            <td>{(m.accuracy * 100).toFixed(1)}%</td>
                            <td>{(m.precision * 100).toFixed(1)}%</td>
                            <td>{(m.recall * 100).toFixed(1)}%</td>
                            <td>{(m.f1_score * 100).toFixed(1)}%</td>
                            <td>{Number(m.roc_auc).toFixed(3)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-base-content/60 mt-4">
                  {display.evaluation_metrics?.message || "No verified evaluation report is available in the repository. No metrics are fabricated here."}
                </p>
              )}
            </div>
          </div>

          <div className="section-card mt-5">
            <p className="eyebrow">Saved model artifacts</p><h2 className="text-xl font-bold">Feature importance</h2>
            {featureImportance.length ? <div className="table-wrap mt-4"><table className="table table-zebra"><thead><tr><th>Feature</th><th>Logistic regression</th><th>CatBoost</th><th>Combined</th></tr></thead><tbody>{featureImportance.map((item) => <tr key={item.feature}><td>{item.feature}</td><td>{Number(item.logistic_regression_importance_pct).toFixed(2)}%</td><td>{Number(item.catboost_importance_pct).toFixed(2)}%</td><td>{Number(item.combined_importance_pct).toFixed(2)}%</td></tr>)}</tbody></table></div> : <p className="text-sm text-base-content/60 mt-4">Feature importance is available when persistent analytics is connected to the saved model artifacts.</p>}
          </div>
        </>
      )}
    </div>
  );
}
