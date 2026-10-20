import { useMemo, useRef, useState } from "react";
import { Download, FileSpreadsheet, Search, Upload } from "lucide-react";
import { requiredColumns } from "../constants";
import { apiMessage, downloadCsv, predictCsv } from "../services/apiClient";
import { notify } from "../utils/notifications";
import { Empty, ErrorState, Loading } from "../components/common";
import { usePredictions } from "../context/PredictionContext";
export default function BatchPredictionPage() {
  const input = useRef();
  const [file, setFile] = useState(null);
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [downloading, setDownloading] = useState(false);
  const { addRecords } = usePredictions();
  const select = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };
  const process = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const r = await predictCsv(file);
      const predictions = r.data.predictions || [];
      setRows(predictions);
      addRecords(predictions, "CSV batch");
      if (r.data.persistence_status === "failed") {
        notify.warning(`${r.data.total_records} records processed, but persistent history could not be saved.`);
      } else {
        notify.success(`${r.data.total_records} CSV records processed.`);
      }
    } catch (e) {
      setError(apiMessage(e));
      notify.error(apiMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const filtered = useMemo(
    () =>
      rows.filter((r) =>
        Object.values(r).some((v) =>
          String(v).toLowerCase().includes(query.toLowerCase()),
        ),
      ),
    [rows, query],
  );
  const download = async () => {
    setDownloading(true);
    try {
      const r = await downloadCsv(file);
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "churn_batch_predictions.csv";
      a.click();
      URL.revokeObjectURL(url);
      notify.success("Prediction CSV downloaded.");
    } catch (e) {
      notify.error(apiMessage(e));
    } finally {
      setDownloading(false);
    }
  };
  return (
    <div>
      <div className="mb-8">
        <p className="eyebrow">Prediction operations</p>
        <h1 className="page-title">CSV batch prediction</h1>
        <p className="page-subtitle">
          Upload a CSV containing the 19 required model columns.
        </p>
      </div>
      <div className="grid xl:grid-cols-3 gap-5">
        <div className="section-card xl:col-span-1">
          <h2 className="text-xl font-bold">Upload dataset</h2>
          <p className="text-sm text-base-content/60 mt-2">
            The API validates file type, columns, blank values, categories, and
            numeric ranges.
          </p>
          <div
            className="dropzone mt-6"
            onClick={() => input.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
          >
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={select}
            />
            <Upload className="mx-auto text-primary" />
            <p className="font-semibold mt-3">Drop a CSV here</p>
            <p className="text-sm text-base-content/55 mt-1">
              or choose a file
            </p>
          </div>
          {file && (
            <div className="alert mt-4">
              <FileSpreadsheet size={17} />
              <span className="text-sm truncate">
                {file.name} · {(file.size / 1024).toFixed(1)} KB
              </span>
            </div>
          )}
          <button
            onClick={process}
            disabled={!file || busy}
            className="btn btn-primary w-full mt-4"
          >
            {busy ? (
              <span className="loading loading-spinner loading-sm" />
            ) : (
              <Upload size={16} />
            )}{" "}
            {busy ? "Processing…" : "Process CSV"}
          </button>
          <div className="divider" />
          <p className="text-xs text-base-content/55">Required columns</p>
          <p className="text-xs leading-6 text-base-content/65 mt-2">
            {requiredColumns.join(", ")}
          </p>
        </div>
        <div className="section-card xl:col-span-2">
          <div className="flex flex-wrap justify-between gap-3 items-center mb-5">
            <div>
              <p className="eyebrow">Results</p>
              <h2 className="text-xl font-bold">
                Processed records {rows.length ? `(${rows.length})` : ""}
              </h2>
            </div>
            {rows.length > 0 && (
              <div className="flex gap-2">
                <label className="input input-bordered input-sm flex items-center gap-2">
                  <Search size={14} />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search results"
                  />
                </label>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={download}
                  disabled={downloading}
                >
                  {downloading ? (
                    <span className="loading loading-spinner loading-xs" />
                  ) : (
                    <Download size={15} />
                  )}{" "}
                  Download
                </button>
              </div>
            )}
          </div>
          {error && <ErrorState text={error} />}{" "}
          {busy ? (
            <Loading text="Validating and scoring CSV…" />
          ) : rows.length === 0 ? (
            <Empty
              title="No batch results yet"
              text="Upload and process a CSV to see the API's returned predictions here."
            />
          ) : (
            <div className="table-wrap">
              <table className="table table-zebra">
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Prediction</th>
                    <th>Probability</th>
                    <th>Risk</th>
                    <th>Quality</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>
                        <span
                          className={`badge ${r.Ensemble_Prediction === "Churn" ? "badge-error" : "badge-success"}`}
                        >
                          {r.Ensemble_Prediction}
                        </span>
                      </td>
                      <td>{r.Ensemble_Churn_Probability}%</td>
                      <td>{r.Risk_Level}</td>
                      <td>{r.Data_Quality_Warning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && (
                <p className="text-center text-sm text-base-content/55 py-8">
                  No rows match your search.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
