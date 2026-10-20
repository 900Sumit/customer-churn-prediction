import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Database,
  FileSpreadsheet,
  Gauge,
  Menu,
  Monitor,
  Moon,
  Settings,
  ShieldCheck,
  Sparkles,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import { Toaster } from "sonner";
import { SignedIn, SignedOut, UserButton, useUser } from "@clerk/clerk-react";
import { useTheme } from "../context/ThemeContext";
import { authUrls } from "../constants/auth";
const links = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge },
  { to: "/predict", label: "Single prediction", icon: Sparkles },
  { to: "/batch", label: "CSV batch", icon: FileSpreadsheet },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/history", label: "Prediction history", icon: Database },
  { to: "/model", label: "Model information", icon: Activity },
];
function Sidebar({ open, close }) {
  return (
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
      <div className="flex items-center justify-between mb-10">
        <Link to="/dashboard" className="brand" onClick={close}>
          <span className="brand-mark">
            <ShieldCheck size={18} />
          </span>{" "}
          ChurnLab
        </Link>
        <button className="btn btn-ghost btn-sm lg:hidden" onClick={close}>
          <X size={18} />
        </button>
      </div>
      <nav className="space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={close}
            className={({ isActive }) =>
              `nav-link ${isActive ? "nav-active" : ""}`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <NavLink to="/settings" onClick={close} className="nav-link">
          <Settings size={18} />
          Settings
        </NavLink>
        <div className="api-chip">
          <span className="status-dot" /> API integration ready
        </div>
      </div>
    </aside>
  );
}
function ThemeSelector() {
  const { preference } = useTheme();
  const [open, setOpen] = useState(false);
  const { setPreference } = useTheme();
  const options = [
    ["light", "Light", Sun],
    ["dark", "Dark", Moon],
    ["system", "System", Monitor],
  ];
  const selected =
    options.find(([value]) => value === preference) || options[2];
  const Icon = selected[2];
  return (
    <div className="dropdown dropdown-end">
      <button
        className="btn btn-ghost btn-sm gap-2"
        aria-label="Change theme"
        onClick={() => setOpen(!open)}
      >
        <Icon size={17} />
        <span className="hidden sm:inline">{selected[1]}</span>
      </button>
      <ul
        className={`dropdown-content z-[60] menu p-2 shadow bg-base-100 rounded-box w-40 ${open ? "" : "hidden"}`}
      >
        {options.map(([value, label, OptionIcon]) => (
          <li key={value}>
            <button
              className={preference === value ? "active" : ""}
              onClick={() => {
                setPreference(value);
                setOpen(false);
              }}
            >
              <OptionIcon size={16} />
              {label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
function ClerkProfileMenu() {
  const { user } = useUser();
  const displayName = user?.fullName || user?.firstName || "Account";
  const email = user?.primaryEmailAddress?.emailAddress;

  return (
    <>
      <SignedIn>
        <div className="hidden sm:block text-right leading-tight">
          <p className="text-sm font-semibold">{displayName}</p>
          {email && (
            <p className="text-xs text-base-content/55 max-w-44 truncate">
              {email}
            </p>
          )}
        </div>
        <UserButton
          afterSignOutUrl={authUrls.landing}
          userProfileMode="modal"
          appearance={{ elements: { userButtonAvatarBox: "w-9 h-9" } }}
        />
      </SignedIn>
      <SignedOut>
        <div className="flex items-center gap-2">
          <Link className="btn btn-ghost btn-sm" to="/sign-in">
            Sign in
          </Link>
          <Link className="btn btn-primary btn-sm" to="/sign-up">
            Sign up
          </Link>
        </div>
      </SignedOut>
    </>
  );
}
export function AppLayout({ clerkEnabled }) {
  const [open, setOpen] = useState(false);
  const { theme } = useTheme();
  const location = useLocation();
  return (
    <div className="app-shell">
      <Sidebar open={open} close={() => setOpen(false)} />
      {open && (
        <div className="sidebar-overlay" onClick={() => setOpen(false)} />
      )}
      <main className="main-shell">
        <header className="topbar">
          <button
            className="btn btn-ghost lg:hidden"
            onClick={() => setOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div>
            <p className="eyebrow">Customer intelligence workspace</p>
            <p className="text-sm font-medium">
              {location.pathname === "/dashboard"
                ? "Overview"
                : "Prediction operations"}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <ThemeSelector />
            {clerkEnabled ? (
              <ClerkProfileMenu />
            ) : (
              <div className="flex items-center gap-2">
                <Link className="btn btn-ghost btn-sm" to="/sign-in">
                  Sign in
                </Link>
                <Link className="btn btn-primary btn-sm" to="/sign-up">
                  Sign up
                </Link>
              </div>
            )}
          </div>
        </header>
        <div className="page-content">
          <Outlet />
        </div>
      </main>
      <Toaster richColors position="bottom-right" theme={theme} />
    </div>
  );
}
export function LandingLayout() {
  return (
    <>
      <Toaster richColors position="bottom-right" />
      <Outlet />
    </>
  );
}
export { links };
