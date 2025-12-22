import React from 'react';

/**
 * 显示表单状态控制按钮
 * @param {Object} props
 * @param {Object} props.user - 当前登录用户
 * @param {Object} props.requirement - 当前选中的表单
 * @param {Function} props.updateFormStatus - 改变状态的函数(id, status)
 */
export default function StatusControls({ user, requirement, updateFormStatus }) {
  if (!user || !requirement) return null;

  // 这里可以根据角色决定显示哪些按钮
  const buttons = [
    { label: 'Confirm', status: 'Confirmed' },
    { label: 'Start (20%)', status: 'In Progress', progress: 20 },
    { label: 'Basics Ready (40%)', status: 'In Progress', progress: 40 },
    { label: 'Main Ready (60%)', status: 'In Progress', progress: 60 },
    { label: 'Pending Review (80%)', status: 'In Progress', progress: 80 },
    { label: 'Complete (100%)', status: 'Completed', progress: 100 },
  ];

  return (
    <div className="status-controls">
      {buttons.map((btn) => (
        <button
          key={btn.label}
          onClick={() => updateFormStatus(requirement.id, btn.status)}
        >
          {btn.label}
        </button>
      ))}
    </div>
  );
}
