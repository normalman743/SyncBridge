import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Sidebar from './Sidebar';
import RequirementList from './RequirementList';

// mock RequirementList 组件
vi.mock('./RequirementList', () => ({
  default: vi.fn(() => <div data-testid="requirement-list-mock" />),
}));

describe('Sidebar component', () => {
  const forms = [
    { id: 1, title: 'Req 1', status: 'open', message: 'm1' },
    { id: 2, title: 'Req 2', status: 'done', message: 'm2' },
  ];
  const selectedForm = forms[0];

  let loginMock;
  let registerMock;
  let logoutMock;
  let onSelectMock;
  let onDeleteMock;
  let onRefreshMock;

  beforeEach(() => {
    loginMock = vi.fn();
    registerMock = vi.fn();
    logoutMock = vi.fn();
    onSelectMock = vi.fn();
    onDeleteMock = vi.fn();
    onRefreshMock = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('未登录时显示注册/登录表单，并能输入信息与切换角色', () => {
    render(
      <Sidebar
        user={null}
        login={loginMock}
        register={registerMock}
        logout={logoutMock}
        forms={forms}
        selectedForm={selectedForm}
        onSelect={onSelectMock}
        onDelete={onDeleteMock}
        onRefresh={onRefreshMock}
      />,
    );

    // 标题
    expect(screen.getByText('SyncBridge')).toBeInTheDocument();
    // auth 区块
    expect(screen.getByText('Register / Login')).toBeInTheDocument();

    const usernameInput = screen.getByPlaceholderText('username');
    const emailInput = screen.getByPlaceholderText('email');
    const passwordInput = screen.getByPlaceholderText('password');

    // 默认角色是 client
    const clientRadio = screen.getByLabelText('Client');
    const developerRadio = screen.getByLabelText('Developer');
    expect(clientRadio).toBeChecked();
    expect(developerRadio).not.toBeChecked();

    // 输入信息
    fireEvent.change(usernameInput, { target: { value: 'alice' } });
    fireEvent.change(emailInput, { target: { value: 'alice@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'secret' } });

    // 切换角色为 developer
    fireEvent.click(developerRadio);
    expect(developerRadio).toBeChecked();
    expect(clientRadio).not.toBeChecked();

    // 点击 Register
    fireEvent.click(screen.getByText('Register'));
    expect(registerMock).toHaveBeenCalledTimes(1);
    expect(registerMock).toHaveBeenCalledWith({
      username: 'alice',
      email: 'alice@example.com',
      password: 'secret',
      role: 'developer',
    });

    // 点击 Login
    fireEvent.click(screen.getByText('Login'));
    expect(loginMock).toHaveBeenCalledTimes(1);
    expect(loginMock).toHaveBeenCalledWith({
      username: 'alice',
      email: 'alice@example.com',
      password: 'secret',
      role: 'developer',
    });

    // 未登录时不应渲染 RequirementList
    expect(screen.queryByTestId('requirement-list-mock')).toBeNull();
  });

  it('登录后显示用户信息和 Logout 按钮，并调用 logout', () => {
    const user = { username: 'bob', role: 'client' };

    render(
      <Sidebar
        user={user}
        login={loginMock}
        register={registerMock}
        logout={logoutMock}
        forms={forms}
        selectedForm={selectedForm}
        onSelect={onSelectMock}
        onDelete={onDeleteMock}
        onRefresh={onRefreshMock}
      />,
    );

    expect(screen.getByText('SyncBridge')).toBeInTheDocument();
    expect(screen.getByText('Signed in as')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('(client)')).toBeInTheDocument();

    const logoutButton = screen.getByText('Logout');
    fireEvent.click(logoutButton);
    expect(logoutMock).toHaveBeenCalledTimes(1);
  });

  it('client 登录时渲染 RequirementList 且传入正确 props', () => {
    const user = { username: 'cathy', role: 'client' };

    render(
      <Sidebar
        user={user}
        login={loginMock}
        register={registerMock}
        logout={logoutMock}
        forms={forms}
        selectedForm={selectedForm}
        onSelect={onSelectMock}
        onDelete={onDeleteMock}
        onRefresh={onRefreshMock}
      />,
    );

    // RequirementList 被渲染（用 mock 占位）
    expect(screen.getByTestId('requirement-list-mock')).toBeInTheDocument();

    // 检查 RequirementList 被调用时的 props
    expect(RequirementList).toHaveBeenCalledTimes(1);
    const props = RequirementList.mock.calls[0][0];

    expect(props.requirements).toEqual(forms);
    expect(props.selectedReq).toEqual(selectedForm);
    expect(props.onSelect).toBe(onSelectMock);
    expect(props.onDelete).toBe(onDeleteMock);
    expect(props.onRefresh).toBe(onRefreshMock);
  });

  it('developer 登录时也渲染 RequirementList（但不显示 client 提交区块）', () => {
    const user = { username: 'devUser', role: 'developer' };

    render(
      <Sidebar
        user={user}
        login={loginMock}
        register={registerMock}
        logout={logoutMock}
        forms={forms}
        selectedForm={selectedForm}
        onSelect={onSelectMock}
        onDelete={onDeleteMock}
        onRefresh={onRefreshMock}
      />,
    );

    expect(screen.getByText('devUser')).toBeInTheDocument();
    expect(screen.getByText('(developer)')).toBeInTheDocument();

    // 目前 client 提交区块是空 div，这里就不具体断言内容了
    // 但 RequirementList 一样会渲染
    expect(screen.getByTestId('requirement-list-mock')).toBeInTheDocument();
  });
});