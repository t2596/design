import apiClient from './client';

export const getOnlineVehicles = async () => {
  const response = await apiClient.get('/api/vehicles/online');
  return response.data;
};

export const getVehicleStatus = async (vehicleId) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/status`);
  return response.data;
};

export const searchVehicles = async (query) => {
  const response = await apiClient.get('/api/vehicles/search', {
    params: { query }
  });
  return response.data;
};

export const getVehicleLatestData = async (vehicleId) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/data/latest`);
  return response.data;
};

export const getVehicleDataHistory = async (vehicleId, params = {}) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/data/history`, {
    params
  });
  return response.data;
};

export const getVehicleTrack = async (vehicleId, params = {}) => {
  const response = await apiClient.get(`/api/vehicles/${vehicleId}/data/track`, {
    params
  });
  return response.data;
};
