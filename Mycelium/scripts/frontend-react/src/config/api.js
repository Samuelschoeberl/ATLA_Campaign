// API Configuration
// This dynamically determines the backend URL based on the current host
// When accessing from localhost, it uses localhost
// When accessing from network IP (e.g., 192.168.0.22), it uses that IP
// When accessing via Cloudflare tunnel (or any HTTPS), uses relative URLs with Vite proxy

const getApiBaseUrl = () => {
  // Get the current hostname (could be localhost, 192.168.0.22, etc.)
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  
  // Backend always runs on port 9002
  const backendPort = 9002;
  
  // If we're on HTTPS or on a tunnel domain, use relative URLs to leverage Vite proxy
  // This prevents mixed content errors when accessing via Cloudflare tunnel
  if (protocol === 'https:' || hostname.includes('trycloudflare.com')) {
    return ''; // Use relative URLs like /api/... which Vite proxy will handle
  }
  
  // For local HTTP access, use absolute URLs with the backend port
  return `http://${hostname}:${backendPort}`;
};

export const API_BASE_URL = getApiBaseUrl();
