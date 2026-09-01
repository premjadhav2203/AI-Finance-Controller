export default function Masthead({ status }) {
  const today = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const statusCopy = {
    checking: { label: "checking backend", dot: "checking" },
    online: { label: "backend connected", dot: "online" },
    offline: { label: "backend not reachable", dot: "offline" },
  }[status];

  return (
    <header className="masthead">
      <div className="masthead__top">
        <p className="masthead__eyebrow">Statement generated {today}</p>
        <div className={`status-pill status-pill--${status}`}>
          <span className="status-pill__dot" />
          {statusCopy.label}
        </div>
      </div>
      <h1 className="masthead__title">AI Finance Controller</h1>
      <p className="masthead__subtitle">
        Reconciles bank and gateway records, matches invoice tax lines, and
        projects the cash position from what's still outstanding.
      </p>
    </header>
  );
}
