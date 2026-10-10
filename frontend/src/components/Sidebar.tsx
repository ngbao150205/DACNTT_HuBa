import {
  History,
  Home,
  PlayCircle,
} from "lucide-react";

import {
  NavLink,
} from "react-router-dom";

function Sidebar() {
  const navItemClass = ({
    isActive,
  }: {
    isActive: boolean;
  }) => {
    return `
      flex
      items-center
      gap-3
      rounded-xl
      px-4
      py-3
      text-sm
      font-medium
      transition
      ${
        isActive
          ? "bg-blue-600 text-white"
          : "text-slate-300 hover:bg-slate-800 hover:text-white"
      }
    `;
  };

  return (
    <aside
      className="
        fixed
        bottom-0
        left-0
        top-0
        z-40
        flex
        w-72
        flex-col
        overflow-hidden
        bg-slate-950
        px-5
        py-6
        text-white
      "
    >
      <div className="mb-10 shrink-0">
        <h1 className="text-2xl font-bold">
          Sentiment AI
        </h1>

        <p className="mt-1 text-sm text-slate-400">
          Customer Feedback Analytics
        </p>
      </div>

      <nav className="shrink-0 space-y-2">
        <NavLink
          to="/"
          end
          className={navItemClass}
        >
          <Home className="h-5 w-5" />
          Trang chủ
        </NavLink>

        <NavLink
          to="/analyze"
          className={navItemClass}
        >
          <PlayCircle className="h-5 w-5" />
          Bắt đầu phân tích
        </NavLink>

        <NavLink
          to="/history"
          className={navItemClass}
        >
          <History className="h-5 w-5" />
          Lịch sử phân tích
        </NavLink>
      </nav>

      <div className="mt-auto shrink-0 rounded-2xl bg-slate-900 p-4">
        <p className="text-xs font-semibold text-slate-300">
          Hệ thống phân tích AI
        </p>

        <p className="mt-1 text-xs leading-5 text-slate-500">
          Phân tích sentiment, nguyên nhân tiêu cực và cảnh báo rủi ro từ review sản phẩm.
        </p>
      </div>
    </aside>
  );
}

export default Sidebar;