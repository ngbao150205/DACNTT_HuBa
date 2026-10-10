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
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Clock,
  MessageSquareText,
  Search,
  ShieldAlert,
  Star,
} from "lucide-react";

import StatCard from "../components/StatCard";
import SentimentChart from "../components/SentimentChart";
import IssueChart from "../components/IssueChart";

import {
  getProductAnalysis,
  getProductReviews,
  type AnalysisHistoryItem,
  type ProductReview,
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

function getReviewSentiment(review: ProductReview): string {
  if (
    review.sentiment &&
    typeof review.sentiment !== "string" &&
    review.sentiment.sentiment
  ) {
    return review.sentiment.sentiment;
  }
  return "";
}

function getSentimentBadge(sentiment: string) {
  if (sentiment === "Positive") {
    return {
      label: "Tích cực",
      className: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    };
  }
  if (sentiment === "Negative") {
    return {
      label: "Tiêu cực",
      className: "bg-rose-50 text-rose-700 border border-rose-200",
    };
  }
  if (sentiment === "Neutral") {
    return {
      label: "Trung tính",
      className: "bg-amber-50 text-amber-700 border border-amber-200",
    };
  }
  return {
    label: "Chưa phân tích",
    className: "bg-slate-100 text-slate-600 border border-slate-200",
  };
}

function Dashboard() {
  const location = useLocation();

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
    dashboardReviews,
    setDashboardReviews,
  ] = useState<ProductReview[]>([]);

  const [
    loadingReviews,
    setLoadingReviews,
  ] = useState(false);

  const [
    selectedRating,
    setSelectedRating,
  ] = useState<number | "ALL">("ALL");

  const [
    selectedSentimentFilter,
    setSelectedSentimentFilter,
  ] = useState<"ALL" | "Positive" | "Neutral" | "Negative">("ALL");

  const [
    reviewSearchText,
    setReviewSearchText,
  ] = useState("");

  const [
    reviewPage,
    setReviewPage,
  ] = useState(1);

  const REVIEWS_PER_PAGE = 5;

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
      setLoadingReviews(true);

      try {
        const [response, reviewsResponse] = await Promise.all([
          getProductAnalysis(
            productId,
            historyIdFromQuery
          ),
          getProductReviews(
            productId,
            1,
            100
          ).catch((err) => {
            console.warn("Lỗi khi tải reviews cho dashboard:", err);
            return { reviews: [] };
          }),
        ]);

        setDashboardReviews(
          reviewsResponse.reviews || []
        );
        setLoadingReviews(false);

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

  const topIssues = useMemo(() => {
    if (!data) {
      return [];
    }

    return data.issues.slice(0, 4);
  }, [
    data,
  ]);

  const ratingCounts = useMemo(() => {
    const counts: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    for (const r of dashboardReviews) {
      const star = Math.max(1, Math.min(5, Math.round(r.rating || 0)));
      counts[star] = (counts[star] || 0) + 1;
    }
    return counts;
  }, [dashboardReviews]);

  const filteredDashboardReviews = useMemo(() => {
    const q = reviewSearchText.trim().toLowerCase();
    return dashboardReviews.filter((r) => {
      if (selectedRating !== "ALL") {
        const star = Math.max(1, Math.min(5, Math.round(r.rating || 0)));
        if (star !== selectedRating) return false;
      }
      if (selectedSentimentFilter !== "ALL") {
        const sent = getReviewSentiment(r);
        if (sent !== selectedSentimentFilter) return false;
      }
      if (q) {
        const content = (r.content || "").toLowerCase();
        if (!content.includes(q)) return false;
      }
      return true;
    });
  }, [
    dashboardReviews,
    selectedRating,
    selectedSentimentFilter,
    reviewSearchText,
  ]);

  const totalReviewPages = useMemo(() => {
    return Math.max(
      1,
      Math.ceil(filteredDashboardReviews.length / REVIEWS_PER_PAGE)
    );
  }, [filteredDashboardReviews.length]);

  const pagedReviews = useMemo(() => {
    const safePage = Math.min(reviewPage, totalReviewPages);
    const start = (safePage - 1) * REVIEWS_PER_PAGE;
    return filteredDashboardReviews.slice(start, start + REVIEWS_PER_PAGE);
  }, [filteredDashboardReviews, reviewPage, totalReviewPages]);

  useEffect(() => {
    setReviewPage(1);
  }, [selectedRating, selectedSentimentFilter, reviewSearchText]);

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
          Tổng quan kết quả phân tích sentiment, nguyên nhân tiêu cực và dữ liệu cảnh báo.
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

      <section className="
        grid
        grid-cols-1
        gap-5
        md:grid-cols-3
      ">
        <Link
          to={`/products/${productId}/reviews`}
          className="
            group
            rounded-2xl
            border
            border-slate-100
            bg-white
            p-6
            shadow-sm
            transition
            hover:border-blue-200
            hover:bg-blue-50
          "
        >
          <div className="
            mb-4
            flex
            h-11
            w-11
            items-center
            justify-center
            rounded-xl
            bg-blue-100
            text-blue-700
          ">
            <MessageSquareText className="
              h-5
              w-5
            " />
          </div>

          <h3 className="
            font-bold
            text-slate-900
          ">
            Đánh giá khách hàng
          </h3>

          <p className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          ">
            Xem toàn bộ review, rating và sentiment của khách hàng.
          </p>
        </Link>

        <Link
          to={`/products/${productId}/issues`}
          className="
            group
            rounded-2xl
            border
            border-slate-100
            bg-white
            p-6
            shadow-sm
            transition
            hover:border-blue-200
            hover:bg-blue-50
          "
        >
          <div className="
            mb-4
            flex
            h-11
            w-11
            items-center
            justify-center
            rounded-xl
            bg-orange-100
            text-orange-700
          ">
            <BarChart3 className="
              h-5
              w-5
            " />
          </div>

          <h3 className="
            font-bold
            text-slate-900
          ">
            Nguyên nhân tiêu cực
          </h3>

          <p className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          ">
            Theo dõi các nhóm vấn đề được phát hiện trong review.
          </p>
        </Link>

        <Link
          to={`/products/${productId}/risk`}
          className="
            group
            rounded-2xl
            border
            border-slate-100
            bg-white
            p-6
            shadow-sm
            transition
            hover:border-blue-200
            hover:bg-blue-50
          "
        >
          <div className="
            mb-4
            flex
            h-11
            w-11
            items-center
            justify-center
            rounded-xl
            bg-red-100
            text-red-700
          ">
            <ShieldAlert className="
              h-5
              w-5
            " />
          </div>

          <h3 className="
            font-bold
            text-slate-900
          ">
            Cảnh báo rủi ro
          </h3>

          <p className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          ">
            Kiểm tra các review có dấu hiệu rủi ro cao hoặc trung bình.
          </p>
        </Link>
      </section>

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

      {topIssues.length > 0 && (
        <section className="
          rounded-2xl
          border
          border-slate-100
          bg-white
          p-6
          shadow-sm
        ">
          <div className="
            mb-5
          ">
            <h2 className="
              text-lg
              font-semibold
              text-slate-800
            ">
              Top nguyên nhân cần theo dõi
            </h2>

            <p className="
              mt-1
              text-sm
              text-slate-500
            ">
              Các nhóm vấn đề xuất hiện nhiều nhất trong dữ liệu hiện tại.
            </p>
          </div>

          <div className="
            grid
            grid-cols-1
            gap-4
            md:grid-cols-2
            lg:grid-cols-4
          ">
            {topIssues.map((issue) => (
              <div
                key={issue.name}
                className="
                  rounded-xl
                  bg-slate-50
                  p-4
                "
              >
                <p className="
                  text-sm
                  font-semibold
                  text-slate-800
                ">
                  {getIssueLabel(issue.name)}
                </p>

                <p className="
                  mt-2
                  text-2xl
                  font-bold
                  text-slate-900
                ">
                  {issue.value}
                </p>

                <p className="
                  mt-1
                  text-xs
                  text-slate-500
                ">
                  {issue.name}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ========================================================
          PHẦN ĐÁNH GIÁ KHÁCH HÀNG & BỘ LỌC THEO SỐ SAO (1 - 5 SAO)
          ======================================================== */}
      <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <MessageSquareText className="h-5 w-5 text-blue-600" />
              <h2 className="text-xl font-bold text-slate-900">
                Đánh giá khách hàng
              </h2>
              <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
                {filteredDashboardReviews.length} / {dashboardReviews.length} đánh giá
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Xem và lọc phản hồi khách hàng theo số sao đánh giá (1 - 5 sao) và nhãn cảm xúc.
            </p>
          </div>

          <Link
            to={{
              pathname: `/products/${productId}/reviews`,
              search: location.search,
            }}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            Trang Đánh giá chi tiết
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* BỘ LỌC SỐ SAO 1 - 5 SAO */}
        <div className="mb-5 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <span className="mr-1 text-xs font-bold uppercase tracking-wider text-slate-500">
                Lọc số sao:
              </span>

              <button
                type="button"
                onClick={() => setSelectedRating("ALL")}
                className={`rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                  selectedRating === "ALL"
                    ? "bg-slate-900 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Tất cả ({dashboardReviews.length})
              </button>

              {[5, 4, 3, 2, 1].map((stars) => {
                const count = ratingCounts[stars] || 0;
                const isSelected = selectedRating === stars;
                return (
                  <button
                    key={stars}
                    type="button"
                    onClick={() => setSelectedRating(stars)}
                    className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                      isSelected
                        ? "bg-amber-500 text-white shadow-sm ring-2 ring-amber-300"
                        : "border border-amber-200 bg-amber-50/60 text-amber-800 hover:bg-amber-100/80"
                    }`}
                  >
                    <span>{stars}</span>
                    <Star
                      className={`h-3.5 w-3.5 ${
                        isSelected
                          ? "fill-white text-white"
                          : "fill-amber-400 text-amber-400"
                      }`}
                    />
                    <span
                      className={`rounded-full px-1.5 py-0.2 text-[10px] ${
                        isSelected
                          ? "bg-amber-600 text-white"
                          : "bg-amber-200/60 text-amber-900"
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Ô TÌM KIẾM BÌNH LUẬN */}
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={reviewSearchText}
                onChange={(e) => setReviewSearchText(e.target.value)}
                placeholder="Tìm từ khóa trong review..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-xs outline-none transition focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </div>

          {/* BỘ LỌC CẢM XÚC PHỤ TRỢ */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs">
            <span className="mr-1 font-medium text-slate-400">Cảm xúc:</span>
            {(["ALL", "Positive", "Neutral", "Negative"] as const).map((sent) => {
              const isSelected = selectedSentimentFilter === sent;
              const labels: Record<string, string> = {
                ALL: "Tất cả",
                Positive: "Tích cực",
                Neutral: "Trung tính",
                Negative: "Tiêu cực",
              };
              return (
                <button
                  key={sent}
                  type="button"
                  onClick={() => setSelectedSentimentFilter(sent)}
                  className={`rounded-lg px-2.5 py-1 transition ${
                    isSelected
                      ? "bg-blue-600 text-white font-medium shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {labels[sent]}
                </button>
              );
            })}
          </div>
        </div>

        {/* DANH SÁCH BÌNH LUẬN */}
        {loadingReviews ? (
          <div className="py-12 text-center text-sm text-slate-500">
            Đang tải dữ liệu đánh giá...
          </div>
        ) : filteredDashboardReviews.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center">
            <p className="text-sm font-medium text-slate-600">
              Không tìm thấy bình luận nào phù hợp với bộ lọc số sao này.
            </p>
            <button
              type="button"
              onClick={() => {
                setSelectedRating("ALL");
                setSelectedSentimentFilter("ALL");
                setReviewSearchText("");
              }}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-200"
            >
              Đặt lại bộ lọc
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {pagedReviews.map((review, idx) => {
              const rating = Math.max(1, Math.min(5, Math.round(review.rating || 0)));
              const sentiment = getReviewSentiment(review);
              const badge = getSentimentBadge(sentiment);

              return (
                <div
                  key={review.id || review.review_id || idx}
                  className="rounded-xl border border-slate-100 bg-slate-50/60 p-4 transition hover:border-blue-200 hover:bg-white"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      {/* HIỂN THỊ SAO VÀNG */}
                      <div className="flex items-center">
                        {[1, 2, 3, 4, 5].map((starIdx) => (
                          <Star
                            key={starIdx}
                            className={`h-4 w-4 ${
                              starIdx <= rating
                                ? "fill-amber-400 text-amber-400"
                                : "text-slate-200"
                            }`}
                          />
                        ))}
                      </div>

                      <span className="text-xs font-bold text-slate-700">
                        {rating}/5 sao
                      </span>

                      {review.review_date && (
                        <span className="text-xs text-slate-400">
                          · {formatDate(review.review_date)}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${badge.className}`}>
                        {badge.label}
                      </span>
                    </div>
                  </div>

                  <p className="text-sm text-slate-800 leading-relaxed break-words">
                    {review.content || (
                      <span className="italic text-slate-400">(Khách hàng không để lại nhận xét văn bản)</span>
                    )}
                  </p>

                  {/* CÁC THẺ ISSUES & RISK NẾU CÓ */}
                  {((review.issues && review.issues.length > 0) || (review.risk && review.risk.risk_flag)) && (
                    <div className="mt-2.5 flex flex-wrap gap-1.5 pt-2 border-t border-slate-200/60 text-xs">
                      {review.issues?.map((iss, iIdx) => (
                        <span
                          key={iIdx}
                          className="rounded-md border border-orange-200 bg-orange-50 px-2 py-0.5 text-[11px] font-medium text-orange-700"
                        >
                          {getIssueLabel(iss.issue_type)}
                          {iss.matched_keyword && `: ${iss.matched_keyword}`}
                        </span>
                      ))}

                      {review.risk?.risk_flag && (
                        <span className="rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700">
                          Rủi ro {review.risk.risk_level || "Cao"}
                          {review.risk.risk_keyword && `: ${review.risk.risk_keyword}`}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* PHÂN TRANG CHO PHẦN BÌNH LUẬN TRÊN DASHBOARD */}
            {totalReviewPages > 1 && (
              <div className="mt-4 flex items-center justify-between pt-3 border-t border-slate-100 text-xs text-slate-500">
                <span>
                  Hiển thị {(reviewPage - 1) * REVIEWS_PER_PAGE + 1} -{" "}
                  {Math.min(reviewPage * REVIEWS_PER_PAGE, filteredDashboardReviews.length)} trên{" "}
                  {filteredDashboardReviews.length} đánh giá
                </span>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={reviewPage === 1}
                    onClick={() => setReviewPage((p) => Math.max(1, p - 1))}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Trước
                  </button>

                  <span className="px-2 font-medium">
                    Trang {reviewPage} / {totalReviewPages}
                  </span>

                  <button
                    type="button"
                    disabled={reviewPage === totalReviewPages}
                    onClick={() => setReviewPage((p) => Math.min(totalReviewPages, p + 1))}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none"
                  >
                    Sau
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default Dashboard;