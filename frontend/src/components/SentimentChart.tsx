import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

interface SentimentChartProps {
  positive: number;
  negative: number;
  neutral: number;
}

function SentimentChart({ positive, negative, neutral }: SentimentChartProps) {
  const data = [
    { name: "Tích cực", value: positive, color: "#22c55e" },
    { name: "Tiêu cực", value: negative, color: "#ef4444" },
    { name: "Trung lập", value: neutral, color: "#94a3b8" },
  ];
  const total = positive + negative + neutral;
  return <section aria-labelledby="sentiment-chart-title" className="min-w-0 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <h2 id="sentiment-chart-title" className="text-lg font-semibold text-slate-900">Phân tích cảm xúc</h2>
    <p className="mt-1 text-sm text-slate-500">Tỷ lệ tính trên những đánh giá đã có kết quả cảm xúc.</p>
    {total > 0 ? <div className="mt-3 h-60" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data.filter((entry) => entry.value > 0)} dataKey="value" nameKey="name" innerRadius={64} outerRadius={96} paddingAngle={3} isAnimationActive={false}>
            {data.filter((entry) => entry.value > 0).map((entry) => <Cell key={entry.name} fill={entry.color} />)}
          </Pie>
          <Tooltip formatter={(value) => [Number(value).toLocaleString("vi-VN"), "Đánh giá"]} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0" }} />
        </PieChart>
      </ResponsiveContainer>
    </div> : <p className="my-6 rounded-xl bg-slate-50 p-8 text-center text-sm text-slate-500">Chưa có kết quả phân tích cảm xúc.</p>}
    <ul className="mt-4 space-y-3 border-t border-slate-100 pt-4 text-sm">
      {data.map((entry) => <li key={entry.name} className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-slate-600"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />{entry.name}</span>
        <span className="text-slate-500"><strong className="mr-2 text-slate-900">{entry.value.toLocaleString("vi-VN")}</strong>{total ? (entry.value / total * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 }) : 0}%</span>
      </li>)}
    </ul>
  </section>;
}

export default SentimentChart;
