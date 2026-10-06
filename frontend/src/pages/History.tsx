import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ArrowRight,
  History as HistoryIcon,
  Loader2,
  Search,
} from "lucide-react";

import {
  Link,
} from "react-router-dom";

import {
  getProductHistory,
  type ProductHistoryItem,
} from "../services/api";

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
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatNumber(value?: number): string {
  return new Intl.NumberFormat("vi-VN").format(value || 0);
}

function History() {
  const [products, setProducts] = useState<ProductHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchText, setSearchText] = useState("");

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      setError("");

      try {
        const response = await getProductHistory();
        setProducts(response.products || []);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Không thể tải lịch sử phân tích.");
        }

        setProducts([]);
      } finally {
        setLoading(false);
      }
    }

    fetchHistory();
  }, []);

  const filteredProducts = useMemo(() => {
    const query = searchText.trim().toLowerCase();

    if (!query) {
      return products;
    }

    return products.filter((product) => {
      return (
        product.name.toLowerCase().includes(query) ||
        product.url.toLowerCase().includes(query) ||
        product.platform_product_id.toLowerCase().includes(query) ||
        String(product.id).includes(query) ||
        (product.category || "").toLowerCase().includes(query)
      );
    });
  }, [products, searchText]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
        <div className="flex items-center gap-3 text-slate-600">
          <Loader2 className="h-5 w-5 animate-spin" />

          <div>
            <p className="font-semibold">
              Đang tải lịch sử phân tích...
            </p>

            <p className="mt-1 text-sm text-slate-500">
              Hệ thống đang lấy danh sách sản phẩm từ database.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">
        <p className="font-semibold">
          Không thể tải lịch sử phân tích
        </p>

        <p className="mt-2 text-sm">
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-slate-900">
          Lịch sử phân tích
        </h1>

        <p className="mt-2 text-slate-500">
          Danh sách các sản phẩm đã được phân tích và lưu trong database.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-700">
              Tổng sản phẩm đã phân tích
            </p>

            <p className="mt-1 text-2xl font-bold text-slate-900">
              {products.length}
            </p>
          </div>

          <div className="relative w-full md:w-96">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />

            <input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder="Tìm theo tên, URL, product ID, category..."
              className="w-full rounded-xl border border-slate-200 py-2.5 pl-9 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </div>
        </div>
      </section>

      {products.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center shadow-sm">
          <HistoryIcon className="mx-auto mb-4 h-10 w-10 text-slate-400" />

          <h2 className="text-lg font-semibold text-slate-800">
            Chưa có sản phẩm nào trong lịch sử
          </h2>

          <p className="mt-2 text-sm text-slate-500">
            Hãy phân tích một sản phẩm để hệ thống lưu vào database.
          </p>

          <Link
            to="/analyze"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            Bắt đầu phân tích
            <ArrowRight className="h-4 w-4" />
          </Link>
        </section>
      ) : filteredProducts.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800">
            Không tìm thấy sản phẩm phù hợp
          </h2>

          <p className="mt-2 text-sm text-slate-500">
            Thử tìm bằng tên sản phẩm, URL, category hoặc product ID khác.
          </p>
        </section>
      ) : (
        <section className="space-y-4">
          {filteredProducts.map((product) => (
            <article
              key={product.id}
              className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition hover:border-blue-200 hover:shadow-md"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                      Product ID: {product.id}
                    </span>

                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                      {product.platform}
                    </span>

                    {product.category && (
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                        {product.category}
                      </span>
                    )}
                  </div>

                  <h2 className="mt-3 line-clamp-2 text-xl font-bold text-slate-900">
                    {product.name}
                  </h2>

                  <p className="mt-2 break-all text-sm text-slate-500">
                    {product.url}
                  </p>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span className="rounded-full bg-slate-100 px-3 py-1">
                      Platform ID: {product.platform_product_id}
                    </span>

                    <span className="rounded-full bg-slate-100 px-3 py-1">
                      Review: {formatNumber(product.total_reviews)}
                    </span>

                    <span className="rounded-full bg-slate-100 px-3 py-1">
                      Ngày phân tích: {formatDate(product.created_at)}
                    </span>

                    {product.last_crawled_at && (
                      <span className="rounded-full bg-slate-100 px-3 py-1">
                        Crawl gần nhất: {formatDate(product.last_crawled_at)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
                  <Link
                    to={`/products/${product.id}/dashboard`}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
                  >
                    Xem dashboard
                    <ArrowRight className="h-4 w-4" />
                  </Link>

                  <Link
                    to={`/products/${product.id}/reviews`}
                    className="inline-flex items-center justify-center rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                  >
                    Xem review
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

export default History;