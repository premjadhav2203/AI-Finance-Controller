export default function LedgerStrip({ items }) {
  return (
    <div className="ledger-strip">
      {items.map((item) => (
        <div className="ledger-strip__item" key={item.label}>
          <span className="ledger-strip__label">{item.label}</span>
          <span
            className="ledger-strip__value"
            style={item.tone ? { color: `var(--${item.tone})` } : undefined}
          >
            {item.value}
          </span>
          {item.hint && (
            <span className="ledger-strip__hint">{item.hint}</span>
          )}
        </div>
      ))}
    </div>
  );
}
