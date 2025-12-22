// src/api/auth.js
import { api } from './index';

export async function loginAPI({ email, password }) {
  const res = await api('/api/v1/auth/login', 'POST', { email, password });
  return res.data; // { access_token, role }
}

export async function registerAPI({ email, password, display_name, license_key }) {
  const res = await api('/api/v1/auth/register', 'POST', { email, password, display_name, license_key });
  return res; // { status, ... }
}

export async function fetchMeAPI(token) {
  const res = await api('/api/v1/auth/me', 'GET', null, token);
  return res;
}






















