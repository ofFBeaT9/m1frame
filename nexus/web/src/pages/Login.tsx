import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("physician@nexus.demo");
  const [password, setPassword] = useState("Demo1234!");
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await login(email, password);
      nav("/monitoring");
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="min-h-screen bg-base flex items-center justify-center">
      <form onSubmit={submit} className="bg-surface border border-border-subtle rounded-xl p-8 w-[380px]">
        <h1 className="text-2xl font-bold text-accent-primary tracking-tight">NEXUS</h1>
        <p className="text-text-secondary text-[13px] mt-1">Clinical Intelligence Platform</p>
        <label className="block mt-6 text-[13px] text-text-secondary">Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)}
          className="w-full mt-1 bg-input border border-border-active rounded px-3 py-2 text-sm" />
        <label className="block mt-3 text-[13px] text-text-secondary">Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
          className="w-full mt-1 bg-input border border-border-active rounded px-3 py-2 text-sm font-mono" />
        {err && <p className="text-critical text-[13px] mt-2">{err}</p>}
        <button className="w-full mt-5 bg-accent-primary text-base font-semibold py-2 rounded text-[#0A0E17]">Sign In</button>
        <p className="text-text-muted text-[11px] mt-4 text-center">Demo: physician@nexus.demo · Demo1234!</p>
      </form>
    </div>
  );
}
