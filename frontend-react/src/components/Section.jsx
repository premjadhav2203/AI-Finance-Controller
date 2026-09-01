export default function Section({ number, title, description, action, children }) {
  return (
    <section className="ledger-section">
      <div className="ledger-section__head">
        <div>
          <div className="ledger-section__title-row">
            <span className="ledger-section__number">{number}</span>
            <h2 className="ledger-section__title">{title}</h2>
          </div>
          {description && (
            <p className="ledger-section__description">{description}</p>
          )}
        </div>
        {action && <div className="ledger-section__action">{action}</div>}
      </div>
      <div className="ledger-section__body">{children}</div>
    </section>
  );
}
