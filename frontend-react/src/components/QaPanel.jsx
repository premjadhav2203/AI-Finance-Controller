import { useState } from "react";
import Button from "./Button";

const SAMPLE_PROMPTS = [
  "Why wasn't ORD-1001 settled?",
  "Which exceptions are gateway-side?",
  "Summarize this week's unmatched amount",
];

export default function QaPanel({ onAsk }) {
  const [question, setQuestion] = useState("");
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit(q) {
    const text = (q ?? question).trim();
    if (!text || loading) return;
    setLoading(true);
    setError(null);
    try {
      const { answer } = await onAsk(text);
      setEntries((prev) => [{ question: text, answer }, ...prev]);
      setQuestion("");
    } catch (err) {
      setError(err.message || "Couldn't reach the Q&A agent.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="qa-panel">
      <form
        className="qa-panel__form"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          className="qa-panel__input"
          placeholder="e.g. why wasn't order ORD-1001 settled?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <Button loading={loading} loadingLabel="Asking…">
          Ask
        </Button>
      </form>

      <div className="qa-panel__prompts">
        {SAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            className="qa-panel__chip"
            onClick={() => submit(p)}
            disabled={loading}
          >
            {p}
          </button>
        ))}
      </div>

      {error && <p className="empty-note empty-note--error">{error}</p>}

      {entries.length === 0 && !error ? (
        <p className="empty-note">
          Ask about a specific order, an exception reason, or a settlement
          pattern.
        </p>
      ) : (
        <div className="qa-panel__thread">
          {entries.map((entry, i) => (
            <div className="qa-panel__entry" key={i}>
              <p className="qa-panel__question">{entry.question}</p>
              <p className="qa-panel__answer">{entry.answer}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
