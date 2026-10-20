import { createContext, useContext, useEffect, useMemo, useState } from "react";
const ThemeContext = createContext(null);
export function ThemeProvider({ children }) {
  const [preference, setPreference] = useState(
    () => localStorage.getItem("churnlab-theme") || "system",
  );
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches,
  );
  const theme =
    preference === "system" ? (systemDark ? "dark" : "light") : preference;
  useEffect(() => {
    localStorage.setItem("churnlab-theme", preference);
    document.documentElement.setAttribute("data-theme", theme);
  }, [preference, theme]);
  useEffect(() => {
    const m = window.matchMedia("(prefers-color-scheme: dark)");
    const f = () => setSystemDark(m.matches);
    m.addEventListener?.("change", f);
    return () => m.removeEventListener?.("change", f);
  }, []);
  const value = useMemo(
    () => ({ preference, setPreference, theme }),
    [preference, theme],
  );
  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}
export const useTheme = () => useContext(ThemeContext);
