import { createContext, useContext, useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import client, { tokenStore } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const stored = await SecureStore.getItemAsync('user');
      const access = await tokenStore.getAccess();
      if (stored && access) setUser(JSON.parse(stored));
      setLoading(false);
    })();
  }, []);

  async function login(username, password) {
    const { data } = await client.post('/auth/login/', { username, password });
    await tokenStore.save(data.access, data.refresh);
    const currentUser = { id: data.user_id, role: data.role, full_name: data.full_name };
    await SecureStore.setItemAsync('user', JSON.stringify(currentUser));
    setUser(currentUser);
    return currentUser;
  }

  async function logout() {
    await tokenStore.clear();
    await SecureStore.deleteItemAsync('user');
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
