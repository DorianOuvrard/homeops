// API client with JWT injection

const BASE = "/api/v1";

function getToken(): string | null {
  return localStorage.getItem("hodoor_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("hodoor_token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  timestamp: string;
}

export interface Appliance {
  id: number;
  name: string;
  category: string | null;
  create_date: string | null;
  maintenance_requests: MaintenanceRequest[];
}

export interface MaintenanceRequest {
  id: number;
  name: string;
  description?: string;
  schedule_date?: string;
  maintenance_type?: string;
  state?: string;
}

export interface PushSubscriptionPayload {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

export const api = {
  auth: {
    signup: (email: string, password: string) =>
      request<User>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      request<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<User>("/auth/me"),
  },
  chat: {
    send: (text: string) =>
      request<ChatResponse>("/chat/message", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    sendPhoto: (text: string, photo: File) => {
      const form = new FormData();
      form.append("text", text);
      form.append("photo", photo);
      return request<ChatResponse>("/chat/message/photo", {
        method: "POST",
        body: form,
      });
    },
    history: () => request<ChatMessage[]>("/chat/history"),
    clearHistory: () => request<void>("/chat/history", { method: "DELETE" }),
  },
  appliances: {
    list: () => request<Appliance[]>("/appliances"),
    get: (id: number) => request<Appliance>(`/appliances/${id}`),
    chat: (id: number, text: string) =>
      request<ChatResponse>(`/appliances/${id}/chat`, {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    chatHistory: (id: number) =>
      request<ChatMessage[]>(`/appliances/${id}/chat`),
  },
  push: {
    getVapidPublicKey: () => request<{ public_key: string }>("/push/vapid-public-key"),
    subscribe: (subscription: PushSubscriptionPayload) =>
      request<void>("/push/subscribe", {
        method: "POST",
        body: JSON.stringify(subscription),
      }),
    debug: () =>
      request<{ count: number; endpoints: string[] }>("/push/debug"),
    test: (title: string, body: string) =>
      request<{ queued: number }>("/push/test", {
        method: "POST",
        body: JSON.stringify({ title, body, delay_seconds: 30 }),
      }),
  },
};
