import { API_URL } from "@/lib/constants";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// A research query can involve translation (NLLB on CPU), Tavily search,
// embedding ranking and answer generation, so 15s aborted almost every
// request before it could finish. Voice endpoints set their own, shorter
// timeouts in voice.ts.
export const DEFAULT_TIMEOUT_MS = 120000

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;

  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs);

  // Honour a caller-supplied signal as well as our own timeout.
  const externalSignal = options.signal
  const onExternalAbort = () => controller.abort()
  externalSignal?.addEventListener("abort", onExternalAbort)

  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `Server error: ${response.status}`;
      try {
        const errorBody = await response.json();
        errorMessage = errorBody.detail || errorBody.message || errorMessage;
      } catch {
        // Fallback if response is not JSON
      }
      throw new ApiError(response.status, errorMessage);
    }

    return response.json() as Promise<T>;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === "AbortError") {
      if (externalSignal?.aborted) {
        throw new ApiError(499, "Request cancelled.");
      }
      if (timedOut) {
        throw new ApiError(408, "Request took too long to respond. The backend might be busy or unavailable.");
      }
      throw new ApiError(408, "Request took too long to respond. The backend might be busy or unavailable.");
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(503, "Unable to connect to the server. Please ensure the backend is running.");
  } finally {
    externalSignal?.removeEventListener("abort", onExternalAbort)
  }
}