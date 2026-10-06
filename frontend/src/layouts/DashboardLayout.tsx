import type {
  ReactNode,
} from "react";

import Header from "../components/Header";
import Sidebar from "../components/Sidebar";

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
          ml-72
          min-h-screen
          px-8
          pb-8
          pt-32
        "
      >
        {children}
      </main>
    </div>
  );
}

export default DashboardLayout;