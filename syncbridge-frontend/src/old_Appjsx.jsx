// src/App.jsx
import React, { useEffect, useState } from 'react';
import './index.css';

const API_BASE = 'http://localhost:5000';

function tokenKey() { return 'syncbridge_token'; }
function getToken() { return localStorage.getItem(tokenKey()); }
function setToken(t) { localStorage.setItem(tokenKey(), t); }
function removeToken() { localStorage.removeItem(tokenKey()); }

export default function App() {
  const [user, setUser] = useState(null); // { id, email, role }
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true); // ⭐ 防止闪回登录页

  const [requirements, setRequirements] = useState([]);
  const [form, setForm] = useState({
    title: '',
    description: '',
    functions: '',
    performance: '',
    budget: '',
    expected_time: '',
  });
  const [selectedReq, setSelectedReq] = useState(null); 
  const [comment, setComment] = useState('');
  const [authForm, setAuthForm] = useState({
    username: '',
    password: '',
    email: '',
    role: 'client', // ★ 默认是需求方（普通用户）
  });
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const t = localStorage.getItem('token');

    if (!t) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        setToken(t);
        const me = await fetchMe(t);
        setUser(me);
        await fetchform({}, t);
      } catch (err) {
        logout(); // token 失效
      } finally {
        setLoading(false);
      }
    })();
  }, []);


  async function api(path, method = 'GET', body = null, token = getToken()) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const resp = await fetch(API_BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: 'Unknown' }));
      throw new Error(err.error || resp.statusText);
    }
    return resp.json();
  }

  async function register() {
    try {
      const { email, password, display_name, license_key } = authForm;

      const body = {
        email,
        password,
        display_name,
        license_key,
      };

      const res = await api('/api/v1/auth/register', 'POST', body);
      if (res.status === 'success') {
        alert('Registration successful. Please log in.');

        setAuthForm((prev) => ({
          ...prev,
          email,
          password: '',
        }));
      }

    } catch (err) {
      switch (err.code) {
        case 'CONFLICT':
          alert('Email already exists.');
          break;
        case 'FORBIDDEN':
          alert('Invalid, used, or expired license key.');
          break;
        default:
          alert(err.message || 'Registration failed.');
      }
    }
  }


// 登录：只拿 token + role
  async function login() {
    try {
      const { email, password } = authForm;
      const res = await api(
        '/api/v1/auth/login',
        'POST',
        { email, password }
      );
      const { access_token, role } = res.data;
      localStorage.setItem('token', access_token);
      localStorage.setItem('role', role);
      setToken(access_token);
      setUser({
        token: access_token,
        role,
      });
      fetchform({ page: 1 }, access_token);

    } catch (err) {
      if (err.code === 'UNAUTHORIZED') {
        alert('Invalid email or password.');
      } else {
        alert(err.message || 'Login failed.');
      }
    }
  }

  // 获取当前登录用户信息
  async function fetchMe(token) {
    try {
      const res = await api(
        '/api/v1/auth/me',
        'GET',
        null,
        token // Authorization: Bearer <token>
      );
      setUser({
        id: res.user_id,
        email: res.email,
        display_name: res.display_name,
        role: res.role,
        token,
      });

      return res;
    } catch (err) {
      if (err.code === 'UNAUTHORIZED') {
        logout(); // 清空本地状态
      } else {
        console.error('fetchMe failed:', err);
      }
      throw err;
    }
  }


  async function logout() {
    removeToken();
    setUser(null);
    setRequirements([]);
    setSelectedReq(null);
  }

  async function fetchform({ page = 1, page_size = 20 } = {}, token = getToken()) {
    if (!token) return;

    try {
      const currentRole = getUser()?.role;
      let query = `?page=${page}&page_size=${page_size}`;

      if (currentRole === 'developer') {
        query += '&available_only=false'; 
      }

      const data = await api(`/api/v1/forms${query}`, 'GET', null, token);
      const forms = data.data.forms || [];

      setRequirements(forms); // 或 setForms(forms)，根据你的 state 命名
      if (selectedReq) {
        const updated = forms.find((r) => r.id === selectedReq.id);
        if (updated) setSelectedReq(updated);
      }
    } catch (err) {
      console.error(err);
    }
  }
  async function fetchformById(id, token = getToken()) {
    if (!token) {
      alert('未登录');
      return null;
    }

    try {
      const res = await api(`/api/v1/form/${id}`, 'GET', null, token);
      return res.data;

    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('你无权限访问该表单');
          break;
        case 'NOT_FOUND':
          alert('表单不存在');
          break;
        case 'UNAUTHORIZED':
          alert('登录已失效，请重新登录');
          logout(); // 清理本地状态
          break;
        default:
          console.error('fetchFormById 错误:', err);
      }

      return null;
    }
  }

  async function submitMainForm() {
    try {
      const token = getToken();
      if (!token) {
        alert('请先登录');
        return;
      }

      const body = {
        title: form.title,
        message: form.message,          // 注意：不是 description
        budget: form.budget,
        expected_time: form.expected_time,
      };

      const res = await api('/api/v1/form', 'POST', body, token);
      const formId = res.data.form_id;

      setForm({
        title: '',
        description: '',
        functions: '',
        performance: '',
        budget: '',
        expected_time: '',
      });

      // 刷新列表
      await fetchForms();

      // 可选：拉取新建的 form 详情并选中
      const createdForm = await fetchFormById(formId);
      setSelectedReq(createdForm);

    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('只有 client 可以创建需求');
      } else if (err.code === 'UNAUTHORIZED') {
        alert('登录已失效，请重新登录');
        logout();
      } else {
        alert('Submit failed: ' + err.message);
      }
    }
  }
  async function updateForm(id, updates, token = getToken()) {
    if (!token) {
      alert('未登录');
      return false;
    }

    try {
      await api(`/api/v1/form/${id}`, 'PUT', updates, token);
      return true;

    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('你没有权限修改该表单');
          break;
        case 'CONFLICT':
          alert('当前状态不允许修改该表单');
          break;
        case 'UNAUTHORIZED':
          alert('登录已失效，请重新登录');
          logout();
          break;
        default:
          console.error('updateForm error:', err);
        }
        return false;
      }
    }

  async function deleteForm(id) {
    if (!window.confirm('Are you sure you want to delete this form?')) return;

    const token = getToken();
    if (!token) {
      alert('Please login first');
      return;
    }

    try {
      await api(`/api/v1/form/${id}`, 'DELETE', null, token);

      // 如果当前选中的正是被删的 form，清空
      if (selectedReq && selectedReq.id === id) {
        setSelectedReq(null);
      }

      // 重新拉取列表（mainform / subform 状态由后端修正）
      await fetchForms();

    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('You are not allowed to delete this form');
          break;
        case 'CONFLICT':
          alert('Current form status does not allow deletion');
          break;
        case 'UNAUTHORIZED':
          alert('Login expired, please login again');
          logout();
          break;
        default:
          alert(err.message || 'Delete failed');
      }
    }
  }


  
  async function createSubform(mainformId, body, token = getToken()) {
    if (!token) {
      alert('Please login first');
      return null;
    }
    
    try {
      const res = await api(
        `/api/v1/form/${mainformId}/subform`,
        'POST',
        body,
        token
      );
      
      // 成功只返回 subform_id
      return res.data.subform_id;
      
    } catch (err) {
      switch (err.code) {
        case 'CONFLICT':
          alert('This form already has a subform');
          break;
          case 'FORBIDDEN':
            alert('You are not allowed to create a subform for this form');
            break;
            case 'UNAUTHORIZED':
              alert('Login expired, please login again');
              logout();
          break;
          default:
            console.error('createSubform error:', err);
            alert(err.message || 'Create subform failed');
          }
          return null;
        }
      }
      
  async function updateFormStatus(id, status) {
    const token = getToken();
    if (!token) {
      alert('Please login first');
      return;
    }

    try {
      await api(
        `/api/v1/form/${id}/status`,
        'PUT',
        { status },
        token
      );

      // 状态更新成功后，重新拉取数据
      await fetchForms();

      // 如果当前选中的是该 form，同步刷新详情
      if (selectedReq && selectedReq.id === id) {
        const updated = await fetchFormById(id);
        setSelectedReq(updated);
      }

    } catch (err) {
      switch (err.code) {
        case 'CONFLICT':
          alert('Illegal status transition');
          break;
        case 'FORBIDDEN':
          alert('You are not allowed to change this form status');
          break;
        case 'UNAUTHORIZED':
          alert('Login expired, please login again');
          logout();
          break;
        default:
          alert(err.message || 'Update status failed');
      }
    }
  }
  
  /**
   * 获取某个 form 下的 functions
   * @param {number} formId - form 的 ID（必填）
   * @param {string} [token] - 登录 token，默认从 getToken() 获取
   * @returns {Promise<Array>} functions 列表
  */
 async function fetchFunctions(formId, token = getToken()) {
    if (!token) {
      alert('Please login first');
      return [];
    }

    if (!formId) {
      console.error('fetchFunctions: formId is required');
      return [];
    }

    try {
      const res = await api(
        `/api/v1/functions?form_id=${formId}`,
        'GET',
        null,
        token
      );
      
      return res.data.functions || [];
      
    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('You are not allowed to view functions of this form');
          break;
          case 'UNAUTHORIZED':
            alert('Login expired, please login again');
            logout();
            break;
        default:
          console.error('fetchFunctions error:', err);
        }
      return [];
    }
  }
  /**
   * 创建 function
   * @param {Object} body - function 内容
   * @param {string} [token] - 登录 token，默认从 getToken() 获取
   * @returns {Promise<number|null>} 新建 function 的 id
  */
 async function createFunction(body, token = getToken()) {
   if (!token) {
     alert('Please login first');
     return null;
    }
    
    try {
      const res = await api(
        '/api/v1/function',
        'POST',
        body,
        token
      );
      
      return res.data.id;
      
    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('You are not allowed to add function to this form');
          break;
          case 'CONFLICT':
            alert('Function cannot be created due to form status');
            break;
            case 'UNAUTHORIZED':
          alert('Login expired, please login again');
          logout();
          break;
          default:
            console.error('createFunction error:', err);
          }
          return null;
        }
      }
  async function updateFunction(id, updates, token = getToken()) {
    if (!token) return false;
    
    try {
      await api(`/api/v1/function/${id}`, 'PUT', updates, token);
      return true;
    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('No permission to update this function');
      } else if (err.code === 'CONFLICT') {
        alert('Function status does not allow modification');
      }
      return false;
    }
  }

  async function deleteFunction(id, token = getToken()) {
    if (!token) return false;

    try {
      await api(`/api/v1/function/${id}`, 'DELETE', null, token);
      return true;
    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('No permission to delete this function');
      } else if (err.code === 'CONFLICT') {
        alert('Function cannot be deleted at this stage');
      }
      return false;
    }
  }
  
  /**
   * 获取某个 form 下的 nonfunctions
   * @param {number} formId
   * @param {string} [token]
   * @returns {Promise<Array>}
  */
  async function fetchNonfunctions(formId, token = getToken()) {
    if (!token) {
      alert('Please login first');
      return [];
    }
    
    if (!formId) {
      console.error('fetchNonfunctions: formId is required');
      return [];
    }
    
    try {
      const res = await api(
        `/api/v1/nonfunctions?form_id=${formId}`,
        'GET',
        null,
        token
      );
      
      return res.data.nonfunctions || [];
      
    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('You are not allowed to view nonfunctions of this form');
          break;
          case 'UNAUTHORIZED':
            alert('Login expired, please login again');
            logout();
            break;
            default:
              console.error('fetchNonfunctions error:', err);
            }
            return [];
          }
        }
        
        /**
         * 创建 nonfunction
         * @param {Object} body
         * @param {string} [token]
         * @returns {Promise<number|null>} 新建 nonfunction 的 id
        */
       async function createNonfunction(body, token = getToken()) {
         if (!token) {
           alert('Please login first');
           return null;
    }

    try {
      const res = await api(
        '/api/v1/nonfunction',
        'POST',
        body,
        token
      );

      return res.data.id;
      
    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('You are not allowed to add nonfunction to this form');
          break;
          case 'CONFLICT':
            alert('Nonfunction cannot be created due to form status');
            break;
            case 'UNAUTHORIZED':
              alert('Login expired, please login again');
              logout();
              break;
              default:
                console.error('createNonfunction error:', err);
      }
      return null;
    }
  }
  
  async function updateNonfunction(id, updates, token = getToken()) {
    if (!token) return false;
    
    try {
      await api(`/api/v1/nonfunction/${id}`, 'PUT', updates, token);
      return true;
    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('No permission to update this nonfunction');
      } else if (err.code === 'CONFLICT') {
        alert('Nonfunction status does not allow modification');
      }
      return false;
    }
  }
  
  async function deleteNonfunction(id, token = getToken()) {
    if (!token) return false;
    
    try {
      await api(`/api/v1/nonfunction/${id}`, 'DELETE', null, token);
      return true;
    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('No permission to delete this nonfunction');
      } else if (err.code === 'CONFLICT') {
        alert('Nonfunction cannot be deleted at this stage');
      }
      return false;
    }
  }

  
  useEffect(() => {
    if (!selectedReq) return;
    fetchMessages(selectedReq.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedReq]);
  

  /**
   * 获取消息列表
   * @param {Object} params
   * @param {number} params.form_id        - 必填
   * @param {number} [params.function_id]  - 可选
   * @param {number} [params.nonfunction_id] - 可选
   * @param {number} [params.page=1]
   * @param {number} [params.page_size=20]
   * @param {string} [token]
   */
  async function fetchMessages(
    { form_id, function_id, nonfunction_id, page = 1, page_size = 20 },
    token = getToken()
  ) {
    if (!token) {
      alert('Please login first');
      return { messages: [], page: 1, page_size, total: 0 };
    }

    if (!form_id) {
      console.error('fetchMessages: form_id is required');
      return { messages: [], page: 1, page_size, total: 0 };
    }

    const query = new URLSearchParams({
      form_id,
      page,
      page_size,
      ...(function_id && { function_id }),
      ...(nonfunction_id && { nonfunction_id }),
    }).toString();

    try {
      const res = await api(
        `/api/v1/messages?${query}`,
        'GET',
        null,
        token
      );

      return res.data;

    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('You are not allowed to view messages of this form');
      } else if (err.code === 'UNAUTHORIZED') {
        alert('Login expired, please login again');
        logout();
      } else {
        console.error('fetchMessages error:', err);
      }

      return { messages: [], page: 1, page_size, total: 0 };
    }
  }
/**
 * 更新 block 状态（normal / urgent）
 * @param {number} blockId - block 的 ID
 * @param {"normal" | "urgent"} status
 */
async function updateBlockStatus(blockId, status) {
  const token = getToken();
  if (!token) {
    alert('Please login first');
    return false;
  }

  if (!blockId || !status) {
    console.error('updateBlockStatus: blockId and status are required');
    return false;
  }

  try {
    await api(
      `/block/${blockId}/status`,
      'PUT',
      { status },
      token
    );

    return true;

  } catch (err) {
    switch (err.code) {
      case 'VALIDATION_ERROR':
        alert('Invalid block status');
        break;
      case 'FORBIDDEN':
        alert('You are not allowed to update this block');
        break;
      case 'NOT_FOUND':
        alert('Block not found');
        break;
      case 'UNAUTHORIZED':
        alert('Login expired, please login again');
        logout();
        break;
      default:
        alert(err.message || 'Update block status failed');
    }
    return false;
  }
}

/**
 * 上传文件到指定 message
 * @param {number} message_id - 消息 ID
 * @param {File} file - 浏览器 File 对象（二进制）
 * @param {string} [token]
 * @returns {Promise<number|null>} 返回 file_id
 */

  async function uploadFile(message_id, file, token = getToken()) {
    if (!token) {
      alert('Please login first');
      return null;
    }

    if (!message_id || !file) {
      console.error('uploadFile: message_id and file are required');
      return null;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB
      alert('File size exceeds 10MB');
      return null;
    }

    const formData = new FormData();
    formData.append('message_id', message_id);
    formData.append('file', file);

    try {
      const res = await api(
        '/api/v1/file',
        'POST',
        formData,
        token,
        { 'Content-Type': 'multipart/form-data' }
      );
      return res.data.file_id;

    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('No permission to upload file to this message');
          break;
        case 'VALIDATION_ERROR':
          alert('File validation failed');
          break;
        case 'UNAUTHORIZED':
          alert('Login expired, please login again');
          logout();
          break;
        default:
          alert(err.message || 'File upload failed');
      }
      return null;
    }
  }

  
  async function getFile(id, token = getToken()) {
    if (!token) {
      alert('Please login first');
      return null;
    }

    try {
      const res = await api(`/api/v1/file/${id}`, 'GET', null, token);
      return res.data;

    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('No permission to access this file');
      } else if (err.code === 'UNAUTHORIZED') {
        alert('Login expired, please login again');
        logout();
      } else {
        console.error('getFile error:', err);
      }
      return null;
    }
  }

  async function deleteFile(id, token = getToken()) {
    if (!token) return false;

    try {
      await api(`/api/v1/file/${id}`, 'DELETE', null, token);
      return true;

    } catch (err) {
      switch (err.code) {
        case 'FORBIDDEN':
          alert('No permission to delete this file');
          break;
        case 'UNAUTHORIZED':
          alert('Login expired, please login again');
          logout();
          break;
        default:
          alert(err.message || 'File deletion failed');
      }
      return false;
    }
  }

  async function sendMessage(
    { form_id, function_id = null, nonfunction_id = null, text_content },
    token = getToken()
  ) {
    if (!token) {
      alert('Please login first');
      return null;
    }

    if (!form_id || !text_content) {
      console.error('sendMessage: form_id and text_content are required');
      return null;
    }

    try {
      const res = await api(
        '/api/v1/message',
        'POST',
        {
          form_id,
          function_id,
          nonfunction_id,
          text_content,
        },
        token
      );

      return res.data.message_id;

    } catch (err) {
      if (err.code === 'FORBIDDEN') {
        alert('You are not allowed to send messages here');
      } else if (err.code === 'UNAUTHORIZED') {
        alert('Login expired, please login again');
        logout();
      } else {
        alert(err.message || 'Failed to send message');
      }
      return null;
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>SyncBridge</h2>
        {!user ? (
          <div className="auth">
            <h3>Register / Login</h3>
            <input
              placeholder="username"
              value={authForm.username}
              onChange={(e) =>
                setAuthForm({ ...authForm, username: e.target.value })
              }
            />
            <input
              placeholder="email (register)"
              value={authForm.email}
              onChange={(e) =>
                setAuthForm({ ...authForm, email: e.target.value })
              }
            />
            <input
              placeholder="password"
              type="password"
              value={authForm.password}
              onChange={(e) =>
                setAuthForm({ ...authForm, password: e.target.value })
              }
            />

            {/* ★ 角色选择（注册时使用） */}
            <div style={{ marginTop: '8px', fontSize: '12px' }}>
              <span>Role: </span>
              <label style={{ marginRight: '8px' }}>
                <input
                  type="radio"
                  value="client"
                  checked={authForm.role === 'client'}
                  onChange={() =>
                    setAuthForm({ ...authForm, role: 'client' })
                  }
                />
                Client（需求方）
              </label>
              <label>
                <input
                  type="radio"
                  value="developer"
                  checked={authForm.role === 'developer'}
                  onChange={() =>
                    setAuthForm({ ...authForm, role: 'developer' })
                  }
                />
                Developer（开发者）
              </label>
            </div>

            <div className="row">
              <button onClick={register}>Register</button>
              <button onClick={login}>Login</button>
            </div>
          </div>
        ) : (
          <div>
            <div className="user-info">
              <span className="signed-in">Signed in as</span>
              <span className="username">{user?.username || 'User'}</span>
              {user?.role && (
                <span
                  className="role-tag"
                  style={{ marginLeft: '8px', fontSize: '12px' }}
                >
                  ({user.role})
                </span>
              )}
              <button className="logout-btn" onClick={logout}>
                Logout
              </button>
            </div>
            <hr />

            {/* ★ 示例权限：只有 client 可以提交需求 */}
            {user?.role === 'developer' ? (
              <p style={{ fontSize: '14px' }}>
                You are logged in as <strong>developer</strong>. You can view,
                discuss, and update requirement status.
              </p>
            ) : (
              <>
                <h3>Submit Requirement</h3>
                <input
                  placeholder="Title"
                  value={form.title}
                  onChange={(e) =>
                    setForm({ ...form, title: e.target.value })
                  }
                />
                <textarea
                  placeholder="Description"
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                ></textarea>
                <input
                  placeholder="Functions (comma)"
                  value={form.functions}
                  onChange={(e) =>
                    setForm({ ...form, functions: e.target.value })
                  }
                />
                <input
                  placeholder="Performance"
                  value={form.performance}
                  onChange={(e) =>
                    setForm({ ...form, performance: e.target.value })
                  }
                />
                <input
                  placeholder="Budget"
                  value={form.budget}
                  onChange={(e) =>
                    setForm({ ...form, budget: e.target.value })
                  }
                />
                <input
                  placeholder="Expected time"
                  value={form.expected_time}
                  onChange={(e) =>
                    setForm({ ...form, expected_time: e.target.value })
                  }
                />
                <button onClick={submitMainForm}>Submit</button>
              </>
            )}
          </div>
        )}

        <hr />
        <div>
          <h3>Requirements</h3>
          <div className="list">
            {requirements.map((r) => (
              <div
                key={r.id}
                className={`list-item ${
                  selectedReq && selectedReq.id === r.id ? 'active' : ''
                }`}
                onClick={() => setSelectedReq(r)}
              >
                <div className="grow">
                  <strong>{r.title || '(No title)'}</strong>
                  <div className="small">
                    {r.status} • {r.progress}%
                  </div>
                  <div className="small">
                    by {r.created_by_name || 'unknown'}
                  </div>
                </div>

                <button
                  className="danger"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteForm(r.id);
                  }}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
          <button onClick={() => fetchform()}>Refresh</button>
        </div>
      </aside>

      <main className="main">
        {!selectedReq ? (
          <div className="placeholder">
            Select a requirement to view details and discussion.
          </div>
        ) : (
          <div>
            <h2>{selectedReq.title}</h2>
            <div className="meta">
              Status: {selectedReq.status} • Progress: {selectedReq.progress}%
            </div>
            <p>{selectedReq.description}</p>
            <p>{selectedReq.functions}</p>
            <p>{selectedReq.performance}</p>
            <p>{selectedReq.budget}</p>
            <p>{selectedReq.expected_time}</p>

            <div className="status-controls">
              <button
                onClick={() =>
                  updateFormStatus(selectedReq.id, 'Confirmed', 0)
                }
              >
                Confirm
              </button>
              <button
                onClick={() =>
                  updateFormStatus(selectedReq.id, 'In Progress', 20)
                }
              >
                Start (20%)
              </button>
              <button
                onClick={() =>
                  updateFormStatus(selectedReq.id, 'In Progress', 40)
                }
              >
                Basics Ready (40%)
              </button>
               <button
                onClick={() =>
                  updateFormStatus(selectedReq.id, 'In Progress', 60)
                }
              >
                Main Ready (60%)
              </button> 
              <button
                onClick={() =>
                  updateFormStatus(selectedReq.id, 'In Progress', 80)
                }
              >
                Pending Review (80%)
              </button>
              <button
                onClick={() =>
                  updateFormStatus(selectedReq.id, 'Completed', 100)
                }
              >
                Complete (100%)
              </button>
            </div>

            <hr />
            <div className="comments">
              <h3>Discussion</h3>
              <div className="message-list">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`message ${
                      m.sender_name === user?.username ? 'mine' : 'other'
                    }`}
                  >
                    <div className="sender">
                      {m.sender_name || 'Unknown'}
                    </div>
                    <div className="content">
                      {m.content}{' '}
                      {m.file_link && (
                        <a
                          href={m.file_link}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          [file]
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <h3>Post a message</h3>
              <textarea
                placeholder="Type message"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              ></textarea>
              <button onClick={sendMessage}>Send</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}