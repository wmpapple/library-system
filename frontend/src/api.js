import axios from 'axios';
import router from './router';

// Create a new axios instance
const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000', // Adjust this to your API's base URL
});

// Add a request interceptor to include the token in headers
apiClient.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle 401 errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token and user info from localStorage
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      // Redirect to login page
      router.push('/login').then(() => {
        // Optional: show a notification to the user
        alert('Your session has expired. Please log in again.');
      });
    }
    return Promise.reject(error);
  }
);

export default apiClient;