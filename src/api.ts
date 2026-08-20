function cookie(name: string) {
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1];
}

async function responseBody<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const error = body && typeof body === "object" && "error" in body ? String(body.error) : null;
    throw new Error(error ?? "The Django server did not return a valid response. Make sure it is running.");
  }

  if (body === null) {
    throw new Error("The Django server did not return JSON. Make sure it is running.");
  }

  return body as T;
}

export async function api<T>(url: string, method = "GET", data?: unknown): Promise<T> {
  if (method !== "GET" && !cookie("csrftoken")) await fetch("/api/csrf/", { credentials: "same-origin" });
  const response = await fetch(`/api${url}`, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") || "" },
    body: data ? JSON.stringify(data) : undefined
  });
  return responseBody<T>(response);
}

export async function apiForm<T>(url: string, data: FormData): Promise<T> {
  if (!cookie("csrftoken")) await fetch("/api/csrf/", { credentials: "same-origin" });
  const response = await fetch(`/api${url}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": cookie("csrftoken") || "" },
    body: data
  });
  return responseBody<T>(response);
}
