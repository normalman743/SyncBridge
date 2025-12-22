import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function AuthForm() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login'); // login / register
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [licenseKey, setLicenseKey] = useState('');
  const [role, setRole] = useState('client'); // 默认 client

  const handleLogin = async () => {
    try {
      await login({ email, password });
      alert('Login successful');
    } catch (err) {
      alert('Login failed: ' + err.message);
    }
  };

  const handleRegister = async () => {
    try {
      await register({ email, password, display_name: displayName, license_key: licenseKey });
      alert('Registration successful. Please login.');
      // 清空敏感信息
      setPassword('');
    } catch (err) {
      alert('Registration failed: ' + err.message);
    }
  };

  return (
    <div className="auth-form">
      <div>
        <button onClick={() => setMode('login')}>Login</button>
        <button onClick={() => setMode('register')}>Register</button>
      </div>

      {mode === 'login' ? (
        <>
          <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
          <button onClick={handleLogin}>Login</button>
        </>
      ) : (
        <>
          <input placeholder="Display Name" value={displayName} onChange={e => setDisplayName(e.target.value)} />
          <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input placeholder="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
          <input placeholder="License Key" value={licenseKey} onChange={e => setLicenseKey(e.target.value)} />
          <div>
            Role:
            <label>
              <input type="radio" value="client" checked={role === 'client'} onChange={() => setRole('client')} />
              Client
            </label>
            <label>
              <input type="radio" value="developer" checked={role === 'developer'} onChange={() => setRole('developer')} />
              Developer
            </label>
          </div>
          <button onClick={handleRegister}>Register</button>
        </>
      )}
    </div>
  );
}
