import { useEffect, useMemo, useState } from "react";
import { Database, Download, LockKeyhole, Search } from "lucide-react";
import { apiMessage, exportHistory, getHistory } from "../services/apiClient";
import { Empty, ErrorState, Loading } from "../components/common";

const PAGE_SIZE = 20;

export default function HistoryPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("");
  const [prediction, setPrediction] = useState("");
  const [source, setSource] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  const params = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
      q: query || undefined,
      risk: risk || undefined,
      prediction: prediction || undefined,
      source: source || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
    [page, query, risk, prediction, source, dateFrom, dateTo],
  );

  useEffect(() => {
    let active = true;
    setStatus("loading");
    setError("");
    getHistory(params)
      .then((response) => {
        if (!active) return;
        setItems(response.data.items || []);
        setTotal(Number(response.data.total || 0));
        setStatus("ready");
      })
      .catch((err) => {
        if (!active) return;
        setError(apiMessage(err));
        setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [params]);

  const updateFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
  };

  const clearFilters = () => {
    setQuery("");
    setRisk("");
    setPrediction("");
    setSource("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const download = async () => {
    setExporting(true);
    try {
      const { limit, offset, ...filters } = params;
      const response = await exportHistory(filters);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "prediction_history.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setExporting(false);
    }
  };

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasFilters = query || risk || prediction || source || dateFrom || dateTo;

  return (
    <div>
      <div className="mb-8">
        <p className="eyebrow">Your records</p>
        <h1 className="page-title">Prediction history</h1>
        <p className="page-subtitle">
          Persistent records loaded from Neon and scoped to the signed-in Clerk
          user.
        </p>
      </div>
      {status === "loading" && (
        <div className="section-card">
          <Loading text="Loading your prediction history…" />
        </div>
      )}
      {status === "error" && (
        <div className="section-card">
          <ErrorState text={error} />
          <div className="flex gap-3 items-start mt-6 text-sm text-base-content/60">
            <LockKeyhole size={18} className="text-primary shrink-0" />
            <p>
              History requires `DATABASE_URL`, Clerk JWKS/issuer/audience
              configuration, and a signed-in user. Prediction requests remain
              available without persistence.
            </p>
          </div>
        </div>
      )}
      {status === "ready" && (
        <div className="section-card">
          <div className="flex flex-wrap justify-between gap-3 items-center mb-5">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-base-200">
                <Database className="text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Saved predictions</h2>
                <p className="text-sm text-base-content/60">
                  {total} records match the current filters
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-outline btn-sm" onClick={download} disabled={exporting || total === 0}>
                {exporting ? <span className="loading loading-spinner loading-xs" /> : <Download size={15} />}
                Export CSV
              </button>
              {hasFilters && (
                <button className="btn btn-ghost btn-sm" onClick={clearFilters}>
                  Clear filters
                </button>
              )}
            </div>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
            <label className="input input-bordered input-sm flex items-center gap-2">
              <Search size={14} />
              <input value={query} onChange={updateFilter(setQuery)} placeholder="Search history" />
            </label>
            <select className="select select-bordered select-sm" value={risk} onChange={updateFilter(setRisk)}>
              <option value="">All risk levels</option>
              <option>Low Risk</option>
              <option>Medium Risk</option>
              <option>High Risk</option>
            </select>
            <select className="select select-bordered select-sm" value={prediction} onChange={updateFilter(setPrediction)}>
              <option value="">All predictions</option>
              <option>Churn</option>
              <option>No Churn</option>
            </select>
            <select className="select select-bordered select-sm" value={source} onChange={updateFilter(setSource)}>
              <option value="">All sources</option>
              <option value="single">Single prediction</option>
              <option value="csv">CSV batch</option>
            </select>
            <input className="input input-bordered input-sm" type="date" value={dateFrom} onChange={updateFilter(setDateFrom)} aria-label="From date" />
            <input className="input input-bordered input-sm" type="date" value={dateTo} onChange={updateFilter(setDateTo)} aria-label="To date" />
          </div>

          {items.length === 0 ? (
            <Empty
              title={total ? "No matching records" : "No persisted predictions"}
              text={total ? "Try another filter combination." : "Successful authenticated predictions will appear here."}
            />
          ) : (
            <>
              <div className="table-wrap">
                <table className="table table-zebra">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Source</th>
                      <th>Prediction</th>
                      <th>Probability</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td>{new Date(item.created_at).toLocaleString()}</td>
                        <td>{item.source === "csv" ? "CSV batch" : "Single prediction"}</td>
                        <td>
                          <span className={`badge ${item.result_data?.Ensemble_Prediction === "Churn" ? "badge-error" : "badge-success"}`}>
                            {item.result_data?.Ensemble_Prediction}
                          </span>
                        </td>
                        <td>{item.result_data?.Ensemble_Churn_Probability}%</td>
                        <td>{item.result_data?.Risk_Level}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex justify-between items-center gap-3 mt-5 text-sm">
                <span>Page {page} of {pageCount}</span>
                <div className="join">
                  <button className="btn btn-sm join-item" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button>
                  <button className="btn btn-sm join-item" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>Next</button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
