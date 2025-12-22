import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import AuthForm from './AuthForm';
import { useAuth } from '../hooks/useAuth';

// mock useAuth hook
vi.mock('../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

describe('AuthForm component', () => {
  let loginMock;
  let registerMock;
  let alertMock;

  beforeEach(() => {
    loginMock = vi.fn();
    registerMock = vi.fn();

    // 默认 useAuth 返回这两个方法
    useAuth.mockReturnValue({
      login: loginMock,
      register: registerMock,
    });

    // mock 全局 alert，避免测试时弹窗
    alertMock = vi.fn();
    vi.stubGlobal('alert', alertMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('默认展示 login 模式', () => {
    render(<AuthForm />);

    // login 模式下应看到 Login 的 email/password 输入框和 Login 按钮
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();

    // 页面上应该有两个 "Login"（一个是 tab，一个是提交按钮），
    // 用 getAllByText 来避免「多个元素」错误
    const loginButtons = screen.getAllByText('Login');
    expect(loginButtons.length).toBeGreaterThanOrEqual(1);

    // 不应出现 Display Name / License Key 文本
    expect(screen.queryByPlaceholderText('Display Name')).toBeNull();
    expect(screen.queryByPlaceholderText('License Key')).toBeNull();
  });

  it('点击 Register 按钮切换到注册模式', () => {
    render(<AuthForm />);

    // 初始是 login 模式，点击顶部的 Register 切换
    const [tabRegisterButton] = screen.getAllByText('Register');
    fireEvent.click(tabRegisterButton);

    // 注册模式下会出现 Display Name / License Key 等输入
    expect(screen.getByPlaceholderText('Display Name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('License Key')).toBeInTheDocument();

    // 页面上有至少一个 "Register" 按钮即可（tab + 提交按钮）
    const registerButtons = screen.getAllByText('Register');
    expect(registerButtons.length).toBeGreaterThanOrEqual(1);
  });

  it('login 成功时会调用 login 并弹出成功提示', async () => {
    loginMock.mockResolvedValueOnce({ access_token: 'token-123' });

    render(<AuthForm />);

    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const loginButton = screen.getAllByText('Login')[1] || screen.getByText('Login');

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: '123456' } });

    await act(async () => {
      fireEvent.click(loginButton);
    });

    expect(loginMock).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: '123456',
    });
    expect(alertMock).toHaveBeenCalledWith('Login successful');
  });

  it('login 失败时会弹出失败提示', async () => {
    const error = new Error('错误信息');
    loginMock.mockRejectedValueOnce(error);

    render(<AuthForm />);

    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const loginButton = screen.getAllByText('Login')[1] || screen.getByText('Login');

    fireEvent.change(emailInput, { target: { value: 'bad@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'wrong' } });

    await act(async () => {
      fireEvent.click(loginButton);
    });

    expect(loginMock).toHaveBeenCalledWith({
      email: 'bad@example.com',
      password: 'wrong',
    });
    expect(alertMock).toHaveBeenCalledWith('Login failed: ' + error.message);
  });

  it('register 成功时会调用 register 并弹出成功提示', async () => {
    registerMock.mockResolvedValueOnce({ success: true });

    render(<AuthForm />);

    // 先切换到 register 模式
    fireEvent.click(screen.getByText('Register'));

    const displayNameInput = screen.getByPlaceholderText('Display Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const licenseKeyInput = screen.getByPlaceholderText('License Key');
    const registerButton = screen.getAllByText('Register')[1] || screen.getByText('Register');

    fireEvent.change(displayNameInput, { target: { value: 'Tester' } });
    fireEvent.change(emailInput, { target: { value: 'reg@example.com' } });
    fireEvent.change(passwordInput, { target: { value: '123456' } });
    fireEvent.change(licenseKeyInput, { target: { value: 'LICENSE-KEY' } });

    await act(async () => {
      fireEvent.click(registerButton);
    });

    expect(registerMock).toHaveBeenCalledWith({
      email: 'reg@example.com',
      password: '123456',
      display_name: 'Tester',
      license_key: 'LICENSE-KEY',
    });
    expect(alertMock).toHaveBeenCalledWith(
      'Registration successful. Please login.',
    );
  });

  it('register 失败时会弹出失败提示', async () => {
    const error = new Error('注册失败');
    registerMock.mockRejectedValueOnce(error);

    render(<AuthForm />);

    fireEvent.click(screen.getByText('Register'));

    const displayNameInput = screen.getByPlaceholderText('Display Name');
    const emailInput = screen.getByPlaceholderText('Email');
    const passwordInput = screen.getByPlaceholderText('Password');
    const licenseKeyInput = screen.getByPlaceholderText('License Key');
    const registerButton = screen.getAllByText('Register')[1] || screen.getByText('Register');

    fireEvent.change(displayNameInput, { target: { value: 'Tester' } });
    fireEvent.change(emailInput, { target: { value: 'reg@example.com' } });
    fireEvent.change(passwordInput, { target: { value: '123456' } });
    fireEvent.change(licenseKeyInput, { target: { value: 'LICENSE-KEY' } });

    await act(async () => {
      fireEvent.click(registerButton);
    });

    expect(registerMock).toHaveBeenCalledWith({
      email: 'reg@example.com',
      password: '123456',
      display_name: 'Tester',
      license_key: 'LICENSE-KEY',
    });
    expect(alertMock).toHaveBeenCalledWith(
      'Registration failed: ' + error.message,
    );
  });

  it('注册模式下默认 role 为 client，且可以在 UI 中切换', () => {
    render(<AuthForm />);

    fireEvent.click(screen.getByText('Register'));

    const clientRadio = screen.getByLabelText('Client');
    const developerRadio = screen.getByLabelText('Developer');

    // 默认 client 选中
    expect(clientRadio).toBeChecked();
    expect(developerRadio).not.toBeChecked();

    // 切换到 developer
    fireEvent.click(developerRadio);
    expect(developerRadio).toBeChecked();
    expect(clientRadio).not.toBeChecked();
  });
});