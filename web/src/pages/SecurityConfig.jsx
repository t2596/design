import React, { useState, useEffect } from 'react';
import { getSecurityPolicy, updateSecurityPolicy } from '../api/config';

function SecurityConfig() {
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadPolicy = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSecurityPolicy();
      setPolicy(data.policy);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      setError(null);
      const result = await updateSecurityPolicy(policy);
      alert(result.message || '安全策略更新成功');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    loadPolicy();
  }, []);

  if (loading) {
    return (
      <div className="container">
        <div className="card">
          <div className="loading">加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="card">
        <h2>安全策略配置</h2>

        {error && <div className="error">错误: {error}</div>}

        {policy && (
          <form onSubmit={handleSave} style={{ marginTop: '20px' }}>
            <div className="form-group">
              <label className="form-label">
                会话超时时间（秒）
                <span style={{ color: '#999', fontSize: '12px', marginLeft: '8px' }}>
                  范围: 300-604800 (5分钟-7天)
                </span>
              </label>
              <input
                type="number"
                className="form-input"
                value={policy.session_timeout}
                onChange={(e) => setPolicy({ ...policy, session_timeout: parseInt(e.target.value) })}
                min={300}
                max={604800}
                required
              />
              <small style={{ color: '#666' }}>
                当前设置: {Math.floor(policy.session_timeout / 3600)} 小时
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">
                证书有效期（天）
                <span style={{ color: '#999', fontSize: '12px', marginLeft: '8px' }}>
                  范围: 30-1825 (1个月-5年)
                </span>
              </label>
              <input
                type="number"
                className="form-input"
                value={policy.certificate_validity}
                onChange={(e) => setPolicy({ ...policy, certificate_validity: parseInt(e.target.value) })}
                min={30}
                max={1825}
                required
              />
              <small style={{ color: '#666' }}>
                当前设置: {Math.floor(policy.certificate_validity / 365)} 年 {policy.certificate_validity % 365} 天
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">
                时间戳容差范围（秒）
                <span style={{ color: '#999', fontSize: '12px', marginLeft: '8px' }}>
                  范围: 60-600 (1-10分钟)
                </span>
              </label>
              <input
                type="number"
                className="form-input"
                value={policy.timestamp_tolerance}
                onChange={(e) => setPolicy({ ...policy, timestamp_tolerance: parseInt(e.target.value) })}
                min={60}
                max={600}
                required
              />
              <small style={{ color: '#666' }}>
                当前设置: {Math.floor(policy.timestamp_tolerance / 60)} 分钟
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">并发会话处理策略</label>
              <select
                className="form-input"
                value={policy.concurrent_session_strategy}
                onChange={(e) => setPolicy({ ...policy, concurrent_session_strategy: e.target.value })}
                required
              >
                <option value="reject_new">拒绝新会话（保持现有会话）</option>
                <option value="terminate_old">终止旧会话（接受新会话）</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">
                最大认证失败次数
                <span style={{ color: '#999', fontSize: '12px', marginLeft: '8px' }}>
                  范围: 3-10
                </span>
              </label>
              <input
                type="number"
                className="form-input"
                value={policy.max_auth_failures}
                onChange={(e) => setPolicy({ ...policy, max_auth_failures: parseInt(e.target.value) })}
                min={3}
                max={10}
                required
              />
              <small style={{ color: '#666' }}>
                超过此次数后将暂时阻止该车辆
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">
                认证失败锁定时长（秒）
                <span style={{ color: '#999', fontSize: '12px', marginLeft: '8px' }}>
                  范围: 60-3600 (1分钟-1小时)
                </span>
              </label>
              <input
                type="number"
                className="form-input"
                value={policy.auth_failure_lockout_duration}
                onChange={(e) => setPolicy({ ...policy, auth_failure_lockout_duration: parseInt(e.target.value) })}
                min={60}
                max={3600}
                required
              />
              <small style={{ color: '#666' }}>
                当前设置: {Math.floor(policy.auth_failure_lockout_duration / 60)} 分钟
              </small>
            </div>

            <div style={{ marginTop: '24px', display: 'flex', gap: '10px' }}>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? '保存中...' : '保存配置'}
              </button>
              <button type="button" className="btn" onClick={loadPolicy}>
                重置
              </button>
            </div>
          </form>
        )}

        <div style={{ marginTop: '40px', padding: '16px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '12px' }}>配置说明</h3>
          <ul style={{ paddingLeft: '20px', lineHeight: '1.8' }}>
            <li>会话超时时间：车辆会话的有效期，超时后需要重新认证</li>
            <li>证书有效期：新颁发证书的有效期限</li>
            <li>时间戳容差：允许的时间戳偏差范围，用于防重放攻击</li>
            <li>并发会话策略：当同一车辆尝试建立多个会话时的处理方式</li>
            <li>最大认证失败次数：触发锁定前允许的最大失败次数</li>
            <li>认证失败锁定时长：认证失败后的锁定时间</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default SecurityConfig;
