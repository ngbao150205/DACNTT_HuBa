import type { ProductReview } from "./product";

export interface ReviewsResponse {
  product_id: number;
  platform_product_id: string;

  pagination: {
    page: number;
    page_size: number;
    total_reviews: number;
    total_pages: number;
  };

  reviews: ProductReview[];
}