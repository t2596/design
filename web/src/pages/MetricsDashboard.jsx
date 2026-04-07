import React, { useState, useEffect } from 'react';
import { getRealtimeMetrics, getHistoricalMetrics } from '../api/metrics';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function MetricsDashboard() {
  const [realtimeMetrics, setRealtimeMetrics] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('24h');

  const loadRealtimeMetrics = async () => {
    try {
      const data = await getRealtimeMetrics();
      setRealtimeMetrics(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const loadHistoricalMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const endTime = new Date().toISOString();
      const startTime = new Date(Date.now() - getTimeRangeMs(timeRange)).toISOString();
      
      const data = await getHistoricalMetrics(startTime, endTime);
      setHistoricalData(data.metrics.map(m => ({
        time: new Date(m.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
        认证成功率: m.auth_success_rate,
        认证失败: m.auth_failure_count,
        安全异常: m.security_anomaly_count
      })));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getTimeRangeMs = (range) => {
    switch (range) {
      case '1h': return 60 * 60 * 1000;
      case '6h': return 6 * 60 * 60 * 1000;
      case '24h': return 24 * 60 * 60 * 1000;
      case '7d': return 7 * 24 * 60 * 60 * 1000;
      default: return 24 * 60 * 60 * 1000;
    }
  };

  useEffect(() => {
    loadRealtimeMetrics();
    loadHistoricalMetrics();
    const interval = setInterval(loadRealtimeMetrics, 5000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="container">
      <h2>安全指标监控</h2>

      {error && <div className="error">错误: {error}</div>}

      {/* 实时指标卡片 */}
      {realtimeMetrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '20px' }}>
          <div className="card">
            <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>在线车辆</h3>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1890ff' }}>
              {realtimeMetrics.online_vehicles}
            </div>
          </div>
          
          <div className="card">
            <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>认证成功率</h3>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#52c41a' }}>
              {realtimeMetrics.auth_success_rate}%
            </div>
          </div>
          
          <div className="card">
            <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>认证失败次数</h3>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ff4d4f' }}>
              {realtimeMetrics.auth_failure_count}
            </div>
          </div>
          
          <div className="card">
            <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>数据传输量</h3>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#722ed1' }}>
              {formatBytes(realtimeMetrics.data_transfer_volume)}
            </div>
          </div>
          
          <div className="card">
            <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>签名失败次数</h3>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#fa8c16' }}>
              {realtimeMetrics.signature_failure_count}
            </div>
          </div>
          
          <div className="card">
            <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>安全异常次数</h3>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ff4d4f' }}>
              {realtimeMetrics.security_anomaly_count}
            </div>
          </div>
        </div>
      )}

      {/* 历史指标图表 */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3>历史指标趋势</h3>
          <div>
            <select 
              value={timeRange} 
              onChange={(e) => setTimeRange(e.target.value)}
              className="form-input"
              style={{ width: 'auto' }}
            >
              <option value="1h">最近1小时</option>
              <option value="6h">最近6小时</option>
              <option value="24h">最近24小时</option>
              <option value="7d">最近7天</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="loading">加载中...</div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={historicalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="认证成功率" stroke="#52c41a" />
              <Line type="monotone" dataKey="认证失败" stroke="#ff4d4f" />
              <Line type="monotone" dataKey="安全异常" stroke="#fa8c16" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

export default MetricsDashboard;
