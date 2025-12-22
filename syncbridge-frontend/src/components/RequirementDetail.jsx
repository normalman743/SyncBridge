import React, { useState } from 'react';
import StatusControls from './StatusControls';
import CommentBox from './CommentBox';

export default function RequirementDetail({
  user,
  requirement,
  messages,
  comment,
  setComment,
  updateFormStatus,
  sendMessage
}) {
  if (!requirement) {
    return <div className="placeholder">Select a requirement to view details and discussion.</div>;
  }

  return (
    <div>
      <h2>{requirement.title}</h2>
      <div className="meta">
        Status: {requirement.status} • Progress: {requirement.progress}%
      </div>
      <p>{requirement.description}</p>
      <p>{requirement.functions}</p>
      <p>{requirement.performance}</p>
      <p>{requirement.budget}</p>
      <p>{requirement.expected_time}</p>

      {/* 状态控制按钮 */}
      <StatusControls
        user={user}
        requirement={requirement}
        updateFormStatus={updateFormStatus}
      />

      <hr />

      {/* 消息区 */}
      <CommentBox
        user={user}
        messages={messages}
        comment={comment}
        setComment={setComment}
        onSend={() => {
          if (!comment.trim()) return;
          sendMessage(comment.trim());
          setComment('');
        }}
      />
    </div>
  );
}
