const BASE_URL = "http://localhost:8000/api";

async function asJson(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${response.status}`);
  }
  return response.json();
}

export function createSession(defaultProvider) {
  return fetch(`${BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ default_provider: defaultProvider || null }),
  }).then(asJson);
}

export function getSession(sessionId) {
  return fetch(`${BASE_URL}/sessions/${sessionId}`).then(asJson);
}

export function uploadAttachment(sessionId, file) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", file);
  return fetch(`${BASE_URL}/upload`, { method: "POST", body: formData }).then(asJson);
}

export function sendChatMessage({ sessionId, content, attachmentIds, provider }) {
  return fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      content,
      attachment_ids: attachmentIds,
      provider,
    }),
  }).then(asJson);
}
