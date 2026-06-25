import { useEffect, useState } from "react";
import MessageList from "./MessageList";
import MessageInput from "./MessageInput";
import { createSession, sendChatMessage } from "../api/client";

export default function ChatWindow() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [provider, setProvider] = useState("gemini");
  const [sending, setSending] = useState(false);
  const [initError, setInitError] = useState(null);

  useEffect(() => {
    createSession(provider)
      .then((session) => setSessionId(session.id))
      .catch((err) => setInitError(err.message));
  }, []);

  async function handleSend(content, attachments) {
    const userMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content,
      attachments: attachments.map((a) => ({
        id: a.attachment_id,
        original_filename: a.original_filename,
        kind: a.kind,
        extraction_status: a.extraction_status,
        extraction_error: a.extraction_error,
        extracted_text: a.extracted_text,
      })),
    };
    setMessages((prev) => [...prev, userMessage]);
    setSending(true);

    try {
      const response = await sendChatMessage({
        sessionId,
        content,
        attachmentIds: attachments.map((a) => a.attachment_id),
        provider,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: response.message_id,
          role: "assistant",
          content: response.content,
          provider_used: response.provider_used,
          model_id_used: response.model_id_used,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `⚠️ ${err.message}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  if (initError) {
    return <div className="chat-window chat-error">Failed to start session: {initError}</div>;
  }

  if (!sessionId) {
    return <div className="chat-window chat-loading">Starting session…</div>;
  }

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h1>Maint Chat</h1>
      </header>
      <MessageList messages={messages} />
      <MessageInput
        sessionId={sessionId}
        provider={provider}
        onProviderChange={setProvider}
        onSend={handleSend}
        sending={sending}
      />
    </div>
  );
}
