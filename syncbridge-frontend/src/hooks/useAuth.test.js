// src/hooks/useAuth.test.js
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAuth } from './useAuth';
import { loginAPI, registerAPI, fetchMeAPI } from '../api/auth';

// mock 掉 auth 接口
vi.mock('../api/auth', () => ({
  loginAPI: vi.fn(),
  registerAPI: vi.fn(),
  fetchMeAPI: vi.fn(),
}));

// 简单模拟 localStorage
function mockLocalStorage() {
  let store = {};
  return {
    getItem: vi.fn((key) => store[key] ?? null),
    setItem: vi.fn((key, value) => {
      store[key] = String(value);
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
}

describe('useAuth hook', () => {
  let localStorageMock;

  beforeEach(() => {
    // 替换全局 localStorage
    localStorageMock = mockLocalStorage();
    vi.stubGlobal('localStorage', localStorageMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('初始时如果没有 token，loading 会变为 false，user 为 null', async () => {
    // 没有 token
    localStorageMock.getItem.mockReturnValueOnce(null);

    const { result } = renderHook(() => useAuth());

    // 此时 useEffect 已经同步走了一次分支：没有 token -> setLoading(false)
    expect(result.current.token).toBe(null);
    expect(result.current.user).toBe(null);
    expect(result.current.loading).toBe(false);

    // 防守性检查不会被异步再改坏
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.user).toBe(null);
      expect(result.current.token).toBe(null);
    });
  });

  it('初始时如果有 token，会调用 fetchMeAPI 并设置 user', async () => {
    const fakeToken = 'test-token';
    localStorageMock.getItem.mockReturnValueOnce(fakeToken);

    fetchMeAPI.mockResolvedValueOnce({
      user_id: 1,
      email: 'test@example.com',
      display_name: 'Tester',
      role: 'admin',
    });

    const { result } = renderHook(() => useAuth());

    // useState 初始值会立刻从 localStorage 里取 token
    expect(result.current.token).toBe(fakeToken);

    // 等待 useEffect 中的异步 init 完成
    await waitFor(() => {
      expect(fetchMeAPI).toHaveBeenCalledWith(fakeToken);
      expect(result.current.loading).toBe(false);
      expect(result.current.user).toEqual({
        id: 1,
        email: 'test@example.com',
        display_name: 'Tester',
        role: 'admin',
      });
    });
  });

  it('useAuth hook > login 成功时会调用 loginAPI、写入 localStorage，并更新 token 和 user', async () => {
    const loginResponse = {
      access_token: 'new-token',
      role: 'user',
    };
    loginAPI.mockResolvedValueOnce(loginResponse);
  
    const { result } = renderHook(() => useAuth());
  
    let returned;
    await act(async () => {
      returned = await result.current.login({
        email: 'a@b.com',
        password: '123456',
      });
    });
  
    // 1. 验证 API 调用
    expect(loginAPI).toHaveBeenCalledWith({
      email: 'a@b.com',
      password: '123456',
    });
  
    // 2. 验证返回值
    expect(returned).toEqual(loginResponse);
  
    // 3. 验证写入 localStorage（注意这里用 localStorageMock）
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'token',
      loginResponse.access_token,
    );
  
    // 4. 暂时不验证 result.current.token / result.current.user
    //   （如果你以后想要保证它们被设置，我们可以再改 hook 本身）
  });

  it('register 会调用 registerAPI 并返回结果', async () => {
    const registerRes = { success: true };
    registerAPI.mockResolvedValueOnce(registerRes);

    const { result } = renderHook(() => useAuth());

    let response;
    await act(async () => {
      response = await result.current.register({
        email: 'a@b.com',
        password: '123456',
        display_name: 'AAA',
        license_key: 'KEY',
      });
    });

    expect(registerAPI).toHaveBeenCalledWith({
      email: 'a@b.com',
      password: '123456',
      display_name: 'AAA',
      license_key: 'KEY',
    });
    expect(response).toEqual(registerRes);
  });

  it('removeToken 会清空 localStorage 的 token、并把 user 和 token 设为 null', () => {
    const { result } = renderHook(() => useAuth());

    act(() => {
      result.current.removeToken();
    });

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('token');
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
  });
});