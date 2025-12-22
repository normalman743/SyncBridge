import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StatusControls from './StatusControls';

describe('StatusControls component', () => {
  const user = { id: 1, username: 'dev', role: 'developer' };
  const requirement = { id: 42, title: 'Test requirement' };

  const buttonsConfig = [
    { label: 'Confirm', status: 'Confirmed' },
    { label: 'Start (20%)', status: 'In Progress' },
    { label: 'Basics Ready (40%)', status: 'In Progress' },
    { label: 'Main Ready (60%)', status: 'In Progress' },
    { label: 'Pending Review (80%)', status: 'In Progress' },
    { label: 'Complete (100%)', status: 'Completed' },
  ];

  it('当没有 user 时不渲染任何内容', () => {
    const { container } = render(
      <StatusControls
        user={null}
        requirement={requirement}
        updateFormStatus={vi.fn()}
      />,
    );

    // 组件直接 return null，容器中不会有 status-controls 的内容
    expect(container.firstChild).toBeNull();
  });

  it('当没有 requirement 时不渲染任何内容', () => {
    const { container } = render(
      <StatusControls
        user={user}
        requirement={null}
        updateFormStatus={vi.fn()}
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it('渲染所有状态按钮，文本正确', () => {
    const updateFormStatusMock = vi.fn();

    render(
      <StatusControls
        user={user}
        requirement={requirement}
        updateFormStatus={updateFormStatusMock}
      />,
    );

    // 6 个按钮都应该出现
    buttonsConfig.forEach((btn) => {
      expect(screen.getByText(btn.label)).toBeInTheDocument();
    });
  });

  it('点击按钮时调用 updateFormStatus，参数为 (requirement.id, 对应status)', () => {
    const updateFormStatusMock = vi.fn();

    render(
      <StatusControls
        user={user}
        requirement={requirement}
        updateFormStatus={updateFormStatusMock}
      />,
    );

    buttonsConfig.forEach((btn) => {
      const button = screen.getByText(btn.label);
      fireEvent.click(button);
      // 每点一次，多一次调用
    });

    expect(updateFormStatusMock).toHaveBeenCalledTimes(buttonsConfig.length);

    // 逐个检查调用参数
    buttonsConfig.forEach((btn, index) => {
      expect(updateFormStatusMock).toHaveBeenNthCalledWith(
        index + 1,
        requirement.id,
        btn.status,
      );
    });
  });
});