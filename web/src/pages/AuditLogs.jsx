import React, { useState, useEffect } from 'react';
import { queryAuditLogs, exportAuditReport } from '../api/audit';

function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [filters, setFilters] = useState({
    startTime: '',
    endTime: '',
    vehicleId: '',
    eventType: '',
    operationResult: ''
  });

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = {};
      if (filters.startTime) params.start_time = filters.startTime;
      if (filters.endTime) params.end_time = filters.endTime;
      if (filters.vehicleId) params.vehicle_id = filters.vehicleId;
      if (filters.eventType) params.event_type = filters.eventType;
      if (filters.operationResult !== '') params.operation_result = filters.operationResult === 'true';
      
      const data = await queryAuditLogs(params);
      setLogs(data.logs);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!filters.startTime || !filters.endTime) {
      alert('请先设置时间范围');
      return;
    }
    
    try {
      const blob = await exportAuditReport(filters.startTime, filters.endTime, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_report_${Date.now()}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const formatDateTime = (dateStr) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const getEventTypeText = (type) => {
    const typeMap = {
      'VEHICLE_CONNECT': '车辆连接',
      'VEHICLE_DISCONNECT': '车辆断开',
      'AUTHENTICATION_SUCCESS': '认证成功',
      'AUTHENTICATION_FAILURE': '认证失败',
      'DATA_ENCRYPTED': '数据加密',
      'DATA_DECRYPTED': '数据解密',
      'CERTIFICATE_ISSUED': '证书颁发',
      'CERTIFICATE_REVOKED': '证书撤销',
      'SIGNATURE_VERIFIED': '签名验证',
      'SIGNATURE_FAILED': '签名失败'
    };
    return typeMap[type] || type;
  };

  return (
    <div className="container">
      <div className="card">
        <h2>审计日志查询</h2>

        {error && <div className="error">错误: {error}</div>}

        {/* 过滤表单 */}
        <div style={{ marginTop: '20px', marginBottom: '20px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
          <h3>过滤条件</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">开始时间</label>
              <input
                type="datetime-local"
                className="form-input"
                value={filters.startTime}
                onChange={(e) => setFilters({ ...filters, startTime: e.target.value })}
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">结束时间</label>
              <input
                type="datetime-local"
                className="form-input"
                value={filters.endTime}
                onChange={(e) => setFilters({ ...filters, endTime: e.target.value })}
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">车辆标识</label>
              <input
                type="text"
                className="form-input"
                value={filters.vehicleId}
                onChange={(e) => setFilters({ ...filters, vehicleId: e.target.value })}
                placeholder="输入车辆ID"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">事件类型</label>
              <select
                className="form-input"
                value={filters.eventType}
                onChange={(e) => setFilters({ ...filters, eventType: e.target.value })}
              >
                <option value="">全部</option>
                <option value="AUTHENTICATION_SUCCESS">认证成功</option>
                <option value="AUTHENTICATION_FAILURE">认证失败</option>
                <option value="DATA_ENCRYPTED">数据加密</option>
                <option value="DATA_DECRYPTED">数据解密</option>
                <option value="CERTIFICATE_ISSUED">证书颁发</option>
                <option value="CERTIFICATE_REVOKED">证书撤销</option>
              </select>
            </div>
            
            <div className="form-group">
              <label className="form-label">操作结果</label>
              <select
                className="form-input"
                value={filters.operationResult}
                onChange={(e) => setFilters({ ...filters, operationResult: e.target.value })}
              >
                <option value="">全部</option>
                <option value="true">成功</option>
                <option value="false">失败</option>
              </select>
            </div>
          </div>
          
          <div style={{ marginTop: '16px', display: 'flex', gap: '10px' }}>
            <button className="btn btn-primary" onClick={loadLogs}>查询</button>
            <button className="btn" onClick={() => handleExport('json')}>导出JSON</button>
            <button className="btn" onClick={() => handleExport('csv')}>导出CSV</button>
          </div>
        </div>

        {/* 日志列表 */}
        {loading ? (
          <div className="loading">加载中...</div>
        ) : (
          <>
            <div style={{ marginBottom: '16px' }}>
              <strong>日志总数: {logs.length}</strong>
            </div>
            
            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>时间</th>
                    <th>事件类型</th>
                    <th>车辆标识</th>
                    <th>操作结果</th>
                    <th>详细信息</th>
                    <th>IP地址</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '40px' }}>
                        暂无日志记录
                      </td>
                    </tr>
                  ) : (
                    logs.map((log) => (
                      <tr key={log.log_id}>
                        <td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(log.timestamp)}</td>
                        <td>{getEventTypeText(log.event_type)}</td>
                        <td>{log.vehicle_id}</td>
                        <td>
                          <span className={`status-badge ${log.operation_result ? 'status-valid' : 'status-revoked'}`}>
                            {log.operation_result ? '成功' : '失败'}
                          </span>
                        </td>
                        <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {log.details}
                        </td>
                        <td>{log.ip_address}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AuditLogs;
