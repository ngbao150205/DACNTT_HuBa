import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Link,
  useParams,
  useSearchParams,
} from "react-router-dom";

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  MessageSquareText,
  ShieldAlert,
} from "lucide-react";

import StatCard from "../components/StatCard";
import SentimentChart from "../components/SentimentChart";
import IssueChart from "../components/IssueChart";

import {
  getProductAnalysis,
} from "../services/api";

interface DashboardData {
  productName: string;
  totalReviews: number;

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
  const {
    productId: productIdFromParams,
  } = useParams();

  const [
    searchParams,
  ] = useSearchParams();

  const productId =
    productIdFromParams ||
    searchParams.get("productId");

  const [
    loading,
    setLoading,
  ] = useState(false);

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
        const response =
          await getProductAnalysis(
            productId
          );

        console.log(
          "Dashboard product analysis:",
          response
        );

        const product =
          response.product;

        const analysis =
          response.analysis;

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

        localStorage.setItem(
          "activeProductId",
          String(productId)
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
    </div>
  );
}

export default Dashboard;