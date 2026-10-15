import React, { Suspense, lazy, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { request, invalidate, cache } from './api';
import { useRoute } from './hooks';
import { Icon, label, State } from './ui';
import { Management } from './management';
import { modules } from './modules';
import { ResourceIntelligence } from './intelligence';
import { Simulator } from './simulator';
import { Reports, History, Search } from './reports';
import './style.css';
import './replay.css';
import { navigationFor } from './navigation';
const Overview = lazy(() => import('./overview').then((m) => ({ default: m.Overview })));
const ReplayStudio = lazy(() => import('./replay').then((m) => ({ default: m.ReplayStudio })));
class PageBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <section className="notice error" role="alert">
        <h2>This page could not be displayed</h2>
        <p>Reload the page to try again. If this continues, see the troubleshooting guide.</p>
        <button onClick={() => location.reload()}>Reload page</button>
      </section>
    ) : (
      this.props.children
    );
  }
}
function Login({ onLogin }) {
  const [register, setRegister] = useState(false),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    const values = Object.fromEntries(new FormData(e.currentTarget));
    try {
      await request(`/api/auth/${register ? 'register' : 'login'}`, {
        method: 'POST',
        body: JSON.stringify(values),
      });
      if (register) {
        setRegister(false);
        setError('Account created. Sign in to report an emergency.');
      } else {
        onLogin(await request('/api/auth/me'));
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-layout">
      <section className="login-story">
        <a className="brand" href="#/overview">
          <span className="brand-mark">D</span>
          <span>
            DMS<strong>Disaster Management System</strong>
          </span>
        </a>
        <span className="eyebrow">PREPAREDNESS. RESPONSE. RECOVERY.</span>
        <h1>
          Every response starts
          <br />
          with a clear picture.
        </h1>
        <p>
          Report emergencies, coordinate resources and keep decisions connected to reliable records.
        </p>
        <div className="login-note">
          <Icon name="map" />
          <span>Built for coordinated disaster response across India.</span>
        </div>
      </section>
      <section className="login-form">
        <span className="eyebrow">RESPONSE OPERATIONS</span>
        <h2>{register ? 'Create your account' : 'Welcome back'}</h2>
        <p>
          {register
            ? 'Public accounts can submit reports and track their status.'
            : 'Sign in to access your response workspace.'}
        </p>
        <form onSubmit={submit}>
          {register && (
            <label>
              <span>Full name</span>
              <input name="full_name" autoComplete="name" required maxLength={100} />
            </label>
          )}
          <label>
            <span>Email address</span>
            <input name="email" type="email" required autoComplete="username" maxLength={150} />
          </label>
          <label>
            <span>Password</span>
            <input
              name="password"
              type="password"
              required
              minLength={register ? 10 : 1}
              maxLength={128}
              autoComplete={register ? 'new-password' : 'current-password'}
            />
          </label>
          {error && (
            <p className="notice error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? 'Please wait…' : register ? 'Create public account' : 'Sign in'}
          </button>
        </form>
        <button
          className="text-button"
          onClick={() => {
            setRegister(!register);
            setError('');
          }}
        >
          {register ? 'Already registered? Sign in' : 'New here? Create a public account'}
        </button>
        <small className="muted">
          Administrator accounts are provisioned securely using the backend setup command.
        </small>
      </section>
    </div>
  );
}
function App() {
  const route = useRoute();
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [initialError, setInitialError] = useState(''),
    [theme, setTheme] = useState(() => localStorage.getItem('dms-theme') || 'light'),
    [open, setOpen] = useState(false),
    [message, setMessage] = useState(''),
    [logoutError, setLogoutError] = useState(''),
    [loggingOut, setLoggingOut] = useState(false);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('dms-theme', theme);
  }, [theme]);
  useEffect(() => {
    let active = true;
    request('/api/auth/me')
      .then((data) => {
        if (active) setUser(data);
      })
      .catch((e) => {
        if (
          active &&
          !e.message.toLowerCase().includes('sign in') &&
          !e.message.toLowerCase().includes('authentication')
        )
          setInitialError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    const expired = () => {
      setUser(null);
      cache.clear();
      setInitialError('Your session expired. Sign in again.');
    };
    window.addEventListener('dms-session-expired', expired);
    return () => {
      active = false;
      window.removeEventListener('dms-session-expired', expired);
    };
  }, []);
  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [route]);
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(''), 6000);
    return () => clearTimeout(timer);
  }, [message]);
  function login(data) {
    cache.clear();
    setUser(data.user || data);
    setInitialError('');
    location.hash = '/overview';
  }
  async function logout() {
    setLoggingOut(true);
    setLogoutError('');
    try {
      await request('/api/auth/logout', { method: 'POST' });
      cache.clear();
      setUser(null);
      location.hash = '/overview';
    } catch (e) {
      setLogoutError(e.message);
    } finally {
      setLoggingOut(false);
    }
  }
  if (loading)
    return (
      <div className="startup">
        <State loading />
      </div>
    );
  if (!user)
    return (
      <>
        {initialError && (
          <div className="connection-banner" role="alert">
            {initialError}
          </div>
        )}
        <Login onLogin={login} />
      </>
    );
  const admin = ['ADMIN', 'DISASTER_MANAGER'].includes(user.role);
  const nav = navigationFor(user.role);
  const allowed = nav.routes;
  const title = allowed.find(([key]) => key === route)?.[1] || 'Overview';
  let content;
  if (!allowed.some(([key]) => key === route))
    content = (
      <div className="notice error">
        This page is unavailable for your role. <a href="#/overview">Return to Overview</a>
      </div>
    );
  else if (modules[route])
    content = <Management key={route} module={route} user={user} notify={setMessage} />;
  else if (route === 'overview') content = <Overview user={user} />;
  else if (route === 'disaster-replay') content = <ReplayStudio />;
  else if (route === 'resource-intelligence')
    content = <ResourceIntelligence notify={setMessage} />;
  else if (route === 'response-simulator') content = <Simulator notify={setMessage} />;
  else if (route === 'reports') content = <Reports />;
  else if (['audit-history', 'resource-movements'].includes(route))
    content = <History key={route} module={route} />;
  else if (route === 'search') content = <Search user={user} />;
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById('main-content')?.focus();
        }}
      >
        Skip to content
      </a>
      {open && (
        <button
          className="sidebar-overlay"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <a className="brand" href="#/overview">
          <span className="brand-mark">D</span>
          <span>
            DMS<strong>Response operations</strong>
          </span>
        </a>
        <div className="workspace-label">{admin ? 'OPERATIONS WORKSPACE' : 'PUBLIC WORKSPACE'}</div>
        <nav aria-label="Main navigation">
          {nav.main.map(([key, title, icon]) => (
            <a
              key={key}
              href={`#/${key}`}
              className={route === key ? 'active' : ''}
              aria-current={route === key ? 'page' : undefined}
            >
              <Icon name={icon} />
              <span>{title}</span>
            </a>
          ))}
          {nav.advanced.length > 0 && (
            <div className="advanced-navigation">
              <div className="workspace-label">ADVANCED TOOLS</div>
              {nav.advanced.map(([key, title, icon]) => (
                <a
                  key={key}
                  href={`#/${key}`}
                  className={route === key ? 'active' : ''}
                  aria-current={route === key ? 'page' : undefined}
                >
                  <Icon name={icon} />
                  <span>{title}</span>
                </a>
              ))}
            </div>
          )}
        </nav>
        <footer>
          <span className="workspace-label">DATABASE MANAGEMENT PROJECT</span>
          <small>Version 4.0 · India</small>
        </footer>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="menu-toggle icon-button"
              aria-label="Open navigation"
              onClick={() => setOpen(!open)}
            >
              <Icon name="menu" />
            </button>
            <span className="breadcrumb">
              Workspace <span>/</span> <strong>{title}</strong>
            </span>
          </div>
          <div className="account-controls">
            {admin && (
              <a
                className="icon-button"
                href="#/search"
                aria-label="Search records"
                title="Search records"
              >
                <Icon name="search" />
              </a>
            )}
            <div className="account">
              <span className="avatar">{user.full_name?.slice(0, 1) || 'U'}</span>
              <span>
                {user.full_name}
                <small>{label(user.role)}</small>
              </span>
            </div>
            <button
              className="icon-button"
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              title="Switch theme"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              <Icon name="sun" />
            </button>
            <button
              className="icon-button"
              aria-label="Sign out"
              title="Sign out"
              disabled={loggingOut}
              onClick={logout}
            >
              <Icon name="logout" />
            </button>
          </div>
        </header>
        {logoutError && (
          <p className="notice error" role="alert">
            {logoutError}
          </p>
        )}
        <main id="main-content" tabIndex="-1">
          <PageBoundary key={route}>
            <Suspense fallback={<State loading />}>{content}</Suspense>
          </PageBoundary>
        </main>
        <footer className="app-footer">
          DMS · Coordinated response, accountable records{' '}
          <span>Data refreshes on request; no live status is implied.</span>
        </footer>
      </div>
      {message && (
        <div className="toast" role="status">
          {message}
          <button aria-label="Dismiss message" onClick={() => setMessage('')}>
            <Icon name="close" />
          </button>
        </div>
      )}
    </div>
  );
}
createRoot(document.getElementById('root')).render(<App />);
