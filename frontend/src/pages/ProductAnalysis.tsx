import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import StatCard from "../components/StatCard";
import RiskCard from "../components/RiskCard";
import SentimentChart from "../components/SentimentChart";
import IssueChart from "../components/IssueChart";
import ReviewTable from "../components/ReviewTable";

import {
  getProductReviews,
  type ProductReviewsResponse,
} from "../services/api";

import type {
  ProductAnalysisResponse,
} from "../types/product";


function ProductAnalysis() {

  const [searchParams] =
    useSearchParams();

  const productId =
    searchParams.get("productId");


  const [result, setResult] =
    useState<ProductAnalysisResponse | null>(
      null
    );


  const [reviewsData, setReviewsData] =
    useState<ProductReviewsResponse | null>(
      null
    );


  const [loading, setLoading] =
    useState(true);


  const [error, setError] =
    useState("");


  const [page, setPage] =
    useState(1);


  const PAGE_SIZE = 10;


  /*
   * ==========================================================
   * LOAD PRODUCT ANALYSIS + REVIEWS
   * ==========================================================
   */

  useEffect(() => {

    async function loadProduct() {

      if (!productId) {

        setError(
          "Không tìm thấy productId."
        );

        setLoading(false);

        return;
      }


      setLoading(true);
      setError("");


      try {

        /*
         * ====================================================
         * 1. LẤY KẾT QUẢ ANALYSIS TỪ SESSION STORAGE
         * ====================================================
         *
         * Home.tsx đã lưu kết quả POST /products/analyze
         * trước khi navigate sang trang này.
         */

        const cached =
          sessionStorage.getItem(
            `product-analysis-${productId}`
          );


        if (cached) {

          try {

            const parsed =
              JSON.parse(cached);

            setResult(parsed);

          } catch (storageError) {

            console.warn(
              "Không thể đọc analysis từ sessionStorage:",
              storageError
            );

          }

        }


        /*
         * ====================================================
         * 2. LẤY TOÀN BỘ REVIEW TỪ DATABASE
         * ====================================================
         *
         * GET:
         *
         * /products/{productId}/reviews
         *
         * Endpoint này lấy review đã lưu trong database,
         * bao gồm sentiment / issue / risk.
         */

        const reviews =
          await getProductReviews(
            productId,
            page,
            PAGE_SIZE
          );


        setReviewsData(
          reviews
        );


        /*
         * ====================================================
         * 3. FALLBACK
         * ====================================================
         *
         * Nếu không có sessionStorage, vẫn tạo một
         * result tối thiểu để trang không bị trắng.
         */

        if (!cached) {

          setResult({

            product_id:
              reviews.platform_product_id,

            product_db_id:
              Number(productId),

            product_name:
                "Unknown Product",

            is_new_product:
              false,

            crawled_reviews:
              reviews.pagination.total_reviews,

            new_reviews:
              0,

            category:
            "GENERAL",


            skipped_reviews:
              reviews.pagination.total_reviews,

            analysis: {

              total_reviews:
                reviews.pagination.total_reviews,

              analyzed_reviews:
                reviews.pagination.total_reviews,

              positive_count:
                0,

              negative_count:
                0,

              neutral_count:
                0,

              positive_rate:
                0,

              negative_rate:
                0,

              neutral_rate:
                0,

              issue_summary:
                {},

              risk_summary:
                {},

            },

            analysis_history_id:
              0,

            reviews:
              [],

          });

        }

      } catch (err) {

        console.error(
          "Load product error:",
          err
        );


        if (err instanceof Error) {

          setError(
            err.message
          );

        } else {

          setError(
            "Không thể tải dữ liệu sản phẩm."
          );

        }

      } finally {

        setLoading(false);

      }

    }


    loadProduct();

  }, [productId, page]);



  /*
   * ==========================================================
   * KHÔNG CÓ PRODUCT ID
   * ==========================================================
   */

  if (!productId) {

    return (

      <div className="
        bg-red-50
        border
        border-red-200
        rounded-2xl
        p-6
        text-red-700
      ">

        <p className="font-semibold">
          Không tìm thấy sản phẩm.
        </p>

        <p className="text-sm mt-1">
          URL không chứa productId.
        </p>

      </div>

    );

  }



  /*
   * ==========================================================
   * LOADING
   * ==========================================================
   */

  if (loading && !result) {

    return (

      <div className="
        bg-white
        rounded-2xl
        border
        border-gray-100
        p-10
        text-center
      ">

        <p className="
          text-gray-700
          font-semibold
        ">
          Đang tải dữ liệu phân tích...
        </p>

        <p className="
          text-sm
          text-gray-400
          mt-2
        ">
          Đang lấy dữ liệu đánh giá từ database.
        </p>

      </div>

    );

  }



  /*
   * ==========================================================
   * ERROR
   * ==========================================================
   */

  if (error && !result) {

    return (

      <div className="
        bg-red-50
        border
        border-red-200
        rounded-2xl
        p-6
        text-red-700
      ">

        <p className="
          font-semibold
        ">
          Không thể tải dữ liệu
        </p>

        <p className="
          mt-1
          text-sm
        ">
          {error}
        </p>

      </div>

    );

  }



  if (!result) {
    return null;
  }



  /*
   * ==========================================================
   * ANALYSIS DATA
   * ==========================================================
   */

  const analysis =
    result.analysis;



  /*
   * ==========================================================
   * MAIN UI
   * ==========================================================
   */

  return (

    <div className="space-y-8">


      {/* ======================================================
          HEADER
      ====================================================== */}

      <div>

        <div className="
          flex
          flex-col
          md:flex-row
          md:items-center
          md:justify-between
          gap-4
        ">


          <div>

            <h1 className="
              text-3xl
              font-bold
              text-slate-800
            ">
              Phân tích sản phẩm
            </h1>


            <p className="
              text-gray-500
              mt-2
            ">
              Tiki Product #{result.product_id}
            </p>

          </div>


          <div className="
            px-4
            py-2
            rounded-full
            bg-blue-50
            text-blue-700
            text-sm
            font-medium
            w-fit
          ">

            {result.category ?? "GENERAL"}

          </div>

        </div>

      </div>



      {/* ======================================================
          PRODUCT SUMMARY
      ====================================================== */}

      <div className="
        bg-white
        rounded-2xl
        border
        border-gray-100
        shadow-sm
        p-6
      ">

        <div className="
          grid
          grid-cols-1
          sm:grid-cols-3
          gap-5
        ">


          {/* TOTAL */}

          <div>

            <p className="
              text-sm
              text-gray-500
            ">
              Tổng đánh giá
            </p>

            <p className="
              text-2xl
              font-bold
              text-slate-800
              mt-1
            ">
              {analysis.total_reviews}
            </p>

          </div>



          {/* NEW */}

          <div>

            <p className="
              text-sm
              text-gray-500
            ">
              Đánh giá mới
            </p>

            <p className="
              text-2xl
              font-bold
              text-blue-600
              mt-1
            ">
              {result.new_reviews}
            </p>

          </div>



          {/* SKIPPED */}

          <div>

            <p className="
              text-sm
              text-gray-500
            ">
              Đánh giá đã có
            </p>

            <p className="
              text-2xl
              font-bold
              text-slate-700
              mt-1
            ">
              {result.skipped_reviews}
            </p>

          </div>


        </div>

      </div>



      {/* ======================================================
          STATISTICS
      ====================================================== */}

      <div className="
        grid
        grid-cols-1
        sm:grid-cols-2
        xl:grid-cols-4
        gap-5
      ">


        <StatCard
          title="Tổng đánh giá"
          value={analysis.total_reviews}
          description="Tất cả đánh giá"
        />


        <StatCard
          title="Tích cực"
          value={`${analysis.positive_rate}%`}
          description={`${analysis.positive_count} đánh giá`}
        />


        <StatCard
          title="Tiêu cực"
          value={`${analysis.negative_rate}%`}
          description={`${analysis.negative_count} đánh giá`}
        />


        <StatCard
          title="Trung lập"
          value={`${analysis.neutral_rate}%`}
          description={`${analysis.neutral_count} đánh giá`}
        />


      </div>



      {/* ======================================================
          CHARTS
      ====================================================== */}

      <div className="
        grid
        grid-cols-1
        xl:grid-cols-2
        gap-6
      ">


        {/* SENTIMENT */}

        <SentimentChart

          positive={
            analysis.positive_count
          }

          negative={
            analysis.negative_count
          }

          neutral={
            analysis.neutral_count
          }

        />



        {/* ISSUES */}

        <IssueChart
          data={
            analysis.issue_summary
          }
        />


      </div>



      {/* ======================================================
          RISK
      ====================================================== */}

      <div>

        <h2 className="
          text-xl
          font-bold
          text-slate-800
          mb-4
        ">
          Cảnh báo rủi ro
        </h2>


        <div className="
          grid
          grid-cols-1
          md:grid-cols-3
          gap-5
        ">


          <RiskCard

            level="HIGH"

            count={
              analysis.risk_summary.HIGH ?? 0
            }

          />


          <RiskCard

            level="MEDIUM"

            count={
              analysis.risk_summary.MEDIUM ?? 0
            }

          />


          <RiskCard

            level="LOW"

            count={
              analysis.risk_summary.LOW ?? 0
            }

          />


        </div>

      </div>



      {/* ======================================================
          REVIEWS
      ====================================================== */}

      <div>


        {/* REVIEW HEADER */}

        <div className="
          flex
          flex-col
          sm:flex-row
          sm:items-center
          sm:justify-between
          gap-2
          mb-4
        ">


          <div>

            <h2 className="
              text-xl
              font-bold
              text-slate-800
            ">
              Đánh giá khách hàng
            </h2>


            <p className="
              text-sm
              text-gray-500
              mt-1
            ">

              {reviewsData
                ? `${reviewsData.pagination.total_reviews} đánh giá`
                : "Đang tải..."}

            </p>

          </div>


          {reviewsData && (

            <p className="
              text-sm
              text-gray-400
            ">

              Trang{" "}
              {reviewsData.pagination.page}
              {" / "}
              {reviewsData.pagination.total_pages}

            </p>

          )}


        </div>



        {/* REVIEW TABLE */}

        {reviewsData &&
        reviewsData.reviews.length > 0 ? (

          <ReviewTable

            reviews={
              reviewsData.reviews as any
            }

          />

        ) : (

          <div className="
            bg-white
            rounded-2xl
            border
            border-gray-100
            p-8
            text-center
            text-gray-500
          ">

            Chưa có dữ liệu đánh giá.

          </div>

        )}



        {/* ====================================================
            PAGINATION
        ==================================================== */}

        {reviewsData &&
        reviewsData.pagination.total_pages > 1 && (

          <div className="
            flex
            items-center
            justify-center
            gap-4
            mt-6
          ">


            {/* PREVIOUS */}

            <button

              type="button"

              disabled={
                page <= 1
              }

              onClick={() => {

                setPage(
                  current =>
                    Math.max(
                      1,
                      current - 1
                    )
                );

                window.scrollTo({
                  top: 0,
                  behavior: "smooth",
                });

              }}

              className="
                px-4
                py-2
                rounded-lg
                border
                border-gray-200
                text-sm
                font-medium
                text-gray-700
                hover:bg-gray-50
                disabled:opacity-40
                disabled:cursor-not-allowed
              "

            >

              Trước

            </button>



            {/* PAGE */}

            <span className="
              text-sm
              text-gray-500
            ">

              {page}
              {" / "}
              {reviewsData.pagination.total_pages}

            </span>



            {/* NEXT */}

            <button

              type="button"

              disabled={
                page >=
                reviewsData.pagination.total_pages
              }

              onClick={() => {

                setPage(
                  current =>
                    Math.min(
                      reviewsData.pagination.total_pages,
                      current + 1
                    )
                );

                window.scrollTo({
                  top: 0,
                  behavior: "smooth",
                });

              }}

              className="
                px-4
                py-2
                rounded-lg
                border
                border-gray-200
                text-sm
                font-medium
                text-gray-700
                hover:bg-gray-50
                disabled:opacity-40
                disabled:cursor-not-allowed
              "

            >

              Sau

            </button>


          </div>

        )}


      </div>



      {/* ======================================================
          LOADING NEXT PAGE
      ====================================================== */}

      {loading && result && (

        <div className="
          text-center
          text-sm
          text-gray-400
          pb-4
        ">

          Đang tải dữ liệu...

        </div>

      )}


    </div>

  );

}


export default ProductAnalysis;