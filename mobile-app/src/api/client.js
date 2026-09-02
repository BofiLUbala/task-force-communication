import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.100:8000/api';

export const tokenStore = {
  async getAccess() {
    return SecureStore.getItemAsync('access_token');
  },
  async getRefresh() {
    return SecureStore.getItemAsync('refresh_token');
  },
  async save(access, refresh) {
    await SecureStore.setItemAsync('access_token', access);
    if (refresh) await SecureStore.setItemAsync('refresh_token', refresh);
  },
  async clear() {
    await SecureStore.deleteItemAsync('access_token');
    await SecureStore.deleteItemAsync('refresh_token');
  },
};

const client = axios.create({ baseURL: API_URL, timeout: 15000 });

client.interceptors.request.use(async (config) => {
  const token = await tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = await tokenStore.getRefresh();
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_URL}/auth/login/refresh/`, { refresh });
          await tokenStore.save(data.access, null);
          original.headers.Authorization = `Bearer ${data.access}`;
          return client(original);
        } catch (refreshError) {
          await tokenStore.clear();
          return Promise.reject(refreshError);
        }
      }
    }
    return Promise.reject(error);
  },
);

export default client;
export { API_URL };
