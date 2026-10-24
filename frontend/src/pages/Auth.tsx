import { useEffect, useRef, useState } from "react";
import type { SyntheticEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { LockKeyhole, Loader2 } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { authRequest } from "../services/http";
type Mode = "login" | "register" | "forgot-password" | "reset-password";
const titles = {login: "Chào mừng trở lại", register: "Tạo tài khoản", "forgot-password": "Quên mật khẩu?", "reset-password": "Đặt lại mật khẩu"};
const input = "mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 disabled:opacity-60";
export default function Auth({mode}: {mode: Mode}) {
  const {user, loading, signedIn, sessionEnded} = useAuth();
  const location = useLocation(); const navigate = useNavigate();
  const [email, setEmail] = useState(""); const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState(""); const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const token = useRef(new URLSearchParams(window.location.hash.slice(1)).get("token") || "");
  useEffect(() => {
    if (mode === "reset-password" && window.location.hash) window.history.replaceState(null, "", window.location.pathname);
  }, [mode]);
  const from = typeof location.state?.from === "string" && location.state.from.startsWith("/") && !location.state.from.startsWith("//") ? location.state.from : "/";
  if (!loading && user && (mode === "login" || mode === "register")) return <Navigate to={from} replace />;
  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setMessage("");
    if ((mode === "register" || mode === "reset-password") && password !== confirm) {setError("Mật khẩu xác nhận chưa khớp."); return;}
    if (mode === "reset-password" && !token.current) {setError("Thiếu liên kết đặt lại mật khẩu. Hãy yêu cầu email mới."); return;}
    setBusy(true);
    try {
      const body = mode === "register" ? {email, password, full_name: fullName} : mode === "forgot-password" ? {email} : mode === "reset-password" ? {token: token.current, password} : {email, password};
      const data = await authRequest(mode, body);
      if (mode === "login" || mode === "register") {signedIn(data.user); navigate(from, {replace: true});}
      else {if (mode === "reset-password") sessionEnded(); setMessage(data.message); setPassword(""); setConfirm("");}
    } catch (err) {setError(err instanceof Error ? err.message : "Không kết nối được backend.");}
    finally {setBusy(false);}
  }
  const passwordForm = mode !== "forgot-password";
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 py-12">
    <div className="w-full max-w-md">
      <div className="mb-7 text-center"><div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600 text-white"><LockKeyhole size={28} /></div><p className="text-sm font-semibold tracking-wide text-blue-700">CUSTOMER FEEDBACK AI</p><h1 className="mt-2 text-3xl font-bold text-slate-900">{titles[mode]}</h1><p className="mt-3 text-sm text-slate-500">{mode === "forgot-password" ? "Nhập email để nhận liên kết đặt lại mật khẩu." : mode === "reset-password" ? "Liên kết có hiệu lực 15 phút và chỉ dùng được một lần." : "Phân tích phản hồi khách hàng trong không gian riêng của bạn."}</p></div>
      <form onSubmit={submit} className="space-y-5 rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        {mode === "register" && <label className="block text-sm font-medium">Họ và tên<input required minLength={2} maxLength={100} autoComplete="name" value={fullName} onChange={e => setFullName(e.target.value)} disabled={busy} className={input} /></label>}
        {mode !== "reset-password" && <label className="block text-sm font-medium">Email<input type="email" required autoComplete="email" maxLength={320} value={email} onChange={e => setEmail(e.target.value)} disabled={busy} className={input} placeholder="ban@example.com" /></label>}
        {passwordForm && <label className="block text-sm font-medium">{mode === "reset-password" ? "Mật khẩu mới" : "Mật khẩu"}<input type="password" required minLength={mode === "login" ? 1 : 10} maxLength={128} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={e => setPassword(e.target.value)} disabled={busy} className={input} />{mode !== "login" && <span className="mt-1 block text-xs text-slate-500">Từ 10 đến 128 ký tự.</span>}</label>}
        {(mode === "register" || mode === "reset-password") && <label className="block text-sm font-medium">Xác nhận mật khẩu<input type="password" required minLength={10} maxLength={128} autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} disabled={busy} className={input} /></label>}
        {mode === "login" && <div className="text-right"><Link className="text-sm text-blue-700 hover:underline" to="/forgot-password">Quên mật khẩu?</Link></div>}
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {message && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
        {!(mode === "reset-password" && message) && <button disabled={busy || loading} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-60">{busy && <Loader2 size={18} className="animate-spin" />}{mode === "login" ? "Đăng nhập" : mode === "register" ? "Đăng ký" : mode === "forgot-password" ? "Gửi liên kết" : "Lưu mật khẩu mới"}</button>}
        <div className="text-center text-sm text-slate-500">{mode === "login" ? <>Chưa có tài khoản? <Link to="/register" className="font-semibold text-blue-700">Đăng ký</Link></> : <Link to="/login" className="font-semibold text-blue-700">Trở về đăng nhập</Link>}</div>
      </form>
      <p className="mt-6 text-center text-xs text-slate-400">Sản phẩm, đánh giá và lịch sử được lưu riêng theo tài khoản.</p>
    </div>
  </main>;
}
