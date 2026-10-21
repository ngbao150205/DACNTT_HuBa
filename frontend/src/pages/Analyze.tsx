import { useState } from "react";
import type { SyntheticEvent } from "react";
import { ArrowRight, Loader2, Link2, FileUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL, apiFetch } from "../services/http";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
type Mode = "url" | "import";
type AnalyzeResponse = {
  product_db_id?: number; product_name?: string;
  crawl_status?: "FULL" | "PARTIAL"; crawl_error?: string | null;
  crawled_reviews?: number; cached_reviews?: number; newly_fetched_reviews?: number;
  retry_after_seconds?: number; unanalyzable_reviews?: number;
  collection?: {received: number; accepted: number; inserted: number;
    duplicates_in_batch: number; duplicates_in_database: number; blank: number; generated_ids: number};
};
const inputClass = "mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:opacity-60";
const modes = [
  {id: "url" as const, label: "URL sản phẩm", icon: Link2},
  {id: "import" as const, label: "Tải file CSV / Excel", icon: FileUp},
];
function downloadExample() {
  const content = '\uFEFFcontent,rating,customer_name,created_at\n"Sản phẩm tốt, giao hàng nhanh",5,Người mua,2026-10-01\n"Chất lượng chưa tốt",2,Khách hàng,2026-10-02\n';
  const objectUrl = URL.createObjectURL(new Blob([content], {type: "text/csv;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = objectUrl; link.download = "reviews-example.csv"; link.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
export default function Analyze() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("url");
  const [url, setUrl] = useState(""); const [productName, setProductName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  const [importResult, setImportResult] = useState<AnalyzeResponse | null>(null);

  function openResult(data: AnalyzeResponse, isImport = false) {
    if (!data.product_db_id) throw new Error("Backend không trả về product_db_id.");
    localStorage.removeItem("activeProductId");
    if (isImport) localStorage.removeItem("lastAnalyzedProductUrl");
    else localStorage.setItem("lastAnalyzedProductUrl", url.trim());
    if (data.product_name) localStorage.setItem("lastAnalyzedProductName", data.product_name);
    navigate(`/products/${data.product_db_id}/dashboard`, {state: {crawlWarning: isImport
      ? "Kết quả được phân tích từ file đã tải lên và các review đã lưu của sản phẩm này."
      : data.crawl_status === "PARTIAL"
        ? `Có ${data.crawled_reviews ?? 0} bình luận để phân tích. ${data.crawl_error ?? "Nguồn chưa cung cấp đủ đánh giá."}${data.retry_after_seconds ? ` Thử lại sau ít nhất ${data.retry_after_seconds} giây.` : ""}` : null}});
  }
  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setImportResult(null);
    if (mode === "url" && !url.trim()) {setError("Vui lòng nhập URL sản phẩm."); return;}
    if (mode === "import") {
      if (!productName.trim()) {setError("Vui lòng nhập tên sản phẩm."); return;}
      if (!file || !/\.(csv|xlsx|xls)$/i.test(file.name)) {setError("Chọn file CSV hoặc Excel (.xlsx, .xls)."); return;}
      if (file.size > MAX_FILE_BYTES) {setError("File vượt quá 5 MiB. Hãy chia thành nhiều file để gộp dữ liệu."); return;}
    }
    setLoading(true);
    try {
      const endpoint = mode === "import"
        ? `/collections/import?${new URLSearchParams({product_name: productName.trim(), format: file!.name.split(".").pop()!.toLowerCase()})}`
        : "/products/analyze";
      const response = await apiFetch(API_BASE_URL + endpoint, {
        method: "POST", headers: {"Content-Type": mode === "import" ? "application/octet-stream" : "application/json"},
        body: mode === "import" ? file : JSON.stringify({url: url.trim()}),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `Phân tích thất bại. HTTP ${response.status}`);
      if (!data?.product_db_id) throw new Error("Backend không trả về product_db_id.");
      if (mode === "import") setImportResult(data); else openResult(data);
    } catch (err) {setError(err instanceof Error ? err.message : "Không kết nối được hệ thống.");}
    finally {setLoading(false);}
  }
  return <div className="mx-auto max-w-4xl space-y-7">
    <header className="text-center"><h1 className="text-4xl font-bold text-slate-900">Bắt đầu phân tích sản phẩm</h1>
      <p className="mx-auto mt-3 max-w-2xl text-slate-500">Nhập URL để thu thập đánh giá hoặc tải file có sẵn để phân tích.</p></header>
    <div role="tablist" aria-label="Nguồn đánh giá" className="grid gap-2 rounded-2xl bg-slate-100 p-2 sm:grid-cols-2">
      {modes.map(({id, label, icon: Icon}) => <button key={id} id={`tab-${id}`} type="button" role="tab" aria-selected={mode === id} aria-controls={`panel-${id}`} disabled={loading}
        onClick={() => {setMode(id); setError(""); setImportResult(null);}}
        className={`flex items-center justify-center gap-2 rounded-xl px-3 py-3 text-sm font-semibold transition ${mode === id ? "bg-white text-blue-700 shadow-sm" : "text-slate-600 hover:bg-white/60"}`}>
        <Icon className="h-4 w-4" />{label}</button>)}
    </div>
    <section id={`panel-${mode}`} role="tabpanel" aria-labelledby={`tab-${mode}`} className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
      <form onSubmit={handleSubmit} className="space-y-5">
        {mode === "url" ? <div><label htmlFor="product-url" className="text-sm font-semibold text-slate-700">URL sản phẩm Lazada</label>
          <input id="product-url" type="url" required value={url} disabled={loading} onChange={event => setUrl(event.target.value)} placeholder="https://www.lazada.vn/products/pdp-i123-s456.html" className={inputClass} />
          <p className="mt-2 text-sm text-slate-500">Hệ thống tự thu thập bình luận, phân tích và lưu kết quả vào tài khoản của bạn.</p></div>
        : <>
          <div><label htmlFor="product-name" className="text-sm font-semibold text-slate-700">Tên sản phẩm</label>
            <input id="product-name" required maxLength={500} value={productName} disabled={loading} onChange={event => {setProductName(event.target.value); setImportResult(null);}} className={inputClass} placeholder="Ví dụ: Tai nghe Bluetooth ABC" />
            <p className="mt-2 text-sm text-slate-500">File cùng tên sản phẩm sẽ được gộp và loại review trùng trong tài khoản của bạn.</p></div>
          <div><label htmlFor="review-file" className="text-sm font-semibold text-slate-700">File đánh giá CSV / Excel</label>
            <input id="review-file" type="file" required accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel" disabled={loading} onChange={event => {setFile(event.target.files?.[0] ?? null); setImportResult(null);}} className={inputClass} />
            <p className="mt-2 text-sm text-slate-500">Cần cột <code>content</code> hoặc <strong>Nội dung / Bình luận</strong>. Số sao, tên khách hàng và ngày là tùy chọn. Excel đọc sheet đầu tiên. Tối đa 5 MiB và 10.000 dòng mỗi file.</p>
            <button type="button" onClick={downloadExample} className="mt-2 text-sm font-medium text-blue-700 hover:underline">Tải mẫu CSV</button></div>
        </>}
        {error && <div role="alert" className="whitespace-pre-wrap break-words rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</div>}
        <button type="submit" disabled={loading} className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 px-6 py-4 font-bold text-white hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60">
          {loading ? <><Loader2 className="h-5 w-5 animate-spin" />Đang phân tích...</> : <>{mode === "import" ? "Tải file và phân tích" : "Phân tích sản phẩm"}<ArrowRight className="h-5 w-5" /></>}</button>
        {loading && <p role="status" className="text-sm text-slate-500">{mode === "import" ? "Đang đọc file, loại trùng và phân tích đánh giá." : "Đang thu thập đánh giá và phân tích."} Tác vụ có thể mất nhiều phút. Vui lòng giữ trang này mở.</p>}
        {importResult?.collection && <div role="status" className="space-y-3 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-semibold">Đã nhập dữ liệu thành công</p>
          <p>{importResult.collection.received} dòng nhận được · {importResult.collection.inserted} review mới · {importResult.collection.duplicates_in_batch + importResult.collection.duplicates_in_database} trùng · {importResult.collection.blank} dòng không có bình luận.</p>
          {!!importResult.unanalyzable_reviews && <p>{importResult.unanalyzable_reviews} review không đủ văn bản cho AI.</p>}
          <button type="button" onClick={() => openResult(importResult, true)} className="font-bold underline">Xem kết quả phân tích →</button></div>}
      </form>
    </section>
  </div>;
}
