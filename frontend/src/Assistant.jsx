import React, { useEffect, useState } from "react";
import { MessageSquareText, ArrowUpRight, LoaderCircle } from "lucide-react";
import { useIdentity } from "./Auth.jsx";
import ProviderSettings from "./ProviderSettings.jsx";

const questions = [
  "Explain this screening",
  "What evidence is missing?",
  "What can a reviewer do next?",
];
const reasons = {
  model_not_configured:
    "No model is configured. Showing saved evidence directly.",
  api_key_missing:
    "This provider needs an API key. Showing saved evidence directly.",
  invalid_api_key:
    "The provider rejected the API key. Check model connection settings.",
  provider_access_denied:
    "The provider denied access. Check your key and model permissions.",
  provider_rate_limit:
    "The provider's rate or quota limit was reached. Showing saved evidence directly.",
  model_not_available:
    "The model was not available. Check the model ID and account access.",
  provider_request_rejected:
    "The provider rejected the request. This model may not support the required tools or response format.",
  requested_evidence_only:
    "Showing saved evidence directly, without using a model.",
};

export default function Assistant({ item, api, onCitation }) {
  const { role } = useIdentity();
  const [question, setQuestion] = useState(questions[0]);
  const [answer, setAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(null);
  const [evidenceOnly, setEvidenceOnly] = useState(false);
  useEffect(() => {
    let active = true;
    api("/assistant/status")
      .then((s) => active && setStatus(s))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [api]);
  async function ask(value) {
    setQuestion(value);
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      setAnswer(
        await api(`/screenings/${encodeURIComponent(item.id)}/assistant`, {
          question: value,
          use_model: !evidenceOnly,
        }),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="assistant-panel" aria-label="Screening assistant">
      <div className="section-heading">
        <MessageSquareText size={19} />
        <h3>Ask about this assessment</h3>
        <span className="assistant-mode">
          {status?.model_configured
            ? `${status.providers?.find((p) => p.id === status.provider)?.label || "Model"} configured`
            : "Evidence-only available"}
        </span>
      </div>
      <p className="muted">
        Explore the findings and what remains unresolved. Every answer stays
        linked to this saved assessment.
      </p>
      {role === "admin" && status?.providers?.length > 0 && (
        <ProviderSettings
          status={status}
          api={api}
          disabled={busy}
          onSaved={(next) => {
            setStatus((previous) => ({ ...previous, ...next }));
            setAnswer(null);
          }}
        />
      )}
      {["openai", "anthropic", "gemini"].includes(status?.provider) &&
        !evidenceOnly && (
          <p className="provider-notice">
            Cloud provider selected: questions and selected synthetic evidence
            will be sent to{" "}
            {status.providers?.find((p) => p.id === status.provider)?.label}.
            API usage may be charged.
          </p>
        )}
      <div className="assistant-prompts">
        {questions.map((q) => (
          <button
            className="secondary"
            key={q}
            disabled={busy}
            onClick={() => ask(q)}
          >
            {q}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
      >
        <label htmlFor="assistant-question">Your question</label>
        <div className="assistant-input">
          <input
            id="assistant-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            minLength={3}
            maxLength={1000}
            required
            disabled={busy}
          />
          <button
            className="primary"
            disabled={busy || question.trim().length < 3}
          >
            {busy ? (
              <>
                <LoaderCircle size={16} className="spin" /> Reading evidence…
              </>
            ) : (
              "Ask assistant"
            )}
          </button>
        </div>
        <label className="assistant-option">
          <input
            type="checkbox"
            role="switch"
            checked={evidenceOnly}
            disabled={busy}
            onChange={(e) => setEvidenceOnly(e.target.checked)}
          />
          Use saved evidence without a model
        </label>
      </form>
      {error && (
        <p role="alert" className="error">
          {error} You can still review the findings above.
        </p>
      )}
      {answer && (
        <div className="assistant-answer" aria-live="polite">
          <div className="eyebrow">
            {answer.mode === "model_assisted"
              ? "Model-selected evidence"
              : "Evidence-only answer"}
          </div>
          {answer.mode === "fallback" && (
            <p className="muted">
              {reasons[answer.fallback_reason] ||
                "The model could not complete a validated answer. Showing the evidence-only fallback."}
            </p>
          )}
          <p>{answer.answer}</p>
          {answer.citations.map((c) => (
            <article className="assistant-citation" key={c.id}>
              <button className="text-button" onClick={() => onCitation(c.id)}>
                {c.label} <ArrowUpRight size={14} />
              </button>
              <span className={`assistant-status ${c.status}`}>
                {c.status.replaceAll("_", " ")}
              </span>
              <p>{c.text}</p>
              {!c.evidence.length && (
                <small className="muted">
                  No patient evidence cited; inspect the requirement for
                  context.
                </small>
              )}
            </article>
          ))}
          <p className="muted">{answer.notice}</p>
          <details className="audit-details">
            <summary>How this answer was produced</summary>
            <p>
              {answer.mode === "model_assisted"
                ? `The model (${answer.model}) selected evidence through read-only tools. Wording and findings come from the saved assessment.`
                : "A fixed question template selected saved findings. No model-generated answer is being shown."}
            </p>
            <p>
              Assessment date: {answer.as_of} · Response: {answer.latency_ms} ms
            </p>
            <p>
              Each question is independent. Answers are not added to the review
              ledger.
            </p>
            {!!answer.tool_trace.length && (
              <ul>
                {answer.tool_trace.map((t, i) => (
                  <li key={i}>
                    {t.tool}
                    {t.criterion_id ? ` · ${t.criterion_id}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </details>
        </div>
      )}
    </section>
  );
}
