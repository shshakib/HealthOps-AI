import React, { createContext, useContext, useEffect, useState } from "react";
import AISettings from "./AISettings.jsx";

const Identity = createContext(null);
export const useIdentity = () => useContext(Identity);

export async function authApi(path, body) {
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", "X-HealthOps-Request": "1" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(60000),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      window.dispatchEvent(new Event("healthops-session-ended"));
    }
    const error = new Error(
      Array.isArray(data.detail)
        ? data.detail
            .map((d) => `${d.loc.slice(1).join(" ")}: ${d.msg}`)
            .join("; ")
        : data.detail || "Request failed. Please retry.",
    );
    error.status = response.status;
    throw error;
  }
  return data;
}

function UserRow({ user, refresh }) {
  const [role, setRole] = useState(user.role);
  const [active, setActive] = useState(Boolean(user.active));
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await authApi(`/admin/users/${user.id}`, {
        role,
        active,
        ...(password ? { password } : {}),
      });
      setPassword("");
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className="user-row"
      onSubmit={save}
      aria-label={`Manage ${user.username}`}
    >
      <strong>{user.username}</strong>
      <label>
        Role
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          {["viewer", "reviewer", "admin"].map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </label>
      <label className="ack">
        <input
          type="checkbox"
          checked={active}
          onChange={(e) => setActive(e.target.checked)}
        />
        Active
      </label>
      <label>
        Reset password
        <input
          type="password"
          autoComplete="new-password"
          minLength={15}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Leave blank to keep password"
        />
      </label>
      <button className="secondary" disabled={busy}>
        Save user
      </button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

function Administration() {
  const [users, setUsers] = useState([]),
    [events, setEvents] = useState([]);
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [role, setRole] = useState("viewer");
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function refresh() {
    const [u, e] = await Promise.all([
      authApi("/admin/users"),
      authApi("/admin/events"),
    ]);
    setUsers(u);
    setEvents(e);
  }
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);
  async function create(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await authApi("/admin/users", { username, password, role });
      setPassword("");
      setUsername("");
      setMessage("Account created.");
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="account-panel panel">
      <h1>User management</h1>
      <p>
        Viewers read records and ask the assistant. Reviewers also screen
        patients and review trial rules. Administrators also manage accounts and
        AI settings.
      </p>
      <p>
        Saving an account revokes its sessions. At least one active
        administrator must remain.
      </p>
      <form onSubmit={create} className="user-row" aria-label="Create account">
        <label>
          New username
          <input
            required
            pattern="[a-zA-Z0-9_.-]{3,64}"
            autoComplete="off"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label>
          Initial password
          <input
            required
            type="password"
            autoComplete="new-password"
            minLength={15}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label>
          New role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {["viewer", "reviewer", "admin"].map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        <button className="primary" disabled={busy}>
          Create account
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {users.map((u) => (
        <UserRow key={u.id} user={u} refresh={refresh} />
      ))}
      <h2>Recent account activity</h2>
      <p>
        Latest 100 events. Review decisions remain in their assessment history.
      </p>
      <div className="account-events">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.occurred * 1000).toLocaleString()}</td>
                <td>{e.action.replaceAll("_", " ")}</td>
                <td>
                  {users.find((u) => u.id === e.actor)?.username ||
                    e.actor ||
                    "Unauthenticated"}
                </td>
                <td>
                  {users.find((u) => u.id === e.target)?.username ||
                    e.target ||
                    "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

function ChangePassword({ done }) {
  const [current, setCurrent] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await authApi("/auth/password", { current_password: current, password });
      done();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="account-panel panel" onSubmit={submit}>
      <h1>Change password</h1>
      <p>Use 15–128 characters. You will sign in again on all devices.</p>
      <label className="field">
        Current password
        <input
          required
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </label>
      <label className="field">
        New password
        <input
          required
          type="password"
          autoComplete="new-password"
          minLength={15}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && <p role="alert">{error}</p>}
      <button className="primary" disabled={busy}>
        Change password and sign out
      </button>
    </form>
  );
}

export default function AuthGate({ children }) {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [panel, setPanel] = useState("");
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const ended = () => {
    setUser(null);
    setPanel("");
    setPassword("");
  };
  useEffect(() => {
    if (panel) window.scrollTo(0, 0);
  }, [panel]);
  useEffect(() => {
    window.addEventListener("healthops-session-ended", ended);
    authApi("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => window.removeEventListener("healthops-session-ended", ended);
  }, []);
  useEffect(() => {
    if (!user) return;
    const check = () =>
      authApi("/auth/me")
        .then(setUser)
        .catch(() => {});
    const timer = setInterval(check, 60000);
    const expiry = setTimeout(
      ended,
      Math.max(0, user.expires * 1000 - Date.now()),
    );
    window.addEventListener("focus", check);
    return () => {
      clearInterval(timer);
      clearTimeout(expiry);
      window.removeEventListener("focus", check);
    };
  }, [user?.id, user?.expires]);
  async function login(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setUser(await authApi("/auth/login", { username, password }));
      setPassword("");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await authApi("/auth/logout", {});
      ended();
    } catch (e) {
      setError(e.message);
    }
  }
  if (loading)
    return (
      <div className="login-shell" role="status">
        Loading HealthOps…
      </div>
    );
  if (!user)
    return (
      <main className="login-shell">
        <form className="login-card" onSubmit={login}>
          <span className="eyebrow">
            HEALTHOPS AI · SYNTHETIC DATA WORKSPACE
          </span>
          <h1>Sign in to HealthOps</h1>
          <p>Review trial evidence and keep every decision accountable.</p>
          <label className="field">
            Username
            <input
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className="field">
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="muted">
            Ask your workspace administrator for an account. First-time setup is
            described in the repository's login guide.
          </p>
        </form>
      </main>
    );
  return (
    <Identity.Provider
      value={{
        ...user,
        canReview: user.role !== "viewer",
        openAISettings:
          user.role === "admin" ? () => setPanel("ai") : undefined,
      }}
    >
      <div className="account-bar">
        <span>
          Signed in as <strong>{user.username}</strong> · {user.role}
        </span>
        <div>
          {panel && (
            <button onClick={() => setPanel("")}>Back to workspace</button>
          )}
          {user.role === "admin" && (
            <>
              <button onClick={() => setPanel("users")}>Manage users</button>
              <button onClick={() => setPanel("ai")}>Settings</button>
            </>
          )}
          <button onClick={() => setPanel("password")}>Change password</button>
          <button onClick={logout}>Sign out</button>
        </div>
      </div>
      {error && <p role="alert">{error}</p>}
      {panel === "ai" && user.role === "admin" ? (
        <AISettings api={authApi} />
      ) : panel === "users" && user.role === "admin" ? (
        <Administration />
      ) : panel === "password" ? (
        <ChangePassword done={ended} />
      ) : null}
      <div hidden={Boolean(panel)}>{children}</div>
    </Identity.Provider>
  );
}
