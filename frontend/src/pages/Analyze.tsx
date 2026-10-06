import {
  useState,
} from "react";

import type {
  SyntheticEvent,
} from "react";

import {
  ArrowRight,
  Loader2,
} from "lucide-react";

import {
  useNavigate,
} from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000";

type AnalyzeResponse = {
  product_id?: string | number;
  product_db_id?: number;
  id?: number;
  productId?: number;
  product_name?: string;
  message?: string;
};

function Analyze() {
  const navigate =
    useNavigate();

  const [
    url,
    setUrl,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  async function handleSubmit(
    event: SyntheticEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    const trimmedUrl =
      url.trim();

    if (!trimmedUrl) {
      setError("Vui lòng nhập URL sản phẩm.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response =
        await fetch(
          `${API_BASE_URL}/products/analyze`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              url: trimmedUrl,
            }),
          }
        );

      if (!response.ok) {
        throw new Error(
          `Phân tích thất bại. HTTP ${response.status}`
        );
      }

      const data: AnalyzeResponse =
        await response.json();

      const productId =
        data.product_db_id ||
        data.id ||
        data.productId;

      if (!productId) {
        throw new Error(
          "Backend không trả về product_db_id."
        );
      }

      localStorage.setItem(
        "activeProductId",
        String(productId)
      );

      localStorage.setItem(
        "lastAnalyzedProductUrl",
        trimmedUrl
      );

      if (data.product_name) {
        localStorage.setItem(
          "lastAnalyzedProductName",
          data.product_name
        );
      }

      navigate(
        `/products/${productId}/dashboard`
      );
    } catch (err) {
      if (
        err instanceof Error
      ) {
        setError(
          err.message
        );
      } else {
        setError(
          "Lỗi không xác định khi phân tích sản phẩm."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="
      mx-auto
      max-w-4xl
      space-y-8
    ">
      <header className="
        text-center
      ">
        <h1 className="
          text-4xl
          font-bold
          text-slate-900
        ">
          Bắt đầu phân tích sản phẩm
        </h1>

        <p className="
          mx-auto
          mt-3
          max-w-2xl
          text-slate-500
        ">
          Nhập URL sản phẩm Tiki. Hệ thống sẽ xử lý review, phân tích sentiment,
          phân loại nguyên nhân tiêu cực và phát hiện rủi ro.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="
          rounded-3xl
          border
          border-slate-100
          bg-white
          p-8
          shadow-sm
        "
      >
        <label className="
          text-sm
          font-semibold
          text-slate-700
        ">
          Tiki Product URL
        </label>

        <input
          value={url}
          onChange={(event) =>
            setUrl(event.target.value)
          }
          placeholder="https://tiki.vn/..."
          className="
            mt-3
            w-full
            rounded-2xl
            border
            border-slate-200
            px-5
            py-4
            text-base
            outline-none
            transition
            focus:border-blue-500
            focus:ring-4
            focus:ring-blue-100
          "
        />

        {error && (
          <div className="
            mt-4
            rounded-xl
            bg-red-50
            px-4
            py-3
            text-sm
            font-medium
            text-red-700
          ">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="
            mt-5
            inline-flex
            w-full
            items-center
            justify-center
            gap-2
            rounded-2xl
            bg-blue-600
            px-6
            py-4
            font-bold
            text-white
            transition
            hover:bg-blue-700
            disabled:cursor-not-allowed
            disabled:opacity-60
          "
        >
          {loading ? (
            <>
              <Loader2 className="
                h-5
                w-5
                animate-spin
              " />
              Đang phân tích...
            </>
          ) : (
            <>
              Phân tích sản phẩm
              <ArrowRight className="
                h-5
                w-5
              " />
            </>
          )}
        </button>
      </form>
    </div>
  );
}

export default Analyze;