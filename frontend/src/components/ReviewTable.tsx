import type { ProductReview } from "../types/product";

interface ReviewTableProps {
  reviews: ProductReview[];
}

function ReviewTable({
  reviews,
}: ReviewTableProps) {

  return (
    <div className="
      bg-white
      rounded-2xl
      border
      border-gray-100
      shadow-sm
      overflow-hidden
    ">

      <div className="p-6">

        <h2 className="
          font-semibold
          text-lg
        ">
          Đánh giá khách hàng
        </h2>

      </div>

      <div className="overflow-x-auto">

        <table className="
          w-full
          text-sm
        ">

          <thead className="
            bg-gray-50
            text-gray-500
          ">

            <tr>

              <th className="text-left p-4">
                Review
              </th>

              <th className="text-left p-4">
                Rating
              </th>

              <th className="text-left p-4">
                Sentiment
              </th>

              <th className="text-left p-4">
                Issue
              </th>

              <th className="text-left p-4">
                Risk
              </th>

            </tr>

          </thead>

          <tbody>

            {reviews.map((review) => (

              <tr
                key={review.id ?? review.review_id}
                className="
                  border-t
                  border-gray-100
                "
              >

                <td className="
                  p-4
                  max-w-md
                ">
                  <p className="line-clamp-2">
                    {review.content}
                  </p>
                </td>

                <td className="p-4">
                  {review.rating}/5
                </td>

                <td className="p-4">

                  <span className="
                    px-3
                    py-1
                    rounded-full
                    text-xs
                    font-medium
                    bg-gray-100
                  ">
                    {review.sentiment?.sentiment ?? "-"}
                  </span>

                </td>

                <td className="p-4">

                  {review.issues &&
                  review.issues.length > 0 ? (

                    <div className="space-y-1">

                      {review.issues.map(
                        (issue, index) => (

                          <div
                            key={index}
                            className="
                              text-xs
                              text-orange-600
                            "
                          >
                            {issue.issue_type}
                          </div>

                        )
                      )}

                    </div>

                  ) : (
                    <span className="
                      text-gray-400
                    ">
                      Không có
                    </span>
                  )}

                </td>

                <td className="p-4">

                  <span className={`
                    px-3
                    py-1
                    rounded-full
                    text-xs
                    font-medium

                    ${
                      review.risk?.risk_level ===
                      "HIGH"
                        ? "bg-red-100 text-red-700"
                        : review.risk?.risk_level ===
                          "MEDIUM"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-green-100 text-green-700"
                    }
                  `}>
                    {review.risk?.risk_level ?? "LOW"}
                  </span>

                </td>

              </tr>

            ))}

          </tbody>

        </table>

      </div>

    </div>
  );
}

export default ReviewTable;