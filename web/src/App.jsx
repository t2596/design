import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import VehicleMonitor from './pages/VehicleMonitor';
import MetricsDashboard from './pages/MetricsDashboard';
import CertificateManagement from './pages/CertificateManagement';
import AuditLogs from './pages/AuditLogs';
import SecurityConfig from './pages/SecurityConfig';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <h1>车联网安全通信网关</h1>
          </div>
          <ul className="navbar-menu">
            <li><Link to="/">车辆监控</Link></li>
            <li><Link to="/metrics">安全指标</Link></li>
            <li><Link to="/certificates">证书管理</Link></li>
            <li><Link to="/audit">审计日志</Link></li>
            <li><Link to="/config">安全配置</Link></li>
          </ul>
        </nav>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<VehicleMonitor />} />
            <Route path="/metrics" element={<MetricsDashboard />} />
            <Route path="/certificates" element={<CertificateManagement />} />
            <Route path="/audit" element={<AuditLogs />} />
            <Route path="/config" element={<SecurityConfig />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
