import { Link } from "react-router-dom";
export default function NotFoundPage() {
  return (
    <div className="min-h-screen grid place-items-center p-6">
      <div className="text-center">
        <p className="eyebrow">404</p>
        <h1 className="page-title">Page not found</h1>
        <p className="text-base-content/60 mt-3">
          That route does not exist in ChurnLab.
        </p>
        <Link to="/dashboard" className="btn btn-primary mt-6">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
