import React, { useState } from "react";

export default function ProviderSettings({ status, api, onSaved, disabled }) {
  const [provider, setProvider] = useState(status.provider || "offline");
  const [model, setModel] = useState(status.model || "");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const current = status.providers.find((p) => p.id === provider);
  const cloud = ["openai", "anthropic", "gemini"].includes(provider);
  function changeProvider(value) {
    setProvider(value);
    setModel(status.providers.find((p) => p.id === value)?.model || "");
    setKey("");
    setError("");
    setMessage("");
  }
  async function save(clearKey = false) {
    setBusy(true);
    setError("");
    setMessage("");
    const payload = { provider, model, clear_key: clearKey };
    if (!clearKey && key.trim()) payload.api_key = key.trim();
    setKey("");
    try {
      const result = await api("/assistant/settings", payload);
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
  return (
    <details className="provider-settings">
      <summary>Model connection settings</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save();
        }}
      >
        <fieldset disabled={busy || disabled}>
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
                  onChange={(e) => setModel(e.target.value)}
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
                  onChange={(e) => setKey(e.target.value)}
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
    </details>
  );
}
