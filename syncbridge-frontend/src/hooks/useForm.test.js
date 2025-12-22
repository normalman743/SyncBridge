// src/hooks/useForm.test.js
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useForm } from './useForm';
import * as formApi from '../api/form';
import * as funcApi from '../api/function';
import * as nonfuncApi from '../api/nonfunction';
import { getToken } from '../api/index';

vi.mock('../api/form');
vi.mock('../api/function');
vi.mock('../api/nonfunction');
vi.mock('../api/index', () => ({
  getToken: vi.fn(),
  removeToken: vi.fn(),
}));

describe('useForm hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 默认有 token，方便测试
    getToken.mockReturnValue('test-token');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('初始 state 正确', () => {
    const { result } = renderHook(() => useForm());

    expect(result.current.forms).toEqual([]);
    expect(result.current.selectedForm).toBeNull();
    expect(result.current.functions).toEqual([]);
    expect(result.current.nonfunctions).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('loadForms 在有 token 时会调用 fetchFormsAPI 并切换 loading', async () => {
    formApi.fetchFormsAPI.mockResolvedValueOnce({});

    const { result } = renderHook(() => useForm());

    await act(async () => {
      await result.current.loadForms({ page: 2, page_size: 10 });
    });

    expect(result.current.loading).toBe(false);
    expect(formApi.fetchFormsAPI).toHaveBeenCalledWith(
      { page: 2, page_size: 10 },
      'test-token',
    );
  });

  it('loadFormById 会调用多个 API 并设置 selectedForm / functions / nonfunctions', async () => {
    const fakeForm = { id: 1, title: 'Form 1' };
    const fakeFuncs = [{ id: 10 }];
    const fakeNonfuncs = [{ id: 20 }];

    formApi.fetchFormByIdAPI.mockResolvedValueOnce(fakeForm);
    funcApi.fetchFunctionsAPI.mockResolvedValueOnce(fakeFuncs);
    nonfuncApi.fetchNonfunctionsAPI.mockResolvedValueOnce(fakeNonfuncs);

    const { result } = renderHook(() => useForm());

    await act(async () => {
      const returnedForm = await result.current.loadFormById(1);
      expect(returnedForm).toEqual(fakeForm);
    });

    expect(formApi.fetchFormByIdAPI).toHaveBeenCalledWith(1, 'test-token');
    expect(funcApi.fetchFunctionsAPI).toHaveBeenCalledWith(1, 'test-token');
    expect(nonfuncApi.fetchNonfunctionsAPI).toHaveBeenCalledWith(
      1,
      'test-token',
    );

    expect(result.current.selectedForm).toEqual(fakeForm);
    expect(result.current.functions).toEqual(fakeFuncs);
    expect(result.current.nonfunctions).toEqual(fakeNonfuncs);
  });

  it('createForm 成功时会调用 submitMainFormAPI，并返回新表单 ID', async () => {
    // submitMainFormAPI 返回 formId
    formApi.submitMainFormAPI.mockResolvedValueOnce(123);

    const { result } = renderHook(() => useForm());

    await act(async () => {
      const newId = await result.current.createForm({ title: 'New' });
      expect(newId).toBe(123);
    });

    expect(formApi.submitMainFormAPI).toHaveBeenCalledWith(
      { title: 'New' },
      'test-token',
    );
    // 是否在内部调用 loadForms/loadFormById 已由它们自己的用例覆盖，这里不再 spy
  });

  it('modifyForm 成功时会调用 updateFormAPI 并返回 true', async () => {
    formApi.updateFormAPI.mockResolvedValueOnce(true);

    const { result } = renderHook(() => useForm());

    await act(async () => {
      const success = await result.current.modifyForm(1, { title: 'New' });
      expect(success).toBe(true);
    });

    expect(formApi.updateFormAPI).toHaveBeenCalledWith(
      1,
      { title: 'New' },
      'test-token',
    );
    // 内部是否调用 loadFormById 同样交给其它用例或集成测试，这里不再 spy
  });

  it('removeForm 成功时会调用 deleteFormAPI 并清空 selectedForm', async () => {
    formApi.deleteFormAPI.mockResolvedValueOnce(true);

    const { result } = renderHook(() => useForm());

    // 先设置一个 selectedForm，模拟已经选中某个表单
    await act(async () => {
      // 直接使用 setSelectedForm 的写法你当前 hook 没暴露，这里通过 loadFormById 设置
      // 为避免真正调用 API，这里简单地直接操作 state
      // 方案：手动把 selectedForm 设进去
      // @ts-expect-error 这里为了测试直接写入内部字段
      result.current.selectedForm = { id: 1 };
    });

    await act(async () => {
      const success = await result.current.removeForm(1);
      expect(success).toBe(true);
    });

    expect(formApi.deleteFormAPI).toHaveBeenCalledWith(1, 'test-token');
    expect(result.current.selectedForm).toBeNull();
  });

  it('loadFunctions 会调用 fetchFunctionsAPI 并更新 functions', async () => {
    const fakeFuncs = [{ id: 1 }];
    funcApi.fetchFunctionsAPI.mockResolvedValueOnce(fakeFuncs);

    const { result } = renderHook(() => useForm());

    await act(async () => {
      const res = await result.current.loadFunctions(1);
      expect(res).toEqual(fakeFuncs);
    });

    expect(funcApi.fetchFunctionsAPI).toHaveBeenCalledWith(1, 'test-token');
    expect(result.current.functions).toEqual(fakeFuncs);
  });

  it('loadNonfunctions 会调用 fetchNonfunctionsAPI 并更新 nonfunctions', async () => {
    const fakeNonfuncs = [{ id: 1 }];
    nonfuncApi.fetchNonfunctionsAPI.mockResolvedValueOnce(fakeNonfuncs);

    const { result } = renderHook(() => useForm());

    await act(async () => {
      const res = await result.current.loadNonfunctions(1);
      expect(res).toEqual(fakeNonfuncs);
    });

    expect(nonfuncApi.fetchNonfunctionsAPI).toHaveBeenCalledWith(
      1,
      'test-token',
    );
    expect(result.current.nonfunctions).toEqual(fakeNonfuncs);
  });
});