import { useEffect, useState } from "react";
import "./App.css";
import { api, API_BASE } from "./api";
import { formatCurrency, formatDays, formatPercent } from "./format";
import Masthead from "./components/Masthead";
import LedgerStrip from "./components/LedgerStrip";
import Section from "./components/Section";
import Button from "./components/Button";
import ExceptionsTable from "./components/ExceptionsTable";
import ForecastBars from "./components/ForecastBars";
import QaPanel from "./components/QaPanel";

const RECON_COLUMNS = [
  { key: "record_ref", label: "Ref" },
  { key: "source", label: "Source" },
  { key: "reason", label: "Reason" },
];

const TAX_COLUMNS = [
  { key: "record_ref", label: "Invoice" },
  { key: "reason", label: "Reason" },
];

export default function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [recon, setRecon] = useState(null);
  const [tax, setTax] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState({ recon: false, tax: false, forecast: false });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/docs`)
      .then((res) => {
        if (!cancelled) setBackendStatus(res.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setBackendStatus("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function runReconcile() {
    setLoading((s) => ({ ...s, recon: true }));
    setErrors((e) => ({ ...e, recon: null }));
    try {
      const data = await api.reconcile();
      setRecon(data);
    } catch (err) {
      setErrors((e) => ({ ...e, recon: err.message }));
    } finally {
      setLoading((s) => ({ ...s, recon: false }));
    }
  }

  async function runTaxCheck() {
    setLoading((s) => ({ ...s, tax: true }));
    setErrors((e) => ({ ...e, tax: null }));
    try {
      const data = await api.taxCheck();
      setTax(data);
    } catch (err) {
      setErrors((e) => ({ ...e, tax: err.message }));
    } finally {
      setLoading((s) => ({ ...s, tax: false }));
    }
  }

  async function runForecast() {
    setLoading((s) => ({ ...s, forecast: true }));
    setErrors((e) => ({ ...e, forecast: null }));
    try {
      const data = await api.forecast();
      setForecast(data);
    } catch (err) {
      setErrors((e) => ({ ...e, forecast: err.message }));
    } finally {
      setLoading((s) => ({ ...s, forecast: false }));
    }
  }

  const kpis = [
    {
      label: "Match rate",
      value: recon ? formatPercent(recon.match_rate) : "—",
    },
    {
      label: "Exceptions",
      value: recon ? String(recon.exception_count) : "—",
      tone: recon && recon.exception_count > 0 ? "risk" : undefined,
    },
    {
      label: "Tax-line match",
      value: tax ? formatPercent(tax.match_rate) : "—",
    },
    {
      label: "At-risk amount",
      value: forecast ? formatCurrency(forecast.at_risk_amount) : "—",
      tone: forecast && forecast.at_risk_amount > 0 ? "risk" : undefined,
    },
  ];

  return (
    <div className="page">
      <div className="page__inner">
        <Masthead status={backendStatus} />
        <LedgerStrip items={kpis} />

        <Section
          number="01"
          title="Reconciliation"
          description="Matches bank settlements against payment-gateway records and lists what's left over."
          action={
            <Button loading={loading.recon} loadingLabel="Reconciling…" onClick={runReconcile}>
              Run reconciliation
            </Button>
          }
        >
          {errors.recon && <p className="empty-note empty-note--error">{errors.recon}</p>}
          <ExceptionsTable
            rows={recon?.exceptions}
            columns={RECON_COLUMNS}
            emptyLabel="No exceptions — every record matched."
          />
        </Section>

        <Section
          number="02"
          title="Cash forecast"
          description="Projects expected inflow from outstanding items, based on historical settlement lag."
          action={
            <Button loading={loading.forecast} loadingLabel="Forecasting…" onClick={runForecast}>
              Run forecast
            </Button>
          }
        >
          {errors.forecast && (
            <p className="empty-note empty-note--error">{errors.forecast}</p>
          )}
          {forecast ? (
            <>
              <ForecastBars forecast={forecast} />
              <div className="forecast-meta">
                <span>
                  Average settlement lag{" "}
                  <strong>{formatDays(forecast.avg_settlement_lag_days)}</strong>
                </span>
                <span>
                  At risk <strong>{formatCurrency(forecast.at_risk_amount)}</strong>
                </span>
              </div>
              {forecast.explanation && (
                <p className="forecast-explanation">{forecast.explanation}</p>
              )}
            </>
          ) : (
            <p className="empty-note">Run the forecast to see the projected cash position.</p>
          )}
        </Section>

        <Section
          number="03"
          title="Tax-line exceptions"
          description="Flags invoice lines whose tax treatment doesn't match the expected rule."
          action={
            <Button loading={loading.tax} loadingLabel="Checking…" onClick={runTaxCheck}>
              Run tax check
            </Button>
          }
        >
          {errors.tax && <p className="empty-note empty-note--error">{errors.tax}</p>}
          <ExceptionsTable
            rows={tax?.exceptions}
            columns={TAX_COLUMNS}
            emptyLabel="No tax-line exceptions found."
          />
        </Section>

        <Section
          number="04"
          title="Settlement Q&A"
          description="Ask about a specific order, exception, or settlement pattern in plain language."
        >
          <QaPanel onAsk={api.ask} />
        </Section>

        <footer className="page__footer">
          Connected to {API_BASE}
        </footer>
      </div>
    </div>
  );
}
