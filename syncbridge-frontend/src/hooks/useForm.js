// hooks/useForm.js
import { useState, useEffect, useCallback } from 'react';
import {
  fetchFormsAPI,
  fetchFormByIdAPI,
  submitMainFormAPI,
  updateFormAPI,
  deleteFormAPI,
  createSubformAPI,
  updateFormStatusAPI
} from '../api/form';
import {
  fetchFunctionsAPI as fetchFunctionsAPI,
  createFunctionAPI as createFunctionAPI,
  updateFunctionAPI as updateFunctionAPI,
  deleteFunctionAPI as deleteFunctionAPI
} from '../api/function';
import {
  fetchNonfunctionsAPI as fetchNonfunctionsAPI,
  createNonfunctionAPI as createNonfunctionAPI,
  updateNonfunctionAPI as updateNonfunctionAPI,
  deleteNonfunctionAPI as deleteNonfunctionAPI
} from '../api/nonfunction';

import { getToken, removeToken } from '../api/index';

export function useForm() {
  const [forms, setForms] = useState([]);
  const [selectedForm, setSelectedForm] = useState(null);
  const [functions, setFunctions] = useState([]);
  const [nonfunctions, setNonfunctions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const token = getToken();

  // ----------------- 表单操作 -----------------
  const loadForms = useCallback(async (params = { page: 1, page_size: 20 }) => {
    if (!token) return;
    setLoading(true);
    try {
      await fetchFormsAPI(params, token);
      // fetchFormsAPI 内部已经 setRequirements，可能你需要把结果返回或同步更新 state
      setForms((prev) => [...prev]); // 如果 fetchFormsAPI 内部修改了全局 state
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const loadFormById = useCallback(async (id) => {
    if (!token) return;
    setLoading(true);
    try {
      const form = await fetchFormByIdAPI(id, token);
      setSelectedForm(form);

      // 加载 function 和 nonfunction
      const funcs = await fetchFunctionsAPI(id, token);
      setFunctions(funcs);

      const nonfuncs = await fetchNonfunctionsAPI(id, token);
      setNonfunctions(nonfuncs);

      return form;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token]);

  const createForm = useCallback(async (formData) => {
    if (!token) return null;
    setLoading(true);
    try {
      const formId = await submitMainFormAPI(formData, token);
      await loadForms();
      if (formId) await loadFormById(formId);
      return formId;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, loadForms, loadFormById]);

  const modifyForm = useCallback(async (id, updates) => {
    if (!token) return false;
    setLoading(true);
    try {
      const success = await updateFormAPI(id, updates, token);
      if (success) await loadFormById(id);
      return success;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token, loadFormById]);

  const removeForm = useCallback(async (id) => {
    if (!token) return false;
    setLoading(true);
    try {
      const success = await deleteFormAPI(id, token);
      if (success) {
        setSelectedForm(null);
        await loadForms();
      }
      return success;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token, loadForms]);

  const changeFormStatus = useCallback(async (id, status) => {
    if (!token) return false;
    setLoading(true);
    try {
      await updateFormStatusAPI(id, status, token);
      await loadFormById(id);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [token, loadFormById]);
  
  const createSubform = useCallback(async (formId, subformData) => {
    if (!token) return null;
    setLoading(true);
    try {
      // 调用 createSubformAPI 创建子表单
      const newSubform = await createSubformAPI(formId, subformData, token);

      // 创建成功后，重新加载该表单的详情
      if (newSubform) {
        await loadFormById(formId);
        return newSubform.id || newSubform._id;
      }

      return null;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, loadFormById]);


  // ----------------- Function 操作 -----------------
  const loadFunctions = useCallback(async (formId) => {
    if (!token) return;
    setLoading(true);
    try {
      const funcs = await fetchFunctionsAPI(formId, token);
      setFunctions(funcs);
      return funcs;
    } catch (err) {
      setError(err);
      return [];
    } finally {
      setLoading(false);
    }
  }, [token]);

  const addFunction = useCallback(async (body) => {
    if (!token || !selectedForm) return null;
    setLoading(true);
    try {
      const id = await createFunctionAPI(body, token);
      if (id) await loadFunctions(selectedForm.id);
      return id;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, selectedForm, loadFunctions]);

  const modifyFunction = useCallback(async (id, updates) => {
    if (!token) return false;
    setLoading(true);
    try {
      const success = await updateFunctionAPI(id, updates, token);
      if (success && selectedForm) await loadFunctions(selectedForm.id);
      return success;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token, selectedForm, loadFunctions]);

  const removeFunction = useCallback(async (id) => {
    if (!token) return false;
    setLoading(true);
    try {
      const success = await deleteFunctionAPI(id, token);
      if (success && selectedForm) await loadFunctions(selectedForm.id);
      return success;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token, selectedForm, loadFunctions]);

  // ----------------- Nonfunction 操作 -----------------
  const loadNonfunctions = useCallback(async (formId) => {
    if (!token) return;
    setLoading(true);
    try {
      const nonfuncs = await fetchNonfunctionsAPI(formId, token);
      setNonfunctions(nonfuncs);
      return nonfuncs;
    } catch (err) {
      setError(err);
      return [];
    } finally {
      setLoading(false);
    }
  }, [token]);

  const addNonfunction = useCallback(async (body) => {
    if (!token || !selectedForm) return null;
    setLoading(true);
    try {
      const id = await createNonfunctionAPI(body, token);
      if (id) await loadNonfunctions(selectedForm.id);
      return id;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, selectedForm, loadNonfunctions]);

  const modifyNonfunction = useCallback(async (id, updates) => {
    if (!token) return false;
    setLoading(true);
    try {
      const success = await updateNonfunctionAPI(id, updates, token);
      if (success && selectedForm) await loadNonfunctions(selectedForm.id);
      return success;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token, selectedForm, loadNonfunctions]);

  const removeNonfunction = useCallback(async (id) => {
    if (!token) return false;
    setLoading(true);
    try {
      const success = await deleteNonfunctionAPI(id, token);
      if (success && selectedForm) await loadNonfunctions(selectedForm.id);
      return success;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [token, selectedForm, loadNonfunctions]);

  return {
    forms,
    selectedForm,
    functions,
    nonfunctions,
    loading,
    error,
    // Form
    loadForms,
    loadFormById,
    createForm,
    modifyForm,
    removeForm,
    changeFormStatus,
    createSubform,
    // Function
    loadFunctions,
    addFunction,
    modifyFunction,
    removeFunction,
    // Nonfunction
    loadNonfunctions,
    addNonfunction,
    modifyNonfunction,
    removeNonfunction
  };
}
