import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import CommentBox from './CommentBox';
import { useMessages } from '../hooks/useMessages';

// mock useMessages hook
vi.mock('../hooks/useMessages', () => ({
  useMessages: vi.fn(),
}));

describe('CommentBox component', () => {
  const formId = 123;

  let sendMessageMock;
  let uploadFileMock;
  let deleteFileMock;
  let getFileMock;

  beforeEach(() => {
    sendMessageMock = vi.fn();
    uploadFileMock = vi.fn();
    deleteFileMock = vi.fn();
    getFileMock = vi.fn();

    // 默认 useMessages 返回空列表、非 loading
    useMessages.mockReturnValue({
      messages: [],
      loading: false,
      sendMessage: sendMessageMock,
      uploadFile: uploadFileMock,
      deleteFile: deleteFileMock,
      getFile: getFileMock,
    });

    // 简单 mock URL.createObjectURL，避免报错
    global.URL = {
      createObjectURL: vi.fn(() => 'blob:mock-url'),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('在 loading 时显示 Loading messages...', () => {
    useMessages.mockReturnValueOnce({
      messages: [],
      loading: true,
      sendMessage: sendMessageMock,
      uploadFile: uploadFileMock,
      deleteFile: deleteFileMock,
      getFile: getFileMock,
    });

    render(<CommentBox formId={formId} />);

    expect(screen.getByText('Loading messages...')).toBeInTheDocument();
  });

  it('在没有消息时显示 No messages yet.', () => {
    render(<CommentBox formId={formId} />);

    expect(screen.getByText('No messages yet.')).toBeInTheDocument();
  });

  it('展示消息列表及文件链接', () => {
    const messages = [
      {
        id: 1,
        sender_name: 'Alice',
        created_at: '2024-01-01T00:00:00Z',
        text_content: 'Hello',
        files: [{ id: 'f1', filename: 'file1.txt' }],
      },
    ];

    useMessages.mockReturnValueOnce({
      messages,
      loading: false,
      sendMessage: sendMessageMock,
      uploadFile: uploadFileMock,
      deleteFile: deleteFileMock,
      getFile: getFileMock,
    });

    render(<CommentBox formId={formId} />);

    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('file1.txt')).toBeInTheDocument();
  });

  it('只输入文本点击 Send 时，会调用 sendMessage，并清空输入框', async () => {
    sendMessageMock.mockResolvedValueOnce(100); // 返回 messageId

    render(<CommentBox formId={formId} />);

    const textarea = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByText('Send');

    fireEvent.change(textarea, { target: { value: 'Test message' } });

    await act(async () => {
      fireEvent.click(sendButton);
    });

    expect(sendMessageMock).toHaveBeenCalledWith({
      text_content: 'Test message',
      function_id: null,
      nonfunction_id: null,
    });

    // 输入应被清空
    expect(textarea).toHaveValue('');
    // 未选择文件时不会上传
    expect(uploadFileMock).not.toHaveBeenCalled();
  });

  it('只有文件且没有文本时，点击 Send 不会调用 sendMessage 或 uploadFile', async () => {
    render(<CommentBox formId={formId} />);

    const sendButton = screen.getByText('Send');
    const fileInput = document.querySelector('input[type="file"]');

    const file = new File(['content'], 'test.txt', { type: 'text/plain' });

    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    await act(async () => {
      fireEvent.click(sendButton);
    });

    // 因为逻辑里：没有 text.trim() 并且没有 messageId（text 没发也不会有 messageId），不会走 uploadFile
    expect(sendMessageMock).not.toHaveBeenCalled();
    expect(uploadFileMock).not.toHaveBeenCalled();
  });

  it('有文本和文件时，点击 Send 会先 sendMessage 再 uploadFile', async () => {
    const messageId = 200;
    sendMessageMock.mockResolvedValueOnce(messageId);
    uploadFileMock.mockResolvedValueOnce('file-id');

    render(<CommentBox formId={formId} />);

    const textarea = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByText('Send');
    const fileInput = document.querySelector('input[type="file"]');

    const file = new File(['content'], 'upload.txt', { type: 'text/plain' });

    fireEvent.change(textarea, { target: { value: 'With file' } });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await act(async () => {
      fireEvent.click(sendButton);
    });

    expect(sendMessageMock).toHaveBeenCalledWith({
      text_content: 'With file',
      function_id: null,
      nonfunction_id: null,
    });
    expect(uploadFileMock).toHaveBeenCalledWith(messageId, file);
  });

  it('点击文件链接时会调用 getFile 并触发下载逻辑', async () => {
    const messages = [
      {
        id: 1,
        sender_name: 'Alice',
        created_at: '2024-01-01T00:00:00Z',
        text_content: 'Hello',
        files: [{ id: 'f1', filename: 'file1.txt' }],
      },
    ];

    getFileMock.mockResolvedValueOnce({ content: 'file-content' });

    useMessages.mockReturnValueOnce({
      messages,
      loading: false,
      sendMessage: sendMessageMock,
      uploadFile: uploadFileMock,
      deleteFile: deleteFileMock,
      getFile: getFileMock,
    });

    // 关键修改：不替换 createElement 的返回值类型，而是在真实元素上 patch click
    const realCreateElement = document.createElement.bind(document);
    const appendChildMock = vi.spyOn(document.body, 'appendChild');
    const removeChildMock = vi.spyOn(document.body, 'removeChild');
    const clickMock = vi.fn();

    vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      const el = realCreateElement(tagName);
      if (tagName === 'a') {
        // 给 <a> 元素打一个 click spy
        el.click = clickMock;
      }
      return el;
    });

    render(<CommentBox formId={formId} />);

    const fileLink = screen.getByText('file1.txt');

    await act(async () => {
      fireEvent.click(fileLink);
    });

    expect(getFileMock).toHaveBeenCalledWith('f1');
    expect(clickMock).toHaveBeenCalled();
    expect(appendChildMock).toHaveBeenCalled();
    expect(removeChildMock).toHaveBeenCalled();
  });
});