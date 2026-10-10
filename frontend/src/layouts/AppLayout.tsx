import {
  Home,
  History,
  PlayCircle,
} from "lucide-react";

import {
  NavLink,
  Outlet,
} from "react-router-dom";

function AppLayout() {
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
    <div className="
      flex
      min-h-screen
      bg-slate-100
    ">
      <aside className="
        fixed
        left-0
        top-0
        z-40
        flex
        h-screen
        w-72
        flex-col
        bg-slate-950
        px-5
        py-6
        text-white
      ">
        <div className="
          mb-10
        ">
          <h1 className="
            text-2xl
            font-bold
          ">
            Sentiment AI
          </h1>

          <p className="
            mt-1
            text-sm
            text-slate-400
          ">
            Customer Feedback Analytics
          </p>
        </div>

        <nav className="
          space-y-2
        ">
          <NavLink
            to="/"
            end
            className={navItemClass}
          >
            <Home className="
              h-5
              w-5
            " />
            Trang chủ
          </NavLink>

          <NavLink
            to="/analyze"
            className={navItemClass}
          >
            <PlayCircle className="
              h-5
              w-5
            " />
            Bắt đầu phân tích
          </NavLink>

          <NavLink
            to="/history"
            className={navItemClass}
          >
            <History className="
              h-5
              w-5
            " />
            Lịch sử phân tích
          </NavLink>
        </nav>

        <div className="
          mt-auto
          rounded-2xl
          bg-slate-900
          p-4
        ">
          <p className="
            text-xs
            font-semibold
            text-slate-300
          ">
            Hệ thống phân tích AI
          </p>

          <p className="
            mt-1
            text-xs
            leading-5
            text-slate-500
          ">
            Phân tích sentiment, nguyên nhân tiêu cực và cảnh báo rủi ro từ review sản phẩm.
          </p>
        </div>
      </aside>

      <div className="
        ml-72
        flex
        min-h-screen
        flex-1
        flex-col
      ">
        <header className="
          sticky
          top-0
          z-30
          flex
          h-20
          items-center
          justify-between
          border-b
          border-slate-200
          bg-white
          px-8
        ">
          <div>
            <h2 className="
              text-xl
              font-bold
              text-slate-900
            ">
              AI Customer Feedback Analysis
            </h2>

            <p className="
              text-sm
              text-slate-500
            ">
              Theo dõi phản hồi khách hàng theo thời gian thực
            </p>
          </div>

          <div className="
            flex
            items-center
            gap-3
          ">
            <div className="
              hidden
              rounded-xl
              bg-slate-100
              px-4
              py-2
              text-sm
              text-slate-500
              md:block
            ">
              Tìm kiếm...
            </div>

            <div className="
              flex
              h-10
              w-10
              items-center
              justify-center
              rounded-full
              bg-blue-600
              text-sm
              font-bold
              text-white
            ">
              A
            </div>
          </div>
        </header>

        <main className="
          flex-1
          p-8
        ">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppLayout;