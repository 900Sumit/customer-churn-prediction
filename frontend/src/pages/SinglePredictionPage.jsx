import { useState } from "react";
import { Link } from "react-router-dom";
import { RotateCcw, Send } from "lucide-react";
import { fields, sample } from "../constants";
import { predict, apiMessage } from "../services/apiClient";
import { notify } from "../utils/notifications";
import { ResultCard } from "../components/common";
import { usePredictions } from "../context/PredictionContext";
function validate(data) {
  const e = {};
  fields.forEach(([key, label, options]) => {
    if (data[key] === "" || data[key] === undefined || data[key] === null)
      e[key] = `${label} is required.`;
    else if (options && !options.map(String).includes(String(data[key])))
      e[key] = `Choose a valid ${label.toLowerCase()}.`;
  });
  ["tenure", "MonthlyCharges", "TotalCharges"].forEach((k) => {
    if (data[k] !== "" && Number(data[k]) < 0)
      e[k] = "Value cannot be negative.";
  });
  return e;
}
export default function SinglePredictionPage() {
  const [form, setForm] = useState(sample);
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const { addRecords } = usePredictions();
  const update = (k, v) => setForm((x) => ({ ...x, [k]: v }));
  const reset = () => {
    setForm(sample);
    setErrors({});
    setResult(null);
  };
  const submit = async (e) => {
    e.preventDefault();
    const next = validate(form);
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      const payload = {
        ...form,
        SeniorCitizen: Number(form.SeniorCitizen),
        tenure: Number(form.tenure),
        MonthlyCharges: Number(form.MonthlyCharges),
        TotalCharges: Number(form.TotalCharges),
      };
      const r = await predict(payload);
      setResult(r.data);
      addRecords([r.data], "Single prediction");
      if (r.data.persistence_status === "failed") {
        notify.warning("Prediction completed, but persistent history could not be saved.");
      } else {
        notify.success("Prediction completed successfully.");
      }
    } catch (err) {
      notify.error(apiMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div>
      <div className="mb-8">
        <p className="eyebrow">Prediction operations</p>
        <h1 className="page-title">Single customer prediction</h1>
        <p className="page-subtitle">
          Submit the exact fields validated by the FastAPI model.
        </p>
      </div>
      {result && (
        <div className="mb-6">
          <ResultCard result={result} />
          <div className="section-card mt-4">
            <p className="eyebrow">Model detail</p>
            <div className="grid sm:grid-cols-3 gap-4">
              <div>
                <small className="text-base-content/55">
                  Logistic Regression
                </small>
                <p className="font-bold">{result.LR_Churn_Probability}%</p>
              </div>
              <div>
                <small className="text-base-content/55">CatBoost</small>
                <p className="font-bold">
                  {result.CatBoost_Churn_Probability}%
                </p>
              </div>
              <div>
                <small className="text-base-content/55">Data quality</small>
                <p className="font-bold">{result.Data_Quality_Warning}</p>
              </div>
            </div>
            <p className="text-xs text-base-content/55 mt-5">
              This estimate reflects the submitted attributes and should
              support—not replace—customer retention judgment.
            </p>
          </div>
        </div>
      )}
      <form onSubmit={submit} className="section-card">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-xl font-bold">Customer attributes</h2>
            <p className="text-sm text-base-content/60 mt-1">
              All 19 fields are required by the current backend schema.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={reset}
          >
            <RotateCcw size={15} /> Reset
          </button>
        </div>
        <div className="form-grid">
          {fields.map(([key, label, options]) => (
            <label className="form-control" key={key}>
              <span className="label-text font-semibold text-sm">{label}</span>
              {options ? (
                <select
                  className={`select select-bordered mt-1 ${errors[key] ? "select-error" : ""}`}
                  value={form[key]}
                  onChange={(e) => update(key, e.target.value)}
                >
                  <option value="">Select…</option>
                  {options.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  className={`input input-bordered mt-1 ${errors[key] ? "input-error" : ""}`}
                  type={key === "tenure" ? "number" : "number"}
                  min="0"
                  step={key === "tenure" ? "1" : "0.01"}
                  value={form[key]}
                  onChange={(e) => update(key, e.target.value)}
                  placeholder={label}
                />
              )}{" "}
              {errors[key] && (
                <span className="label-text-alt text-error mt-1">
                  {errors[key]}
                </span>
              )}
            </label>
          ))}
        </div>
        <div className="flex justify-end mt-8">
          <button className="btn btn-primary" disabled={busy}>
            {busy ? (
              <span className="loading loading-spinner loading-sm" />
            ) : (
              <Send size={16} />
            )}{" "}
            {busy ? "Running model…" : "Predict churn"}
          </button>
        </div>
      </form>
      <p className="text-xs text-base-content/50 mt-4">
        Need to score many customers?{" "}
        <Link className="link" to="/batch">
          Use CSV batch prediction.
        </Link>
      </p>
    </div>
  );
}
