// Deepfake Shield API Client Service

const API_BASE = import.meta.env.VITE_API_URL
  ? `${(import.meta.env.VITE_API_URL as string).replace(/\/$/, '')}/api/v1`
  : '/api/v1';

export function getAuthToken(): string | null {
  return localStorage.getItem('dfs_token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('dfs_token', token);
}

export function removeAuthToken() {
  localStorage.removeItem('dfs_token');
  localStorage.removeItem('dfs_user');
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: HeadersInit = {
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  // Do not set Content-Type for FormData (browser sets boundary automatically)
  if (!(options.body instanceof FormData) && !('Content-Type' in headers)) {
    (headers as Record<string, string>)['Content-Type'] = 'application/json';
  }

  let response: Response;
  const targetUrl = `${API_BASE}${endpoint}`;
  try {
    response = await fetch(targetUrl, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      `Unable to connect to Deepfake Shield API at ${API_BASE}. Please verify backend is running.`
    );
  }

  if (!response.ok) {
    if (response.status === 405) {
      throw new Error(
        `HTTP 405 Method Not Allowed: The frontend is currently making requests to "${targetUrl}" (Vercel) instead of your Render backend. Please ensure VITE_API_URL is saved as "Config" in Vercel Settings -> Environment Variables, and redeploy with build cache cleared.`
      );
    }
    let errorDetail = `HTTP error ${response.status}`;
    try {
      const rawText = await response.text();
      try {
        const errorJson = JSON.parse(rawText);
        if (Array.isArray(errorJson.detail)) {
          errorDetail = errorJson.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        } else if (typeof errorJson.detail === 'string') {
          errorDetail = errorJson.detail;
        } else if (errorJson.message) {
          errorDetail = errorJson.message;
        } else if (errorJson.detail) {
          errorDetail = JSON.stringify(errorJson.detail);
        } else {
          errorDetail = rawText || errorDetail;
        }
      } catch {
        errorDetail = rawText || errorDetail;
      }
    } catch (err: any) {
      errorDetail = err.message || errorDetail;
    }

    if (
      response.status === 502 ||
      response.status === 503 ||
      response.status === 504 ||
      (typeof errorDetail === 'string' && errorDetail.includes('ECONNREFUSED'))
    ) {
      errorDetail = 'Backend API is currently offline. Please ensure the FastAPI backend is running on http://localhost:8000.';
    }

    throw new Error(errorDetail || `HTTP error ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// Auth API
export const authApi = {
  login: (credentials: { email: string; password: string }) =>
    request<{ access_token: string; token_type: string; user: any }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }),

  register: (data: { email: string; password: string; full_name: string; role?: string }) =>
    request<{ access_token: string; token_type: string; user: any }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMe: () => request<any>('/auth/me'),

  updateProfile: (data: { full_name?: string; password?: string }) =>
    request<any>('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};

// Scans API
export const scansApi = {
  uploadAndScan: (formData: FormData) =>
    request<any>('/scans/upload', {
      method: 'POST',
      body: formData,
    }),

  scanFromUrl: (data: { url: string; title?: string; scan_type?: string }) =>
    request<any>('/scans/from-url', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  list: (params: { media_type?: string; verdict?: string; search?: string; page?: number; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.media_type) query.set('media_type', params.media_type);
    if (params.verdict) query.set('verdict', params.verdict);
    if (params.search) query.set('search', params.search);
    if (params.page) query.set('page', params.page.toString());
    if (params.limit) query.set('limit', params.limit.toString());
    return request<any>(`/scans/?${query.toString()}`);
  },

  getById: (id: string) => request<any>(`/scans/${id}`),

  getCertificate: (id: string) => request<any>(`/scans/${id}/certificate`),

  delete: (id: string) =>
    request<void>(`/scans/${id}`, {
      method: 'DELETE',
    }),
};

// Analytics API
export const analyticsApi = {
  getOverview: () => request<any>('/analytics/overview'),
};

// Alerts API
export const alertsApi = {
  list: () => request<any[]>('/alerts/'),
  markRead: (id: string) =>
    request<any>(`/alerts/${id}/read`, {
      method: 'PATCH',
    }),
  markAllRead: () =>
    request<{ message: string }>('/alerts/mark-all-read', {
      method: 'POST',
    }),
};

// Audit Logs API
export const auditApi = {
  list: (limit = 50) => request<any[]>(`/audit/?limit=${limit}`),
};

// Dedicated Audio Deepfake Forensics API
export const audioApi = {
  analyze: (formData: FormData) =>
    request<any>('/audio/analyze', {
      method: 'POST',
      body: formData,
    }),
};

// Dedicated Video Deepfake Forensics API
export const videoApi = {
  analyze: (formData: FormData) =>
    request<any>('/video/analyze', {
      method: 'POST',
      body: formData,
    }),
};

// Multimodal Risk Assessment API
export const multimodalApi = {
  analyze: (formData: FormData) =>
    request<any>('/multimodal/analyze', {
      method: 'POST',
      body: formData,
    }),
  fuse: (data: { audio_result?: any; video_result?: any }) =>
    request<any>('/multimodal/fuse', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Hugging Face Dataset Intelligence API
export const huggingFaceApi = {
  getStatus: (dataset?: string) => {
    const q = dataset ? `?dataset=${encodeURIComponent(dataset)}` : '';
    return request<any>(`/huggingface/status${q}`);
  },

  getMetadata: (dataset?: string) => {
    const q = dataset ? `?dataset=${encodeURIComponent(dataset)}` : '';
    return request<any>(`/huggingface/metadata${q}`);
  },

  getSplits: (dataset?: string) => {
    const q = dataset ? `?dataset=${encodeURIComponent(dataset)}` : '';
    return request<any>(`/huggingface/splits${q}`);
  },

  getParquet: (params: { dataset?: string; config?: string; split?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.dataset) query.set('dataset', params.dataset);
    if (params.config) query.set('config', params.config);
    if (params.split) query.set('split', params.split);
    return request<any>(`/huggingface/parquet?${query.toString()}`);
  },

  getRows: (params: { dataset?: string; config?: string; split?: string; offset?: number; length?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.dataset) query.set('dataset', params.dataset);
    if (params.config) query.set('config', params.config);
    if (params.split) query.set('split', params.split);
    if (params.offset !== undefined) query.set('offset', params.offset.toString());
    if (params.length !== undefined) query.set('length', params.length.toString());
    return request<any>(`/huggingface/rows?${query.toString()}`);
  },

  syncMetadata: (dataset?: string) => {
    const q = dataset ? `?dataset=${encodeURIComponent(dataset)}` : '';
    return request<any>(`/huggingface/sync${q}`, {
      method: 'POST',
    });
  },
};

// Data Retention & Lifecycle Governance API
export const retentionApi = {
  getStatus: (days?: number) => {
    const q = days ? `?days=${days}` : '';
    return request<any>(`/retention/status${q}`);
  },
  purgeExpired: (retentionDays: number = 30) =>
    request<any>(`/retention/purge?retention_days=${retentionDays}`, {
      method: 'POST',
    }),
};

// Model Evaluation Benchmark API
export const evaluationApi = {
  getMetrics: () => request<any>('/analytics/evaluation-metrics'),
};

