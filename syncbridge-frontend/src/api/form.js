// src/api/form.js
import { api } from './index';

// 所有函数现在只返回数据或布尔，不直接操作状态或 alert
export async function fetchFormsAPI({ page = 1, page_size = 20 } = {}, token) {
  if (!token) return null;
  try {
    const data = await api(`/api/v1/forms?page=${page}&page_size=${page_size}`, 'GET', null, token);
    return data.data.forms || [];
  } catch (err) {
    throw err;
  }
}

export async function fetchFormByIdAPI(id, token) {
  if (!token) throw new Error('未登录');
  try {
    const res = await api(`/api/v1/form/${id}`, 'GET', null, token);
    return res.data;
  } catch (err) {
    throw err;
  }
}

export async function submitMainFormAPI(body, token) {
  if (!token) throw new Error('未登录');
  const res = await api('/api/v1/form', 'POST', body, token);
  return res.data.form_id;
}

export async function updateFormAPI(id, updates, token) {
  if (!token) throw new Error('未登录');
  await api(`/api/v1/form/${id}`, 'PUT', updates, token);
  return true;
}

export async function deleteFormAPI(id, token) {
  if (!token) throw new Error('未登录');
  await api(`/api/v1/form/${id}`, 'DELETE', null, token);
  return true;
}

export async function createSubformAPI(mainformId, body, token) {
  if (!token) throw new Error('未登录');
  const res = await api(`/api/v1/form/${mainformId}/subform`, 'POST', body, token);
  return res.data.subform_id;
}

export async function updateFormStatusAPI(id, status, token) {
  if (!token) throw new Error('未登录');
  await api(`/api/v1/form/${id}/status`, 'PUT', { status }, token);
  return true;
}
