interface RiskCardProps {
  level: string;
  count: number;
}

function RiskCard({
  level,
  count,
}: RiskCardProps) {

  const normalized = level.toUpperCase();

  const styles =
    normalized === "HIGH"
      ? "border-red-200 bg-red-50 text-red-700"
      : normalized === "MEDIUM"
      ? "border-yellow-200 bg-yellow-50 text-yellow-700"
      : "border-green-200 bg-green-50 text-green-700";

  return (
    <div className={`
      rounded-2xl
      border
      p-5
      ${styles}
    `}>

      <p className="
        text-sm
        font-medium
      ">
        {level}
      </p>

      <p className="
        text-3xl
        font-bold
        mt-2
      ">
        {count}
      </p>

      <p className="
        text-xs
        mt-1
        opacity-70
      ">
        đánh giá
      </p>

    </div>
  );
}

export default RiskCard;