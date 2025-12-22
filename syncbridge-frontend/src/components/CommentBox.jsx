// src/components/CommentBox.jsx
import React, { useState } from 'react';
import { useMessages } from '../hooks/useMessages';

export default function CommentBox({ formId, functionId = null, nonfunctionId = null }) {
  const {
    messages,
    loading,
    sendMessage,
    uploadFile,
    deleteFile,
    getFile,
  } = useMessages(formId);

  const [text, setText] = useState('');
  const [fileInput, setFileInput] = useState(null);

  const handleSend = async () => {
    if (!text.trim() && !fileInput) return;

    let messageId = null;
    if (text.trim()) {
      messageId = await sendMessage({ text_content: text, function_id: functionId, nonfunction_id: nonfunctionId });
      setText('');
    }

    if (fileInput && messageId) {
      await uploadFile(messageId, fileInput);
      setFileInput(null);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFileInput(e.target.files[0]);
    }
  };

  return (
    <div className="comment-box border rounded p-4 bg-white">
      <div className="messages mb-4 max-h-64 overflow-y-auto">
        {loading ? (
          <p>Loading messages...</p>
        ) : messages.length === 0 ? (
          <p>No messages yet.</p>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="message mb-2 p-2 border-b">
              <div className="flex justify-between items-center">
                <strong>{msg.sender_name}</strong>
                <span className="text-sm text-gray-500">{new Date(msg.created_at).toLocaleString()}</span>
              </div>
              <p>{msg.text_content}</p>
              {msg.files?.length > 0 && (
                <div className="files mt-1">
                  {msg.files.map((f) => (
                    <a
                      key={f.id}
                      href="#"
                      className="text-blue-500 underline mr-2"
                      onClick={async (e) => {
                        e.preventDefault();
                        const fileData = await getFile(f.id);
                        // 简单处理：下载
                        const url = window.URL.createObjectURL(new Blob([fileData.content]));
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = f.filename;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                      }}
                    >
                      {f.filename}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="send-message flex flex-col gap-2">
        <textarea
          className="border rounded p-2 w-full"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type your message..."
        />
        <input type="file" onChange={handleFileChange} />
        <button
          className="bg-blue-500 text-white rounded px-4 py-2"
          onClick={handleSend}
        >
          Send
        </button>
      </div>
    </div>
  );
}
