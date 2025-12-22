// src/api/nonfunction.js
import { api } from './index';

/**
 * 获取某个表单的 nonfunctions
 * @param {number|string} formId 
 * @param {string} token 
 * @returns {Promise<Array>}
 */
export async function fetchNonfunctionsAPI(formId, token) {
  if (!token) throw new Error('未登录');
  if (!formId) throw new Error('formId is required');

  const res = await api(`/api/v1/nonfunctions?form_id=${formId}`, 'GET', null, token);
  return res.data.nonfunctions || [];
}

/**
 * 创建 nonfunction
 * @param {Object} body 
 * @param {string} token 
 * @returns {Promise<number>} 新建 nonfunction 的 id
 */
export async function createNonfunctionAPI(body, token) {
  if (!token) throw new Error('未登录');

  const res = await api('/api/v1/nonfunction', 'POST', body, token);
  return res.data.id;
}

/**
 * 更新 nonfunction
 * @param {number|string} id 
 * @param {Object} updates 
 * @param {string} token 
 * @returns {Promise<boolean>}
 */
export async function updateNonfunctionAPI(id, updates, token) {
  if (!token) throw new Error('未登录');

  await api(`/api/v1/nonfunction/${id}`, 'PUT', updates, token);
  return true;
}

/**
 * 删除 nonfunction
 * @param {number|string} id 
 * @param {string} token 
 * @returns {Promise<boolean>}
 */
export async function deleteNonfunctionAPI(id, token) {
  if (!token) throw new Error('未登录');

  await api(`/api/v1/nonfunction/${id}`, 'DELETE', null, token);
  return true;
}
