import { CheckCircle2, Cpu, Database, GitBranch } from "lucide-react";
export default function ModelPage() {
  return (
    <div>
      <div className="mb-8">
        <p className="eyebrow">Research notes</p>
        <h1 className="page-title">Model information</h1>
        <p className="page-subtitle">
          Verified from the FastAPI source and production feature-engineering
          module.
        </p>
      </div>
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="section-card lg:col-span-2">
          <div className="flex gap-3">
            <Database className="text-primary" />
            <div>
              <h2 className="text-xl font-bold">Customer churn pipeline</h2>
              <p className="text-sm text-base-content/65 mt-2">
                The current service accepts the IBM Telco-style 19-column
                customer schema and applies the saved production pipelines at
                inference time.
              </p>
            </div>
          </div>
          <div className="divider" />
          <h3 className="font-bold">Feature engineering confirmed in code</h3>
          <div className="grid sm:grid-cols-2 gap-3 mt-4">
            {["TenureGroup", "ServiceCount", "AverageMonthlySpending"].map(
              (x) => (
                <div className="p-4 rounded-xl bg-base-200" key={x}>
                  <CheckCircle2 size={17} className="text-success" />
                  <p className="font-semibold mt-3">{x}</p>
                  <p className="text-xs text-base-content/55 mt-1">
                    Created by production_pipeline.py
                  </p>
                </div>
              ),
            )}
          </div>
          <p className="text-xs text-base-content/55 mt-5">
            The prompt mentions LongTermCustomer and HighMonthlyCharges, but
            those features are not present in the inspected feature-engineering
            implementation and are intentionally not claimed here.
          </p>
        </div>
        <div className="section-card">
          <Cpu className="text-primary" />
          <h2 className="text-xl font-bold mt-5">Available models</h2>
          <div className="space-y-4 mt-6">
            <div>
              <p className="font-semibold">Logistic Regression</p>
              <p className="text-sm text-base-content/55">
                Saved pipeline probability
              </p>
            </div>
            <div>
              <p className="font-semibold">CatBoost</p>
              <p className="text-sm text-base-content/55">
                Saved pipeline probability
              </p>
            </div>
            <div>
              <p className="font-semibold">Ensemble</p>
              <p className="text-sm text-base-content/55">
                Mean of both probabilities
              </p>
            </div>
          </div>
          <div className="divider" />
          <div className="flex gap-2 text-sm">
            <GitBranch size={17} className="text-primary shrink-0" />
            <span>
              Churn threshold: <b>45%</b>. Risk bands: Low &lt;30%, Medium
              &lt;60%, High ≥60%.
            </span>
          </div>
        </div>
      </div>
      <div className="section-card mt-5">
        <h3 className="font-bold">Evaluation metrics</h3>
        <p className="text-sm text-base-content/60 mt-2">
          No evaluation report or verified metric artifact is present in the
          inspected repository, so accuracy, precision, recall, and comparisons
          are not displayed.
        </p>
      </div>
    </div>
  );
}
