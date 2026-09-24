// Typed fetch wrapper. Attaches the Bearer token when present and parses
// every failure into the single error envelope shape the backend emits, so
// callers have exactly one error shape to handle regardless of endpoint.

export interface ApiErrorDetail {
  field: string;
  issue: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: ApiErrorDetail[];
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorDetail[];

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? [];
  }
}

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

const BASE_URL = "/api";

async function request<T>(
  method: string,
  path: string,
  options: { body?: unknown; isFormData?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  let body: BodyInit | undefined;
  if (options.isFormData) {
    body = options.body as FormData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${BASE_URL}${path}`, { method, headers, body });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody: ApiErrorBody = payload?.error ?? {
      code: "UNKNOWN_ERROR",
      message: "Something went wrong",
    };
    throw new ApiError(response.status, errorBody);
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>("POST", path, { body: form, isFormData: true }),
};
