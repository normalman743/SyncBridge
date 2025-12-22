import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import RequirementDetail from './RequirementDetail';
import StatusControls from './StatusControls';
import CommentBox from './CommentBox';

// mock 子组件，只关注它们是否被调用以及收到的 props
vi.mock('./StatusControls', () => ({
  default: vi.fn(() => <div data-testid="status-controls-mock" />),
}));

vi.mock('./CommentBox', () => ({
  default: vi.fn(() => <div data-testid="comment-box-mock" />),
}));

describe('RequirementDetail component', () => {
  const user = { id: 1, name: 'Tester' };
  const requirement = {
    id: 1,
    title: 'Req Title',
    status: 'open',
    progress: 50,
    description: 'Description',
    functions: 'Some functions',
    performance: 'High performance',
    budget: '$1000',
    expected_time: '2 weeks',
  };

  const messages = [{ id: 1, text: 'msg1' }];
  let comment;
  let setCommentMock;
  let updateFormStatusMock;
  let sendMessageMock;

  beforeEach(() => {
    comment = 'test comment';
    setCommentMock = vi.fn();
    updateFormStatusMock = vi.fn();
    sendMessageMock = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('当没有 requirement 时显示占位信息', () => {
    render(
      <RequirementDetail
        user={user}
        requirement={null}
        messages={messages}
        comment={comment}
        setComment={setCommentMock}
        updateFormStatus={updateFormStatusMock}
        sendMessage={sendMessageMock}
      />,
    );

    expect(
      screen.getByText(
        'Select a requirement to view details and discussion.',
      ),
    ).toBeInTheDocument();

    // 不应渲染子组件
    expect(screen.queryByTestId('status-controls-mock')).toBeNull();
    expect(screen.queryByTestId('comment-box-mock')).toBeNull();
  });

  it('展示 requirement 的基本信息', () => {
    render(
      <RequirementDetail
        user={user}
        requirement={requirement}
        messages={messages}
        comment={comment}
        setComment={setCommentMock}
        updateFormStatus={updateFormStatusMock}
        sendMessage={sendMessageMock}
      />,
    );

    expect(screen.getByText('Req Title')).toBeInTheDocument();
    expect(
      screen.getByText('Status: open \u2022 Progress: 50%'),
    ).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Some functions')).toBeInTheDocument();
    expect(screen.getByText('High performance')).toBeInTheDocument();
    expect(screen.getByText('$1000')).toBeInTheDocument();
    expect(screen.getByText('2 weeks')).toBeInTheDocument();
  });

  it('渲染 StatusControls 并传入正确的 props', () => {
    render(
      <RequirementDetail
        user={user}
        requirement={requirement}
        messages={messages}
        comment={comment}
        setComment={setCommentMock}
        updateFormStatus={updateFormStatusMock}
        sendMessage={sendMessageMock}
      />,
    );

    expect(screen.getByTestId('status-controls-mock')).toBeInTheDocument();

    // 只检查第一个参数（props）是否正确
    expect(StatusControls).toHaveBeenCalledTimes(1);
    const statusControlsProps = StatusControls.mock.calls[0][0];

    expect(statusControlsProps).toEqual({
      user,
      requirement,
      updateFormStatus: updateFormStatusMock,
    });
  });

  it('渲染 CommentBox 并传入正确的 props', () => {
    render(
      <RequirementDetail
        user={user}
        requirement={requirement}
        messages={messages}
        comment={comment}
        setComment={setCommentMock}
        updateFormStatus={updateFormStatusMock}
        sendMessage={sendMessageMock}
      />,
    );

    expect(screen.getByTestId('comment-box-mock')).toBeInTheDocument();

    expect(CommentBox).toHaveBeenCalledTimes(1);
    const commentBoxProps = CommentBox.mock.calls[0][0];

    expect(commentBoxProps.user).toEqual(user);
    expect(commentBoxProps.messages).toEqual(messages);
    expect(commentBoxProps.comment).toBe(comment);
    expect(commentBoxProps.setComment).toBe(setCommentMock);
    expect(typeof commentBoxProps.onSend).toBe('function');
  });

  it('onSend 在 comment 非空时会调用 sendMessage 并清空 comment', () => {
    render(
      <RequirementDetail
        user={user}
        requirement={requirement}
        messages={messages}
        comment={comment}
        setComment={setCommentMock}
        updateFormStatus={updateFormStatusMock}
        sendMessage={sendMessageMock}
      />,
    );

    // 取出传给 CommentBox 的 onSend 回调
    const props = CommentBox.mock.calls[0][0];
    const onSend = props.onSend;

    // 执行 onSend
    onSend();

    expect(sendMessageMock).toHaveBeenCalledWith('test comment');
    expect(setCommentMock).toHaveBeenCalledWith('');
  });

  it('onSend 在 comment 为空或空白时不会调用 sendMessage', () => {
    render(
      <RequirementDetail
        user={user}
        requirement={requirement}
        messages={messages}
        comment="   " // 全是空格
        setComment={setCommentMock}
        updateFormStatus={updateFormStatusMock}
        sendMessage={sendMessageMock}
      />,
    );

    const props = CommentBox.mock.calls[0][0];
    const onSend = props.onSend;

    onSend();

    expect(sendMessageMock).not.toHaveBeenCalled();
    expect(setCommentMock).not.toHaveBeenCalled();
  });
});