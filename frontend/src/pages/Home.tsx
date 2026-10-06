import {
  ArrowRight,
  BarChart3,
  History,
  MessageSquareText,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import {
  Link,
} from "react-router-dom";

function Home() {
  return (
    <div className="
      mx-auto
      max-w-6xl
      space-y-10
    ">
      <section className="
        rounded-3xl
        bg-gradient-to-br
        from-blue-600
        to-slate-900
        p-10
        text-white
        shadow-sm
      ">
        <div className="
          max-w-3xl
        ">
          <div className="
            mb-5
            inline-flex
            items-center
            gap-2
            rounded-full
            bg-white/10
            px-4
            py-2
            text-sm
            font-semibold
            text-blue-100
          ">
            <Sparkles className="
              h-4
              w-4
            " />
            AI Customer Feedback Analysis
          </div>

          <h1 className="
            text-4xl
            font-bold
            leading-tight
            md:text-5xl
          ">
            Phân tích phản hồi khách hàng bằng AI
          </h1>

          <p className="
            mt-5
            max-w-2xl
            text-base
            leading-7
            text-blue-100
          ">
            Hệ thống hỗ trợ phân tích review sản phẩm, nhận diện cảm xúc khách hàng,
            phân loại nguyên nhân tiêu cực và phát hiện các cảnh báo rủi ro quan trọng.
          </p>

          <div className="
            mt-8
            flex
            flex-col
            gap-3
            sm:flex-row
          ">
            <Link
              to="/analyze"
              className="
                inline-flex
                items-center
                justify-center
                gap-2
                rounded-xl
                bg-white
                px-6
                py-3
                text-sm
                font-bold
                text-blue-700
                transition
                hover:bg-blue-50
              "
            >
              Bắt đầu phân tích
              <ArrowRight className="
                h-4
                w-4
              " />
            </Link>

            <Link
              to="/history"
              className="
                inline-flex
                items-center
                justify-center
                gap-2
                rounded-xl
                border
                border-white/20
                px-6
                py-3
                text-sm
                font-bold
                text-white
                transition
                hover:bg-white/10
              "
            >
              Xem lịch sử
            </Link>
          </div>
        </div>
      </section>

      <section className="
        grid
        grid-cols-1
        gap-5
        md:grid-cols-4
      ">
        <div className="
          rounded-2xl
          border
          border-slate-100
          bg-white
          p-6
          shadow-sm
        ">
          <MessageSquareText className="
            mb-4
            h-7
            w-7
            text-blue-600
          " />

          <h3 className="
            font-bold
            text-slate-900
          ">
            Phân tích review
          </h3>

          <p className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          ">
            Thu thập và hiển thị toàn bộ đánh giá khách hàng của sản phẩm.
          </p>
        </div>

        <div className="
          rounded-2xl
          border
          border-slate-100
          bg-white
          p-6
          shadow-sm
        ">
          <BarChart3 className="
            mb-4
            h-7
            w-7
            text-green-600
          " />

          <h3 className="
            font-bold
            text-slate-900
          ">
            Sentiment AI
          </h3>

          <p className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          ">
            Nhận diện Positive, Neutral và Negative từ nội dung review.
          </p>
        </div>

        <div className="
          rounded-2xl
          border
          border-slate-100
          bg-white
          p-6
          shadow-sm
        ">
          <ShieldAlert className="
            mb-4
            h-7
            w-7
            text-red-600
          " />

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
            Phát hiện các dấu hiệu nghiêm trọng như hàng fake, khiếu nại, hoàn tiền.
          </p>
        </div>

        <div className="
          rounded-2xl
          border
          border-slate-100
          bg-white
          p-6
          shadow-sm
        ">
          <History className="
            mb-4
            h-7
            w-7
            text-purple-600
          " />

          <h3 className="
            font-bold
            text-slate-900
          ">
            Lịch sử phân tích
          </h3>

          <p className="
            mt-2
            text-sm
            leading-6
            text-slate-500
          ">
            Xem lại các sản phẩm đã từng phân tích mà không bị mất dữ liệu.
          </p>
        </div>
      </section>
    </div>
  );
}

export default Home;