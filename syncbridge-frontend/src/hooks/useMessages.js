// src/hooks/useMessages.js
import { useState, useEffect, useCallback } from 'react';
import {
  fetchMessagesAPI,
  sendMessageAPI,
  updateBlockStatusAPI,
} from '../api/message';
import { uploadFileAPI, getFileAPI, deleteFileAPI } from '../api/file';
import { getToken, removeToken } from '../api/index'; // 这里假设你有 getToken 和 removeToken 工具

export function useMessages(formId) {
  const [messages, setMessages] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const token = getToken();

  const fetchMessages = useCallback(
    async ({ page: fetchPage = 1 } = {}) => {
      if (!token) {
        alert('请先登录');
        return;
      }

      try {
        setLoading(true);
        const data = await fetchMessagesAPI(
          { form_id: formId, page: fetchPage, page_size: pageSize },
          token
        );
        setMessages(data.messages || []);
        setPage(data.page || fetchPage);
        setTotal(data.total || 0);
      } catch (err) {
        if (err.message === '未登录') removeToken();
        else alert(err.message || '获取消息失败');
      } finally {
        setLoading(false);
      }
    },
    [formId, pageSize, token]
  );

  const sendMessage = useCallback(
    async ({ text_content, function_id = null, nonfunction_id = null }) => {
      if (!token) {
        alert('请先登录');
        return null;
      }

      try {
        const messageId = await sendMessageAPI(
          { form_id: formId, function_id, nonfunction_id, text_content },
          token
        );
        await fetchMessages({ page }); // 发送后刷新列表
        return messageId;
      } catch (err) {
        if (err.message === '未登录') removeToken();
        else alert(err.message || '发送消息失败');
        return null;
      }
    },
    [formId, page, token, fetchMessages]
  );

  const updateBlockStatus = useCallback(
    async (blockId, status) => {
      if (!token) {
        alert('请先登录');
        return false;
      }

      try {
        await updateBlockStatusAPI(blockId, status, token);
        await fetchMessages({ page }); // 更新后刷新
        return true;
      } catch (err) {
        if (err.message === '未登录') removeToken();
        else alert(err.message || '更新 block 状态失败');
        return false;
      }
    },
    [page, token, fetchMessages]
  );

  const uploadFile = useCallback(
    async (messageId, file) => {
      if (!token) {
        alert('请先登录');
        return null;
      }

      try {
        const fileId = await uploadFileAPI(messageId, file, token);
        await fetchMessages({ page });
        return fileId;
      } catch (err) {
        if (err.message === '未登录') removeToken();
        else alert(err.message || '上传文件失败');
        return null;
      }
    },
    [page, token, fetchMessages]
  );

  const deleteFile = useCallback(
    async (fileId) => {
      if (!token) {
        alert('请先登录');
        return false;
      }

      try {
        const res = await deleteFileAPI(fileId, token);
        await fetchMessages({ page });
        return res;
      } catch (err) {
        if (err.message === '未登录') removeToken();
        else alert(err.message || '删除文件失败');
        return false;
      }
    },
    [page, token, fetchMessages]
  );

  const getFile = useCallback(
    async (fileId) => {
      if (!token) {
        alert('请先登录');
        return null;
      }

      try {
        return await getFileAPI(fileId, token);
      } catch (err) {
        if (err.message === '未登录') removeToken();
        else alert(err.message || '获取文件失败');
        return null;
      }
    },
    [token]
  );

  useEffect(() => {
    if (formId) fetchMessages({ page: 1 });
  }, [formId, fetchMessages]);

  return {
    messages,
    page,
    pageSize,
    total,
    loading,
    fetchMessages,
    sendMessage,
    updateBlockStatus,
    uploadFile,
    deleteFile,
    getFile,
  };
}
