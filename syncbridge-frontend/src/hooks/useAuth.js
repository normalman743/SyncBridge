// src/hooks/useAuth.js
import { useState, useEffect } from 'react';
import { loginAPI, registerAPI, fetchMeAPI } from '../api/auth';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function init() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const me = await fetchMeAPI(token);
        setUser({ id: me.user_id, email: me.email, display_name: me.display_name, role: me.role });
      } catch {
        removeToken();
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [token]);

  const login = async ({ email, password }) => {
    const data = await loginAPI({ email, password });
    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    setUser({ token: data.access_token, role: data.role });
    return data;
  };

  const register = async ({ email, password, display_name, license_key }) => {
    const res = await registerAPI({ email, password, display_name, license_key });
    return res;
  };

  const removeToken = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return { user, token, loading, login, register, removeToken, setUser };
}
