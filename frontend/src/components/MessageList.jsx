import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list message-list-empty">
        <p>Start a conversation. Attach an image for context.</p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
