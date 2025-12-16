// API Configuration
// This dynamically determines the backend URL based on the current host
// When accessing from localhost, it uses localhost
// When accessing from network IP (e.g., 192.168.0.22), it uses that IP

const getApiBaseUrl = () => {
  // Get the current hostname (could be localhost, 192.168.0.22, etc.)
  const hostname = window.location.hostname;
  
  // Backend always runs on port 9002
  const backendPort = 9002;
  
  // Use the same hostname as the frontend, but with the backend port
  return `http://${hostname}:${backendPort}`;
};

export const API_BASE_URL = getApiBaseUrl();
