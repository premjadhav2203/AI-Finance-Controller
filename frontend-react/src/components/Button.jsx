export default function Button({
  children,
  onClick,
  loading,
  loadingLabel,
  disabled,
  variant = "solid",
}) {
  return (
    <button
      className={`btn btn--${variant}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? loadingLabel || "Working…" : children}
    </button>
  );
}
