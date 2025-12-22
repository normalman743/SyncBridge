// src/api/file.js
import { api } from './index';

/**
 * 上传文件
 * @param {number} message_id
 * @param {File} file
 * @param {string} token
 * @returns {Promise<number>} 新建 file 的 ID
 */
export async function uploadFileAPI(message_id, file, token) {
  if (!token) throw new Error('未登录');
  if (!message_id || !file) throw new Error('message_id 和 file 必填');
  if (file.size > 10 * 1024 * 1024) throw new Error('File size exceeds 10MB');

  const formData = new FormData();
  formData.append('message_id', message_id);
  formData.append('file', file);

  const res = await api(
    '/api/v1/file',
    'POST',
    formData,
    token,
    { 'Content-Type': 'multipart/form-data' }
  );
  return res.data.file_id;
}

/**
 * 获取文件信息
 * @param {number} id
 * @param {string} token
 * @returns {Promise<Object>} 文件数据
 */
export async function getFileAPI(id, token) {
  if (!token) throw new Error('未登录');
  const res = await api(`/api/v1/file/${id}`, 'GET', null, token);
  return res.data;
}

/**
 * 删除文件
 * @param {number} id
 * @param {string} token
 * @returns {Promise<boolean>}
 */
export async function deleteFileAPI(id, token) {
  if (!token) throw new Error('未登录');
  await api(`/api/v1/file/${id}`, 'DELETE', null, token);
  return true;
}
