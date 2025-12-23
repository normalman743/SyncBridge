// src/api/index.js
const API_BASE = 'http://localhost:8000';

export function getToken() {
  return localStorage.getItem('token');
}

export function setToken(token) {
  localStorage.setItem('token', token);
}

export function removeToken() {
  localStorage.removeItem('token');
}

export async function api(path, method = 'GET', body = null, token = getToken(), extraHeaders = {}) {
  const headers = { ...extraHeaders };
  if (!(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  if (token) headers['Authorization'] = 'Bearer ' + token;

  const resp = await fetch(API_BASE + path, {
    method,
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : null,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: 'Unknown' }));
    throw { code: err.code || resp.status, message: err.error || resp.statusText };
  }

  return resp.json();
}
