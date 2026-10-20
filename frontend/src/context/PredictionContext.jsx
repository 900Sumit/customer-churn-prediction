import { createContext, useContext, useMemo, useState } from "react";

const PredictionContext = createContext(null);

export function PredictionProvider({ children }) {
  const [records, setRecords] = useState([]);

  const addRecords = (items, source) => {
    const timestamp = new Date().toISOString();
    setRecords((current) => [
      ...items.map((item, index) => ({
        id: `${timestamp}-${index}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp,
        source,
        ...item,
      })),
      ...current,
    ]);
  };

  const value = useMemo(() => ({ records, addRecords }), [records]);
  return (
    <PredictionContext.Provider value={value}>
      {children}
    </PredictionContext.Provider>
  );
}

export function usePredictions() {
  const context = useContext(PredictionContext);
  if (!context)
    throw new Error("usePredictions must be used inside PredictionProvider");
  return context;
}
