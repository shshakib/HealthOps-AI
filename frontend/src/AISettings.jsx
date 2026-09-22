import React, { useEffect, useState } from "react";
import ProviderSettings from "./ProviderSettings.jsx";

export default function AISettings({ api }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true);
    setError("");
    try {
      setStatus(await api("/assistant/status"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);
  return (
    <main
      className="account-panel panel ai-settings"
      aria-label="AI configuration"
    >
      <span className="eyebrow">Settings · Administrator</span>
      <h1>AI configuration</h1>
      <p>
        Choose the model used by this workspace's assessment assistant.
        Reviewers can ask questions and use saved evidence without changing
        these settings.
      </p>
      {loading && <p role="status">Loading AI settings…</p>}
      {error && (
        <div role="alert">
          <p>{error}</p>
          <button className="secondary" onClick={load}>
            Retry
          </button>
        </div>
      )}
      {!loading && status && (
        <ProviderSettings
          status={status}
          api={api}
          onSaved={(next) => {
            setStatus((previous) => ({ ...previous, ...next }));
            window.dispatchEvent(new Event("healthops-ai-settings-changed"));
          }}
        />
      )}
    </main>
  );
}
