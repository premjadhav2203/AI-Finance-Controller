import { formatCurrency } from "../format";

export default function ForecastBars({ forecast }) {
  const buckets = [
    { label: "Next 7 days", value: forecast.next_7_days },
    { label: "Next 14 days", value: forecast.next_14_days },
    { label: "Next 30 days", value: forecast.next_30_days },
  ];
  const max = Math.max(...buckets.map((b) => b.value), 1);

  return (
    <div className="forecast-bars">
      {buckets.map((b) => (
        <div className="forecast-bars__row" key={b.label}>
          <span className="forecast-bars__label">{b.label}</span>
          <div className="forecast-bars__track">
            <div
              className="forecast-bars__fill"
              style={{ width: `${Math.max((b.value / max) * 100, 2)}%` }}
            />
          </div>
          <span className="forecast-bars__value">{formatCurrency(b.value)}</span>
        </div>
      ))}
    </div>
  );
}
