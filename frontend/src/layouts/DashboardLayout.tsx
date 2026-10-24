import type {
  ReactNode,
} from "react";

import Header from "../components/Header";
import Sidebar from "../components/Sidebar";
import { NavLink } from "react-router-dom";

interface DashboardLayoutProps {
  children: ReactNode;
}

function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-100">
      <Sidebar />

      <Header />

      <main
        className="
          lg:ml-72
          min-h-screen
          px-4 sm:px-8
          pb-24 lg:pb-8
          pt-28 lg:pt-32
        "
      >
        {children}
      </main>
      <nav aria-label="Điều hướng chính trên điện thoại" className="fixed bottom-0 left-0 right-0 z-40 flex justify-around border-t border-slate-200 bg-white p-2 lg:hidden">
        {[["/", "Trang chủ"], ["/analyze", "Phân tích"], ["/history", "Lịch sử"]].map(([to, label]) => <NavLink key={to} to={to} end className={({ isActive }) => `rounded-xl px-4 py-3 text-sm font-semibold ${isActive ? "bg-blue-50 text-blue-700" : "text-slate-600"}`}>{label}</NavLink>)}
      </nav>
    </div>
  );
}

export default DashboardLayout;
