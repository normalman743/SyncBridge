import React, { useState, useEffect } from 'react';
import './index.css';

import { useAuth } from './hooks/useAuth';
import { useForm } from './hooks/useForm';
import { useMessages } from './hooks/useMessages';

import RequirementList from './components/RequirementList';
import RequirementDetail from './components/RequirementDetail';
import Sidebar from './components/Sidebar';
import StatusControls from './components/StatusControls';

export default function App() {
  const { user, login, register, logout } = useAuth();
  const {
    forms,
    selectedForm,
    loadForms,
    loadFormById,
    createForm,
    modifyForm,
    removeForm,
    changeFormStatus
  } = useForm();

  const { messages, sendMessage, fetchMessages } = useMessages(selectedForm?.id);

  const [comment, setComment] = useState('');

  // 初次加载表单列表
  useEffect(() => {
    if (user) loadForms();
  }, [user, loadForms]);

  // 当选中表单变化时，拉取消息
  useEffect(() => {
    if (selectedForm?.id) {
      fetchMessages(selectedForm.id);
    }
  }, [selectedForm, fetchMessages]);

  return (
    <div className="app">
      <aside className="sidebar">
        <Sidebar
          user={user}
          login={login}
          register={register}
          logout={logout}
          forms={forms}
          selectedForm={selectedForm}
          onSelect={loadFormById}
          onDelete={removeForm}
          onRefresh={loadForms}
        />
      </aside>

      <main className="main">
        <RequirementDetail
          user={user}
          requirement={selectedForm}
          messages={messages}
          comment={comment}
          setComment={setComment}
          updateFormStatus={changeFormStatus}
          sendMessage={(text) =>
            sendMessage({
              form_id: selectedForm.id,
              text_content: text
            })
          }
        />
      </main>
    </div>
  );
}
