const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface ApiError {
  code: string;
  message: string;
  details?: any;
}

export class ApiException extends Error {
  code: string;
  details?: any;
  status: number;

  constructor(status: number, error: ApiError) {
    super(error.message || "An unexpected error occurred");
    this.name = "ApiException";
    this.status = status;
    this.code = error.code || "UNKNOWN_ERROR";
    this.details = error.details;
  }
}

// In-memory token storage with localStorage fallback for page refreshes
let authToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("pf_access_token", token);
    } else {
      localStorage.removeItem("pf_access_token");
    }
  }
};

export const getAuthToken = (): string | null => {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    return localStorage.getItem("pf_access_token");
  }
  return null;
};

interface RequestOptions extends RequestInit {
  skipAuthRefresh?: boolean;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "include", // Required for httpOnly refresh_token cookie
    });

    // 204 No Content
    if (response.status === 204) {
      return null as any;
    }

    // Handle 401 Unauthorized by attempting a token refresh
    if (response.status === 401 && !options.skipAuthRefresh && !endpoint.includes("/auth/")) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        });

        if (refreshResponse.ok) {
          const refreshData = await refreshResponse.json();
          if (refreshData.access_token) {
            setAuthToken(refreshData.access_token);
            // Retry the original request with new token
            headers.set("Authorization", `Bearer ${refreshData.access_token}`);
            return apiRequest<T>(endpoint, {
              ...options,
              headers,
              skipAuthRefresh: true,
            });
          }
        } else {
          // Token refresh failed, clear token
          setAuthToken(null);
        }
      } catch (e) {
        setAuthToken(null);
      }
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errPayload: ApiError = data?.error || {
        code: `HTTP_${response.status}`,
        message: data?.detail || response.statusText || "Request failed",
      };
      throw new ApiException(response.status, errPayload);
    }

    return data as T;
  } catch (error: any) {
    if (error instanceof ApiException) {
      throw error;
    }
    throw new ApiException(500, {
      code: "NETWORK_ERROR",
      message: error.message || "Network error. Please check your connection.",
    });
  }
}

