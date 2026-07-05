const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

interface FetchOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiClient {
  private accessToken: string | null = null;
  private isRefreshing = false;
  private refreshSubscribers: ((token: string) => void)[] = [];

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  private onAccessTokenFetched(token: string) {
    this.refreshSubscribers.forEach((callback) => callback(token));
    this.refreshSubscribers = [];
  }

  private addRefreshSubscriber(callback: (token: string) => void) {
    this.refreshSubscribers.push(callback);
  }

  async request<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
    const { params, headers, ...customOptions } = options;
    
    // Construct URL with query parameters
    let url = `${API_BASE_URL}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    // Prepare headers
    const requestHeaders: Record<string, string> = {};
    if (!(customOptions.body instanceof FormData)) {
      requestHeaders["Content-Type"] = "application/json";
    }
    if (headers) {
      Object.assign(requestHeaders, headers);
    }

    if (this.accessToken) {
      requestHeaders["Authorization"] = `Bearer ${this.accessToken}`;
    }

    const config: RequestInit = {
      ...customOptions,
      headers: requestHeaders as HeadersInit,
    };

    try {
      const response = await fetch(url, config);

      if (response.status === 401 && endpoint !== "/auth/login" && endpoint !== "/auth/refresh") {
        return this.handleUnauthorized<T>(endpoint, options);
      }

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          errorData = { error: { message: "An unexpected error occurred" } };
        }
        throw new Error(errorData?.error?.message || `HTTP error! status: ${response.status}`);
      }

      if (response.status === 24) {
        return {} as T;
      }

      return (await response.json()) as T;
    } catch (error) {
      logger_error(error);
      throw error;
    }
  }

  private async handleUnauthorized<T>(endpoint: string, options: FetchOptions): Promise<T> {
    if (this.isRefreshing) {
      return new Promise<T>((resolve, reject) => {
        this.addRefreshSubscriber((token) => {
          options.headers = {
            ...options.headers,
            "Authorization": `Bearer ${token}`,
          };
          this.request<T>(endpoint, options).then(resolve).catch(reject);
        });
      });
    }

    this.isRefreshing = true;

    try {
      // Call token refresh endpoint (credentials/cookie-based)
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (!refreshResponse.ok) {
        // Refresh failed, redirect to login unless already on login/register pages
        this.setAccessToken(null);
        if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/register")) {
          window.location.href = "/login?expired=true";
        }
        throw new Error("Session expired. Please log in again.");
      }

      const refreshData = await refreshResponse.json();
      const newAccessToken = refreshData.access_token;
      
      this.setAccessToken(newAccessToken);
      this.onAccessTokenFetched(newAccessToken);
      
      options.headers = {
        ...options.headers,
        "Authorization": `Bearer ${newAccessToken}`,
      };
      
      return this.request<T>(endpoint, options);
    } catch (error) {
      throw error;
    } finally {
      this.isRefreshing = false;
    }
  }

  get<T>(endpoint: string, options?: FetchOptions) {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  post<T>(endpoint: string, body?: any, options?: FetchOptions) {
    const isFormData = body instanceof FormData;
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    });
  }

  patch<T>(endpoint: string, body?: any, options?: FetchOptions) {
    const isFormData = body instanceof FormData;
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    });
  }

  delete<T>(endpoint: string, options?: FetchOptions) {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }
}

function logger_error(error: any) {
  if (process.env.NODE_ENV !== "production") {
    console.error("API request failed:", error);
  }
}

export const apiClient = new ApiClient();
