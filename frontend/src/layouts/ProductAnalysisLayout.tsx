import {
  AlertTriangle,
  BarChart3,
  FileText,
  LayoutDashboard,
  RefreshCcw,
  ShieldAlert,
  Users,
} from "lucide-react";

import {
  NavLink,
  Outlet,
  useNavigate,
  useParams,
} from "react-router-dom";

function ProductAnalysisLayout() {
  const {
    productId,
  } = useParams();

  const navigate =
    useNavigate();

  const tabClass = ({
    isActive,
  }: {
    isActive: boolean;
  }) => {
    return `
      flex
      items-center
      gap-2
      rounded-xl
      px-4
      py-2.5
      text-sm
      font-semibold
      transition
      ${
        isActive
          ? "bg-blue-600 text-white"
          : "bg-white text-slate-600 hover:bg-slate-50"
      }
    `;
  };

  if (!productId) {
    return (
      <div className="
        rounded-2xl
        border
        border-red-100
        bg-red-50
        p-6
        text-red-700
      ">
        <div className="
          flex
          items-center
          gap-2
          font-semibold
        ">
          <AlertTriangle className="
            h-5
            w-5
          " />
          Thiếu productId.
        </div>

        <p className="
          mt-2
          text-sm
        ">
          Vui lòng quay lại trang phân tích sản phẩm.
        </p>
      </div>
    );
  }

  return (
    <div className="
      space-y-6
    ">
      <section className="
        rounded-2xl
        border
        border-slate-100
        bg-white
        p-6
        shadow-sm
      ">
        <div className="
          flex
          flex-col
          gap-4
          lg:flex-row
          lg:items-center
          lg:justify-between
        ">
          <div>
            <p className="
              text-sm
              font-semibold
              text-blue-600
            ">
              Product ID: {productId}
            </p>

            <h1 className="
              mt-1
              text-2xl
              font-bold
              text-slate-900
            ">
              Kết quả phân tích sản phẩm
            </h1>

            <p className="
              mt-1
              text-sm
              text-slate-500
            ">
              Xem tổng quan, đánh giá khách hàng, nguyên nhân tiêu cực và cảnh báo rủi ro.
            </p>
          </div>

          <button
            type="button"
            onClick={() => navigate("/analyze")}
            className="
              inline-flex
              items-center
              justify-center
              gap-2
              rounded-xl
              bg-blue-600
              px-5
              py-3
              text-sm
              font-semibold
              text-white
              transition
              hover:bg-blue-700
            "
          >
            <RefreshCcw className="
              h-4
              w-4
            " />
            Phân tích sản phẩm khác
          </button>
        </div>

        <div className="
          mt-6
          flex
          flex-wrap
          gap-3
        ">
          <NavLink
            to={`/products/${productId}/dashboard`}
            className={tabClass}
          >
            <LayoutDashboard className="
              h-4
              w-4
            " />
            Tổng quan
          </NavLink>

          <NavLink
            to={`/products/${productId}/reviews`}
            className={tabClass}
          >
            <FileText className="
              h-4
              w-4
            " />
            Đánh giá khách hàng
          </NavLink>

          <NavLink
            to={`/products/${productId}/issues`}
            className={tabClass}
          >
            <BarChart3 className="
              h-4
              w-4
            " />
            Nguyên nhân tiêu cực
          </NavLink>

          <NavLink
            to={`/products/${productId}/risk`}
            className={tabClass}
          >
            <ShieldAlert className="
              h-4
              w-4
            " />
            Cảnh báo rủi ro
          </NavLink>

          <NavLink
            to={`/products/${productId}/competitor`}
            className={tabClass}
          >
            <Users className="
              h-4
              w-4
            " />
            Phân tích cạnh tranh
          </NavLink>
        </div>
      </section>

      <Outlet />
    </div>
  );
}

export default ProductAnalysisLayout;