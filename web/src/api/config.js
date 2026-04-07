import apiClient from './client';

export const getSecurityPolicy = async () => {
  const response = await apiClient.get('/api/config/security');
  return response.data;
};

export const updateSecurityPolicy = async (policy) => {
  const response = await apiClient.put('/api/config/security', policy);
  return response.data;
};
