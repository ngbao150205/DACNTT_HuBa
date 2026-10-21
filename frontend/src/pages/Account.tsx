import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
export default function Account() {
  const {user} = useAuth();
  return <div className="mx-auto max-w-2xl space-y-6">
    <h1 className="text-3xl font-bold">Tài khoản</h1>
    <section className="space-y-4 rounded-2xl border bg-white p-6">
      <div><h2 className="font-semibold">{user?.full_name}</h2><p className="mt-2 text-slate-500">{user?.email}</p></div>
      <p className="text-sm text-slate-500">Sản phẩm, đánh giá và lịch sử được lưu riêng cho tài khoản của bạn.</p>
      <Link to="/forgot-password" className="inline-block text-sm font-semibold text-blue-700 hover:underline">Đặt lại mật khẩu qua email</Link>
    </section>
  </div>;
}
