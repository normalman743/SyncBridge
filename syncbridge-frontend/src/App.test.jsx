import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';

import { useAuth } from './hooks/useAuth';
import { useForm } from './hooks/useForm';
import { useMessages } from './hooks/useMessages';

import Sidebar from './components/Sidebar';
import RequirementDetail from './components/RequirementDetail';

// mock hooks
vi.mock('./hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

vi.mock('./hooks/useForm', () => ({
  useForm: vi.fn(),
}));

vi.mock('./hooks/useMessages', () => ({
  useMessages: vi.fn(),
}));

// mock 子组件，只关心 props
vi.mock('./components/Sidebar', () => ({
  default: vi.fn(() => <div data-testid="sidebar-mock" />),
}));

vi.mock('./components/RequirementDetail', () => ({
  default: vi.fn(() => <div data-testid="requirement-detail-mock" />),
}));

describe('App component', () => {
  let loginMock;
  let registerMock;
  let logoutMock;

  let loadFormsMock;
  let loadFormByIdMock;
  let createFormMock;
  let modifyFormMock;
  let removeFormMock;
  let changeFormStatusMock;

  let sendMessageMock;
  let fetchMessagesMock;

  const user = { id: 1, username: 'alice', role: 'client' };
  const forms = [
    { id: 1, title: 'Form 1', status: 'open', message: 'm1' },
    { id: 2, title: 'Form 2', status: 'done', message: 'm2' },
  ];
  const selectedForm = forms[0];
  const messages = [{ id: 1, text_content: 'hello' }];

  beforeEach(() => {
    loginMock = vi.fn();
    registerMock = vi.fn();
    logoutMock = vi.fn();

    loadFormsMock = vi.fn();
    loadFormByIdMock = vi.fn();
    createFormMock = vi.fn();
    modifyFormMock = vi.fn();
    removeFormMock = vi.fn();
    changeFormStatusMock = vi.fn();

    sendMessageMock = vi.fn();
    fetchMessagesMock = vi.fn();

    // 默认 mock：有 user，有 selectedForm
    useAuth.mockReturnValue({
      user,
      login: loginMock,
      register: registerMock,
      logout: logoutMock,
    });

    useForm.mockReturnValue({
      forms,
      selectedForm,
      loadForms: loadFormsMock,
      loadFormById: loadFormByIdMock,
      createForm: createFormMock,
      modifyForm: modifyFormMock,
      removeForm: removeFormMock,
      changeFormStatus: changeFormStatusMock,
    });

    useMessages.mockReturnValue({
      messages,
      sendMessage: sendMessageMock,
      fetchMessages: fetchMessagesMock,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('挂载时，user 存在会调用 loadForms，selectedForm 有 id 会调用 fetchMessages', () => {
    render(<App />);

    // loadForms 在 effect 中被调用一次
    expect(loadFormsMock).toHaveBeenCalledTimes(1);

    // fetchMessages 在 effect 中以 selectedForm.id 调用一次
    expect(fetchMessagesMock).toHaveBeenCalledTimes(1);
    expect(fetchMessagesMock).toHaveBeenCalledWith(selectedForm.id);
  });

  it('当 user 为空时，不会调用 loadForms', () => {
    useAuth.mockReturnValueOnce({
      user: null,
      login: loginMock,
      register: registerMock,
      logout: logoutMock,
    });

    render(<App />);

    expect(loadFormsMock).not.toHaveBeenCalled();
  });

  it('当 selectedForm 没有 id 时，不会调用 fetchMessages', () => {
    useForm.mockReturnValueOnce({
      forms,
      selectedForm: null,
      loadForms: loadFormsMock,
      loadFormById: loadFormByIdMock,
      createForm: createFormMock,
      modifyForm: modifyFormMock,
      removeForm: removeFormMock,
      changeFormStatus: changeFormStatusMock,
    });

    render(<App />);

    expect(fetchMessagesMock).not.toHaveBeenCalled();
  });

  it('渲染 Sidebar，并向其传递正确的 props', () => {
    render(<App />);

    expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
    expect(Sidebar).toHaveBeenCalledTimes(1);

    const props = Sidebar.mock.calls[0][0];

    expect(props.user).toEqual(user);
    expect(props.login).toBe(loginMock);
    expect(props.register).toBe(registerMock);
    expect(props.logout).toBe(logoutMock);

    expect(props.forms).toEqual(forms);
    expect(props.selectedForm).toEqual(selectedForm);
    expect(props.onSelect).toBe(loadFormByIdMock);
    expect(props.onDelete).toBe(removeFormMock);
    expect(props.onRefresh).toBe(loadFormsMock);
  });

  it('渲染 RequirementDetail，并向其传递正确的 props', () => {
    render(<App />);

    expect(screen.getByTestId('requirement-detail-mock')).toBeInTheDocument();
    expect(RequirementDetail).toHaveBeenCalledTimes(1);

    const props = RequirementDetail.mock.calls[0][0];

    expect(props.user).toEqual(user);
    expect(props.requirement).toEqual(selectedForm);
    expect(props.messages).toEqual(messages);

    // comment 是 App 内部 state，初始为空字符串
    expect(props.comment).toBe('');

    // setComment 应该是一个函数（useState 的 setter）
    expect(typeof props.setComment).toBe('function');

    // 状态更新函数
    expect(props.updateFormStatus).toBe(changeFormStatusMock);

    // sendMessage 是封装过的函数
    expect(typeof props.sendMessage).toBe('function');
  });

  it('RequirementDetail 传入的 sendMessage 会按 form_id + text_content 调用 useMessages 的 sendMessage', () => {
    render(<App />);

    const props = RequirementDetail.mock.calls[0][0];
    const wrappedSendMessage = props.sendMessage;

    wrappedSendMessage('hello world');

    expect(sendMessageMock).toHaveBeenCalledTimes(1);
    expect(sendMessageMock).toHaveBeenCalledWith({
      form_id: selectedForm.id,
      text_content: 'hello world',
    });
  });

  it('当 RequirementDetail 内部调用 setComment 时，App 中的 comment 会更新', () => {
    // 渲染 App
    const { rerender } = render(<App />);

    // 第一次渲染时，拿到 RequirementDetail 的 props
    let firstProps = RequirementDetail.mock.calls[0][0];
    const setComment = firstProps.setComment;

    // 模拟在子组件中调用 setComment
    setComment('new comment');

    // 由于这是 state 更新，组件会重新渲染；
    // 为了确保拿到最新的 props，可以重新执行 render
    rerender(<App />);

    // 再取一次 props，检查 comment 是否变了
    const secondProps = RequirementDetail.mock.calls.at(-1)[0];
    expect(secondProps.comment).toBe('new comment');
  });
});