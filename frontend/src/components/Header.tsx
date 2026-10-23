import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, UserRound } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
export default function Header() {
  const {user, logout} = useAuth(); const navigate = useNavigate();
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function leave() {setBusy(true); setError(""); try {await logout(); navigate("/login", {replace: true});} catch {setError("Đăng xuất chưa thành công. Thử lại.");} finally {setBusy(false);}}
  return <header className="fixed left-0 lg:left-72 right-0 top-0 z-30 flex h-20 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 sm:px-8"><div className="min-w-0"><h2 className="text-sm sm:text-xl font-semibold text-slate-900"><span className="sm:hidden">Sentiment AI</span><span className="hidden sm:inline">AI Customer Feedback Analysis</span></h2><p className="hidden sm:block text-sm text-slate-500">Phân tích phản hồi khách hàng</p></div><div className="flex shrink-0 items-center gap-2 sm:gap-4"><Link to="/account" aria-label={user?.full_name} className="flex items-center gap-2 text-sm hover:text-blue-700"><UserRound size={20} /><span className="hidden sm:inline">{user?.full_name}</span></Link><button type="button" disabled={busy} onClick={() => void leave()} className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-50"><LogOut size={18} />Đăng xuất</button>{error && <p role="alert" className="max-w-40 text-xs text-red-600">{error}</p>}</div></header>;
}
