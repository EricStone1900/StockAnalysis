import { Component, StrictMode, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { useEffect, useState } from 'react';
import type { DashboardData, DependencyStatus } from './dashboard.js';
import { statusLabel } from './dashboard.js';
import { checkCompatibility, fetchConfiguredDashboard } from './dashboard-client.js';
import { authStatus, routeFor } from './app-state.js';
import './styles.css';

class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  public state = { failed: false };
  public static getDerivedStateFromError() { return { failed: true }; }
  public render() { return this.state.failed ? <div className="error" role="alert">页面暂时无法显示，请刷新重试。</div> : this.props.children; }
}

function ResultCard({ title, result }: { title: string; result: { status: DependencyStatus; data?: unknown; errorCode?: string } }) {
  return <section className={`card status-${result.status.toLowerCase()}`}><h2>{title}</h2><p className="status">{statusLabel(result.status)}</p>{result.data ? <pre>{JSON.stringify(result.data, null, 2)}</pre> : <p>{result.errorCode ?? '暂无数据'}</p>}</section>;
}

function App() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [compatible, setCompatible] = useState(true);
  useEffect(() => { checkCompatibility().then(setCompatible); }, []);
  useEffect(() => { fetchConfiguredDashboard().then((result) => { if (result.data) setDashboard(result.data); if (result.error) setError(result.error); }); }, []);
  const route = routeFor(window.location.pathname);
  return <main><header><h1>Stock Analysis</h1><p>平台状态总览 · {authStatus('web-user')}</p></header>{!compatible && <div className="error" role="alert">前后端版本不兼容，请刷新或联系管理员。</div>}{route === 'unknown' ? <div className="error" role="alert">页面不存在</div> : <ErrorBoundary>{error && <div className="error" role="alert">{error}</div>}{dashboard ? <div className="grid"><ResultCard title="最新 DataVersion" result={dashboard.dataVersion} /><ResultCard title="日分析快照" result={dashboard.dailyAnalysisSnapshot} /><ResultCard title="Agent 服务" result={dashboard.agents} />{Object.entries(dashboard.services).map(([name, result]) => <ResultCard key={name} title={name} result={result as { status: DependencyStatus; data?: unknown; errorCode?: string }} />)}</div> : !error && <p>正在加载…</p>}</ErrorBoundary>}</main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
