import React, { useState } from 'react';
import RequirementList from './RequirementList';

export default function Sidebar({
  user,
  login,
  register,
  logout,
  forms,
  selectedForm,
  onSelect,
  onDelete,
  onRefresh
}) {
  const [authForm, setAuthForm] = useState({ username: '', email: '', password: '', role: 'client' });

  return (
    <div>
      <h2>SyncBridge</h2>

      {!user ? (
        <div className="auth">
          <h3>Register / Login</h3>
          <input placeholder="username" value={authForm.username} onChange={e => setAuthForm({ ...authForm, username: e.target.value })} />
          <input placeholder="email" value={authForm.email} onChange={e => setAuthForm({ ...authForm, email: e.target.value })} />
          <input placeholder="password" type="password" value={authForm.password} onChange={e => setAuthForm({ ...authForm, password: e.target.value })} />
          <div style={{ marginTop: '8px', fontSize: '12px' }}>
            <label>
              <input type="radio" checked={authForm.role === 'client'} onChange={() => setAuthForm({ ...authForm, role: 'client' })} /> Client
            </label>
            <label>
              <input type="radio" checked={authForm.role === 'developer'} onChange={() => setAuthForm({ ...authForm, role: 'developer' })} /> Developer
            </label>
          </div>
          <div className="row">
            <button onClick={() => register(authForm)}>Register</button>
            <button onClick={() => login(authForm)}>Login</button>
          </div>
        </div>
      ) : (
        <div>
          <div className="user-info">
            <span className="signed-in">Signed in as</span>
            <span className="username">{user.username}</span>
            <span className="role-tag">({user.role})</span>
            <button onClick={logout}>Logout</button>
          </div>

          {/* 只有 client 可以提交需求 */}
          {user.role === 'client' && (
            <div>
              {/* 这里可以再拆 SubmitForm 组件 */}
            </div>
          )}

          <hr />
          <RequirementList
            requirements={forms}
            selectedReq={selectedForm}
            onSelect={onSelect}
            onDelete={onDelete}
            onRefresh={onRefresh}
          />
        </div>
      )}
    </div>
  );
}
