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
  Search,
} from "lucide-react";

import {
  getProductReviews,
  type ProductReview,
} from "../services/api";

type RiskLevelFilter = "ALL" | "HIGH" | "MEDIUM";

const BACKEND_PAGE_SIZE = 100;
const CLIENT_PAGE_SIZE = 10;

function getReviewDisplayId(review: ProductReview): string | number {
  return review.review_id || review.id;
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

function getReviewConfidence(review: ProductReview): number | null {
  if (
    review.sentiment &&
    typeof review.sentiment !== "string" &&
    typeof review.sentiment.confidence === "number"
  ) {
    return review.sentiment.confidence;
  }

  return null;
}

function getSentimentBadgeClass(sentiment: string): string {
  if (sentiment === "Positive") {
    return "bg-green-100 text-green-700";
  }

  if (sentiment === "Negative") {
    return "bg-red-100 text-red-700";
  }

  return "bg-slate-100 text-slate-700";
}

function getRiskBadgeClass(riskLevel?: string | null): string {
  if (riskLevel === "HIGH") {
    return "bg-red-100 text-red-700";
  }

  if (riskLevel === "MEDIUM") {
    return "bg-orange-100 text-orange-700";
  }

  return "bg-slate-100 text-slate-700";
}

function getStars(rating?: number | null): string {
  const safeRating = Math.max(
    0,
    Math.min(
      5,
      rating ?? 0
    )
  );

  return "★".repeat(safeRating);
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "Không rõ ngày";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function Risk() {
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
    reviews,
    setReviews,
  ] = useState<ProductReview[]>(
    []
  );

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    loadingProgress,
    setLoadingProgress,
  ] = useState("");

  const [
    error,
    setError,
  ] = useState("");

  const [
    totalReviews,
    setTotalReviews,
  ] = useState(0);

  const [
    selectedRiskLevel,
    setSelectedRiskLevel,
  ] = useState<RiskLevelFilter>("ALL");

  const [
    searchText,
    setSearchText,
  ] = useState("");

  const [
    clientPage,
    setClientPage,
  ] = useState(1);

  useEffect(() => {
    async function fetchAllReviews() {
      if (!productId) {
        setReviews([]);
        setTotalReviews(0);
        return;
      }

      setLoading(true);
      setError("");
      setLoadingProgress("Đang tải page 1...");

      try {
        const firstResponse =
          await getProductReviews(
            productId,
            1,
            BACKEND_PAGE_SIZE
          );

        let allReviews =
          firstResponse.reviews || [];

        const totalPages =
          firstResponse.pagination?.total_pages || 1;

        const total =
          firstResponse.pagination?.total_reviews ||
          allReviews.length;

        setTotalReviews(total);

        if (totalPages > 1) {
          for (
            let page = 2;
            page <= totalPages;
            page += 1
          ) {
            setLoadingProgress(
              `Đang tải page ${page}/${totalPages}...`
            );

            const response =
              await getProductReviews(
                productId,
                page,
                BACKEND_PAGE_SIZE
              );

            allReviews = [
              ...allReviews,
              ...(response.reviews || []),
            ];
          }
        }

        setReviews(allReviews);
        setClientPage(1);

        localStorage.removeItem(
          "activeProductId"
        );
      } catch (err) {
        console.error(
          "Lỗi khi tải risk reviews:",
          err
        );

        if (
          err instanceof Error
        ) {
          setError(
            err.message
          );
        } else {
          setError(
            "Không thể tải dữ liệu rủi ro."
          );
        }

        setReviews([]);
        setTotalReviews(0);
      } finally {
        setLoading(false);
        setLoadingProgress("");
      }
    }

    fetchAllReviews();
  }, [
    productId,
  ]);

  const riskReviews = useMemo(() => {
    return reviews.filter((review) => {
      return review.risk?.risk_flag === true;
    });
  }, [
    reviews,
  ]);

  const riskSummary = useMemo(() => {
    const summary: Record<RiskLevelFilter, number> = {
      ALL: riskReviews.length,
      HIGH: 0,
      MEDIUM: 0,
    };

    for (const review of riskReviews) {
      const riskLevel =
        review.risk?.risk_level;

      if (
        riskLevel === "HIGH" ||
        riskLevel === "MEDIUM"
      ) {
        summary[riskLevel] += 1;
      }
    }

    return summary;
  }, [
    riskReviews,
  ]);

  const filteredRiskReviews = useMemo(() => {
    const query =
      searchText
        .trim()
        .toLowerCase();

    return riskReviews.filter((review) => {
      const riskLevel =
        review.risk?.risk_level || "";

      const riskKeyword =
        review.risk?.risk_keyword || "";

      const sentiment =
        getReviewSentiment(review);

      const content =
        review.content || "";

      const reviewId =
        String(
          getReviewDisplayId(review)
        );

      const matchRiskLevel =
        selectedRiskLevel === "ALL" ||
        riskLevel === selectedRiskLevel;

      const matchSearch =
        query === "" ||
        content.toLowerCase().includes(query) ||
        reviewId.toLowerCase().includes(query) ||
        riskLevel.toLowerCase().includes(query) ||
        riskKeyword.toLowerCase().includes(query) ||
        sentiment.toLowerCase().includes(query);

      return matchRiskLevel && matchSearch;
    });
  }, [
    riskReviews,
    selectedRiskLevel,
    searchText,
  ]);

  const clientTotalPages = useMemo(() => {
    return Math.max(
      1,
      Math.ceil(
        filteredRiskReviews.length / CLIENT_PAGE_SIZE
      )
    );
  }, [
    filteredRiskReviews.length,
  ]);

  const paginatedRiskReviews = useMemo(() => {
    const safePage = Math.min(
      clientPage,
      clientTotalPages
    );

    const start =
      (safePage - 1) * CLIENT_PAGE_SIZE;

    const end =
      start + CLIENT_PAGE_SIZE;

    return filteredRiskReviews.slice(
      start,
      end
    );
  }, [
    filteredRiskReviews,
    clientPage,
    clientTotalPages,
  ]);

  useEffect(() => {
    setClientPage(1);
  }, [
    selectedRiskLevel,
    searchText,
  ]);

  useEffect(() => {
    if (
      clientPage > clientTotalPages
    ) {
      setClientPage(
        clientTotalPages
      );
    }
  }, [
    clientPage,
    clientTotalPages,
  ]);

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
            mb-4
            text-4xl
          ">
            !
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
            Vui lòng bắt đầu phân tích sản phẩm để xem cảnh báo rủi ro.
          </p>

          <Link
            to="/analyze"
            className="
              mt-6
              inline-block
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
          </Link>
        </div>
      </div>
    );
  }

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
            Đang tải dữ liệu rủi ro...
          </div>

          <p className="
            text-sm
            text-slate-500
          ">
            {loadingProgress || "Đang lấy dữ liệu từ database."}
          </p>
        </div>
      </div>
    );
  }

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
            mb-4
            text-4xl
            text-red-500
          ">
            !
          </div>

          <h2 className="
            text-2xl
            font-bold
            text-slate-800
          ">
            Không thể tải dữ liệu rủi ro
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
              inline-block
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
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="
      space-y-6
    ">
      <header>
        <p className="
          text-sm
          font-semibold
          text-blue-600
        ">
          Product ID: {productId}
        </p>

        <h1 className="
          mt-1
          text-3xl
          font-bold
          text-slate-800
        ">
          Cảnh báo rủi ro
        </h1>

        <p className="
          mt-2
          text-slate-500
        ">
          Trang này hiển thị các review có dấu hiệu rủi ro cao hoặc trung bình
          dựa trên nội dung đánh giá, từ khóa rủi ro và kết quả phân tích.
        </p>

        <p className="
          mt-1
          text-sm
          text-slate-400
        ">
          Tổng review:{" "}
          <span className="
            font-semibold
            text-slate-600
          ">
            {totalReviews}
          </span>{" "}
          · Đã tải:{" "}
          <span className="
            font-semibold
            text-slate-600
          ">
            {reviews.length}
          </span>{" "}
          · Có rủi ro:{" "}
          <span className="
            font-semibold
            text-red-600
          ">
            {riskReviews.length}
          </span>
        </p>
      </header>

      <section className="
        grid
        grid-cols-1
        gap-4
        md:grid-cols-3
      ">
        <button
          type="button"
          onClick={() => setSelectedRiskLevel("ALL")}
          className={`
            rounded-2xl
            border
            p-5
            text-left
            shadow-sm
            transition
            ${
              selectedRiskLevel === "ALL"
                ? "border-blue-500 bg-blue-50"
                : "border-slate-100 bg-white hover:bg-slate-50"
            }
          `}
        >
          <p className="
            text-sm
            text-slate-500
          ">
            Tất cả rủi ro
          </p>

          <p className="
            mt-2
            text-2xl
            font-bold
            text-slate-900
          ">
            {riskSummary.ALL}
          </p>
        </button>

        <button
          type="button"
          onClick={() => setSelectedRiskLevel("HIGH")}
          className={`
            rounded-2xl
            border
            p-5
            text-left
            shadow-sm
            transition
            ${
              selectedRiskLevel === "HIGH"
                ? "border-red-500 bg-red-50"
                : "border-slate-100 bg-white hover:bg-slate-50"
            }
          `}
        >
          <p className="
            text-sm
            text-slate-500
          ">
            HIGH
          </p>

          <p className="
            mt-2
            text-2xl
            font-bold
            text-red-700
          ">
            {riskSummary.HIGH}
          </p>
        </button>

        <button
          type="button"
          onClick={() => setSelectedRiskLevel("MEDIUM")}
          className={`
            rounded-2xl
            border
            p-5
            text-left
            shadow-sm
            transition
            ${
              selectedRiskLevel === "MEDIUM"
                ? "border-orange-500 bg-orange-50"
                : "border-slate-100 bg-white hover:bg-slate-50"
            }
          `}
        >
          <p className="
            text-sm
            text-slate-500
          ">
            MEDIUM
          </p>

          <p className="
            mt-2
            text-2xl
            font-bold
            text-orange-700
          ">
            {riskSummary.MEDIUM}
          </p>
        </button>
      </section>

      <section className="
        flex
        flex-col
        gap-3
        rounded-2xl
        border
        border-slate-100
        bg-white
        p-4
        shadow-sm
        md:flex-row
        md:items-center
        md:justify-between
      ">
        <div>
          <p className="
            text-sm
            font-semibold
            text-slate-700
          ">
            Bộ lọc rủi ro
          </p>

          <p className="
            text-xs
            text-slate-500
          ">
            Đang hiển thị {paginatedRiskReviews.length} review trên trang {clientPage} / {clientTotalPages}.
            Tổng sau lọc: {filteredRiskReviews.length}.
          </p>
        </div>

        <div className="
          flex
          flex-col
          gap-3
          md:flex-row
        ">
          <select
            value={selectedRiskLevel}
            onChange={(event) =>
              setSelectedRiskLevel(
                event.target.value as RiskLevelFilter
              )
            }
            className="
              rounded-xl
              border
              border-slate-200
              bg-white
              px-4
              py-2
              text-sm
              outline-none
              focus:border-blue-500
            "
          >
            <option value="ALL">
              Tất cả rủi ro ({riskSummary.ALL})
            </option>
            <option value="HIGH">
              HIGH ({riskSummary.HIGH})
            </option>
            <option value="MEDIUM">
              MEDIUM ({riskSummary.MEDIUM})
            </option>
          </select>

          <div className="
            relative
            w-full
            md:w-80
          ">
            <Search className="
              absolute
              left-3
              top-2.5
              h-4
              w-4
              text-slate-400
            " />

            <input
              value={searchText}
              onChange={(event) =>
                setSearchText(event.target.value)
              }
              placeholder="Tìm review, mã review, keyword..."
              className="
                w-full
                rounded-xl
                border
                border-slate-200
                py-2
                pl-9
                pr-4
                text-sm
                outline-none
                focus:border-blue-500
              "
            />
          </div>
        </div>
      </section>

      {riskReviews.length === 0 ? (
        <div className="
          rounded-2xl
          border
          border-dashed
          border-slate-200
          bg-white
          p-10
          text-center
          shadow-sm
        ">
          <AlertTriangle className="
            mx-auto
            mb-3
            h-9
            w-9
            text-slate-400
          " />

          <h2 className="
            text-lg
            font-semibold
            text-slate-700
          ">
            Chưa phát hiện rủi ro
          </h2>

          <p className="
            mt-2
            text-sm
            text-slate-500
          ">
            Nếu tổng review đã tải lớn hơn 0 nhưng vẫn không có rủi ro,
            hãy kiểm tra lại dữ liệu RiskDetection ở backend hoặc chạy rebuild risk.
          </p>
        </div>
      ) : paginatedRiskReviews.length === 0 ? (
        <div className="
          rounded-2xl
          border
          border-dashed
          border-slate-200
          bg-white
          p-10
          text-center
          shadow-sm
        ">
          <h2 className="
            text-lg
            font-semibold
            text-slate-700
          ">
            Không có review phù hợp
          </h2>

          <p className="
            mt-2
            text-sm
            text-slate-500
          ">
            Thử đổi bộ lọc rủi ro hoặc từ khóa tìm kiếm.
          </p>
        </div>
      ) : (
        <section className="
          space-y-4
        ">
          {paginatedRiskReviews.map((review) => {
            const sentiment =
              getReviewSentiment(review);

            const confidence =
              getReviewConfidence(review);

            const riskLevel =
              review.risk?.risk_level;

            const riskKeyword =
              review.risk?.risk_keyword;

            return (
              <article
                key={review.id}
                className="
                  rounded-2xl
                  border
                  border-red-100
                  bg-white
                  p-6
                  shadow-sm
                "
              >
                <div className="
                  flex
                  flex-col
                  gap-3
                  sm:flex-row
                  sm:items-center
                  sm:justify-between
                ">
                  <div>
                    <p className="
                      text-sm
                      font-semibold
                      text-slate-700
                    ">
                      Review #{getReviewDisplayId(review)}
                    </p>

                    <p className="
                      mt-1
                      text-xs
                      text-slate-400
                    ">
                      {formatDate(review.review_date)}
                    </p>
                  </div>

                  <div className="
                    font-semibold
                    text-amber-500
                  ">
                    {getStars(review.rating)}

                    <span className="
                      ml-2
                      text-sm
                      text-slate-500
                    ">
                      {review.rating}/5
                    </span>
                  </div>
                </div>

                <p className="
                  mt-5
                  whitespace-pre-wrap
                  leading-7
                  text-slate-700
                ">
                  {review.content || "Không có nội dung review."}
                </p>

                <div className="
                  mt-5
                  flex
                  flex-wrap
                  gap-2
                ">
                  <span
                    className={`
                      rounded-full
                      px-3
                      py-1
                      text-xs
                      font-semibold
                      ${getRiskBadgeClass(riskLevel)}
                    `}
                  >
                    Risk: {riskLevel || "UNKNOWN"}
                  </span>

                  {riskKeyword && (
                    <span className="
                      rounded-full
                      bg-red-50
                      px-3
                      py-1
                      text-xs
                      font-semibold
                      text-red-700
                    ">
                      Keyword: {riskKeyword}
                    </span>
                  )}

                  {sentiment && (
                    <span
                      className={`
                        rounded-full
                        px-3
                        py-1
                        text-xs
                        font-semibold
                        ${getSentimentBadgeClass(sentiment)}
                      `}
                    >
                      {sentiment}

                      {typeof confidence === "number" && (
                        <span className="
                          ml-1
                          font-normal
                        ">
                          ({(confidence * 100).toFixed(1)}%)
                        </span>
                      )}
                    </span>
                  )}

                  {review.is_analyzed && (
                    <span className="
                      rounded-full
                      bg-blue-100
                      px-3
                      py-1
                      text-xs
                      font-semibold
                      text-blue-700
                    ">
                      Đã phân tích
                    </span>
                  )}
                </div>

                <div className="
                  mt-4
                  rounded-xl
                  border
                  border-red-100
                  bg-red-50
                  p-4
                ">
                  <p className="
                    text-sm
                    font-semibold
                    text-red-700
                  ">
                    Phát hiện rủi ro
                  </p>

                  <p className="
                    mt-1
                    text-xs
                    text-red-600
                  ">
                    Mức độ:{" "}
                    <strong>
                      {riskLevel || "UNKNOWN"}
                    </strong>

                    {riskKeyword && (
                      <>
                        {" · "}
                        Từ khóa:{" "}
                        <strong>
                          {riskKeyword}
                        </strong>
                      </>
                    )}
                  </p>
                </div>
              </article>
            );
          })}
        </section>
      )}

      {clientTotalPages > 1 && (
        <div className="
          flex
          items-center
          justify-center
          gap-4
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-4
          shadow-sm
        ">
          <button
            type="button"
            disabled={
              clientPage <= 1
            }
            onClick={() => {
              setClientPage(
                (current) =>
                  Math.max(
                    1,
                    current - 1
                  )
              );
            }}
            className="
              rounded-lg
              border
              border-slate-200
              px-4
              py-2
              text-sm
              font-medium
              text-slate-700
              transition
              hover:bg-slate-50
              disabled:cursor-not-allowed
              disabled:opacity-40
            "
          >
            ← Trước
          </button>

          <span className="
            text-sm
            font-medium
            text-slate-600
          ">
            Trang {clientPage} / {clientTotalPages}
          </span>

          <button
            type="button"
            disabled={
              clientPage >= clientTotalPages
            }
            onClick={() => {
              setClientPage(
                (current) =>
                  Math.min(
                    clientTotalPages,
                    current + 1
                  )
              );
            }}
            className="
              rounded-lg
              border
              border-slate-200
              px-4
              py-2
              text-sm
              font-medium
              text-slate-700
              transition
              hover:bg-slate-50
              disabled:cursor-not-allowed
              disabled:opacity-40
            "
          >
            Sau →
          </button>
        </div>
      )}
    </div>
  );
}

export default Risk;