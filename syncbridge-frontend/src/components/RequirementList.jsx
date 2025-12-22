// src/components/RequirementList.jsx
import React, { useEffect } from 'react';
import { useForm } from '../hooks/useForm';

export default function RequirementList({ onSelect }) {
  const {
    requirements,       // 表单列表
    selectedReq,        // 当前选中的表单
    fetchForms,         // 获取表单列表
    setSelectedReq,     // 设置选中表单
    loading,
  } = useForm();

  // 初始化拉取表单列表
  useEffect(() => {
    fetchForms();
  }, []);

  const handleSelect = (req) => {
    setSelectedReq(req);
    if (onSelect) onSelect(req);
  };

  return (
    <div className="requirement-list border-r w-64 h-full overflow-y-auto bg-gray-50">
      <h2 className="text-lg font-bold p-4 border-b">需求列表</h2>

      {loading ? (
        <p className="p-4">Loading...</p>
      ) : requirements.length === 0 ? (
        <p className="p-4 text-gray-500">No forms available</p>
      ) : (
        <ul>
          {requirements.map((req) => (
            <li
              key={req.id}
              className={`cursor-pointer p-3 border-b hover:bg-gray-100 ${
                selectedReq?.id === req.id ? 'bg-blue-100 font-semibold' : ''
              }`}
              onClick={() => handleSelect(req)}
            >
              <div className="flex justify-between items-center">
                <span>{req.title}</span>
                <span className="text-sm text-gray-500">{req.status}</span>
              </div>
              <p className="text-sm text-gray-600 truncate">{req.message}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
