import apiClient from './client';

export const getCertificates = async (status = null) => {
  const response = await apiClient.get('/api/certificates', {
    params: status ? { status } : {}
  });
  return response.data;
};

export const issueCertificate = async (vehicleId, organization, country) => {
  const response = await apiClient.post('/api/certificates/issue', {
    vehicle_id: vehicleId,
    organization,
    country
  });
  return response.data;
};

export const revokeCertificate = async (serialNumber, reason) => {
  const response = await apiClient.post('/api/certificates/revoke', {
    serial_number: serialNumber,
    reason
  });
  return response.data;
};

export const getCRL = async () => {
  const response = await apiClient.get('/api/certificates/crl');
  return response.data;
};
