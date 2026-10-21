import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { API_BASE_URL, authRequest } from "../services/http";
export type User = {id: number; email: string; full_name: string};
function clearProductState() {
  ["activeProductId", "lastAnalyzedProductUrl", "lastAnalyzedProductName"].forEach(key => localStorage.removeItem(key));
  Object.keys(sessionStorage).filter(key => key.startsWith("analysis-")).forEach(key => sessionStorage.removeItem(key));
}
const AuthContext = createContext<{user: User | null; loading: boolean; error: string; reload: () => Promise<void>; signedIn: (user: User) => void; logout: () => Promise<void>; sessionEnded: () => void} | null>(null);
export function AuthProvider({children}: {children: ReactNode}) {
  const channel = useRef<BroadcastChannel | null>(null);
  const revision = useRef(0);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function reload() {
    const current = ++revision.current;
    setLoading(true); setError("");
    try {
      const response = await fetch(API_BASE_URL + "/auth/me", {credentials: "include"});
      if (current !== revision.current) return;
      if (response.status === 401) setUser(null);
      else if (!response.ok) throw new Error("Backend chưa sẵn sàng. Hãy kiểm tra dịch vụ và thử lại.");
      else setUser((await response.json()).user);
    } catch {if (current === revision.current) setError("Không kết nối được backend. Hãy kiểm tra dịch vụ và thử lại.");}
    finally {if (current === revision.current) setLoading(false);}
  }
  function sessionEnded() {
    revision.current++; clearProductState(); setUser(null); setError(""); setLoading(false);
    channel.current?.postMessage("changed");
  }
  useEffect(() => {
    const sync = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("duancntt-auth") : null;
    channel.current = sync;
    if (sync) sync.onmessage = () => {clearProductState(); setUser(null); void reload();};
    void reload();
    const expired = () => sessionEnded();
    window.addEventListener("auth-expired", expired);
    return () => {revision.current++; sync?.close(); channel.current = null; window.removeEventListener("auth-expired", expired);};
  }, []);
  function signedIn(value: User) {
    revision.current++; clearProductState(); setError(""); setLoading(false); setUser(value);
    channel.current?.postMessage("changed");
  }
  async function logout() {await authRequest("logout"); sessionEnded();}
  return <AuthContext.Provider value={{user, loading, error, reload, signedIn, logout, sessionEnded}}>{children}</AuthContext.Provider>;
}
export function useAuth() {const value = useContext(AuthContext); if (!value) throw new Error("AuthProvider missing"); return value;}
export function RequireAuth() {
  const {user, loading, error, reload} = useAuth();
  const location = useLocation();
  if (loading) return <div className="p-10 text-center" role="status">Đang kiểm tra phiên đăng nhập...</div>;
  if (error) return <div className="p-10 text-center"><p role="alert">{error}</p><button className="mt-4 text-blue-700 underline" onClick={() => void reload()}>Thử lại</button></div>;
  if (!user) return <Navigate to="/login" replace state={{from: location.pathname + location.search}} />;
  return <Outlet />;
}
