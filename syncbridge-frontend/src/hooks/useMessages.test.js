// src/hooks/useMessages.test.js
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useMessages } from './useMessages';
import * as messageApi from '../api/message';
import * as fileApi from '../api/file';
import { getToken, removeToken } from '../api/index';

vi.mock('../api/message');
vi.mock('../api/file');
vi.mock('../api/index', () => ({
  getToken: vi.fn(),
  removeToken: vi.fn(),
}));

describe('useMessages hook', () => {
  const formId = 123;

  beforeEach(() => {
    vi.clearAllMocks();
    // 默认有 token
    getToken.mockReturnValue('test-token');
    // 避免真正弹窗，mock 掉 alert
    vi.stubGlobal('alert', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('初始 state 正确', () => {
    const { result } = renderHook(() => useMessages(formId));

    expect(result.current.messages).toEqual([]);
    expect(result.current.page).toBe(1);
    expect(result.current.pageSize).toBe(20);
    expect(result.current.total).toBe(0);
    // useEffect 一进来就会触发 fetchMessages，里面 setLoading(true)，
    // 所以在测试里 render 完成时 loading 为 true 是合理的
    expect(result.current.loading).toBe(true);
  });

  it('formId 存在时，effect 会自动调用 fetchMessages(page=1)', async () => {
    messageApi.fetchMessagesAPI.mockResolvedValueOnce({
      messages: [{ id: 1 }],
      page: 1,
      total: 1,
    });

    const { result } = renderHook(() => useMessages(formId));

    // 等 useEffect 触发的异步 fetchMessages 执行完
    await waitFor(() => {
      expect(messageApi.fetchMessagesAPI).toHaveBeenCalledWith(
        { form_id: formId, page: 1, page_size: 20 },
        'test-token',
      );
      expect(result.current.messages).toEqual([{ id: 1 }]);
      expect(result.current.page).toBe(1);
      expect(result.current.total).toBe(1);
      expect(result.current.loading).toBe(false);
    });
  });

  it('fetchMessages 在没有 token 时会 alert 并直接返回', async () => {
    getToken.mockReturnValueOnce(null);

    const { result } = renderHook(() => useMessages(formId));

    await act(async () => {
      await result.current.fetchMessages({ page: 2 });
    });

    expect(global.alert).toHaveBeenCalledWith('请先登录');
    expect(messageApi.fetchMessagesAPI).not.toHaveBeenCalled();
  });

  it('sendMessage 成功时会调用 sendMessageAPI 并刷新列表', async () => {
    messageApi.sendMessageAPI.mockResolvedValueOnce(999);
    messageApi.fetchMessagesAPI.mockResolvedValue({
      messages: [],
      page: 1,
      total: 0,
    });

    const { result } = renderHook(() => useMessages(formId));

    await act(async () => {
      const id = await result.current.sendMessage({
        text_content: 'hello',
      });
      expect(id).toBe(999);
    });

    expect(messageApi.sendMessageAPI).toHaveBeenCalledWith(
      {
        form_id: formId,
        function_id: null,
        nonfunction_id: null,
        text_content: 'hello',
      },
      'test-token',
    );
    // sendMessage 之后会调用 fetchMessages
    expect(messageApi.fetchMessagesAPI).toHaveBeenCalled();
  });

  it('updateBlockStatus 成功时会调用 API 并刷新消息', async () => {
    messageApi.updateBlockStatusAPI.mockResolvedValueOnce({});
    messageApi.fetchMessagesAPI.mockResolvedValue({
      messages: [],
      page: 1,
      total: 0,
    });

    const { result } = renderHook(() => useMessages(formId));

    await act(async () => {
      const ok = await result.current.updateBlockStatus(10, 'resolved');
      expect(ok).toBe(true);
    });

    expect(messageApi.updateBlockStatusAPI).toHaveBeenCalledWith(
      10,
      'resolved',
      'test-token',
    );
    expect(messageApi.fetchMessagesAPI).toHaveBeenCalled();
  });

  it('uploadFile 成功时会调用 uploadFileAPI 并刷新消息', async () => {
    fileApi.uploadFileAPI.mockResolvedValueOnce('file-id');
    messageApi.fetchMessagesAPI.mockResolvedValue({
      messages: [],
      page: 1,
      total: 0,
    });

    const { result } = renderHook(() => useMessages(formId));

    await act(async () => {
      const fileId = await result.current.uploadFile(1, new File([], 'a.txt'));
      expect(fileId).toBe('file-id');
    });

    expect(fileApi.uploadFileAPI).toHaveBeenCalledWith(
      1,
      expect.any(File),
      'test-token',
    );
    expect(messageApi.fetchMessagesAPI).toHaveBeenCalled();
  });

  it('deleteFile 成功时会调用 deleteFileAPI 并刷新消息', async () => {
    fileApi.deleteFileAPI.mockResolvedValueOnce(true);
    messageApi.fetchMessagesAPI.mockResolvedValue({
      messages: [],
      page: 1,
      total: 0,
    });

    const { result } = renderHook(() => useMessages(formId));

    await act(async () => {
      const res = await result.current.deleteFile('file-id');
      expect(res).toBe(true);
    });

    expect(fileApi.deleteFileAPI).toHaveBeenCalledWith('file-id', 'test-token');
    expect(messageApi.fetchMessagesAPI).toHaveBeenCalled();
  });

  it('getFile 调用 getFileAPI 并返回结果', async () => {
    const fileData = { id: 'file-id' };
    fileApi.getFileAPI.mockResolvedValueOnce(fileData);

    const { result } = renderHook(() => useMessages(formId));

    let res;
    await act(async () => {
      res = await result.current.getFile('file-id');
    });

    expect(fileApi.getFileAPI).toHaveBeenCalledWith('file-id', 'test-token');
    expect(res).toEqual(fileData);
  });

  it('当 API 抛出 “未登录” 错误时会调用 removeToken', async () => {
    const error = new Error('未登录');
    messageApi.fetchMessagesAPI.mockRejectedValueOnce(error);

    const { result } = renderHook(() => useMessages(formId));

    await act(async () => {
      await result.current.fetchMessages({ page: 1 });
    });

    expect(removeToken).toHaveBeenCalled();
  });
});