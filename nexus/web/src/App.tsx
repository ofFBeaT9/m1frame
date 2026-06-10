import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { useAuth } from "./store/auth";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Monitoring } from "./pages/Monitoring";
import { Alerts } from "./pages/Alerts";
import { PatientConsole } from "./pages/PatientConsole";
import { Calculators } from "./pages/Calculators";
import { Protocols } from "./pages/Protocols";
import { Admin } from "./pages/Admin";

function Protected({ children }: { children: React.ReactNode }) {
  const user = useAuth((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function Guarded({ perm, children }: { perm: string; children: React.ReactNode }) {
  const can = useAuth((s) => s.can);
  if (!can(perm)) return <div className="text-text-secondary">Your role does not have access to this section.</div>;
  return <>{children}</>;
}

export default function App() {
  const restore = useAuth((s) => s.restore);
  useEffect(() => { restore(); }, [restore]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/monitoring" element={<Protected><Monitoring /></Protected>} />
        <Route path="/monitoring/:id" element={<Protected><PatientConsole /></Protected>} />
        <Route path="/alerts" element={<Protected><Alerts /></Protected>} />
        <Route path="/patients" element={<Protected><Monitoring /></Protected>} />
        <Route path="/calculators" element={<Protected><Guarded perm="calculators"><Calculators /></Guarded></Protected>} />
        <Route path="/protocols" element={<Protected><Guarded perm="protocol_read"><Protocols /></Guarded></Protected>} />
        <Route path="/admin" element={<Protected><Guarded perm="audit_read"><Admin /></Guarded></Protected>} />
        <Route path="*" element={<Navigate to="/monitoring" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
