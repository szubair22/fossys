/**
 * OrgMeet API Client
 *
 * Centralized API layer replacing PocketBase usage.
 * Provides domain-specific APIs and core request helpers.
 */
(function() {
  const BASE_COLLECTIONS = '/api/collections';
  const BASE_V1 = '/api/v1';
  const TOKEN_KEY = 'orgmeet_token';
  const USER_KEY = 'orgmeet_user';
  const ORG_KEY = 'orgmeet_current_org';

  // ========================================
  // TOKEN & SESSION MANAGEMENT
  // ========================================

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
  function clearToken() { localStorage.removeItem(TOKEN_KEY); }

  function getStoredUser() {
    try {
      const data = localStorage.getItem(USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch { return null; }
  }
  function setStoredUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function clearStoredUser() { localStorage.removeItem(USER_KEY); }

  function getCurrentOrgId() { return localStorage.getItem(ORG_KEY); }
  function setCurrentOrgId(id) { localStorage.setItem(ORG_KEY, id); }
  function clearCurrentOrgId() { localStorage.removeItem(ORG_KEY); }

  // ========================================
  // CORE REQUEST HELPER
  // ========================================

  /**
   * Core fetch wrapper with auth, error handling, and JSON support
   * @param {string} method - HTTP method
   * @param {string} url - Request URL
   * @param {Object} options - { body, params, headers, raw }
   * @returns {Promise<any>}
   */
  async function request(method, url, options = {}) {
    const headers = { ...options.headers };

    // Handle body serialization
    let body = options.body;
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
      if (typeof body === 'object') {
        body = JSON.stringify(body);
      }
    }

    // Add auth token
    const token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;

    // Build URL with query params
    let fullUrl = url;
    if (options.params) {
      const searchParams = new URLSearchParams();
      Object.entries(options.params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          searchParams.set(k, v);
        }
      });
      const qs = searchParams.toString();
      if (qs) fullUrl += (url.includes('?') ? '&' : '?') + qs;
    }

    const resp = await fetch(fullUrl, { method, headers, body });

    // Handle errors
    if (!resp.ok) {
      let detail;
      try { detail = await resp.json(); } catch (_) { detail = { message: resp.statusText }; }
      // Extract error message, handling nested objects and arrays
      let errorMsg = 'Request failed';
      if (detail?.detail) {
        if (typeof detail.detail === 'string') {
          errorMsg = detail.detail;
        } else if (Array.isArray(detail.detail)) {
          // FastAPI validation errors: [{loc: [...], msg: "...", type: "..."}]
          errorMsg = detail.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('; ');
        } else if (typeof detail.detail === 'object') {
          // Object detail - try common patterns
          errorMsg = detail.detail.message || detail.detail.msg || JSON.stringify(detail.detail);
        }
      } else if (detail?.message) {
        errorMsg = typeof detail.message === 'string' ? detail.message : JSON.stringify(detail.message);
      } else if (detail?.error) {
        errorMsg = typeof detail.error === 'string' ? detail.error : JSON.stringify(detail.error);
      }
      const err = new Error(errorMsg);
      err.data = detail;
      err.status = resp.status;
      throw err;
    }

    // Return raw response if requested (for downloads, etc.)
    if (options.raw) return resp;

    // Parse JSON or return response
    const ct = resp.headers.get('Content-Type') || '';
    if (ct.includes('application/json')) return resp.json();
    if (resp.status === 204) return null;
    return resp;
  }

  // Convenience methods
  const get = (url, params) => request('GET', url, { params });
  const post = (url, body, options = {}) => request('POST', url, { body, ...options });
  const patch = (url, body) => request('PATCH', url, { body });
  const put = (url, body) => request('PUT', url, { body });
  const del = (url, body) => request('DELETE', url, { body });

  // Legacy jsonFetch for backward compatibility
  async function jsonFetch(url, options = {}) {
    return request(options.method || 'GET', url, {
      body: options.body,
      headers: options.headers,
      raw: options.raw
    });
  }

  // ========================================
  // AUTHENTICATION
  // ========================================

  async function login(email, password) {
    const data = await post(`${BASE_COLLECTIONS}/users/auth-with-password`, {
      identity: email,
      password
    });
    setToken(data.token);
    setStoredUser(data.record);
    return data.record;
  }

  async function register(name, email, password, passwordConfirm) {
    const record = await post(`${BASE_COLLECTIONS}/users/records`, {
      name, email, password, passwordConfirm
    });
    // Auto-login
    await login(email, password);
    return record;
  }

  async function authRefresh() {
    const data = await post(`${BASE_COLLECTIONS}/users/auth-refresh`);
    setToken(data.token);
    setStoredUser(data.record);
    return data.record;
  }

  async function getCurrentUser() {
    // Return cached user if available
    const cached = getStoredUser();
    if (cached) return cached;

    const token = getToken();
    if (!token) return null;
    try { return await authRefresh(); } catch { return null; }
  }

  async function updateCurrentUserProfile(userId, payload) {
    const user = await patch(`${BASE_COLLECTIONS}/users/records/${userId}`, payload);
    setStoredUser(user);
    return user;
  }

  async function changePassword(userId, oldPassword, password, passwordConfirm) {
    return post(`${BASE_COLLECTIONS}/users/records/${userId}/change-password`, {
      oldPassword, password, passwordConfirm
    });
  }

  function logout() {
    clearToken();
    clearStoredUser();
    clearCurrentOrgId();
  }

  // ========================================
  // ROLE & PERMISSION HELPERS
  // ========================================

  // Cache for org memberships
  let orgMembershipsCache = null;
  let orgMembershipsCacheTime = 0;
  const CACHE_TTL = 60000; // 1 minute

  /**
   * Get current user's role in an organization
   * @param {string} orgId - Organization ID (uses current org if not provided)
   * @returns {Promise<string|null>} Role: 'owner', 'admin', 'member', 'viewer', or null
   */
  async function getUserRole(orgId) {
    const targetOrgId = orgId || getCurrentOrgId();
    if (!targetOrgId) return null;

    const user = await getCurrentUser();
    if (!user) return null;

    // Check cache validity
    const now = Date.now();
    if (!orgMembershipsCache || (now - orgMembershipsCacheTime) > CACHE_TTL) {
      try {
        // Use the correct governance endpoint for user's memberships
        const resp = await get(`${BASE_V1}/governance/org-memberships/my`);
        orgMembershipsCache = resp.items || resp;
        orgMembershipsCacheTime = now;
      } catch {
        return null;
      }
    }

    const membership = orgMembershipsCache.find(m => m.organization_id === targetOrgId);
    return membership?.role || null;
  }

  /**
   * Check if user has at least the specified role
   * @param {string} minRole - Minimum role required: 'viewer', 'member', 'admin', 'owner'
   * @param {string} orgId - Organization ID (uses current org if not provided)
   * @returns {Promise<boolean>}
   */
  async function hasMinRole(minRole, orgId) {
    const roleHierarchy = ['viewer', 'member', 'admin', 'owner'];
    const userRole = await getUserRole(orgId);
    if (!userRole) return false;

    const userLevel = roleHierarchy.indexOf(userRole);
    const requiredLevel = roleHierarchy.indexOf(minRole);
    return userLevel >= requiredLevel;
  }

  /**
   * Check if user is admin or owner
   * @param {string} orgId - Organization ID (uses current org if not provided)
   * @returns {Promise<boolean>}
   */
  async function isAdmin(orgId) {
    return hasMinRole('admin', orgId);
  }

  /**
   * Check if user is owner
   * @param {string} orgId - Organization ID (uses current org if not provided)
   * @returns {Promise<boolean>}
   */
  async function isOwner(orgId) {
    return hasMinRole('owner', orgId);
  }

  /**
   * Clear role cache (call after org switch or membership changes)
   */
  function clearRoleCache() {
    orgMembershipsCache = null;
    orgMembershipsCacheTime = 0;
  }

  // ========================================
  // FILES DOMAIN
  // ========================================

  async function listFiles(filter) {
    return get(`${BASE_COLLECTIONS}/files/records`, { filter });
  }

  async function uploadFile(formData) {
    return post(`${BASE_COLLECTIONS}/files/records`, formData);
  }

  async function getFile(id) {
    return get(`${BASE_COLLECTIONS}/files/records/${id}`);
  }

  async function deleteFile(id) {
    return del(`${BASE_COLLECTIONS}/files/records/${id}`);
  }

  // ========================================
  // EXPORT API OBJECT
  // ========================================

  window.API = {
    // Core request helpers
    request,
    get,
    post,
    patch,
    put,
    del,

    // Authentication
    auth: {
      login,
      register,
      refresh: authRefresh,
      getCurrentUser,
      updateCurrentUserProfile,
      changePassword,
      logout,
      isLoggedIn: () => !!getToken(),
      getToken,
      getStoredUser
    },

    // Role & Permission helpers
    roles: {
      getUserRole,
      hasMinRole,
      isAdmin,
      isOwner,
      clearCache: clearRoleCache
    },

    // Organization context
    org: {
      getCurrentId: getCurrentOrgId,
      setCurrentId: (id) => {
        setCurrentOrgId(id);
        clearRoleCache();
      },
      clearCurrentId: () => {
        clearCurrentOrgId();
        clearRoleCache();
      }
    },

    // Files domain
    files: {
      list: listFiles,
      get: getFile,
      upload: uploadFile,
      delete: deleteFile,
      // Legacy aliases
      listFiles,
      uploadFile,
      getFile,
      deleteFile
    },

    // AI Integrations domain
    ai_integrations: {
      list: (params) => get(`${BASE_COLLECTIONS}/ai_integrations/records`, params),
      get: (id) => get(`${BASE_COLLECTIONS}/ai_integrations/records/${id}`),
      create: (payload) => post(`${BASE_COLLECTIONS}/ai_integrations/records`, payload),
      update: (id, payload) => patch(`${BASE_COLLECTIONS}/ai_integrations/records/${id}`, payload),
      delete: (id) => del(`${BASE_COLLECTIONS}/ai_integrations/records/${id}`)
    },

    // Recordings domain
    recordings: {
      list: (params = {}) => get(`${BASE_COLLECTIONS}/recordings/records`, {
        page: 1,
        perPage: 50,
        sort: '-recording_date',
        ...params
      }),
      get: (id) => get(`${BASE_COLLECTIONS}/recordings/records/${id}`),
      create: (payload) => post(`${BASE_COLLECTIONS}/recordings/records`, payload),
      update: (id, payload) => patch(`${BASE_COLLECTIONS}/recordings/records/${id}`, payload),
      delete: (id) => del(`${BASE_COLLECTIONS}/recordings/records/${id}`)
    },

    // Meeting Notifications domain
    meeting_notifications: {
      list: (params) => get(`${BASE_COLLECTIONS}/meeting_notifications/records`, params),
      create: (payload) => post(`${BASE_COLLECTIONS}/meeting_notifications/records`, payload),
      update: (id, payload) => patch(`${BASE_COLLECTIONS}/meeting_notifications/records/${id}`, payload),
      delete: (id) => del(`${BASE_COLLECTIONS}/meeting_notifications/records/${id}`)
    },

    // Meetings (legacy PB-style)
    meetings: {
      list: (params = {}) => get(`${BASE_COLLECTIONS}/meetings/records`, {
        page: 1,
        perPage: 100,
        sort: '-start_time',
        ...params
      })
    },

    // Organizations domain - use v1 API which returns user_role
    organizations: {
      list: (page = 1, perPage = 50) => get(`${BASE_V1}/organizations`, {
        page,
        perPage
      }),
      get: (id) => get(`${BASE_COLLECTIONS}/organizations/records/${id}`),
      create: (payload) => post(`${BASE_COLLECTIONS}/organizations/records`, payload),
      update: (id, payload) => patch(`${BASE_COLLECTIONS}/organizations/records/${id}`, payload),
      delete: (id) => del(`${BASE_COLLECTIONS}/organizations/records/${id}`)
    },

    // Governance domain (FastAPI v1)
    governance: {
      meetings: {
        list: (params = {}) => get(`${BASE_V1}/governance/meetings`, params),
        get: (id) => get(`${BASE_V1}/governance/meetings/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/meetings`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/meetings/${id}`, payload),
        close: (id) => post(`${BASE_V1}/governance/meetings/${id}/close`),
        delete: (id) => del(`${BASE_V1}/governance/meetings/${id}`)
      },
      agenda: {
        list: (meeting_id) => get(`${BASE_V1}/governance/agenda-items`, { meeting_id }),
        get: (id) => get(`${BASE_V1}/governance/agenda-items/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/agenda-items`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/agenda-items/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/agenda-items/${id}`)
      },
      motions: {
        list: (meeting_id) => get(`${BASE_V1}/governance/motions`, { meeting_id }),
        get: (id) => get(`${BASE_V1}/governance/motions/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/motions`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/motions/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/motions/${id}`)
      },
      polls: {
        list: (meeting_id) => get(`${BASE_V1}/governance/polls`, { meeting_id }),
        get: (id) => get(`${BASE_V1}/governance/polls/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/polls`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/polls/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/polls/${id}`),
        open: (id) => post(`${BASE_V1}/governance/polls/${id}/open`),
        close: (id) => post(`${BASE_V1}/governance/polls/${id}/close`),
        results: (id) => get(`${BASE_V1}/governance/polls/${id}/results`)
      },
      motionTransitions: {
        list: (motion_id) => get(`${BASE_V1}/governance/motions/${motion_id}/transitions`),
        transition: (motion_id, new_state) => post(`${BASE_V1}/governance/motions/${motion_id}/transition`, null, { params: { new_state } })
      },
      templates: {
        list: (params) => get(`${BASE_V1}/governance/templates`, params),
        get: (id) => get(`${BASE_V1}/governance/templates/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/templates`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/templates/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/templates/${id}`)
      },
      minutes: {
        list: (meeting_id) => get(`${BASE_V1}/governance/minutes`, { meeting_id }),
        get: (id) => get(`${BASE_V1}/governance/minutes/${id}`),
        getByMeeting: (meeting_id) => get(`${BASE_V1}/governance/minutes/by-meeting/${meeting_id}`),
        create: (payload) => post(`${BASE_V1}/governance/minutes`, payload),
        upsert: (payload) => post(`${BASE_V1}/governance/minutes/upsert`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/minutes/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/minutes/${id}`)
      },
      votes: {
        list: (poll_id) => get(`${BASE_V1}/governance/votes`, { poll_id }),
        create: (payload) => post(`${BASE_V1}/governance/votes`, payload)
      },
      committees: {
        list: (organization_id) => get(`${BASE_V1}/governance/committees`, { organization_id }),
        get: (id) => get(`${BASE_V1}/governance/committees/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/committees`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/committees/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/committees/${id}`)
      },
      participants: {
        list: (meeting_id) => get(`${BASE_V1}/governance/participants`, { meeting_id }),
        get: (id) => get(`${BASE_V1}/governance/participants/${id}`),
        create: (payload) => post(`${BASE_V1}/governance/participants`, payload),
        update: (id, payload) => patch(`${BASE_V1}/governance/participants/${id}`, payload),
        delete: (id) => del(`${BASE_V1}/governance/participants/${id}`),
        markPresent: (id) => post(`${BASE_V1}/governance/participants/${id}/mark-present`),
        markAbsent: (id) => post(`${BASE_V1}/governance/participants/${id}/mark-absent`)
      },
      orgMemberships: {
        check: (organization_id) => get(`${BASE_V1}/governance/org-memberships/check/${organization_id}`),
        my: () => get(`${BASE_V1}/governance/org-memberships/my`),
        listByOrg: (organization_id) => get(`${BASE_V1}/governance/org-memberships/org/${organization_id}`),
        addByEmail: (organization_id, payload) => post(`${BASE_V1}/governance/org-memberships/org/${organization_id}/add-by-email`, payload),
        update: (membershipId, payload) => patch(`${BASE_V1}/governance/org-memberships/${membershipId}`, payload),
        delete: (membershipId) => del(`${BASE_V1}/governance/org-memberships/${membershipId}`)
      }
    },

    // Membership domain (FastAPI v1)
    membership: {
      members: {
        list: (orgId, params = {}) => get(`${BASE_V1}/membership/members`, {
          organization_id: orgId,
          page: 1,
          perPage: 30,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/membership/members/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/membership/members?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/membership/members/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/membership/members/${id}?organization_id=${orgId}`)
      },
      contacts: {
        list: (orgId, params = {}) => get(`${BASE_V1}/membership/contacts`, {
          organization_id: orgId,
          page: 1,
          perPage: 30,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/membership/contacts/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/membership/contacts?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/membership/contacts/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/membership/contacts/${id}?organization_id=${orgId}`)
      }
    },

    // Finance domain (FastAPI v1)
    finance: {
      accounts: {
        list: (orgId, params = {}) => get(`${BASE_V1}/finance/accounts`, {
          organization_id: orgId,
          page: 1,
          perPage: 50,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/finance/accounts/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/finance/accounts?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/finance/accounts/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/finance/accounts/${id}?organization_id=${orgId}`)
      },
      journal: {
        list: (orgId, params = {}) => get(`${BASE_V1}/finance/journal-entries`, {
          organization_id: orgId,
          page: 1,
          perPage: 50,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/finance/journal-entries/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/finance/journal-entries?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/finance/journal-entries/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/finance/journal-entries/${id}?organization_id=${orgId}`),
        post: (orgId, id) => post(`${BASE_V1}/finance/journal-entries/${id}/post?organization_id=${orgId}`),
        void: (orgId, id) => post(`${BASE_V1}/finance/journal-entries/${id}/void?organization_id=${orgId}`)
      },
      donations: {
        list: (orgId, params = {}) => get(`${BASE_V1}/finance/donations`, {
          organization_id: orgId,
          page: 1,
          perPage: 50,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/finance/donations/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/finance/donations?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/finance/donations/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/finance/donations/${id}?organization_id=${orgId}`)
      }
    },

    // Events domain (FastAPI v1)
    events: {
      projects: {
        list: (orgId, params = {}) => get(`${BASE_V1}/events/projects`, {
          organization_id: orgId,
          page: 1,
          perPage: 50,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/events/projects/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/events/projects?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/events/projects/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/events/projects/${id}?organization_id=${orgId}`)
      }
    },

    // Settings domain (FastAPI v1)
    settings: {
      get: (orgId, category) => get(`${BASE_V1}/settings/${category}`, { organization_id: orgId }),
      update: (orgId, category, payload) => patch(`${BASE_V1}/settings/${category}?organization_id=${orgId}`, payload)
    },

    // Admin domain (FastAPI v1)
    admin: {
      getAppSettings: () => get(`${BASE_V1}/admin/app-settings`),
      updateAppSettings: (payload) => patch(`${BASE_V1}/admin/app-settings`, payload)
    },

    // Dashboard domain (FastAPI v1)
    dashboard: {
      getSummary: (orgId) => get(`${BASE_V1}/dashboard/summary`, { organization_id: orgId }),
      // Metrics API
      metrics: {
        list: (orgId, includeArchived = false) => get(`${BASE_V1}/dashboard/metrics`, {
          organization_id: orgId,
          include_archived: includeArchived
        }),
        get: (orgId, metricId) => get(`${BASE_V1}/dashboard/metrics/${metricId}`, { organization_id: orgId }),
        create: (orgId, data) => post(`${BASE_V1}/dashboard/metrics`, { organization_id: orgId, ...data }),
        update: (orgId, metricId, data) => put(`${BASE_V1}/dashboard/metrics/${metricId}?organization_id=${orgId}`, data),
        delete: (orgId, metricId) => del(`${BASE_V1}/dashboard/metrics/${metricId}?organization_id=${orgId}`),
        // Values
        listValues: (orgId, metricId, limit = 50) => get(`${BASE_V1}/dashboard/metrics/${metricId}/values`, {
          organization_id: orgId,
          limit
        }),
        addValue: (orgId, metricId, data) => post(`${BASE_V1}/dashboard/metrics/${metricId}/values?organization_id=${orgId}`, data),
        // Setup / Templates
        getTemplates: () => get(`${BASE_V1}/dashboard/metrics/templates`),
        setup: (orgId, metrics) => post(`${BASE_V1}/dashboard/metrics/setup`, {
          organization_id: orgId,
          metrics
        })
      }
    },

    // Org Invites domain (FastAPI v1)
    orgInvites: {
      list: (orgId) => get(`${BASE_V1}/governance/org-invites/org/${orgId}`),
      create: (orgId, email, role) => post(`${BASE_V1}/governance/org-invites`, { organization_id: orgId, email, role }),
      accept: (token) => post(`${BASE_V1}/governance/org-invites/accept`, { token }),
      cancel: (inviteId) => post(`${BASE_V1}/governance/org-invites/${inviteId}/cancel`)
    },

    // CRM domain (FastAPI v1)
    crm: {
      leads: {
        list: (orgId, params = {}) => get(`${BASE_V1}/crm/leads`, {
          organization_id: orgId,
          page: 1,
          perPage: 30,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/crm/leads/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/crm/leads?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/crm/leads/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/crm/leads/${id}?organization_id=${orgId}`),
        convert: (orgId, id, payload) => post(`${BASE_V1}/crm/leads/${id}/convert?organization_id=${orgId}`, payload)
      },
      opportunities: {
        list: (orgId, params = {}) => get(`${BASE_V1}/crm/opportunities`, {
          organization_id: orgId,
          page: 1,
          perPage: 30,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/crm/opportunities/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/crm/opportunities?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/crm/opportunities/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/crm/opportunities/${id}?organization_id=${orgId}`),
        changeStage: (orgId, id, newStage) => post(`${BASE_V1}/crm/opportunities/${id}/stage?organization_id=${orgId}`, { new_stage: newStage })
      },
      activities: {
        list: (orgId, params = {}) => get(`${BASE_V1}/crm/activities`, {
          organization_id: orgId,
          page: 1,
          perPage: 50,
          ...params
        }),
        get: (orgId, id) => get(`${BASE_V1}/crm/activities/${id}`, { organization_id: orgId }),
        create: (orgId, payload) => post(`${BASE_V1}/crm/activities?organization_id=${orgId}`, payload),
        update: (orgId, id, payload) => patch(`${BASE_V1}/crm/activities/${id}?organization_id=${orgId}`, payload),
        delete: (orgId, id) => del(`${BASE_V1}/crm/activities/${id}?organization_id=${orgId}`),
        complete: (orgId, id) => post(`${BASE_V1}/crm/activities/${id}/complete?organization_id=${orgId}`)
      }
    }
  };
})();
