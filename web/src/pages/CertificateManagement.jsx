import React, { useState, useEffect } from 'react';
import { getCertificates, issueCertificate, revokeCertificate, getCRL } from '../api/certificates';

function CertificateManagement() {
  const [certificates, setCertificates] = useState([]);
  const [crl, setCrl] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showIssueForm, setShowIssueForm] = useState(false);
  const [showCRL, setShowCRL] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  
  const [issueForm, setIssueForm] = useState({
    vehicleId: '',
    organization: '车辆制造商',
    country: 'CN'
  });

  const loadCertificates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCertificates(statusFilter || null);
      setCertificates(data.certificates);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadCRL = async () => {
    try {
      const data = await getCRL();
      setCrl(data.revoked_certificates);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadCertificates();
  }, [statusFilter]);

  const handleIssueCertificate = async (e) => {
    e.preventDefault();
    try {
      setError(null);
      await issueCertificate(issueForm.vehicleId, issueForm.organization, issueForm.country);
      alert('证书颁发成功');
      setShowIssueForm(false);
      setIssueForm({ vehicleId: '', organization: '车辆制造商', country: 'CN' });
      loadCertificates();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRevokeCertificate = async (serialNumber) => {
    if (!confirm('确定要撤销此证书吗？')) return;
    
    try {
      setError(null);
      await revokeCertificate(serialNumber, '管理员撤销');
      alert('证书撤销成功');
      loadCertificates();
    } catch (err) {
      setError(err.message);
    }
  };

  const formatDateTime = (dateStr) => {
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const getStatusText = (status) => {
    const statusMap = {
      'valid': '有效',
      'expired': '已过期',
      'revoked': '已撤销',
      'not_yet_valid': '未生效'
    };
    return statusMap[status] || status;
  };

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>证书管理</h2>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-primary" onClick={() => setShowIssueForm(!showIssueForm)}>
              {showIssueForm ? '取消颁发' : '颁发证书'}
            </button>
            <button className="btn" onClick={() => { setShowCRL(!showCRL); if (!showCRL) loadCRL(); }}>
              {showCRL ? '隐藏CRL' : '查看CRL'}
            </button>
          </div>
        </div>

        {error && <div className="error">错误: {error}</div>}

        {/* 证书颁发表单 */}
        {showIssueForm && (
          <form onSubmit={handleIssueCertificate} style={{ marginBottom: '20px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
            <h3>颁发新证书</h3>
            <div className="form-group">
              <label className="form-label">车辆标识 *</label>
              <input
                type="text"
                className="form-input"
                value={issueForm.vehicleId}
                onChange={(e) => setIssueForm({ ...issueForm, vehicleId: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">组织名称</label>
              <input
                type="text"
                className="form-input"
                value={issueForm.organization}
                onChange={(e) => setIssueForm({ ...issueForm, organization: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">国家代码</label>
              <input
                type="text"
                className="form-input"
                value={issueForm.country}
                onChange={(e) => setIssueForm({ ...issueForm, country: e.target.value })}
                maxLength={2}
              />
            </div>
            <button type="submit" className="btn btn-primary">提交</button>
          </form>
        )}

        {/* CRL 显示 */}
        {showCRL && (
          <div style={{ marginBottom: '20px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
            <h3>证书撤销列表 (CRL)</h3>
            <p>撤销证书总数: {crl.length}</p>
            {crl.length > 0 ? (
              <div style={{ maxHeight: '200px', overflow: 'auto' }}>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {crl.map((serial, index) => (
                    <li key={index} style={{ padding: '4px 0', borderBottom: '1px solid #eee' }}>
                      {serial}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p>暂无撤销证书</p>
            )}
          </div>
        )}

        {/* 状态过滤 */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ marginRight: '10px' }}>状态过滤:</label>
          <select 
            value={statusFilter} 
            onChange={(e) => setStatusFilter(e.target.value)}
            className="form-input"
            style={{ width: 'auto' }}
          >
            <option value="">全部</option>
            <option value="valid">有效</option>
            <option value="expired">已过期</option>
            <option value="revoked">已撤销</option>
          </select>
        </div>

        {/* 证书列表 */}
        {loading ? (
          <div className="loading">加载中...</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>序列号</th>
                <th>主体</th>
                <th>颁发者</th>
                <th>生效时间</th>
                <th>过期时间</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {certificates.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '40px' }}>
                    暂无证书
                  </td>
                </tr>
              ) : (
                certificates.map((cert) => (
                  <tr key={cert.serial_number}>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{cert.serial_number}</td>
                    <td>{cert.subject}</td>
                    <td>{cert.issuer}</td>
                    <td>{formatDateTime(cert.valid_from)}</td>
                    <td>{formatDateTime(cert.valid_to)}</td>
                    <td>
                      <span className={`status-badge status-${cert.status}`}>
                        {getStatusText(cert.status)}
                      </span>
                    </td>
                    <td>
                      {cert.status === 'valid' && (
                        <button 
                          className="btn btn-danger"
                          onClick={() => handleRevokeCertificate(cert.serial_number)}
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          撤销
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default CertificateManagement;
