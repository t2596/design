import axios from 'axios';

// 在 K8s 部署时，使用相对路径通过 Nginx 代理访问后端
// 在本地开发时，使用环境变量指定的完整 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_TOKEN = import.meta.env.VITE_API_TOKEN || 'dev-token-12345';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_TOKEN}`
  }
});

apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export default apiClient;
