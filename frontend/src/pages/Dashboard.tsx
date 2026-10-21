import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";

import {
  AlertTriangle,
  ArrowRight,
  Clock,
} from "lucide-react";

import SentimentChart from "../components/SentimentChart";
import IssueChart from "../components/IssueChart";
import StatCard from "../components/StatCard";

import {
  getProductAnalysis,
  type AnalysisHistoryItem,
} from "../services/api";

interface DashboardData {
  productName: string;
  totalReviews: number;
  historyId?: number | null;
  analyzedAt?: string | null;

  sentiment: {
    positive: number;
    negative: number;
    neutral: number;

    positiveRate: number;
    negativeRate: number;
    neutralRate: number;
  };

  issues: Array<{
    name: string;
    value: number;
  }>;
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "Không rõ thời gian";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatPercent(value?: number): string {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "0%";
  }

  return `${Math.round(value * 10) / 10}%`;
}

function getIssueLabel(issueType: string): string {
  const labels: Record<string, string> = {
    PRODUCT_QUALITY: "Chất lượng sản phẩm",
    SHIPPING_LOGISTICS: "Giao hàng và vận chuyển",
    CUSTOMER_SERVICE_RETURNS: "Dịch vụ khách hàng và đổi trả",
    PRICING_PROMOTIONS: "Giá cả và khuyến mãi",
  };

  return labels[issueType] || issueType;
}

function Dashboard() {
  const location = useLocation();
  const crawlWarning = (location.state as { crawlWarning?: string } | null)?.crawlWarning;
  const {
    productId: productIdFromParams,
  } = useParams();

  const [
    searchParams,
    setSearchParams,
  ] = useSearchParams();

  const historyIdFromQuery =
    searchParams.get("historyId");

  const productId =
    productIdFromParams ||
    searchParams.get("productId");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    histories,
    setHistories,
  ] = useState<AnalysisHistoryItem[]>([]);

  const [
    data,
    setData,
  ] = useState<DashboardData | null>(null);

  const [
    error,
    setError,
  ] = useState("");

  /*
   * ==========================================================
   * LOAD DASHBOARD
   * ==========================================================
   */

  useEffect(() => {
    async function fetchDashboard() {
      if (!productId) {
        setData(null);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const response = await getProductAnalysis(
          productId,
          historyIdFromQuery
        );

        console.log(
          "Dashboard product analysis:",
          response
        );

        const product =
          response.product;

        const analysis =
          response.analysis;

        setHistories(
          response.histories || []
        );

        const issues =
          Object.entries(
            analysis.issue_summary ?? {}
          )
            .map(
              ([name, value]) => ({
                name,
                value: Number(value) || 0,
              })
            )
            .sort(
              (a, b) =>
                b.value - a.value
            );

        const dashboardData: DashboardData = {
          productName:
            product?.name ||
            "Sản phẩm",

          totalReviews:
            analysis?.total_reviews || 0,

          historyId:
            analysis?.history_id ?? null,

          analyzedAt:
            analysis?.analyzed_at ?? null,

          sentiment: {
            positive:
              analysis?.positive_count || 0,

            negative:
              analysis?.negative_count || 0,

            neutral:
              analysis?.neutral_count || 0,

            positiveRate:
              analysis?.positive_rate || 0,

            negativeRate:
              analysis?.negative_rate || 0,

            neutralRate:
              analysis?.neutral_rate || 0,
          },

          issues,
        };

        setData(
          dashboardData
        );

        localStorage.removeItem(
          "activeProductId"
        );
      } catch (err) {
        console.error(
          "Lỗi khi tải Dashboard:",
          err
        );

        if (err instanceof Error) {
          setError(
            err.message
          );
        } else {
          setError(
            "Không thể tải dữ liệu phân tích sản phẩm."
          );
        }

        setData(null);
      } finally {
        setLoading(false);
      }
    }

    fetchDashboard();
  }, [
    productId,
    historyIdFromQuery,
  ]);

  const issueData = useMemo(() => {
    const result: Record<string, number> = {};

    if (!data) {
      return result;
    }

    data.issues.forEach((issue) => {
      result[
        getIssueLabel(issue.name)
      ] = issue.value;
    });

    return result;
  }, [
    data,
  ]);

  /*
   * ==========================================================
   * NO PRODUCT ID
   * ==========================================================
   */

  if (!productId) {
    return (
      <div className="
        flex
        min-h-[400px]
        items-center
        justify-center
      ">
        <div className="
          max-w-lg
          text-center
        ">
          <div className="
            mx-auto
            mb-4
            flex
            h-12
            w-12
            items-center
            justify-center
            rounded-full
            bg-orange-100
            text-orange-600
          ">
            <AlertTriangle className="
              h-6
              w-6
            " />
          </div>

          <h2 className="
            text-2xl
            font-bold
            text-slate-800
          ">
            Chưa chọn sản phẩm
          </h2>

          <p className="
            mt-3
            text-slate-500
          ">
            Vui lòng bắt đầu phân tích sản phẩm để xem dashboard.
          </p>

          <Link
            to="/analyze"
            className="
              mt-6
              inline-flex
              items-center
              gap-2
              rounded-xl
              bg-blue-600
              px-5
              py-3
              font-semibold
              text-white
              transition
              hover:bg-blue-700
            "
          >
            Bắt đầu phân tích
            <ArrowRight className="
              h-4
              w-4
            " />
          </Link>
        </div>
      </div>
    );
  }

  /*
   * ==========================================================
   * LOADING
   * ==========================================================
   */

  if (loading) {
    return (
      <div className="
        flex
        min-h-[400px]
        items-center
        justify-center
      ">
        <div className="
          rounded-2xl
          border
          border-slate-100
          bg-white
          p-8
          text-center
          shadow-sm
        ">
          <div className="
            mb-3
            text-lg
            font-semibold
            text-slate-700
          ">
            Đang tải dữ liệu dashboard...
          </div>

          <p className="
            text-sm
            text-slate-500
          ">
            Đang lấy dữ liệu phân tích sản phẩm từ database.
          </p>
        </div>
      </div>
    );
  }

  /*
   * ==========================================================
   * ERROR
   * ==========================================================
   */

  if (error) {
    return (
      <div className="
        flex
        min-h-[400px]
        items-center
        justify-center
      ">
        <div className="
          max-w-lg
          text-center
        ">
          <div className="
            mx-auto
            mb-4
            flex
            h-12
            w-12
            items-center
            justify-center
            rounded-full
            bg-red-100
            text-red-600
          ">
            <AlertTriangle className="
              h-6
              w-6
            " />
          </div>

          <h2 className="
            text-2xl
            font-bold
            text-slate-800
          ">
            Không thể tải dữ liệu
          </h2>

          <p className="
            mt-3
            text-sm
            text-red-600
          ">
            {error}
          </p>

          <Link
            to="/analyze"
            className="
              mt-6
              inline-flex
              items-center
              gap-2
              rounded-xl
              bg-blue-600
              px-5
              py-3
              font-semibold
              text-white
              transition
              hover:bg-blue-700
            "
          >
            Phân tích sản phẩm khác
            <ArrowRight className="
              h-4
              w-4
            " />
          </Link>
        </div>
      </div>
    );
  }

  /*
   * ==========================================================
   * NO DATA
   * ==========================================================
   */

  if (!data) {
    return (
      <div className="
        flex
        min-h-[400px]
        items-center
        justify-center
      ">
        <div className="
          max-w-lg
          text-center
        ">
          <div className="
            mx-auto
            mb-4
            flex
            h-12
            w-12
            items-center
            justify-center
            rounded-full
            bg-orange-100
            text-orange-600
          ">
            <AlertTriangle className="
              h-6
              w-6
            " />
          </div>

          <h2 className="
            text-2xl
            font-bold
            text-slate-800
          ">
            Chưa có dữ liệu phân tích
          </h2>

          <p className="
            mt-3
            text-slate-500
          ">
            Sản phẩm này chưa có dữ liệu phân tích trong database.
          </p>

          <Link
            to="/analyze"
            className="
              mt-6
              inline-flex
              items-center
              gap-2
              rounded-xl
              bg-blue-600
              px-5
              py-3
              font-semibold
              text-white
              transition
              hover:bg-blue-700
            "
          >
            Phân tích sản phẩm khác
            <ArrowRight className="
              h-4
              w-4
            " />
          </Link>
        </div>
      </div>
    );
  }

  /*
   * ==========================================================
   * DASHBOARD
   * ==========================================================
   */

  return (
    <div className="
      space-y-8
    ">
      {crawlWarning && (
        <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
          {crawlWarning}
        </p>
      )}
      <header>
        <p className="
          text-sm
          font-semibold
          text-blue-600
        ">
          Dashboard sản phẩm
        </p>

        <h1 className="
          mt-1
          text-3xl
          font-bold
          text-slate-900
        ">
          {data.productName}
        </h1>

        <p className="
          mt-2
          text-slate-500
        ">
          Tổng quan kết quả phân tích cảm xúc và các vấn đề thường gặp từ review sản phẩm.
        </p>
      </header>

      {/* BANNER THÔNG TIN LẦN PHÂN TÍCH */}
      <div className="flex flex-col gap-4 rounded-2xl border border-blue-100 bg-gradient-to-r from-blue-50/70 to-indigo-50/70 p-5 md:flex-row md:items-center md:justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
            <Clock className="h-5 w-5" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-700">
                Lần phân tích đang hiển thị
              </span>

              {data.historyId && histories.length > 0 && histories[0].id === data.historyId && (
                <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[10px] font-bold text-white">
                  Mới nhất
                </span>
              )}
            </div>

            <p className="mt-0.5 text-sm font-bold text-slate-900">
              {data.analyzedAt
                ? `Thời gian thực hiện: ${formatDate(data.analyzedAt)}`
                : "Dữ liệu phân tích snapshot cơ sở dữ liệu"}
            </p>
          </div>
        </div>

        {histories.length > 1 && (
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold text-slate-600 whitespace-nowrap">
              Chuyển lần phân tích:
            </label>

            <select
              value={data.historyId || ""}
              onChange={(e) => {
                const newHistoryId = e.target.value;

                if (newHistoryId) {
                  setSearchParams({ historyId: newHistoryId });
                } else {
                  setSearchParams({});
                }
              }}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-800 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            >
              {histories.map((h, idx) => {
                const runNum = histories.length - idx;
                const isNewest = idx === 0;

                return (
                  <option key={h.id} value={h.id}>
                    Lần #{runNum} ({formatDate(h.analyzed_at)}){isNewest ? " - Mới nhất" : ""}
                  </option>
                );
              })}
            </select>
          </div>
        )}
      </div>

      {/* THỐNG KÊ TỔNG QUAN */}
      <section
        className="
          grid
          grid-cols-1
          gap-5
          sm:grid-cols-2
          lg:grid-cols-4
        "
      >
        <StatCard
          title="Tổng số đánh giá"
          value={data.totalReviews}
        />

        <StatCard
          title="Tích cực"
          value={formatPercent(data.sentiment.positiveRate)}
        />

        <StatCard
          title="Tiêu cực"
          value={formatPercent(data.sentiment.negativeRate)}
        />

        <StatCard
          title="Trung lập"
          value={formatPercent(data.sentiment.neutralRate)}
        />
      </section>

      {/* 2 LƯỢC ĐỒ CHÍNH */}
      <section
        className="
          grid
          grid-cols-1
          gap-6
          lg:grid-cols-2
        "
      >
        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-6
            shadow-sm
          "
        >
          <div className="
            mb-5
            flex
            items-center
            justify-between
          ">
            <div>
              <h2 className="
                text-lg
                font-semibold
                text-slate-800
              ">
                Phân tích cảm xúc
              </h2>

              <p className="
                mt-1
                text-sm
                text-slate-500
              ">
                Phân bố Positive, Neutral và Negative.
              </p>
            </div>
          </div>

          <SentimentChart
            positive={data.sentiment.positive}
            negative={data.sentiment.negative}
            neutral={data.sentiment.neutral}
          />
        </div>

        <div
          className="
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-6
            shadow-sm
          "
        >
          <div className="
            mb-5
            flex
            items-center
            justify-between
          ">
            <div>
              <h2 className="
                text-lg
                font-semibold
                text-slate-800
              ">
                Các vấn đề thường gặp
              </h2>

              <p className="
                mt-1
                text-sm
                text-slate-500
              ">
                Nhóm issue được phát hiện từ review.
              </p>
            </div>
          </div>

          {data.issues.length === 0 ? (
            <div className="
              rounded-xl
              border
              border-dashed
              border-slate-200
              p-8
              text-center
              text-sm
              text-slate-500
            ">
              Chưa có issue nào được phát hiện.
            </div>
          ) : (
            <IssueChart
              data={issueData}
            />
          )}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
