import { useState } from "react";
import FileUploadButton from "./FileUploadButton";
import AttachmentPreview from "./AttachmentPreview";
import ProviderSwitcher from "./ProviderSwitcher";
import { uploadAttachment } from "../api/client";

export default function MessageInput({ sessionId, provider, onProviderChange, onSend, sending }) {
  const [text, setText] = useState("");
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [uploading, setUploading] = useState(false);

  async function handleFileSelect(file) {
    setUploading(true);
    try {
      const result = await uploadAttachment(sessionId, file);
      setPendingAttachments((prev) => [...prev, result]);
    } catch (err) {
      setPendingAttachments((prev) => [
        ...prev,
        {
          attachment_id: `error-${Date.now()}`,
          original_filename: file.name,
          kind: "unknown",
          extraction_status: "failed",
          extraction_error: err.message,
          extracted_text: null,
        },
      ]);
    } finally {
      setUploading(false);
    }
  }

  function removeAttachment(attachmentId) {
    setPendingAttachments((prev) => prev.filter((a) => a.attachment_id !== attachmentId));
  }

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    const usableAttachments = pendingAttachments.filter((a) => a.extraction_status === "success");
    onSend(trimmed, usableAttachments);
    setText("");
    setPendingAttachments([]);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="message-input">
      {pendingAttachments.length > 0 && (
        <div className="pending-attachments">
          {pendingAttachments.map((a) => (
            <AttachmentPreview
              key={a.attachment_id}
              attachment={{ ...a, id: a.attachment_id }}
              onRemove={() => removeAttachment(a.attachment_id)}
            />
          ))}
        </div>
      )}
      <div className="message-input-row">
        <ProviderSwitcher provider={provider} onChange={onProviderChange} disabled={sending} />
        <FileUploadButton onSelect={handleFileSelect} disabled={uploading || sending} />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your data…"
          disabled={sending}
          rows={1}
        />
        <button
          type="button"
          className="send-button"
          onClick={handleSend}
          disabled={sending || uploading || !text.trim()}
        >
          {sending ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
