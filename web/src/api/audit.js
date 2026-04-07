import apiClient from './client';

export const queryAuditLogs = async (filters) => {
  const response = await apiClient.get('/api/audit/logs', {
    params: filters
  });
  return response.data;
};

export const exportAuditReport = async (startTime, endTime, format = 'json') => {
  const response = await apiClient.get('/api/audit/export', {
    params: {
      start_time: startTime,
      end_time: endTime,
      format
    },
    responseType: 'blob'
  });
  return response.data;
};
