import type {
  ProductAnalysisResponse,
} from "../types/product";


/*
 * ============================================================
 * API BASE URL
 * ============================================================
 */

const API_BASE_URL =
  "http://127.0.0.1:8000";


/*
 * ============================================================
 * PRODUCT REVIEW
 * ============================================================
 */

export interface ProductReview {
  id: number;

  review_id: string;

  content: string;

  rating: number;

  review_date?: string | null;

  sentiment:
    | {
        sentiment: string;

        confidence: number;

        model_version?: string;

        method?: string;
      }
    | string
    | null;

  issues: Array<{
    issue_type: string;

    matched_keyword: string;
  }>;

  risk:
    | {
        risk_flag: boolean;

        risk_level: string;

        risk_keyword: string | null;
      }
    | null;

  is_analyzed?: boolean;
}


/*
 * ============================================================
 * PRODUCT REVIEWS RESPONSE
 * ============================================================
 *
 * GET /products/{productId}/reviews
 */

export interface ProductReviewsResponse {
  product_id: number | string;

  platform_product_id: string;

  pagination: {
    page: number;

    page_size: number;

    total_reviews: number;

    total_pages: number;
  };

  reviews: ProductReview[];
}


/*
 * ============================================================
 * PRODUCT ANALYSIS API RESPONSE
 * ============================================================
 *
 * GET /products/{productId}/analysis
 *
 * Dữ liệu được lấy trực tiếp từ PostgreSQL
 * thông qua backend.
 */

export interface ProductAnalysisApiResponse {
  product: {
    id: number;

    platform_product_id: string;

    platform: string;

    name: string;

    url: string;

    seller_name?: string | null;

    rating?: number | null;

    product_type?: string | null;

    category?: string | null;

    total_reviews: number;

    is_active?: boolean;

    created_at?: string | null;

    updated_at?: string | null;

    last_crawled_at?: string | null;
  };

  analysis: {
    total_reviews: number;

    analyzed_reviews: number;

    positive_count: number;

    negative_count: number;

    neutral_count: number;

    positive_rate: number;

    negative_rate: number;

    neutral_rate: number;

    issue_summary: Record<
      string,
      number
    >;

    risk_summary: Record<
      string,
      number
    >;
  };

  latest_history?: {
    id: number;

    total_reviews: number;

    analyzed_reviews: number;

    positive_count: number;

    negative_count: number;

    neutral_count: number;

    positive_rate: number;

    negative_rate: number;

    neutral_rate: number;

    issue_summary: string;

    risk_summary: string;

    analyzed_at: string;
  } | null;
}


/*
 * ============================================================
 * ANALYZE PRODUCT API RESPONSE
 * ============================================================
 *
 * POST /products/analyze
 *
 * Dùng khi user nhập URL Tiki.
 */

export interface AnalyzeProductResponse
  extends ProductAnalysisResponse {}


/*
 * ============================================================
 * PARSE API ERROR
 * ============================================================
 */

async function parseError(
  response: Response
): Promise<string> {

  const text =
    await response.text();


  if (!text) {

    return (
      `API error: ${response.status}`
    );

  }


  try {

    const data =
      JSON.parse(text);


    if (
      typeof data.detail ===
      "string"
    ) {

      return data.detail;

    }


    if (
      typeof data.message ===
      "string"
    ) {

      return data.message;

    }


    return JSON.stringify(
      data
    );

  } catch {

    return text;

  }

}


/*
 * ============================================================
 * ANALYZE PRODUCT
 * ============================================================
 *
 * POST /products/analyze
 *
 * Flow:
 *
 * Frontend
 *    ↓
 * POST /products/analyze
 *    ↓
 * Backend crawl + AI + database
 *    ↓
 * PostgreSQL
 *    ↓
 * Response
 */

export async function analyzeProduct(
  url: string
): Promise<AnalyzeProductResponse> {

  const cleanUrl =
    url.trim();


  if (!cleanUrl) {

    throw new Error(
      "URL sản phẩm không được để trống."
    );

  }


  const response =
    await fetch(
      `${API_BASE_URL}/products/analyze`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          url: cleanUrl,
        }),
      }
    );


  if (!response.ok) {

    throw new Error(
      await parseError(
        response
      )
    );

  }


  return response.json();

}


/*
 * ============================================================
 * GET PRODUCT ANALYSIS
 * ============================================================
 *
 * GET /products/{productId}/analysis
 *
 * Đây là API chính cho Dashboard.
 *
 * QUAN TRỌNG:
 *
 * API này KHÔNG crawl.
 * API này KHÔNG gọi AI.
 *
 * Backend đọc dữ liệu từ:
 *
 * products
 * reviews
 * review_analysis
 * issue_analysis
 * risk_detection
 * analysis_history
 */

export async function getProductAnalysis(
  productId: string | number
): Promise<ProductAnalysisApiResponse> {

  const response =
    await fetch(
      `${API_BASE_URL}/products/${productId}/analysis`
    );


  if (!response.ok) {

    throw new Error(
      await parseError(
        response
      )
    );

  }


  return response.json();

}


/*
 * ============================================================
 * GET PRODUCT REVIEWS
 * ============================================================
 *
 * GET /products/{productId}/reviews
 *
 * API này dùng cho trang Reviews.
 *
 * Dữ liệu được đọc trực tiếp từ PostgreSQL.
 */

export async function getProductReviews(
  productId: string | number,

  page: number = 1,

  pageSize: number = 10
): Promise<ProductReviewsResponse> {

  const params =
    new URLSearchParams({

      page:
        String(
          Math.max(
            1,
            page
          )
        ),

      page_size:
        String(
          Math.min(
            100,
            Math.max(
              1,
              pageSize
            )
          )
        ),

    });


  const response =
    await fetch(
      `${API_BASE_URL}/products/${productId}/reviews?${params.toString()}`
    );


  if (!response.ok) {

    throw new Error(
      await parseError(
        response
      )
    );

  }


  return response.json();

}


/*
 * ============================================================
 * HEALTH CHECK
 * ============================================================
 *
 * Dùng để kiểm tra backend có đang chạy hay không.
 *
 * Nếu main.py chưa có /health thì không cần sử dụng hàm này.
 */

export async function checkApiHealth(): Promise<boolean> {

  try {

    const response =
      await fetch(
        `${API_BASE_URL}/docs`,
        {
          method: "GET",
        }
      );


    return response.ok;

  } catch {

    return false;

  }

}

export type ProductHistoryItem = {
  id: number;
  platform: string;
  platform_product_id: string;
  name: string;
  url: string;
  seller_name?: string | null;
  rating?: number | null;
  total_reviews: number;
  stored_total_reviews?: number;
  product_type?: string;
  category?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  last_crawled_at?: string | null;
};

export type ProductHistoryResponse = {
  products: ProductHistoryItem[];
};

export async function getProductHistory(): Promise<ProductHistoryResponse> {
  const response = await fetch(`${API_BASE_URL}/products`);

  if (!response.ok) {
    throw new Error(
      `Không thể tải lịch sử sản phẩm. HTTP ${response.status}`
    );
  }

  return response.json();
}