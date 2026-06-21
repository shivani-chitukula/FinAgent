import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";

const API_BASE = "http://localhost:8001";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { data } = await axios.post(`${API_BASE}/login`, form);
      localStorage.setItem("token", data.access_token);
      // Remove stale session so a fresh one is created on first message
      localStorage.removeItem("session_id");
      navigate("/chat");
    } catch (err) {
      setError(
        err?.response?.data?.detail || "Login failed. Check your credentials."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
      <div className="w-full max-w-md bg-white/5 border border-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8">
        {/* Logo / Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-blue-600 mb-4 shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M3 10h18M3 6h18M5 14h14M7 18h10" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">BankingBot</h1>
          <p className="text-sm text-blue-300 mt-1">Sign in to your account</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-blue-200 mb-1" htmlFor="email">
              Email Address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              className="w-full px-4 py-2.5 rounded-lg bg-white/10 border border-white/20
                         text-white placeholder-white/40 focus:outline-none focus:ring-2
                         focus:ring-blue-500 transition"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-blue-200 mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="current-password"
              value={form.password}
              onChange={handleChange}
              placeholder="••••••••"
              className="w-full px-4 py-2.5 rounded-lg bg-white/10 border border-white/20
                         text-white placeholder-white/40 focus:outline-none focus:ring-2
                         focus:ring-blue-500 transition"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            id="login-submit"
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500
                       text-white font-semibold transition disabled:opacity-60
                       disabled:cursor-not-allowed shadow-md"
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-blue-300">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="text-blue-400 hover:text-white font-medium transition">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}
