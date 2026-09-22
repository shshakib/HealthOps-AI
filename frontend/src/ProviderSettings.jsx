import React, { useState } from "react";

export default function ProviderSettings({ status, api, onSaved, disabled }) {
  const [provider, setProvider] = useState(status.provider || "offline");
  const [model, setModel] = useState(status.model || "");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const current = status.providers.find((p) => p.id === provider);
  const cloud = ["openai", "anthropic", "gemini"].includes(provider);
  const unsaved =
    provider !== status.provider ||
    model !== (status.model || "") ||
    Boolean(key.trim());
  function changeProvider(value) {
    setProvider(value);
    setModel(status.providers.find((p) => p.id === value)?.model || "");
    setKey("");
    setError("");
    setMessage("");
    setTestResult(null);
  }
  async function save(clearKey = false) {
    setBusy(true);
    setError("");
    setMessage("");
    setTestResult(null);
    const payload = { provider, model, clear_key: clearKey };
    if (!clearKey && key.trim()) payload.api_key = key.trim();
    setKey("");
    try {
      const result = await api("/assistant/settings", payload);
      setProvider(result.provider);
      setModel(result.model || "");
      onSaved(result);
      setMessage(
        clearKey
          ? "Key removed from this server session."
          : "Settings saved. No model request was made.",
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function testConnection() {
    setTesting(true);
    setTestResult(null);
    setError("");
    try {
      // Reuse the bounded admin-only evaluation; never submit a patient review.
      const report = await api("/admin/evaluations", { limit: 1 });
      setTestResult({
        passed: report.passed,
        text: report.passed
          ? "Connection verified. The saved model completed one synthetic assessment check."
          : "The model did not complete a validated answer. Check the provider, model, key, and account access. Evidence-only mode remains available.",
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setTesting(false);
    }
  }
  return (
    <section
      className="provider-settings"
      aria-label="Model connection settings"
    >
      <h2>Model connection settings</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
      >
        <fieldset disabled={busy || disabled || testing}>
          <div className="provider-fields">
            <label>
              Provider
              <select
                aria-label="AI provider"
                value={provider}
                onChange={(e) => changeProvider(e.target.value)}
              >
                {status.providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            {provider !== "offline" && (
              <label>
                Model ID
                <input
                  aria-label="Model ID"
                  value={model}
                  onChange={(e) => {
                    setModel(e.target.value);
                    setTestResult(null);
                  }}
                  required
                  maxLength={100}
                  placeholder="Exact model ID from your provider"
                  autoComplete="off"
                  spellCheck={false}
                />
              </label>
            )}
          </div>
          {cloud && (
            <>
              <label>
                API key
                <input
                  aria-label="Provider API key"
                  type="password"
                  autoComplete="new-password"
                  value={key}
                  onChange={(e) => {
                    setKey(e.target.value);
                    setTestResult(null);
                  }}
                  maxLength={1024}
                  placeholder={
                    current?.key_configured
                      ? "Key is configured. Leave blank to keep it."
                      : "Paste your provider API key"
                  }
                />
              </label>
              <p className="muted">
                {current?.key_configured
                  ? "A key is configured on the server."
                  : "No key configured for this provider."}{" "}
                Keys are kept in server memory and are not returned to the
                browser. Session keys are lost when the server restarts.
              </p>
              <p className="provider-notice">
                Asking with this provider sends your question and selected
                synthetic assessment evidence to its API and may incur usage
                charges. Saving these settings makes no API call.
              </p>
            </>
          )}
          {provider === "ollama" && (
            <p className="muted">
              Enter the exact name of a downloaded local model that supports
              tools.
            </p>
          )}
          <div className="assistant-prompts">
            <button className="primary" type="submit">
              {busy ? "Saving…" : "Save model settings"}
            </button>
            {cloud && current?.key_configured && (
              <button
                className="secondary"
                type="button"
                onClick={() => save(true)}
              >
                Remove API key
              </button>
            )}
          </div>
        </fieldset>
      </form>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      <div className="connection-test">
        <h3>Check the saved connection</h3>
        <p>
          Runs one fictional assessment check using the saved settings, with up
          to four model calls. Cloud providers may charge for this test. No
          patient assessment or review is created. A successful check does not
          validate every answer the model might give.
        </p>
        {unsaved && <p className="muted">Save your changes before testing.</p>}
        {!status.model_configured && (
          <p className="muted">
            Configure a model and any required key to enable testing.
          </p>
        )}
        <button
          className="secondary"
          type="button"
          onClick={testConnection}
          disabled={
            busy || disabled || testing || unsaved || !status.model_configured
          }
        >
          {testing ? "Testing connection…" : "Test saved connection"}
        </button>
        {testing && (
          <p role="status">Checking the model; this may take up to a minute.</p>
        )}
        {testResult && (
          <p role={testResult.passed ? "status" : "alert"}>{testResult.text}</p>
        )}
      </div>
    </section>
  );
}
