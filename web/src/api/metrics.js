import apiClient from './client';

export const getRealtimeMetrics = async () => {
  const response = await apiClient.get('/api/metrics/realtime');
  return response.data;
};

export const getHistoricalMetrics = async (startTime, endTime) => {
  const response = await apiClient.get('/api/metrics/history', {
    params: {
      start_time: startTime,
      end_time: endTime
    }
  });
  return response.data;
};
