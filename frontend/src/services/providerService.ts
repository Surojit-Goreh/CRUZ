import type { Provider } from "../types/providers";

const API_BASE = "http://127.0.0.1:8000";

export async function fetchProviders(): Promise<Provider[]> {
  const res = await fetch(`${API_BASE}/providers`);
  if (!res.ok) {
    throw new Error(`Failed to load providers: ${res.statusText}`);
  }
  const data = await res.json();
  return data.providers || [];
}

export async function connectProvider(
  providerId: string,
  apiKey: string,
  accountId?: string,
  model?: string
): Promise<{ connected: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/providers/${providerId}/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: apiKey,
      account_id: accountId,
      model: model,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Connect failed" }));
    throw new Error(err.detail || "Connect failed");
  }
  return res.json();
}

export async function testProviderConnection(
  providerId: string,
  apiKey?: string,
  accountId?: string,
  model?: string
): Promise<{ connected: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/providers/${providerId}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: apiKey,
      account_id: accountId,
      model: model,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Test failed" }));
    throw new Error(err.detail || "Test failed");
  }
  return res.json();
}

export async function fetchProviderModels(
  providerId: string,
  apiKey?: string,
  accountId?: string
): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/providers/${providerId}/models`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: apiKey,
        account_id: accountId,
      }),
    });
    if (!res.ok) {
      return [];
    }
    const data = await res.json();
    return data.models || [];
  } catch (e) {
    console.error(`Failed to fetch models for ${providerId}:`, e);
    return [];
  }
}

export async function disconnectProvider(providerId: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/providers/${providerId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error("Disconnect failed");
  }
  const data = await res.json();
  return data.status === "disconnected";
}
