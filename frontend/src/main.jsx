import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  FileText,
  FlaskConical,
  History,
  Info,
  Layers3,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import "./style.css";
import Assistant from "./Assistant.jsx";

import AuthGate, { authApi as api, useIdentity } from "./Auth.jsx";

const labels = {
  pending_review: "Awaiting review",
  approved: "Approved",
  rejected: "Rejected",
  advance_for_screening: "Advanced for screening",
  request_information: "Information requested",
  dismiss: "Dismissed",
  met: "Met",
  not_met: "Not met",
  unknown: "Unknown",
  all_modeled_criteria_met: "Modeled criteria met",
  insufficient_evidence: "More evidence needed",
  criteria_not_met: "Criteria not met",
};
const date = (value, time = false) =>
  value
    ? new Intl.DateTimeFormat("en-CA", {
        month: "short",
        day: "numeric",
        year: "numeric",
        ...(time ? { hour: "numeric", minute: "2-digit" } : {}),
      }).format(new Date(value.length === 10 ? `${value}T12:00:00` : value))
    : "Not recorded";
const patientName = (patient) => {
  const n = patient?.name?.[0];
  return (
    n?.text ||
    [n?.given?.join(" "), n?.family].filter(Boolean).join(" ") ||
    patient?.id ||
    "Select a patient"
  );
};
const initials = (text) =>
  text
    .split(" ")
    .filter(Boolean)
    .map((s) => s[0])
    .slice(0, 2)
    .join("");
const resourceLabel = (r) =>
  r.code?.text || r.code?.coding?.[0]?.display || r.resourceType;
const sourceUrl = (url) => {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" &&
      parsed.hostname === "clinicaltrials.gov"
      ? url
      : undefined;
  } catch {
    return undefined;
  }
};
function Badge({ value, children }) {
  return (
    <span
      className={`badge ${["met", "approved", "advance_for_screening", "all_modeled_criteria_met"].includes(value) ? "green" : ["not_met", "rejected", "criteria_not_met"].includes(value) ? "rose" : ["unknown", "pending_review", "insufficient_evidence", "request_information"].includes(value) ? "amber" : "neutral"}`}
    >
      {children || labels[value] || value}
    </span>
  );
}
function ErrorBox({ children }) {
  return children ? (
    <div className="error" role="alert">
      <Info size={17} />
      <span>{children}</span>
    </div>
  ) : null;
}
function Empty({ title, children }) {
  return (
    <div className="empty">
      <FileText size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Modal({ title, children, close }) {
  const ref = useRef(null);
  useEffect(() => {
    ref.current.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={close}
      onClick={(e) => {
        if (e.target === ref.current) close();
      }}
      aria-label={title}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button
          className="icon-button"
          onClick={close}
          aria-label="Close dialog"
        >
          <X size={20} />
        </button>
      </div>
      <div className="modal-body">{children}</div>
    </dialog>
  );
}
function ReviewForm({ kind, item, onSaved, onConflict }) {
  const identity = useIdentity();
  const [reason, setReason] = useState(""),
    [decision, setDecision] = useState(""),
    [ack, setAck] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const rules = kind === "rules";
  const options = rules
    ? [
        [
          "approve",
          "Approve interpretation",
          "Accept these partial rules for this synthetic demo.",
        ],
        [
          "reject",
          "Reject interpretation",
          "Keep this version inactive and record why.",
        ],
      ]
    : [
        [
          "request_information",
          "Request information",
          "Flag missing evidence for follow-up.",
        ],
        [
          "advance_for_screening",
          "Advance for screening",
          "Send the case to a more detailed human assessment.",
        ],
        [
          "dismiss",
          "Dismiss this match",
          "Stop considering this patient for this trial.",
        ],
      ];
  async function submit(e) {
    e.preventDefault();
    if (!ack || !decision) return;
    setBusy(true);
    setError("");
    try {
      const result = await api(
        rules
          ? `/rule-sets/${item.id}/reviews`
          : `/screenings/${item.id}/reviews`,
        {
          reason,
          decision,
          ...(rules
            ? { expected_rules_hash: item.rules_hash }
            : { expected_revision: item.revision }),
        },
      );
      await onSaved(result);
      setReason("");
      setDecision("");
      setAck(false);
    } catch (e) {
      setError(e.message);
      if (e.status === 409) {
        setAck(false);
        await onConflict?.();
      }
    } finally {
      setBusy(false);
    }
  }
  if (!identity.canReview)
    return (
      <p className="note">
        A reviewer account is required to record a decision.
      </p>
    );
  return (
    <form onSubmit={submit} className="review-form">
      <div className="section-heading">
        <ShieldCheck size={19} />
        <h3>{rules ? "Review this interpretation" : "Record your decision"}</h3>
      </div>
      <p className="muted">
        {rules
          ? "Review the source text and each proposed mapping before activating these partial rules."
          : "Your decision and reason are saved with the evidence you reviewed."}
      </p>
      <div className="decision-options">
        {options.map(([value, title, description]) => (
          <label
            className={`decision ${decision === value ? "chosen" : ""}`}
            key={value}
          >
            <input
              type="radio"
              name={`decision-${item.id}`}
              value={value}
              checked={decision === value}
              onChange={() => setDecision(value)}
              required
              disabled={busy}
            />
            <span>
              <strong>{title}</strong>
              <small>{description}</small>
            </span>
          </label>
        ))}
      </div>
      <p>
        Reviewer: <strong>{identity.username}</strong> � Signed-in account
      </p>
      <label className="field">
        Reason
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Explain the evidence and any unresolved questions…"
          required
          minLength={10}
          maxLength={2000}
          rows={3}
          disabled={busy}
        />
      </label>
      <label className="ack">
        <input
          type="checkbox"
          checked={ack}
          onChange={(e) => setAck(e.target.checked)}
          required
          disabled={busy}
        />
        <span>
          I have reviewed the{" "}
          {rules
            ? "source criteria and limits of this interpretation"
            : "evidence and unresolved requirements"}
          .
        </span>
      </label>
      <ErrorBox>{error}</ErrorBox>
      <button
        className="primary"
        disabled={busy || !ack || !decision || reason.trim().length < 10}
      >
        {busy ? (
          <LoaderCircle className="spin" size={16} />
        ) : (
          <Check size={16} />
        )}{" "}
        {rules ? "Save interpretation review" : "Save patient review"}
      </button>
      <p className="micro">
        Local demo · Reviewer labels are self-reported.{" "}
        {rules
          ? "Approval is not clinical validation."
          : "Saving a review does not contact anyone or enroll a patient."}
      </p>
    </form>
  );
}
function Evidence({ resource }) {
  return (
    <>
      <div className="eyebrow">{resource.resourceType}</div>
      <h3>{resourceLabel(resource)}</h3>
      <dl className="facts">
        <div>
          <dt>Record identifier</dt>
          <dd className="mono">{resource.id}</dd>
        </div>
        {resource.birthDate && (
          <div>
            <dt>Date of birth</dt>
            <dd>{date(resource.birthDate)}</dd>
          </div>
        )}
        {(resource.effectiveDateTime || resource.recordedDate) && (
          <div>
            <dt>Recorded date</dt>
            <dd>{date(resource.effectiveDateTime || resource.recordedDate)}</dd>
          </div>
        )}
        {resource.valueQuantity && (
          <div>
            <dt>Value</dt>
            <dd>
              {resource.valueQuantity.comparator} {resource.valueQuantity.value}{" "}
              {resource.valueQuantity.unit || resource.valueQuantity.code}
            </dd>
          </div>
        )}
        {resource.code?.coding?.map((c, i) => (
          <div key={i}>
            <dt>Code</dt>
            <dd>
              {c.display} <span className="mono">{c.code}</span>
            </dd>
          </div>
        ))}
      </dl>
      <details>
        <summary>Original resource</summary>
        <pre>{JSON.stringify(resource, null, 2)}</pre>
      </details>
    </>
  );
}
function PatientRecord({ bundle, onEvidence }) {
  const [query, setQuery] = useState(""),
    [limit, setLimit] = useState(30);
  const resources = bundle.entry
    .map((e) => e.resource)
    .filter((r) => r.resourceType !== "Patient");
  const filtered = resources
    .filter((r) =>
      `${resourceLabel(r)} ${r.id} ${r.resourceType}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    )
    .sort((a, b) =>
      (b.effectiveDateTime || b.recordedDate || "").localeCompare(
        a.effectiveDateTime || a.recordedDate || "",
      ),
    );
  return (
    <>
      <p className="muted">
        Patient, condition, and observation evidence. This is a limited view of
        the synthetic record.
      </p>
      <label className="searchbox">
        <Search size={17} />
        <input
          aria-label="Search health records"
          placeholder="Search diagnoses or observations"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setLimit(30);
          }}
        />
      </label>
      <p className="micro">{filtered.length} matching records</p>
      <div className="record-list">
        {filtered.slice(0, limit).map((r) => (
          <button
            key={`${r.resourceType}/${r.id}`}
            onClick={() => onEvidence(r)}
          >
            <span>
              <small>
                {r.resourceType} · {date(r.effectiveDateTime || r.recordedDate)}
              </small>
              <strong>{resourceLabel(r)}</strong>
            </span>
            <span>
              {r.valueQuantity?.value} {r.valueQuantity?.unit}
              <ArrowUpRight size={15} />
            </span>
          </button>
        ))}
      </div>
      {!filtered.length && (
        <Empty title="No matching records">Try a different search term.</Empty>
      )}
      {filtered.length > limit && (
        <button className="secondary" onClick={() => setLimit(limit + 30)}>
          Show more records
        </button>
      )}
    </>
  );
}
function ScreeningResult({ item, update, onEvidence }) {
  const patient = item.source_snapshot.patient_bundle.entry.find(
    (e) => e.resource.resourceType === "Patient",
  )?.resource;
  const trial = item.source_snapshot.trial;
  const title =
    trial.summary_at_screening?.title || trial.title || item.trial_id;
  return (
    <section className="panel result-panel">
      <div className="panel-head">
        <div>
          <div className="eyebrow">
            Saved assessment · {date(item.created_at)}
          </div>
          <h2>{patientName(patient)}</h2>
          <p className="muted">{title}</p>
        </div>
        <Badge value={item.outcome} />
      </div>
      <div className="case-meta">
        <span>
          <Clock3 size={15} /> Assessed as of {date(item.as_of)}
        </span>
        <span>
          {item.data_source === "hapi"
            ? "Synthea evidence"
            : "Handcrafted fixture"}
        </span>
        <span>
          {item.trial_id.startsWith("NCT")
            ? "Registry snapshot"
            : "Fictional trial exercise"}
        </span>
      </div>
      <div className="finding-counts">
        {["met", "not_met", "unknown"].map((status) => (
          <div key={status}>
            <strong>
              {item.criteria.filter((c) => c.status === status).length}
            </strong>
            <Badge value={status} />
          </div>
        ))}
      </div>
      <div className="findings">
        {item.criteria.map((c) => (
          <details
            key={c.criterion}
            className="finding"
            id={`criterion-${c.criterion}`}
          >
            <summary>
              <span className={`finding-icon ${c.status}`}>
                {c.status === "met" ? (
                  <Check size={17} />
                ) : c.status === "not_met" ? (
                  <X size={17} />
                ) : (
                  <Info size={17} />
                )}
              </span>
              <span>
                <strong>
                  {c.label ||
                    {
                      age: "Age requirement",
                      documented_condition: "Documented condition",
                      recent_lab_in_range: "Recent laboratory result",
                      full_eligibility_review: "Full eligibility review",
                    }[c.criterion] ||
                    c.criterion}
                </strong>
                <small>
                  {c.direction
                    ? `${c.direction[0].toUpperCase() + c.direction.slice(1)} · `
                    : ""}
                  {c.reason}
                </small>
              </span>
              <Badge value={c.status} />
            </summary>
            <div className="finding-body">
              {c.source_text && (
                <>
                  <div className="eyebrow">Trial source text</div>
                  <blockquote>{c.source_text}</blockquote>
                </>
              )}
              {c.evidence?.length > 0 ? (
                <div className="evidence-links">
                  {c.evidence.map((ref) => {
                    const resource =
                      item.source_snapshot.patient_bundle.entry.find(
                        (e) =>
                          `${e.resource.resourceType}/${e.resource.id}` === ref,
                      )?.resource;
                    return (
                      <button
                        className="text-button"
                        key={ref}
                        onClick={() => resource && onEvidence(resource)}
                        disabled={!resource}
                      >
                        <FileText size={15} />
                        {resource ? resourceLabel(resource) : ref}
                        <ArrowUpRight size={13} />
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p className="muted">
                  No supporting patient record establishes this requirement.
                </p>
              )}
            </div>
          </details>
        ))}
      </div>
      <div className="note">
        <Info size={17} />
        <p>{item.notice}</p>
      </div>
      <Assistant
        key={`${item.id}-${item.revision}`}
        item={item}
        api={api}
        onCitation={(id) => {
          const finding = document.getElementById(`criterion-${id}`);
          if (finding) {
            finding.open = true;
            finding.scrollIntoView({ behavior: "smooth", block: "center" });
            finding.querySelector("summary")?.focus();
          }
        }}
      />
      <div className="review-columns">
        <div>
          <ReviewForm
            key={item.id}
            kind="screening"
            item={item}
            onSaved={update}
            onConflict={async () =>
              update(await api(`/screenings/${item.id}`), false)
            }
          />
        </div>
        <div className="review-history">
          <div className="section-heading">
            <History size={18} />
            <h3>Decision history</h3>
          </div>
          {!item.reviews.length ? (
            <p className="muted">
              No decision yet. This assessment is awaiting a reviewer.
            </p>
          ) : (
            item.reviews
              .slice()
              .reverse()
              .map((review) => (
                <article className="timeline-item" key={review.id}>
                  <Badge value={review.decision} />
                  <p>{review.reason}</p>
                  <small>
                    {review.reviewer} · {date(review.recorded_at, true)} ·{" "}
                    {review.identity_verification ===
                    "authenticated_local_account"
                      ? "Signed-in account"
                      : "Legacy unverified label"}
                  </small>
                </article>
              ))
          )}
          <details className="audit-details">
            <summary>Assessment provenance</summary>
            <dl>
              <dt>Assessment ID</dt>
              <dd>{item.id}</dd>
              <dt>Evidence fingerprint</dt>
              <dd>{item.evidence_hash}</dd>
              <dt>Rules version</dt>
              <dd>{item.rules_version}</dd>
            </dl>
          </details>
        </div>
      </div>
    </section>
  );
}
function RuleEditor({ trial, rules, saved, close }) {
  const [rows, setRows] = useState(structuredClone(rules.document.rules)),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const change = (i, key, value) =>
    setRows((old) => old.map((r, j) => (j === i ? { ...r, [key]: value } : r)));
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const result = await api(`/trials/${trial.id}/rule-sets`, {
        snapshot_id: trial.snapshot_id,
        rules: rows,
      });
      await saved(result);
      close();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <p className="muted">
        A changed interpretation creates a new version for human review. Source
        quotations must match the saved registry text.
      </p>
      {rows.map((r, i) => (
        <fieldset className="editor-rule" key={r.id}>
          <legend>
            {r.kind === "age" ? "Age component" : "Condition component"}
          </legend>
          <label className="field">
            Label
            <input
              value={r.label}
              onChange={(e) => change(i, "label", e.target.value)}
              minLength={5}
              maxLength={300}
              required
            />
          </label>
          <label className="field">
            Direction
            <select
              value={r.direction}
              onChange={(e) => change(i, "direction", e.target.value)}
            >
              <option value="inclusion">Inclusion — required component</option>
              <option value="exclusion">
                Exclusion — disqualifying component
              </option>
            </select>
          </label>
          {r.kind === "age" ? (
            <div className="two-fields">
              {["minimum_years", "maximum_years"].map((key) => (
                <label className="field" key={key}>
                  {key === "minimum_years" ? "Minimum age" : "Maximum age"}
                  <input
                    type="number"
                    min="0"
                    max="150"
                    value={r[key] ?? ""}
                    onChange={(e) =>
                      change(
                        i,
                        key,
                        e.target.value === "" ? null : Number(e.target.value),
                      )
                    }
                  />
                </label>
              ))}
            </div>
          ) : (
            <label className="field">
              SNOMED CT code
              <input
                value={r.code}
                pattern="[0-9]{6,18}"
                required
                onChange={(e) => change(i, "code", e.target.value)}
              />
            </label>
          )}
          <label className="field">
            Exact source quotation
            <textarea
              rows={3}
              value={r.source_text}
              required
              minLength={3}
              onChange={(e) => change(i, "source_text", e.target.value)}
            />
          </label>
        </fieldset>
      ))}
      <ErrorBox>{error}</ErrorBox>
      <button className="primary" disabled={busy}>
        {busy ? (
          <LoaderCircle className="spin" size={17} />
        ) : (
          <Plus size={17} />
        )}{" "}
        Save draft version
      </button>
    </form>
  );
}
function TrialWorkspace({ trials, selected, select, refresh, notify }) {
  const { canReview } = useIdentity();
  const trial = trials.find((t) => t.id === selected),
    [activeRule, setActiveRule] = useState(""),
    [editing, setEditing] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    setActiveRule("");
    setError("");
  }, [selected]);
  const versions = trial?.rule_sets || [],
    rule = versions.find((v) => v.id === activeRule) || versions.at(-1);
  async function draft() {
    setBusy(true);
    setError("");
    try {
      const r = await api(`/trials/${trial.id}/rule-sets/draft`, {});
      await refresh(trial.id);
      setActiveRule(r.id);
      notify("Draft prepared. It still needs a human review.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="trial-layout">
      <aside className="panel trial-list">
        <div className="panel-head">
          <h3>Saved registry studies</h3>
          <span className="count">{trials.length}</span>
        </div>
        {trials.map((t) => (
          <button
            className={`trial-option ${selected === t.id ? "selected" : ""}`}
            onClick={() => select(t.id)}
            key={t.id}
          >
            <small>{t.id}</small>
            <strong>{t.title}</strong>
            <span>
              <Badge
                value={
                  t.rule_sets?.some(
                    (r) =>
                      r.status === "approved" &&
                      r.document.snapshot_id === t.snapshot_id,
                  )
                    ? "approved"
                    : "pending_review"
                }
              />
              <ArrowRight size={16} />
            </span>
          </button>
        ))}
      </aside>
      {!trial ? (
        <section className="panel">
          <Empty title="Select a study">
            Choose a saved registry study to inspect its source and
            interpretations.
          </Empty>
        </section>
      ) : (
        <div className="trial-detail">
          <section className="panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">ClinicalTrials.gov · {trial.id}</div>
                <h2>{trial.title}</h2>
              </div>
            </div>
            <div className="trial-dates">
              <span>
                <strong>
                  {trial.recruitment_status_at_snapshot
                    ?.replaceAll("_", " ")
                    .toLowerCase()}
                </strong>{" "}
                at snapshot
              </span>
              <span>
                Saved {date(trial.retrieved_at)} · {trial.snapshot_age_days}{" "}
                days old
              </span>
              <span>Registry update {date(trial.registry_last_update)}</span>
            </div>
            <p className="muted">{trial.selection_reason}</p>
            <div className="note">
              <Info size={17} />
              <p>
                Recruitment and locations reflect a saved snapshot. They do not
                confirm that a site currently accepts participants.
              </p>
            </div>
            <a
              className="text-button"
              href={sourceUrl(trial.source_url)}
              target="_blank"
              rel="noreferrer"
            >
              Open registry source <ArrowUpRight size={16} />
            </a>
            <details className="source-criteria">
              <summary>Read complete eligibility criteria</summary>
              <div className="source-text">
                {trial.eligibility?.eligibilityCriteria ||
                  "Study details are loading or unavailable. Refresh to retry."}
              </div>
            </details>
            <details>
              <summary>
                Study locations at snapshot (
                {trial.locations_at_snapshot?.length || 0})
              </summary>
              <ul className="locations">
                {trial.locations_at_snapshot?.map((l, i) => (
                  <li key={i}>
                    <strong>{l.facility}</strong>
                    <span>
                      {[l.city, l.state, l.country].filter(Boolean).join(", ")}{" "}
                      ·{" "}
                      {l.status?.replaceAll("_", " ") || "Status not recorded"}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          </section>
          <section className="panel">
            <div className="panel-head">
              <div>
                <div className="eyebrow">Human review comes first</div>
                <h2>Partial rule interpretation</h2>
              </div>
              <button
                className="secondary"
                onClick={draft}
                disabled={!canReview || busy || !trial.eligibility}
              >
                {busy ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <Plus size={16} />
                )}{" "}
                Prepare draft
              </button>
            </div>
            <ErrorBox>{error || trial.detailError}</ErrorBox>
            {!rule ? (
              <Empty title="No interpretation yet">
                Prepare a sourced draft, inspect its limits, then review it
                before screening.
              </Empty>
            ) : (
              <>
                <div className="rule-toolbar">
                  <label className="field">
                    Interpretation version
                    <select
                      value={rule.id}
                      onChange={(e) => setActiveRule(e.target.value)}
                    >
                      {versions.map((v, i) => (
                        <option key={v.id} value={v.id}>
                          Version {i + 1} · {labels[v.status]} ·{" "}
                          {v.id.slice(0, 8)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Badge value={rule.status} />
                </div>
                {rule.document.snapshot_id !== trial.snapshot_id && (
                  <div className="error">
                    This version belongs to an older snapshot. Prepare a current
                    draft.
                  </div>
                )}
                <div className="rule-cards">
                  {rule.document.rules.map((r) => (
                    <article key={r.id}>
                      <span className="eyebrow">
                        {r.direction} component · {r.kind}
                      </span>
                      <h3>{r.label}</h3>
                      <p className="rule-value">
                        {r.kind === "age"
                          ? `${r.minimum_years ?? "No minimum"} – ${r.maximum_years ?? "no maximum"} years`
                          : `Exact SNOMED CT code ${r.code}`}
                      </p>
                      <blockquote>{r.source_text}</blockquote>
                    </article>
                  ))}
                </div>
                <div className="note">
                  <ShieldCheck size={18} />
                  <p>
                    These rules cover only part of the study requirements. Full
                    eligibility, context, and unsupported criteria always remain
                    for manual assessment.
                  </p>
                </div>
                <button
                  className="secondary"
                  disabled={!canReview}
                  onClick={() => setEditing(rule)}
                >
                  Revise interpretation
                </button>
                {rule.status === "pending_review" &&
                rule.document.snapshot_id === trial.snapshot_id ? (
                  <ReviewForm
                    key={rule.id}
                    kind="rules"
                    item={rule}
                    onSaved={async () => {
                      await refresh(trial.id);
                      notify("Interpretation review saved.");
                    }}
                    onConflict={() => refresh(trial.id)}
                  />
                ) : (
                  rule.review && (
                    <article className="recorded-review">
                      <div className="section-heading">
                        <ClipboardCheck size={18} />
                        <h3>Recorded interpretation review</h3>
                      </div>
                      <p>{rule.review.reason}</p>
                      <small>
                        {rule.review.reviewer} ·{" "}
                        {rule.review.identity_verification ===
                        "authenticated_local_account"
                          ? "Signed-in account"
                          : "Legacy unverified label"}{" "}
                        · {date(rule.review.recorded_at, true)}
                      </small>
                    </article>
                  )
                )}
              </>
            )}
          </section>
        </div>
      )}
      {editing && (
        <Modal title="Revise interpretation" close={() => setEditing(null)}>
          <RuleEditor
            trial={trial}
            rules={editing}
            close={() => setEditing(null)}
            saved={async (result) => {
              await refresh(trial.id);
              setActiveRule(result.id);
              notify("Draft version saved. Review is required before use.");
            }}
          />
        </Modal>
      )}
    </div>
  );
}

function App() {
  const { canReview } = useIdentity();
  const [view, setView] = useState("screen"),
    [patients, setPatients] = useState({ hapi: [], fixtures: [] }),
    [trials, setTrials] = useState([]),
    [history, setHistory] = useState({
      items: [],
      total: 0,
      pending_count: 0,
      offset: 0,
      limit: 20,
    }),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [mode, setMode] = useState("hapi"),
    [patientId, setPatientId] = useState(""),
    [query, setQuery] = useState(""),
    [trialId, setTrialId] = useState("DEMO-SYNTHEA-T2D-001"),
    [ruleId, setRuleId] = useState(""),
    [asOf, setAsOf] = useState("2026-09-01"),
    [record, setRecord] = useState(null),
    [recordError, setRecordError] = useState(""),
    [recordBusy, setRecordBusy] = useState(false),
    [busy, setBusy] = useState(false),
    [screening, setScreening] = useState(null),
    [modal, setModal] = useState(null),
    [registryId, setRegistryId] = useState(""),
    [historyBusy, setHistoryBusy] = useState(false);
  const list = patients[mode],
    patient = list.find((p) => p.id === patientId),
    selectedTrial = trials.find((t) => t.id === trialId),
    registry = trials.filter((t) => !t.fictional),
    approved =
      selectedTrial?.rule_sets?.filter(
        (r) =>
          r.status === "approved" &&
          r.document.snapshot_id === selectedTrial.snapshot_id,
      ) || [];
  const [initialHash] = useState(() => window.location.hash);
  function navigate(next) {
    setView(next);
    window.history.replaceState(null, "", `#${next}`);
  }
  async function loadHistory(offset = 0) {
    setHistoryBusy(true);
    try {
      const next = await api(`/screenings?limit=20&offset=${offset}`);
      setHistory(next);
    } catch (e) {
      setError(e.message);
    } finally {
      setHistoryBusy(false);
    }
  }
  async function refreshTrial(id) {
    try {
      const detail = await api(`/trials/${id}`);
      setTrials((old) => old.map((t) => (t.id === id ? detail : t)));
      return detail;
    } catch (e) {
      setTrials((old) =>
        old.map((t) => (t.id === id ? { ...t, detailError: e.message } : t)),
      );
      throw e;
    }
  }
  async function load() {
    setLoading(true);
    setError("");
    const requests = await Promise.allSettled([
      api("/patients?source=hapi"),
      api("/patients?source=fixtures"),
      api("/trials"),
      api("/screenings?limit=20"),
    ]);
    const names = [
      "Synthea patients",
      "Demo fixtures",
      "Studies",
      "Review history",
    ];
    requests.forEach((r, i) => {
      if (r.status === "rejected")
        setError(
          (old) => `${old ? old + " · " : ""}${names[i]}: ${r.reason.message}`,
        );
    });
    if (requests[0].status === "fulfilled") {
      setPatients((old) => ({ ...old, hapi: requests[0].value }));
      setPatientId((old) => old || requests[0].value[0]?.id || "");
    }
    if (requests[1].status === "fulfilled")
      setPatients((old) => ({ ...old, fixtures: requests[1].value }));
    if (requests[3].status === "fulfilled") setHistory(requests[3].value);
    if (requests[2].status === "fulfilled") {
      setTrials(requests[2].value);
      const real = requests[2].value.filter((t) => !t.fictional);
      setRegistryId((old) => old || real[0]?.id || "");
      await Promise.allSettled(real.map((t) => refreshTrial(t.id)));
    }
    setLoading(false);
  }
  useEffect(() => {
    load();
    if (initialHash.startsWith("#assessment/"))
      openScreening(initialHash.slice(12));
  }, []);
  useEffect(() => {
    let active = true;
    setRecord(null);
    setRecordError("");
    if (!patientId) return;
    setRecordBusy(true);
    api(`/patients/${encodeURIComponent(patientId)}/record?source=${mode}`)
      .then((r) => {
        if (active) setRecord(r);
      })
      .catch((e) => {
        if (active) setRecordError(e.message);
      })
      .finally(() => {
        if (active) setRecordBusy(false);
      });
    return () => {
      active = false;
    };
  }, [patientId, mode]);
  useEffect(() => {
    if (notice) {
      const timer = setTimeout(() => setNotice(""), 6000);
      return () => clearTimeout(timer);
    }
  }, [notice]);
  const notify = (text) => setNotice(text);
  function changeMode(value) {
    setMode(value);
    setPatientId(patients[value][0]?.id || "");
    setTrialId(value === "hapi" ? "DEMO-SYNTHEA-T2D-001" : "DEMO-T2D-001");
    setRuleId("");
    setScreening(null);
    setQuery("");
  }
  async function openScreening(id) {
    setBusy(true);
    setError("");
    try {
      setScreening(await api(`/screenings/${encodeURIComponent(id)}`));
      setView("screen");
      window.history.replaceState(null, "", `#assessment/${id}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function run(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api("/screenings", {
        patient_id: patientId,
        trial_id: trialId,
        source: mode,
        as_of: asOf,
        ...(!selectedTrial?.fictional ? { rule_set_id: ruleId } : {}),
      });
      setScreening(result);
      window.history.replaceState(null, "", `#assessment/${result.id}`);
      await loadHistory();
      notify(
        "Assessment saved. Review the evidence before recording a decision.",
      );
    } catch (e) {
      setError(e.message);
      if (e.status === 409 && !selectedTrial?.fictional)
        await refreshTrial(trialId).catch(() => {});
    } finally {
      setBusy(false);
    }
  }
  const recordCounts = record?.entry.reduce(
    (acc, e) => ({
      ...acc,
      [e.resource.resourceType]: (acc[e.resource.resourceType] || 0) + 1,
    }),
    {},
  );
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          href="#screen"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            navigate("screen");
          }}
        >
          <span className="brand-icon">
            <Activity size={24} />
          </span>
          <span>
            HealthOps<span className="brand-sub">CLINICAL RESEARCH</span>
          </span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {[
            ["screen", Users, "Patient screening"],
            ["trials", FlaskConical, "Trial rules"],
            ["history", History, "Review history"],
          ].map(([key, Icon, label]) => (
            <button
              className={view === key ? "active" : ""}
              key={key}
              onClick={() => {
                navigate(key);
                if (key === "history") loadHistory();
              }}
            >
              <Icon size={19} />
              {label}
              {key === "history" && history.pending_count > 0 && (
                <span className="nav-count">{history.pending_count}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-note">
            <span className="local-mark" />
            <span>
              Local demo workspace<small>Synthetic patient data only</small>
            </span>
          </div>
          <a href="/docs" target="_blank" rel="noreferrer">
            API documentation <ArrowUpRight size={14} />
          </a>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>
            Workspace <ChevronRight size={14} />{" "}
            <strong>
              {view === "screen"
                ? "Patient screening"
                : view === "trials"
                  ? "Trial rules"
                  : "Review history"}
            </strong>
          </span>
          <div>
            <span className="demo-pill">
              <ShieldCheck size={14} /> Synthetic data
            </span>
            <button
              className="text-button refresh"
              onClick={load}
              disabled={loading}
            >
              {loading ? (
                <LoaderCircle className="spin" size={14} />
              ) : (
                <Activity size={14} />
              )}{" "}
              Refresh
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">RESEARCH COORDINATOR WORKSPACE</div>
              <h1>
                {view === "screen"
                  ? "Patient screening"
                  : view === "trials"
                    ? "From trial text to reviewed rules"
                    : "Every decision, with its evidence"}
              </h1>
              <p>
                {view === "screen"
                  ? "Connect patient evidence to trial requirements. Keep the decision human."
                  : view === "trials"
                    ? "Inspect the source, understand the limits, and review each interpretation."
                    : "Reopen a saved assessment and follow the complete review history."}
              </p>
            </div>
            <span className="page-marker">
              {view === "screen" ? "01" : view === "trials" ? "02" : "03"}{" "}
              <span>/ WORKSPACE</span>
            </span>
          </div>
          <ErrorBox>{error}</ErrorBox>
          {loading && (
            <div className="loading-line" role="status">
              <LoaderCircle className="spin" size={17} /> Loading workspace
              data…
            </div>
          )}
          {view === "screen" ? (
            <>
              <div className="stats">
                <Stat
                  icon={Users}
                  value={patients.hapi.length}
                  label="Synthea patients"
                  detail="Generated records in HAPI"
                />
                <Stat
                  icon={FlaskConical}
                  value={registry.length}
                  label="Registry studies"
                  detail="Saved ClinicalTrials.gov snapshots"
                />
                <Stat
                  icon={ClipboardCheck}
                  value={history.pending_count}
                  label="Awaiting review"
                  detail={`${history.total} saved assessments`}
                />
              </div>
              {screening ? (
                <>
                  <div className="back-row">
                    <button
                      className="text-button"
                      onClick={() => {
                        setScreening(null);
                        window.history.replaceState(null, "", "#screen");
                      }}
                    >
                      <ChevronLeft size={16} /> Start another assessment
                    </button>
                    <Badge value={screening.review_status} />
                  </div>
                  <ScreeningResult
                    item={screening}
                    onEvidence={(resource) =>
                      setModal({ type: "evidence", resource })
                    }
                    update={async (item, saved = true) => {
                      setScreening(item);
                      await loadHistory();
                      if (saved)
                        notify("Review saved with the original evidence.");
                    }}
                  />
                </>
              ) : (
                <div className="screen-layout">
                  <section className="panel patient-panel">
                    <div className="panel-head">
                      <div>
                        <div className="eyebrow">01 / SELECT</div>
                        <h2>Choose a patient</h2>
                      </div>
                      <span className="count">{list.length}</span>
                    </div>
                    <label className="field source-switch">
                      Patient data
                      <select
                        value={mode}
                        onChange={(e) => changeMode(e.target.value)}
                        disabled={busy || loading}
                      >
                        <option value="hapi">Synthea records</option>
                        <option value="fixtures">
                          Handcrafted demo fixtures
                        </option>
                      </select>
                    </label>
                    <label className="searchbox">
                      <Search size={17} />
                      <input
                        aria-label="Search patients"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search by name or ID"
                        disabled={busy}
                      />
                    </label>
                    <div className="patient-list">
                      {list
                        .filter((p) =>
                          `${patientName(p)} ${p.id}`
                            .toLowerCase()
                            .includes(query.toLowerCase()),
                        )
                        .map((p) => (
                          <button
                            key={p.id}
                            className={`patient-option ${patientId === p.id ? "selected" : ""}`}
                            onClick={() => setPatientId(p.id)}
                            disabled={busy}
                          >
                            <span className="avatar">
                              {initials(patientName(p))}
                            </span>
                            <span>
                              <strong>{patientName(p)}</strong>
                              <small>Born {date(p.birthDate)}</small>
                            </span>
                            {patientId === p.id ? (
                              <CheckCircle2 size={18} />
                            ) : (
                              <ChevronRight size={16} />
                            )}
                          </button>
                        ))}
                      {!list.filter((p) =>
                        `${patientName(p)} ${p.id}`
                          .toLowerCase()
                          .includes(query.toLowerCase()),
                      ).length && (
                        <Empty
                          title={
                            list.length
                              ? "No matching patients"
                              : "No patients available"
                          }
                        >
                          {list.length
                            ? "Try another name or identifier."
                            : "Import Synthea records or select the demo fixtures."}
                        </Empty>
                      )}
                    </div>
                    <div className="panel-footer">
                      <ShieldCheck size={14} /> Every person in this workspace
                      is synthetic.
                    </div>
                  </section>
                  <div className="assessment-column">
                    <section className="panel patient-summary">
                      <div className="summary-top">
                        <div className="avatar large">
                          {initials(patientName(patient))}
                        </div>
                        <div>
                          <div className="eyebrow">SELECTED PATIENT</div>
                          <h2>{patientName(patient)}</h2>
                          <span className="muted">
                            Born {date(patient?.birthDate)}
                          </span>
                        </div>
                        <Badge value="neutral">
                          {mode === "hapi" ? "Synthea" : "Demo fixture"}
                        </Badge>
                      </div>
                      <ErrorBox>{recordError}</ErrorBox>
                      <div className="record-strip">
                        <span>
                          <strong>
                            {recordBusy
                              ? "…"
                              : (recordCounts?.Condition ?? "—")}
                          </strong>{" "}
                          conditions
                        </span>
                        <span>
                          <strong>
                            {recordBusy
                              ? "…"
                              : (recordCounts?.Observation ?? "—")}
                          </strong>{" "}
                          observations
                        </span>
                        <button
                          className="text-button"
                          disabled={!record || recordBusy}
                          onClick={() =>
                            setModal({ type: "record", bundle: record })
                          }
                        >
                          View health records <ArrowUpRight size={15} />
                        </button>
                      </div>
                    </section>
                    <section className="panel assessment-panel">
                      <div className="panel-head">
                        <div>
                          <div className="eyebrow">02 / COMPARE</div>
                          <h2>Prepare an assessment</h2>
                        </div>
                        <Layers3 size={23} className="muted" />
                      </div>
                      <form onSubmit={run}>
                        <label className="field">
                          Trial or screening exercise
                          <select
                            value={trialId}
                            onChange={(e) => {
                              setTrialId(e.target.value);
                              setRuleId("");
                            }}
                            disabled={busy}
                            required
                          >
                            {trials
                              .filter((t) =>
                                mode === "hapi"
                                  ? t.id !== "DEMO-T2D-001"
                                  : t.id === "DEMO-T2D-001",
                              )
                              .map((t) => (
                                <option value={t.id} key={t.id}>
                                  {t.fictional ? "Demo exercise" : t.id} ·{" "}
                                  {t.title}
                                </option>
                              ))}
                          </select>
                        </label>
                        {selectedTrial?.fictional ? (
                          <div className="trial-context">
                            <Badge value="neutral">Fictional exercise</Badge>
                            <p>
                              Use this exercise to explore screening and human
                              review. Its thresholds are not clinical guidance.
                            </p>
                          </div>
                        ) : (
                          selectedTrial && (
                            <div className="trial-context">
                              <Badge value="neutral">
                                Real registry snapshot
                              </Badge>
                              <p>
                                Saved {date(selectedTrial.retrieved_at)}.
                                Recruitment status and all eligibility
                                requirements need review.
                              </p>
                              {approved.length ? (
                                <label className="field">
                                  Approved interpretation
                                  <select
                                    aria-label="Approved interpretation"
                                    value={ruleId}
                                    onChange={(e) => setRuleId(e.target.value)}
                                    required
                                    disabled={busy}
                                  >
                                    <option value="">
                                      Select a reviewed version
                                    </option>
                                    {approved.map((r) => (
                                      <option key={r.id} value={r.id}>
                                        {r.id.slice(0, 8)} · reviewed{" "}
                                        {date(r.review.recorded_at)}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                              ) : (
                                <div className="approval-gate">
                                  <Info size={18} />
                                  <div>
                                    <strong>Rule review required</strong>
                                    <p>
                                      This study needs an approved
                                      interpretation before screening.
                                    </p>
                                    <button
                                      type="button"
                                      className="text-button"
                                      onClick={() => {
                                        setRegistryId(trialId);
                                        navigate("trials");
                                      }}
                                    >
                                      Review trial rules{" "}
                                      <ArrowRight size={15} />
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        )}
                        <label className="field date-field">
                          Assess records as of
                          <input
                            type="date"
                            value={asOf}
                            onChange={(e) => setAsOf(e.target.value)}
                            required
                            disabled={busy}
                          />
                          <small>
                            Synthetic dataset reference: September 1, 2026.
                          </small>
                        </label>
                        <div className="assessment-action">
                          <p>
                            <ShieldCheck size={17} /> Results always await your
                            decision.
                          </p>
                          <button
                            className="primary"
                            disabled={
                              busy ||
                              !canReview ||
                              recordBusy ||
                              !record ||
                              !selectedTrial ||
                              (!selectedTrial.fictional &&
                                !approved.some((r) => r.id === ruleId))
                            }
                          >
                            {busy ? (
                              <LoaderCircle className="spin" size={17} />
                            ) : (
                              <ArrowRight size={17} />
                            )}{" "}
                            Run screening
                          </button>
                        </div>
                      </form>
                    </section>
                    <div className="workflow-note">
                      <span>
                        <CheckCircle2 size={16} /> Collect evidence
                      </span>
                      <ChevronRight size={13} />
                      <span>
                        <Layers3 size={16} /> Compare requirements
                      </span>
                      <ChevronRight size={13} />
                      <span>
                        <ClipboardCheck size={16} /> Human review
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : view === "trials" ? (
            <TrialWorkspace
              trials={registry}
              selected={registryId}
              select={setRegistryId}
              refresh={refreshTrial}
              notify={notify}
            />
          ) : (
            <section className="panel history-panel">
              <div className="panel-head">
                <div>
                  <div className="eyebrow">SAVED ASSESSMENTS</div>
                  <h2>
                    Review ledger <span className="count">{history.total}</span>
                  </h2>
                </div>
                <span className="muted">
                  {history.pending_count} awaiting a first review
                </span>
              </div>
              {history.items.length ? (
                <>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Patient</th>
                          <th>Study / exercise</th>
                          <th>Assessment</th>
                          <th>Review status</th>
                          <th>Created</th>
                          <th>
                            <span className="sr-only">Open</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.items.map((row) => {
                          const p = Object.values(patients)
                            .flat()
                            .find((p) => p.id === row.patient_id);
                          return (
                            <tr key={row.id}>
                              <td>
                                <strong>
                                  {p ? patientName(p) : row.patient_id}
                                </strong>
                                <small>
                                  {p ? "Synthetic patient" : row.patient_id}
                                </small>
                              </td>
                              <td>
                                {row.trial_id}
                                <small>
                                  {row.data_source === "hapi"
                                    ? "Synthea record"
                                    : "Handcrafted fixture"}
                                </small>
                              </td>
                              <td>
                                <Badge value={row.outcome} />
                              </td>
                              <td>
                                <Badge value={row.review_status} />
                              </td>
                              <td className="nowrap">{date(row.created_at)}</td>
                              <td>
                                <button
                                  className="icon-button"
                                  aria-label={`Open assessment ${row.id}`}
                                  onClick={() => openScreening(row.id)}
                                  disabled={busy}
                                >
                                  <ArrowUpRight size={18} />
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <div className="pagination">
                    <span>
                      {history.offset + 1}–
                      {Math.min(history.offset + history.limit, history.total)}{" "}
                      of {history.total}
                    </span>
                    <div>
                      <button
                        className="secondary"
                        disabled={history.offset === 0 || historyBusy}
                        onClick={() =>
                          loadHistory(
                            Math.max(0, history.offset - history.limit),
                          )
                        }
                      >
                        <ChevronLeft size={15} /> Previous
                      </button>
                      <button
                        className="secondary"
                        disabled={
                          history.offset + history.limit >= history.total ||
                          historyBusy
                        }
                        onClick={() =>
                          loadHistory(history.offset + history.limit)
                        }
                      >
                        Next <ChevronRight size={15} />
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <Empty title="No assessments yet">
                  Start with a patient, choose a trial, and run your first
                  screening.
                </Empty>
              )}
            </section>
          )}
          <footer>
            HealthOps · Synthetic research workspace{" "}
            <span>Evidence supports decisions. People make them.</span>
          </footer>
        </main>
      </div>
      {notice && (
        <div className="toast" role="status">
          <CheckCircle2 size={19} />
          {notice}
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {modal && (
        <Modal
          title={
            modal.type === "record"
              ? "Patient health records"
              : "Supporting evidence"
          }
          close={() => setModal(null)}
        >
          {modal.type === "record" ? (
            <PatientRecord
              bundle={modal.bundle}
              onEvidence={(resource) =>
                setModal({ type: "evidence", resource })
              }
            />
          ) : (
            <Evidence resource={modal.resource} />
          )}
        </Modal>
      )}
    </div>
  );
}
function Stat({ icon: Icon, value, label, detail }) {
  return (
    <section className="stat">
      <div className="stat-label">
        <span>{label}</span>
        <Icon size={19} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </section>
  );
}
createRoot(document.getElementById("root")).render(
  <AuthGate>
    <App />
  </AuthGate>,
);
