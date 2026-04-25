export type UserRole = 'CA_ADMIN' | 'STAFF' | 'CLIENT';

export interface ServiceCatalogPublic {
  id: string;
  service_code: string;
  name: string;
  description: string | null;
  base_fee: string;
  sla_days: number | null;
  is_active: boolean;
}

export interface UserPublic {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: UserPublic;
  tokens: TokenPair;
}

export type TaskStatus =
  | 'TODO'
  | 'IN_PROGRESS'
  | 'COMPLETED_BY_STAFF'
  | 'PENDING_FROM_STAFF'
  | 'UNDER_CA_REVIEW'
  | 'REJECTED_BY_CA'
  | 'APPROVED_BY_CA'
  | 'INVOICED'
  | 'PAYMENT_PENDING'
  | 'PAYMENT_CONFIRMED'
  | 'DOCUMENT_RELEASED'
  | 'CLOSED';

export interface TaskPublic {
  id: string;
  title: string;
  description: string | null;
  client_id: string;
  service_id: string;
  assigned_staff_id: string | null;
  reviewed_by_ca_id: string | null;
  status: TaskStatus;
  priority: string;
  submitted_at: string;
  due_date: string | null;
  staff_completed_at: string | null;
  ca_reviewed_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  payment_confirmed_at: string | null;
  document_released_at: string | null;
  created_at: string;
  updated_at: string;
}

export type InvoiceStatus = 'DRAFT' | 'ISSUED' | 'PARTIALLY_PAID' | 'PAID' | 'VOID' | 'OVERDUE';

export interface InvoicePublic {
  id: string;
  invoice_number: string;
  task_id: string;
  client_id: string;
  issued_by_id: string;
  currency: string;
  sub_total: string;
  tax_total: string;
  discount_total: string;
  total_amount: string;
  amount_paid: string;
  balance_due: string;
  status: InvoiceStatus;
  due_date: string | null;
  issued_at: string | null;
  paid_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type NotificationChannel = 'IN_APP' | 'EMAIL';
export type NotificationStatus = 'PENDING' | 'SENT' | 'FAILED';

export interface NotificationPublic {
  id: string;
  user_id: string;
  task_id: string | null;
  invoice_id: string | null;
  channel: NotificationChannel;
  status: NotificationStatus;
  title: string;
  message: string;
  scheduled_for: string | null;
  sent_at: string | null;
  read_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}
