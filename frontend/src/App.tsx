import { useEffect, useMemo, useState } from 'react';
import type { Dispatch, FormEvent, ReactNode, SetStateAction } from 'react';
import {
  ApiError,
  assignTask,
  createInvoice,
  createTask,
  getInvoices,
  getMe,
  getNotifications,
  getServices,
  getStaffMembers,
  getTasks,
  login,
  probeRoleAccess,
  updateTaskStatus,
} from './api';
import type {
  AuthResponse,
  InvoicePublic,
  NotificationPublic,
  ServiceCatalogPublic,
  TaskPublic,
  TaskStatus,
  UserPublic,
  UserRole,
} from './types';

const STORAGE_KEY = 'ca-firm-frontend.tokens';

type Tokens = {
  accessToken: string;
  refreshToken: string;
};

type AccessScope = 'client' | 'staff' | 'ca' | 'ops';

type AccessProbe = {
  scope: AccessScope;
  label: string;
  status: 'allowed' | 'forbidden' | 'error';
  detail: string;
};

type WorkspaceFormState = {
  clientTask: {
    serviceId: string;
    title: string;
    description: string;
    dueDate: string;
  };
  staffUpdate: {
    taskId: string;
    status: TaskStatus;
    note: string;
  };
  caAssign: {
    taskId: string;
    staffUserId: string;
  };
  invoice: {
    taskId: string;
    subTotal: string;
    taxTotal: string;
    discountTotal: string;
    dueDate: string;
    notes: string;
  };
};

type Metric = {
  label: string;
  value: number;
  tone: 'cyan' | 'gold' | 'violet';
  note: string;
};

type RolePreset = {
  role: UserRole;
  label: string;
  email: string;
  password: string;
  description: string;
  accent: 'cyan' | 'gold' | 'violet';
};

const ROLE_PRESETS: RolePreset[] = [
  {
    role: 'CA_ADMIN',
    label: 'CA Admin',
    email: 'ca.admin@cafirm.local',
    password: 'ChangeMe@123',
    description: 'Assign staff, issue invoices, and release documents.',
    accent: 'cyan',
  },
  {
    role: 'STAFF',
    label: 'Staff',
    email: 'staff1@cafirm.local',
    password: 'ChangeMe@123',
    description: 'Update assigned tasks and coordinate follow-ups.',
    accent: 'gold',
  },
  {
    role: 'CLIENT',
    label: 'Client',
    email: 'client1@cafirm.local',
    password: 'ChangeMe@123',
    description: 'Create a request, track progress, and review invoices.',
    accent: 'violet',
  },
];

const INITIAL_FORM_STATE: WorkspaceFormState = {
  clientTask: {
    serviceId: '',
    title: 'Income tax filing support',
    description: 'Need help preparing and filing the current year return.',
    dueDate: '',
  },
  staffUpdate: {
    taskId: '',
    status: 'IN_PROGRESS',
    note: 'Working through the assigned checklist.',
  },
  caAssign: {
    taskId: '',
    staffUserId: '',
  },
  invoice: {
    taskId: '',
    subTotal: '1500',
    taxTotal: '270',
    discountTotal: '0',
    dueDate: '',
    notes: 'Professional fee for the completed engagement.',
  },
};

function App() {
  const [tokens, setTokens] = useState<Tokens | null>(null);
  const [profile, setProfile] = useState<UserPublic | null>(null);
  const [tasks, setTasks] = useState<TaskPublic[]>([]);
  const [invoices, setInvoices] = useState<InvoicePublic[]>([]);
  const [notifications, setNotifications] = useState<NotificationPublic[]>([]);
  const [services, setServices] = useState<ServiceCatalogPublic[]>([]);
  const [staffMembers, setStaffMembers] = useState<UserPublic[]>([]);
  const [accessMatrix, setAccessMatrix] = useState<AccessProbe[]>([]);
  const [form, setForm] = useState({ email: ROLE_PRESETS[0].email, password: ROLE_PRESETS[0].password });
  const [workspaceForm, setWorkspaceForm] = useState<WorkspaceFormState>(INITIAL_FORM_STATE);
  const [loading, setLoading] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      setLoading(false);
      return;
    }

    try {
      const stored = JSON.parse(raw) as Tokens;
      if (stored.accessToken) {
        setTokens(stored);
        void hydrateWorkspace(stored.accessToken, { initialLoad: true });
        return;
      }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }

    setLoading(false);
  }, []);

  async function hydrateWorkspace(accessToken: string, options: { initialLoad: boolean }) {
    if (options.initialLoad) {
      setLoading(true);
    }
    setDashboardLoading(true);

    try {
      const me = await getMe(accessToken);
      const [taskItems, invoiceItems, notificationItems, serviceItems, accessItems, staffItems] = await Promise.all([
        getTasks(accessToken),
        getInvoices(accessToken),
        getNotifications(accessToken),
        getServices(accessToken),
        probeCurrentRole(accessToken),
        me.role === 'CA_ADMIN' ? getStaffMembers(accessToken) : Promise.resolve([]),
      ]);

      setProfile(me);
      setTasks(taskItems);
      setInvoices(invoiceItems);
      setNotifications(notificationItems);
      setServices(serviceItems);
      setAccessMatrix(accessItems);
      setStaffMembers(staffItems);
      setError(null);
      setStatusMessage(`Signed in as ${me.role.replaceAll('_', ' ').toLowerCase()}`);
      setWorkspaceForm((current) => {
        const nextTaskId = current.clientTask.serviceId || serviceItems[0]?.id || '';
        const nextVisibleTaskId = current.staffUpdate.taskId || taskItems[0]?.id || '';
        return {
          clientTask: {
            ...current.clientTask,
            serviceId: nextTaskId,
          },
          staffUpdate: {
            ...current.staffUpdate,
            taskId: nextVisibleTaskId,
          },
          caAssign: {
            taskId: current.caAssign.taskId || taskItems[0]?.id || '',
            staffUserId: current.caAssign.staffUserId || staffItems[0]?.id || '',
          },
          invoice: {
            ...current.invoice,
            taskId: current.invoice.taskId || taskItems[0]?.id || '',
          },
        };
      });
    } catch (requestError) {
      clearSession();
      setError(normalizeError(requestError));
    } finally {
      if (options.initialLoad) {
        setLoading(false);
      }
      setDashboardLoading(false);
    }
  }

  async function performLogin(email: string, password: string) {
    setAuthLoading(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await login(email, password);
      const nextTokens = serializeTokens(response);
      setTokens(nextTokens);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextTokens));
      setForm({ email, password });
      await hydrateWorkspace(nextTokens.accessToken, { initialLoad: false });
    } catch (requestError) {
      setError(normalizeError(requestError));
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await performLogin(form.email, form.password);
  }

  async function handlePresetLogin(preset: RolePreset) {
    setForm({ email: preset.email, password: preset.password });
    await performLogin(preset.email, preset.password);
  }

  function clearSession() {
    window.localStorage.removeItem(STORAGE_KEY);
    setTokens(null);
    setProfile(null);
    setTasks([]);
    setInvoices([]);
    setNotifications([]);
    setServices([]);
    setStaffMembers([]);
    setAccessMatrix([]);
  }

  function handleLogout() {
    clearSession();
    setError(null);
    setStatusMessage('Session cleared.');
    setLoading(false);
  }

  async function refreshWorkspace() {
    if (!tokens?.accessToken) {
      return;
    }
    await hydrateWorkspace(tokens.accessToken, { initialLoad: false });
  }

  async function handleCreateTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tokens?.accessToken) return;

    try {
      const dueDate = workspaceForm.clientTask.dueDate ? new Date(`${workspaceForm.clientTask.dueDate}T09:00:00`).toISOString() : null;
      await createTask(tokens.accessToken, {
        service_id: workspaceForm.clientTask.serviceId,
        title: workspaceForm.clientTask.title,
        description: workspaceForm.clientTask.description || null,
        due_date: dueDate,
      });
      setStatusMessage('Client request created successfully.');
      await refreshWorkspace();
    } catch (requestError) {
      setError(normalizeError(requestError));
    }
  }

  async function handleAssignTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tokens?.accessToken) return;

    try {
      await assignTask(tokens.accessToken, workspaceForm.caAssign.taskId, workspaceForm.caAssign.staffUserId);
      setStatusMessage('Task assigned to staff member.');
      await refreshWorkspace();
    } catch (requestError) {
      setError(normalizeError(requestError));
    }
  }

  async function handleUpdateStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tokens?.accessToken) return;

    try {
      await updateTaskStatus(
        tokens.accessToken,
        workspaceForm.staffUpdate.taskId,
        workspaceForm.staffUpdate.status,
        workspaceForm.staffUpdate.note || null,
      );
      setStatusMessage('Task status updated by staff.');
      await refreshWorkspace();
    } catch (requestError) {
      setError(normalizeError(requestError));
    }
  }

  async function handleCreateInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tokens?.accessToken) return;

    try {
      const dueDate = workspaceForm.invoice.dueDate ? new Date(`${workspaceForm.invoice.dueDate}T09:00:00`).toISOString() : null;
      await createInvoice(tokens.accessToken, {
        task_id: workspaceForm.invoice.taskId,
        sub_total: workspaceForm.invoice.subTotal,
        tax_total: workspaceForm.invoice.taxTotal,
        discount_total: workspaceForm.invoice.discountTotal,
        due_date: dueDate,
        notes: workspaceForm.invoice.notes || null,
      });
      setStatusMessage('Invoice created by CA admin.');
      await refreshWorkspace();
    } catch (requestError) {
      setError(normalizeError(requestError));
    }
  }

  const metrics = useMemo<Metric[]>(() => {
    const openTasks = tasks.filter((task) => !['CLOSED', 'DOCUMENT_RELEASED'].includes(task.status)).length;
    const pendingInvoices = invoices.filter((invoice) => invoice.balance_due !== '0' && invoice.status !== 'PAID').length;
    const unreadNotifications = notifications.filter((item) => !item.read_at).length;

    return [
      {
        label: 'Visible tasks',
        value: tasks.length,
        tone: 'cyan',
        note: openTasks > 0 ? `${openTasks} still active` : 'No open work at the moment',
      },
      {
        label: 'Outstanding invoices',
        value: pendingInvoices,
        tone: 'gold',
        note: 'Only the client can see their own invoices',
      },
      {
        label: 'Unread notifications',
        value: unreadNotifications,
        tone: 'violet',
        note: 'Fresh notifications stay with the signed-in user',
      },
    ];
  }, [invoices, notifications, tasks]);

  const currentRole = profile?.role ?? null;

  if (loading) {
    return <LoadingScreen />;
  }

  if (profile) {
    return (
      <Dashboard
        profile={profile}
        tokens={tokens}
        metrics={metrics}
        tasks={tasks}
        invoices={invoices}
        notifications={notifications}
        services={services}
        staffMembers={staffMembers}
        accessMatrix={accessMatrix}
        forms={workspaceForm}
        setForms={setWorkspaceForm}
        statusMessage={statusMessage}
        error={error}
        refreshing={dashboardLoading}
        onLogout={handleLogout}
        onCreateTask={handleCreateTask}
        onAssignTask={handleAssignTask}
        onUpdateStatus={handleUpdateStatus}
        onCreateInvoice={handleCreateInvoice}
      />
    );
  }

  return (
    <AuthScreen
      form={form}
      setForm={setForm}
      error={error}
      onSubmit={handleLogin}
      onPresetLogin={handlePresetLogin}
      submitting={authLoading}
      currentRole={currentRole}
    />
  );
}

function AuthScreen(props: {
  form: { email: string; password: string };
  setForm: Dispatch<SetStateAction<{ email: string; password: string }>>;
  error: string | null;
  submitting: boolean;
  currentRole: UserRole | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onPresetLogin: (preset: RolePreset) => Promise<void>;
}) {
  const { form, setForm, error, onSubmit, onPresetLogin, submitting } = props;

  return (
    <main className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      <section className="auth-layout">
        <div className="glass hero-panel">
          <div className="eyebrow">CA Firm Nexus</div>
          <h1>Role-aware workspace for CA admin, staff, and clients.</h1>
          <p>
            Each demo account opens a different surface. Use the quick presets to jump between roles and
            verify that the backend only exposes what that role is allowed to do.
          </p>

          <div className="feature-grid">
            <Feature label="CA admin" value="Assign staff, create invoices, and release documents." />
            <Feature label="Staff" value="Update assigned work and keep the review queue moving." />
            <Feature label="Client" value="Submit requests, view own work, and follow invoice status." />
          </div>

          <div className="preset-grid">
            {ROLE_PRESETS.map((preset) => (
              <button key={preset.role} className={`preset-card preset-${preset.accent}`} type="button" onClick={() => void onPresetLogin(preset)}>
                <span>{preset.label}</span>
                <strong>{preset.email}</strong>
                <small>{preset.description}</small>
              </button>
            ))}
          </div>
        </div>

        <div className="glass auth-panel">
          <div className="panel-header">
            <div>
              <div className="panel-kicker">Sign in</div>
              <h2>Enter the workspace</h2>
            </div>
            <span className="status-pill">Live API</span>
          </div>

          <form className="auth-form" onSubmit={onSubmit}>
            <label>
              <span>Email</span>
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="ca.admin@cafirm.local"
                autoComplete="email"
              />
            </label>

            <label>
              <span>Password</span>
              <input
                type="password"
                value={form.password}
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="ChangeMe@123"
                autoComplete="current-password"
              />
            </label>

            {error ? <div className="error-banner">{error}</div> : null}

            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? 'Signing in...' : 'Enter workspace'}
            </button>

            <div className="hint-box">
              <strong>Quick role test</strong>
              <span>Use the preset buttons to jump into all three roles and see their exact permissions.</span>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
}

function Dashboard(props: {
  profile: UserPublic;
  tokens: Tokens | null;
  metrics: Metric[];
  tasks: TaskPublic[];
  invoices: InvoicePublic[];
  notifications: NotificationPublic[];
  services: ServiceCatalogPublic[];
  staffMembers: UserPublic[];
  accessMatrix: AccessProbe[];
  forms: WorkspaceFormState;
  setForms: Dispatch<SetStateAction<WorkspaceFormState>>;
  statusMessage: string | null;
  error: string | null;
  refreshing: boolean;
  onLogout: () => void;
  onCreateTask: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onAssignTask: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onUpdateStatus: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onCreateInvoice: (event: FormEvent<HTMLFormElement>) => Promise<void>;
}) {
  const {
    accessMatrix,
    error,
    forms,
    invoices,
    metrics,
    notifications,
    onAssignTask,
    onCreateInvoice,
    onCreateTask,
    onLogout,
    onUpdateStatus,
    profile,
    refreshing,
    services,
    setForms,
    staffMembers,
    statusMessage,
    tasks,
    tokens,
  } = props;

  const roleCapabilities = getRoleCapabilities(profile.role);
  const visibleTasks = getVisibleTasksForRole(tasks, profile.role);
  const visibleInvoices = getVisibleInvoicesForRole(invoices, profile.role);
  const visibleNotifications = notifications;

  return (
    <main className="app-shell dashboard-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      <header className="topbar glass">
        <div>
          <div className="eyebrow">CA Firm Nexus</div>
          <div className="topbar-title">Operational command center</div>
        </div>

        <div className="topbar-actions">
          <span className="status-pill">{refreshing ? 'Refreshing' : 'Connected'}</span>
          <span className="status-pill role-pill">{profile.role}</span>
          <button className="ghost-button" type="button" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>

      <section className="dashboard-grid">
        <div className="glass hero-panel hero-panel--wide">
          <div className="panel-header panel-header--stacked">
            <div>
              <div className="panel-kicker">Signed in as</div>
              <h1>{profile.full_name}</h1>
            </div>
            <span className="status-pill role-pill">{profile.role}</span>
          </div>

          <p>
            {profile.email} is connected to the live backend. This view now changes based on role, so CA admin,
            staff, and client sessions only expose the actions they are supposed to use.
          </p>

          <div className="profile-grid">
            <MetricCard label="Account status" value={profile.is_active ? 'Active' : 'Inactive'} note="Current user session" />
            <MetricCard label="Verification" value={profile.is_verified ? 'Verified' : 'Pending'} note="Seeded demo account" />
            <MetricCard label="Access token" value={tokens ? 'Loaded' : 'Missing'} note="Session persisted locally" />
          </div>

          {statusMessage ? <div className="status-banner">{statusMessage}</div> : null}
          {error ? <div className="error-banner">{error}</div> : null}
        </div>

        <aside className="glass side-panel">
          <div className="panel-header">
            <div>
              <div className="panel-kicker">Live snapshot</div>
              <h2>Workspace metrics</h2>
            </div>
          </div>

          <div className="metric-stack">
            {metrics.map((metric) => (
              <MetricRow key={metric.label} metric={metric} />
            ))}
          </div>
        </aside>

        <SectionCard title="Role playbook" subtitle="Only the actions your role is allowed to use" className="action-panel">
          <div className="capability-grid">
            {roleCapabilities.map((item) => (
              <article key={item} className="capability-card">
                {item}
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Permission checks" subtitle="Current token against backend role gates" className="action-panel">
          <div className="access-grid">
            {accessMatrix.map((probe) => (
              <article key={probe.scope} className={`access-card access-${probe.status}`}>
                <strong>{probe.label}</strong>
                <span>{probe.detail}</span>
              </article>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Actions" subtitle="Role-specific commands" className="action-panel">
          {profile.role === 'CLIENT' ? (
            <form className="workspace-form" onSubmit={onCreateTask}>
              <h3>Submit a service request</h3>
              <Field label="Service">
                <select
                  value={forms.clientTask.serviceId}
                  onChange={(event) => setForms((current) => ({ ...current, clientTask: { ...current.clientTask, serviceId: event.target.value } }))}
                >
                  {services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} ({service.service_code})
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Title">
                <input
                  value={forms.clientTask.title}
                  onChange={(event) => setForms((current) => ({ ...current, clientTask: { ...current.clientTask, title: event.target.value } }))}
                  placeholder="Income tax filing support"
                />
              </Field>
              <Field label="Description">
                <textarea
                  value={forms.clientTask.description}
                  onChange={(event) => setForms((current) => ({ ...current, clientTask: { ...current.clientTask, description: event.target.value } }))}
                  rows={4}
                />
              </Field>
              <Field label="Due date">
                <input
                  type="date"
                  value={forms.clientTask.dueDate}
                  onChange={(event) => setForms((current) => ({ ...current, clientTask: { ...current.clientTask, dueDate: event.target.value } }))}
                />
              </Field>
              <button className="primary-button" type="submit">Create request</button>
            </form>
          ) : null}

          {profile.role === 'STAFF' ? (
            <form className="workspace-form" onSubmit={onUpdateStatus}>
              <h3>Update assigned task</h3>
              <Field label="Task">
                <select
                  value={forms.staffUpdate.taskId}
                  onChange={(event) => setForms((current) => ({ ...current, staffUpdate: { ...current.staffUpdate, taskId: event.target.value } }))}
                >
                  {visibleTasks.map((task) => (
                    <option key={task.id} value={task.id}>
                      {task.title} - {task.status}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Status">
                <select
                  value={forms.staffUpdate.status}
                  onChange={(event) => setForms((current) => ({ ...current, staffUpdate: { ...current.staffUpdate, status: event.target.value as TaskStatus } }))}
                >
                  <option value="IN_PROGRESS">In progress</option>
                  <option value="PENDING_FROM_STAFF">Pending from staff</option>
                  <option value="COMPLETED_BY_STAFF">Completed by staff</option>
                </select>
              </Field>
              <Field label="Note">
                <textarea
                  value={forms.staffUpdate.note}
                  onChange={(event) => setForms((current) => ({ ...current, staffUpdate: { ...current.staffUpdate, note: event.target.value } }))}
                  rows={4}
                />
              </Field>
              <button className="primary-button" type="submit">Save status</button>
            </form>
          ) : null}

          {profile.role === 'CA_ADMIN' ? (
            <div className="ca-stack">
              <form className="workspace-form" onSubmit={onAssignTask}>
                <h3>Assign a task to staff</h3>
                <Field label="Task">
                  <select
                    value={forms.caAssign.taskId}
                    onChange={(event) => setForms((current) => ({ ...current, caAssign: { ...current.caAssign, taskId: event.target.value } }))}
                  >
                    {tasks.map((task) => (
                      <option key={task.id} value={task.id}>
                        {task.title} - {task.status}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Staff member">
                  <select
                    value={forms.caAssign.staffUserId}
                    onChange={(event) => setForms((current) => ({ ...current, caAssign: { ...current.caAssign, staffUserId: event.target.value } }))}
                  >
                    {staffMembers.map((staff) => (
                      <option key={staff.id} value={staff.id}>
                        {staff.full_name}
                      </option>
                    ))}
                  </select>
                </Field>
                <button className="primary-button" type="submit">Assign task</button>
              </form>

              <form className="workspace-form" onSubmit={onCreateInvoice}>
                <h3>Create an invoice</h3>
                <Field label="Task">
                  <select
                    value={forms.invoice.taskId}
                    onChange={(event) => setForms((current) => ({ ...current, invoice: { ...current.invoice, taskId: event.target.value } }))}
                  >
                    {tasks.map((task) => (
                      <option key={task.id} value={task.id}>
                        {task.title} - {task.status}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Sub total">
                  <input
                    value={forms.invoice.subTotal}
                    onChange={(event) => setForms((current) => ({ ...current, invoice: { ...current.invoice, subTotal: event.target.value } }))}
                    inputMode="decimal"
                  />
                </Field>
                <Field label="Tax total">
                  <input
                    value={forms.invoice.taxTotal}
                    onChange={(event) => setForms((current) => ({ ...current, invoice: { ...current.invoice, taxTotal: event.target.value } }))}
                    inputMode="decimal"
                  />
                </Field>
                <Field label="Discount total">
                  <input
                    value={forms.invoice.discountTotal}
                    onChange={(event) => setForms((current) => ({ ...current, invoice: { ...current.invoice, discountTotal: event.target.value } }))}
                    inputMode="decimal"
                  />
                </Field>
                <Field label="Due date">
                  <input
                    type="date"
                    value={forms.invoice.dueDate}
                    onChange={(event) => setForms((current) => ({ ...current, invoice: { ...current.invoice, dueDate: event.target.value } }))}
                  />
                </Field>
                <Field label="Notes">
                  <textarea
                    value={forms.invoice.notes}
                    onChange={(event) => setForms((current) => ({ ...current, invoice: { ...current.invoice, notes: event.target.value } }))}
                    rows={4}
                  />
                </Field>
                <button className="primary-button" type="submit">Issue invoice</button>
              </form>
            </div>
          ) : null}
        </SectionCard>

        <SectionCard title="Tasks" subtitle="Visible by current role" className="list-panel">
          <RecordList
            emptyText="No tasks are visible yet. Create one as a client or use the seeded workflow."
            items={visibleTasks.map((task) => (
              <RecordItem
                key={task.id}
                title={task.title}
                meta={task.service_id}
                status={task.status}
                detail={task.description ?? 'No description provided.'}
                secondary={formatDate(task.due_date) ?? 'No due date'}
              />
            ))}
          />
        </SectionCard>

        <SectionCard title="Invoices" subtitle="Role filtered billing view" className="list-panel">
          <RecordList
            emptyText="No invoices are visible for this role yet."
            items={visibleInvoices.map((invoice) => (
              <RecordItem
                key={invoice.id}
                title={invoice.invoice_number}
                meta={invoice.currency}
                status={invoice.status}
                detail={`Balance due ${formatMoney(invoice.balance_due, invoice.currency)}`}
                secondary={`Total ${formatMoney(invoice.total_amount, invoice.currency)}`}
              />
            ))}
          />
        </SectionCard>

        <SectionCard title="Notifications" subtitle="Inbox and activity feed" className="list-panel">
          <RecordList
            emptyText="No notifications are available for this account."
            items={visibleNotifications.map((item) => (
              <RecordItem
                key={item.id}
                title={item.title}
                meta={item.channel}
                status={item.status}
                detail={item.message}
                secondary={formatDate(item.created_at) ?? 'Recently created'}
              />
            ))}
          />
        </SectionCard>
      </section>
    </main>
  );
}

function LoadingScreen() {
  return (
    <main className="app-shell loading-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <div className="glass loading-card">
        <div className="eyebrow">CA Firm Nexus</div>
        <h1>Loading workspace...</h1>
        <p>Booting the secure dashboard and fetching the live API session.</p>
      </div>
    </main>
  );
}

function Feature(props: { label: string; value: string }) {
  return (
    <article className="feature-card">
      <strong>{props.label}</strong>
      <span>{props.value}</span>
    </article>
  );
}

function MetricCard(props: { label: string; value: string; note: string }) {
  return (
    <article className="metric-card">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
      <small>{props.note}</small>
    </article>
  );
}

function MetricRow(props: { metric: Metric }) {
  return (
    <article className={`metric-row tone-${props.metric.tone}`}>
      <div>
        <span>{props.metric.label}</span>
        <strong>{props.metric.value}</strong>
      </div>
      <small>{props.metric.note}</small>
    </article>
  );
}

function SectionCard(props: { title: string; subtitle: string; className?: string; children: ReactNode }) {
  return (
    <section className={`glass section-card ${props.className ?? ''}`}>
      <div className="panel-header">
        <div>
          <div className="panel-kicker">Workspace</div>
          <h2>{props.title}</h2>
        </div>
        <span className="section-subtitle">{props.subtitle}</span>
      </div>
      {props.children}
    </section>
  );
}

function Field(props: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{props.label}</span>
      {props.children}
    </label>
  );
}

function RecordList(props: { emptyText: string; items: ReactNode[] }) {
  if (props.items.length === 0) {
    return <div className="empty-state">{props.emptyText}</div>;
  }

  return <div className="record-list">{props.items}</div>;
}

function RecordItem(props: { title: string; meta: string; status: string; detail: string; secondary: string }) {
  return (
    <article className="record-item">
      <div className="record-item__main">
        <div>
          <strong>{props.title}</strong>
          <span>{props.detail}</span>
        </div>
        <div className="record-item__meta">
          <span>{props.meta}</span>
          <span>{props.secondary}</span>
        </div>
      </div>
      <span className={`badge badge-${badgeTone(props.status)}`}>{props.status}</span>
    </article>
  );
}

function badgeTone(value: string) {
  const normalized = value.toUpperCase();
  if (['PAID', 'APPROVED_BY_CA', 'PAYMENT_CONFIRMED', 'DOCUMENT_RELEASED', 'CLOSED', 'SENT'].includes(normalized)) {
    return 'success';
  }
  if (['ISSUED', 'UNDER_CA_REVIEW', 'IN_PROGRESS', 'PAYMENT_PENDING', 'TODO', 'PENDING_FROM_STAFF'].includes(normalized)) {
    return 'warning';
  }
  if (['FAILED', 'REJECTED_BY_CA', 'VOID', 'CANCELLED'].includes(normalized)) {
    return 'danger';
  }
  return 'neutral';
}

function serializeTokens(response: AuthResponse): Tokens {
  return {
    accessToken: response.tokens.access_token,
    refreshToken: response.tokens.refresh_token,
  };
}

function normalizeError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Unexpected error';
}

function formatMoney(value: string, currency: string) {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return `${currency} ${value}`;
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDate(value: string | null) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function getRoleCapabilities(role: UserRole): string[] {
  if (role === 'CA_ADMIN') {
    return [
      'Assign staff to active work',
      'Issue invoices after approval',
      'Release finalized documents',
      'Read every visible task in the system',
    ];
  }

  if (role === 'STAFF') {
    return [
      'View only assigned tasks',
      'Update task progress for assigned work',
      'Upload staff working/output documents',
      'Send manual reminders to clients',
    ];
  }

  return [
    'Create service requests for your own account',
    'See only your own tasks, invoices, and notifications',
    'Upload client input documents for your tasks',
    'Download released documents after payment and approval',
  ];
}

function getVisibleTasksForRole(tasks: TaskPublic[], role: UserRole): TaskPublic[] {
  if (role === 'CLIENT') {
    return tasks.filter((task) => task.client_id);
  }
  if (role === 'STAFF') {
    return tasks.filter((task) => task.assigned_staff_id);
  }
  return tasks;
}

function getVisibleInvoicesForRole(invoices: InvoicePublic[], role: UserRole): InvoicePublic[] {
  if (role === 'CLIENT') {
    return invoices;
  }
  return invoices;
}

async function probeCurrentRole(accessToken: string): Promise<AccessProbe[]> {
  const scopes: Array<{ scope: AccessScope; label: string }> = [
    { scope: 'client', label: 'Client gate' },
    { scope: 'staff', label: 'Staff gate' },
    { scope: 'ca', label: 'CA admin gate' },
    { scope: 'ops', label: 'CA or staff gate' },
  ];

  const results = await Promise.all(
    scopes.map(async ({ scope, label }) => {
      try {
        await probeRoleAccess(accessToken, scope);
        return { scope, label, status: 'allowed', detail: '200 OK' } as AccessProbe;
      } catch (requestError) {
        if (requestError instanceof ApiError && requestError.status === 403) {
          return { scope, label, status: 'forbidden', detail: '403 Forbidden' } as AccessProbe;
        }
        return { scope, label, status: 'error', detail: normalizeError(requestError) } as AccessProbe;
      }
    }),
  );

  return results;
}

export default App;