import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { useEffect, useState } from 'react';
import type { DashboardData, DependencyStatus } from './dashboard.js';
import { statusLabel } from './dashboard.js';
import './styles.css';

function ResultCard({ title, result }: { title: string; result: { status: DependencyStatus; data?: unknown; errorCode?: string } }) {
  return <section className={`card status-${result.status.toLowerCase()}`}><h2>{title}</h2><p className="status">{statusLabel(result.status)}</p>{result.data ? <pre>{JSON.stringify(result.data, null, 2)}</pre> : <p>{result.errorCode ?? '暂无数据'}</p>}</section>;
}

function App() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { fetch('/api/v1/dashboard', { headers: { 'x-roles': 'RESEARCH_READ' } }).then(async (response) => { if (!response.ok) throw new Error(`Dashboard 请求失败：${response.status}`); return await response.json() as DashboardData; }).then(setDashboard).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Dashboard 请求失败')); }, []);
  return <main><header><h1>Stock Analysis</h1><p>平台状态总览</p></header>{error && <div className="error" role="alert">{error}</div>}{dashboard ? <div className="grid"><ResultCard title="最新 DataVersion" result={dashboard.dataVersion} /><ResultCard title="日分析快照" result={dashboard.dailyAnalysisSnapshot} />{Object.entries(dashboard.services).map(([name, result]) => <ResultCard key={name} title={name} result={result as { status: DependencyStatus; data?: unknown; errorCode?: string }} />)}</div> : !error && <p>正在加载…</p>}</main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
