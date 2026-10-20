import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  timeout: 30000,
});
let tokenGetter = null;
export const setTokenGetter = (getter) => {
  tokenGetter = getter;
};
api.interceptors.request.use(async (config) => {
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
export function apiMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    "The API could not complete that request."
  );
}
export const health = () => api.get("/health");
export const readiness = () => api.get("/ready", { validateStatus: () => true });
export const predict = (payload) => api.post("/predict", payload);
export const predictCsv = (file) => {
  const data = new FormData();
  data.append("file", file);
  return api.post("/predict-csv-json-to-table", data, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const downloadCsv = (file) => {
  const data = new FormData();
  data.append("file", file);
  return api.post("/predict-csv/download", data, {
    responseType: "blob",
    headers: { "Content-Type": "multipart/form-data" },
  });
};
export const getHistory = (params) => api.get("/history", { params });
export const exportHistory = (params) =>
  api.get("/history/export", { params, responseType: "blob" });
export const getAnalytics = () => api.get("/analytics");
