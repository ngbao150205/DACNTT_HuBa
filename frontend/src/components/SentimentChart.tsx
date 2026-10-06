import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface SentimentChartProps {
  positive: number;
  negative: number;
  neutral: number;
}

function SentimentChart({
  positive,
  negative,
  neutral,
}: SentimentChartProps) {

  const data = [
    {
      name: "Tích cực",
      value: positive,
    },
    {
      name: "Tiêu cực",
      value: negative,
    },
    {
      name: "Trung lập",
      value: neutral,
    },
  ];

  return (
    <div className="
      bg-white
      rounded-2xl
      border
      border-gray-100
      p-6
      shadow-sm
    ">

      <h2 className="
        font-semibold
        text-lg
        mb-5
      ">
        Phân tích cảm xúc
      </h2>

      <div className="h-72">

        <ResponsiveContainer
          width="100%"
          height="100%"
        >

          <PieChart>

            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label
            >

              {data.map((_, index) => (
                <Cell
                  key={index}
                  fill={
                    index === 0
                      ? "#22c55e"
                      : index === 1
                      ? "#ef4444"
                      : "#94a3b8"
                  }
                />
              ))}

            </Pie>

            <Tooltip />

          </PieChart>

        </ResponsiveContainer>

      </div>

    </div>
  );
}

export default SentimentChart;