// src/api/function.js
import { api } from './index';

/**
 * 获取某个表单的 functions
 * @param {number|string} formId 
 * @param {string} token 
 * @returns {Promise<Array>}
 */
export async function fetchFunctionsAPI(formId, token) {
  if (!token) throw new Error('未登录');
  if (!formId) throw new Error('formId is required');

  const res = await api(`/api/v1/functions?form_id=${formId}`, 'GET', null, token);
  return res.data.functions || [];
}

/**
 * 创建 function
 * @param {Object} body - function 内容
 * @param {string} token 
 * @returns {Promise<number>} 新建 function 的 id
 */
export async function createFunctionAPI(body, token) {
  if (!token) throw new Error('未登录');

  const res = await api('/api/v1/function', 'POST', body, token);
  return res.data.id;
}

/**
 * 更新 function
 * @param {number|string} id 
 * @param {Object} updates 
 * @param {string} token 
 * @returns {Promise<boolean>}
 */
export async function updateFunctionAPI(id, updates, token) {
  if (!token) throw new Error('未登录');

  await api(`/api/v1/function/${id}`, 'PUT', updates, token);
  return true;
}

/**
 * 删除 function
 * @param {number|string} id 
 * @param {string} token 
 * @returns {Promise<boolean>}
 */
export async function deleteFunctionAPI(id, token) {
  if (!token) throw new Error('未登录');

  await api(`/api/v1/function/${id}`, 'DELETE', null, token);
  return true;
}
