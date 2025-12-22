// src/api/message.js
import { api } from './index';

/**
 * 获取消息列表
 * @param {Object} params
 * @param {number} params.form_id
 * @param {number} [params.function_id]
 * @param {number} [params.nonfunction_id]
 * @param {number} [params.page=1]
 * @param {number} [params.page_size=20]
 * @param {string} token
 * @returns {Promise<Object>} { messages: [], page, page_size, total }
 */
export async function fetchMessagesAPI(
  { form_id, function_id, nonfunction_id, page = 1, page_size = 20 },
  token
) {
  if (!token) throw new Error('未登录');
  if (!form_id) throw new Error('form_id is required');

  const query = new URLSearchParams({
    form_id,
    page,
    page_size,
    ...(function_id ? { function_id } : {}),
    ...(nonfunction_id ? { nonfunction_id } : {}),
  }).toString();

  const res = await api(`/api/v1/messages?${query}`, 'GET', null, token);
  return res.data;
}

/**
 * 发送消息
 * @param {Object} params
 * @param {number} params.form_id
 * @param {number} [params.function_id]
 * @param {number} [params.nonfunction_id]
 * @param {string} params.text_content
 * @param {string} token
 * @returns {Promise<number>} 新建 message 的 ID
 */
export async function sendMessageAPI(
  { form_id, function_id = null, nonfunction_id = null, text_content },
  token
) {
  if (!token) throw new Error('未登录');
  if (!form_id || !text_content) throw new Error('form_id 和 text_content 必填');

  const res = await api(
    '/api/v1/message',
    'POST',
    { form_id, function_id, nonfunction_id, text_content },
    token
  );
  return res.data.message_id;
}

/**
 * 更新 block 状态
 * @param {number} blockId
 * @param {"normal"|"urgent"} status
 * @param {string} token
 * @returns {Promise<boolean>}
 */
export async function updateBlockStatusAPI(blockId, status, token) {
  if (!token) throw new Error('未登录');
  if (!blockId || !status) throw new Error('blockId 和 status 必填');

  await api(`/block/${blockId}/status`, 'PUT', { status }, token);
  return true;
}
