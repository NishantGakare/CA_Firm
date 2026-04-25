import type {
  AuthResponse,
  InvoicePublic,
  NotificationPublic,
  ServiceCatalogPublic,
  TaskPublic,
  TaskStatus,
  UserPublic,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function extractDetail(payload: unknown): string {
  if (typeof payload === 'string') {
    return payload;
  }

  if (payload && typeof payload === 'object') {
    const typed = payload as { detail?: unknown; message?: unknown };
    if (typeof typed.message === 'string') {
      return typed.message;
    }
    if (typeof typed.detail === 'string') {
      return typed.detail;
    }
    if (Array.isArray(typed.detail) && typed.detail.length > 0) {
      const first = typed.detail[0] as { msg?: string };
      if (typeof first.msg === 'string') {
        return first.msg;
      }
    }
  }

  return 'Request failed';
}

async function request<T>(path: string, token?: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('accept', 'application/json');

  if (init.body && !headers.has('content-type')) {
    headers.set('content-type', 'application/json');
  }

  if (token) {
    headers.set('authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  const payload = await parseJson(response);
  if (!response.ok) {
    throw new ApiError(extractDetail(payload), response.status);
  }

  return payload as T;
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', undefined, {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(token: string): Promise<UserPublic> {
  return request<UserPublic>('/auth/me', token);
}

export function getTasks(token: string): Promise<TaskPublic[]> {
  return request<TaskPublic[]>('/tasks', token);
}

export function getInvoices(token: string): Promise<InvoicePublic[]> {
  return request<InvoicePublic[]>('/invoices', token);
}

export function getNotifications(token: string): Promise<NotificationPublic[]> {
  return request<NotificationPublic[]>('/notifications/me', token);
}

export function getServices(token: string): Promise<ServiceCatalogPublic[]> {
  return request<ServiceCatalogPublic[]>('/catalog/services', token);
}

export function getStaffMembers(token: string): Promise<UserPublic[]> {
  return request<UserPublic[]>('/catalog/staff', token);
}

export function probeRoleAccess(token: string, scope: 'client' | 'staff' | 'ca' | 'ops'): Promise<UserPublic> {
  return request<UserPublic>(`/auth/rbac/${scope}`, token);
}

export function createTask(
  token: string,
  payload: { service_id: string; title: string; description?: string | null; due_date?: string | null },
): Promise<TaskPublic> {
  return request<TaskPublic>('/tasks', token, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function assignTask(token: string, taskId: string, staffUserId: string): Promise<TaskPublic> {
  return request<TaskPublic>(`/tasks/${taskId}/assign`, token, {
    method: 'POST',
    body: JSON.stringify({ staff_user_id: staffUserId }),
  });
}

export function updateTaskStatus(
  token: string,
  taskId: string,
  status: TaskStatus,
  note?: string | null,
): Promise<TaskPublic> {
  return request<TaskPublic>(`/tasks/${taskId}/staff-status`, token, {
    method: 'POST',
    body: JSON.stringify({ status, note }),
  });
}

export function createInvoice(
  token: string,
  payload: {
    task_id: string;
    sub_total: string;
    tax_total?: string;
    discount_total?: string;
    due_date?: string | null;
    notes?: string | null;
  },
): Promise<InvoicePublic> {
  return request<InvoicePublic>('/invoices', token, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
