import AttachmentPreview from "./AttachmentPreview";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-bubble ${isUser ? "message-user" : "message-assistant"}`}>
      {message.attachments?.length > 0 && (
        <div className="message-attachments">
          {message.attachments.map((a) => (
            <AttachmentPreview key={a.id} attachment={a} />
          ))}
        </div>
      )}
      <div className="message-content">{message.content}</div>
      {!isUser && message.provider_used && (
        <div className="message-attribution">
          {message.provider_used} · {message.model_id_used}
        </div>
      )}
    </div>
  );
}
