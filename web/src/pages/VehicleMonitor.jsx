import React, { useState, useEffect } from 'react';
import { getOnlineVehicles, searchVehicles, getVehicleLatestData, getVehicleDataHistory } from '../api/vehicles';

function VehicleMonitor() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [vehicleData, setVehicleData] = useState(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [historyData, setHistoryData] = useState([]);

  const loadVehicles = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getOnlineVehicles();
      setVehicles(data.vehicles);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadVehicles();
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      const data = await searchVehicles(searchQuery);
      setVehicles(data.vehicles);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadVehicleData = async (vehicleId) => {
    try {
      setDataLoading(true);
      const [latest, history] = await Promise.all([
        getVehicleLatestData(vehicleId),
        getVehicleDataHistory(vehicleId, { limit: 20 })
      ]);
      setVehicleData(latest);
      setHistoryData(history.data || []);
    } catch (err) {
      console.error('加载车辆数据失败:', err);
      setVehicleData(null);
      setHistoryData([]);
    } finally {
      setDataLoading(false);
    }
  };

  const handleVehicleClick = (vehicle) => {
    setSelectedVehicle(vehicle);
    loadVehicleData(vehicle.vehicle_id);
  };

  useEffect(() => {
    loadVehicles();
    const interval = setInterval(loadVehicles, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedVehicle) {
      const interval = setInterval(() => {
        loadVehicleData(selectedVehicle.vehicle_id);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedVehicle]);

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('zh-CN');
  };

  const formatValue = (value, unit = '') => {
    if (value === null || value === undefined) return '-';
    return `${value}${unit}`;
  };

  return (
    <div className="container">
      <div style={{ display: 'grid', gridTemplateColumns: selectedVehicle ? '1fr 2fr' : '1fr', gap: '20px' }}>
        {/* 左侧：车辆列表 */}
        <div className="card">
          <h2>车辆状态监控</h2>
          
          <form onSubmit={handleSearch} style={{ marginTop: '20px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="text"
                className="form-input"
                placeholder="搜索车辆标识..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ flex: 1 }}
              />
              <button type="submit" className="btn btn-primary">搜索</button>
              <button type="button" className="btn" onClick={loadVehicles}>刷新</button>
            </div>
          </form>

          {error && <div className="error">错误: {error}</div>}

          {loading ? (
            <div className="loading">加载中...</div>
          ) : (
            <>
              <div style={{ marginBottom: '16px' }}>
                <strong>在线车辆数: {vehicles.length}</strong>
              </div>
              
              <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
                {vehicles.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                    暂无在线车辆
                  </div>
                ) : (
                  vehicles.map((vehicle) => (
                    <div
                      key={vehicle.vehicle_id}
                      onClick={() => handleVehicleClick(vehicle)}
                      style={{
                        padding: '12px',
                        marginBottom: '8px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        backgroundColor: selectedVehicle?.vehicle_id === vehicle.vehicle_id ? '#e3f2fd' : '#fff',
                        transition: 'background-color 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        if (selectedVehicle?.vehicle_id !== vehicle.vehicle_id) {
                          e.currentTarget.style.backgroundColor = '#f5f5f5';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (selectedVehicle?.vehicle_id !== vehicle.vehicle_id) {
                          e.currentTarget.style.backgroundColor = '#fff';
                        }
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong>{vehicle.vehicle_id}</strong>
                        <span className={`status-badge status-${vehicle.status}`}>
                          {vehicle.status === 'online' ? '在线' : '离线'}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                        最后活动: {formatDateTime(vehicle.last_activity)}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        {/* 右侧：车辆详情 */}
        {selectedVehicle && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2>车辆详情: {selectedVehicle.vehicle_id}</h2>
              <button 
                className="btn" 
                onClick={() => {
                  setSelectedVehicle(null);
                  setVehicleData(null);
                  setHistoryData([]);
                }}
              >
                关闭
              </button>
            </div>

            {dataLoading && !vehicleData ? (
              <div className="loading">加载数据中...</div>
            ) : vehicleData ? (
              <>
                {/* 实时数据卡片 */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                  <div style={{ padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>状态</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{vehicleData.state || '-'}</div>
                  </div>
                  
                  <div style={{ padding: '16px', backgroundColor: '#e3f2fd', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>速度</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatValue(vehicleData.motion?.speed, ' km/h')}</div>
                  </div>
                  
                  <div style={{ padding: '16px', backgroundColor: '#fff3e0', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>发动机温度</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatValue(vehicleData.temperature?.engine, '°C')}</div>
                  </div>
                  
                  <div style={{ padding: '16px', backgroundColor: '#e8f5e9', borderRadius: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>油量</div>
                    <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{formatValue(vehicleData.fuel?.level, '%')}</div>
                  </div>
                </div>

                {/* GPS 信息 */}
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ marginBottom: '12px' }}>GPS 位置</h3>
                  <div style={{ padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                      <div>
                        <span style={{ color: '#666' }}>纬度: </span>
                        <strong>{formatValue(vehicleData.gps?.latitude)}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>经度: </span>
                        <strong>{formatValue(vehicleData.gps?.longitude)}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>海拔: </span>
                        <strong>{formatValue(vehicleData.gps?.altitude, ' m')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>方向: </span>
                        <strong>{formatValue(vehicleData.gps?.heading, '°')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>卫星数: </span>
                        <strong>{formatValue(vehicleData.gps?.satellites)}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 运动数据 */}
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ marginBottom: '12px' }}>运动数据</h3>
                  <div style={{ padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                      <div>
                        <span style={{ color: '#666' }}>速度: </span>
                        <strong>{formatValue(vehicleData.motion?.speed, ' km/h')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>加速度: </span>
                        <strong>{formatValue(vehicleData.motion?.acceleration, ' m/s²')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>总里程: </span>
                        <strong>{formatValue(vehicleData.motion?.odometer, ' km')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>本次行程: </span>
                        <strong>{formatValue(vehicleData.motion?.trip_distance, ' km')}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 温度和电池 */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '24px' }}>
                  <div>
                    <h3 style={{ marginBottom: '12px' }}>温度</h3>
                    <div style={{ padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                      <div style={{ marginBottom: '8px' }}>
                        <span style={{ color: '#666' }}>发动机: </span>
                        <strong>{formatValue(vehicleData.temperature?.engine, '°C')}</strong>
                      </div>
                      <div style={{ marginBottom: '8px' }}>
                        <span style={{ color: '#666' }}>车内: </span>
                        <strong>{formatValue(vehicleData.temperature?.cabin, '°C')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>室外: </span>
                        <strong>{formatValue(vehicleData.temperature?.outside, '°C')}</strong>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 style={{ marginBottom: '12px' }}>电池</h3>
                    <div style={{ padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                      <div style={{ marginBottom: '8px' }}>
                        <span style={{ color: '#666' }}>电压: </span>
                        <strong>{formatValue(vehicleData.battery?.voltage, ' V')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>电流: </span>
                        <strong>{formatValue(vehicleData.battery?.current, ' A')}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 诊断数据 */}
                <div style={{ marginBottom: '24px' }}>
                  <h3 style={{ marginBottom: '12px' }}>诊断数据</h3>
                  <div style={{ padding: '16px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                      <div>
                        <span style={{ color: '#666' }}>发动机负载: </span>
                        <strong>{formatValue(vehicleData.diagnostics?.engine_load, '%')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>转速: </span>
                        <strong>{formatValue(vehicleData.diagnostics?.rpm, ' RPM')}</strong>
                      </div>
                      <div>
                        <span style={{ color: '#666' }}>油门开度: </span>
                        <strong>{formatValue(vehicleData.diagnostics?.throttle_position, '%')}</strong>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 历史数据表格 */}
                {historyData.length > 0 && (
                  <div>
                    <h3 style={{ marginBottom: '12px' }}>最近数据 (最新20条)</h3>
                    <div style={{ overflowX: 'auto' }}>
                      <table className="table" style={{ fontSize: '12px' }}>
                        <thead>
                          <tr>
                            <th>时间</th>
                            <th>状态</th>
                            <th>速度</th>
                            <th>发动机温度</th>
                            <th>油量</th>
                            <th>转速</th>
                          </tr>
                        </thead>
                        <tbody>
                          {historyData.map((item, index) => (
                            <tr key={index}>
                              <td>{formatDateTime(item.timestamp)}</td>
                              <td>{item.state || '-'}</td>
                              <td>{formatValue(item.motion_speed, ' km/h')}</td>
                              <td>{formatValue(item.temp_engine, '°C')}</td>
                              <td>{formatValue(item.fuel_level, '%')}</td>
                              <td>{formatValue(item.diag_rpm, ' RPM')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                暂无车辆数据
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default VehicleMonitor;
