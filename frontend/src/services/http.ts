// Keep UI and API on the same hostname so SameSite cookies work locally.
export const API_BASE_URL = (import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000`).replace(/\/$/, "");
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, {...init, credentials: "include"});
  if (response.status === 401 && !String(input).includes("/auth/")) window.dispatchEvent(new Event("auth-expired"));
  return response;
}
export async function authRequest(path: string, body?: unknown, method = "POST") {
  const response = await apiFetch(`${API_BASE_URL}/auth/${path}`, {method, headers: {"Content-Type": "application/json"}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "Thông tin không hợp lệ. Kiểm tra email và mật khẩu (ít nhất 10 ký tự).";
    throw new Error(response.status === 429 ? "Bạn đã thử quá nhiều lần. Vui lòng chờ và thử lại sau." : detail);
  }
  return data;
}
