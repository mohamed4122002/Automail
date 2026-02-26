import axios from "axios";

// Create an Axios instance with default configuration
const api = axios.create({
  baseURL: "/api", // Proxy in vite.config.ts handles this redirection to backend
  headers: {
    "Content-Type": "application/json",
  },
});

// Add a request interceptor for auth token (placeholder for now)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      // console.log(`[API] Attaching token to ${config.url}`);
    } else {
      console.warn(`[API] No auth_token found for ${config.url}`);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle 401s
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn("[API] 401 Unauthorized - Logging out");
      localStorage.removeItem("auth_token");
      // Optional: dispatch a custom event or use a callback to redirect
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
