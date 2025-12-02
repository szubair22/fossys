// OrgMeet Application JavaScript
// Note: Requires ui.js and api.js to be loaded first

// Application configuration (can be overridden via window.APP_CONFIG)
window.APP_CONFIG = window.APP_CONFIG || {
    JITSI_DOMAIN: 'meet.jit.si',
    SITE_URL: window.location.origin
};

const App = {
    jitsiDomain: window.APP_CONFIG.JITSI_DOMAIN,

    // PocketBase compatibility shim - provides App.pb.authStore.token
    // This maintains backward compatibility with pages that still reference App.pb
    pb: {
        authStore: {
            get token() {
                return localStorage.getItem('orgmeet_token');
            }
        }
    },

    // ========================================
    // INITIALIZATION
    // ========================================

    init() {
        // Update nav on initial load & token changes
        this.updateNav();
        window.addEventListener('storage', (e) => { if (e.key === 'orgmeet_token') this.updateNav(); });

        // Setup HTMX error handling
        document.body.addEventListener('htmx:responseError', (e) => {
            console.error('HTMX Error:', e.detail);
            this.showNotification('An error occurred. Please try again.', 'error');
        });
    },

    // ========================================
    // LIST REFRESH HELPERS (delegated to UI module)
    // These are kept for backward compatibility.
    // New code should use window.UI directly.
    // ========================================

    /**
     * Refresh a table list (delegates to UI.refreshTableList)
     */
    async refreshList(containerId, fetchFn, renderFn, emptyMessage = 'No items found.') {
        return window.UI.refreshTableList(containerId, fetchFn, renderFn, emptyMessage);
    },

    /**
     * Refresh a card/grid list (delegates to UI.refreshCardList)
     */
    async refreshCardList(containerId, fetchFn, renderFn, emptyMessage = 'No items found.') {
        return window.UI.refreshCardList(containerId, fetchFn, renderFn, emptyMessage);
    },

    /**
     * Generic form submission handler (delegates to UI.handleFormSubmit)
     */
    async handleFormSubmit(form, submitFn, refreshFn) {
        return window.UI.handleFormSubmit(form, submitFn, refreshFn);
    },

    // Auth methods
    async login(email, password) {
        try {
            await window.API.auth.login(email, password);
            this.showNotification('Login successful!', 'success');
            window.location.href = '/pages/dashboard.html';
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Invalid credentials', 'error');
            return false;
        }
    },

    async register(name, email, password, passwordConfirm) {
        try {
            await window.API.auth.register(name, email, password, passwordConfirm);
            this.showNotification('Registration successful!', 'success');
            window.location.href = '/pages/dashboard.html';
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Registration failed', 'error');
            return false;
        }
    },

    logout() {
        window.API.auth.logout();
        window.location.href = '/';
    },

    isLoggedIn() {
        return window.API.auth.isLoggedIn();
    },

    getUser() {
        // After migration, store minimal user record in memory after refresh
        return this._currentUser || null;
    },

    // Get current user with fresh data from server
    async getCurrentUser() {
        try {
            if (!this.isLoggedIn()) return null;
            const user = await window.API.auth.getCurrentUser();
            this._currentUser = user;
            return user;
        } catch (err) {
            console.error('Failed to fetch current user:', err);
            return null;
        }
    },

    // Update current user's profile
    async updateCurrentUserProfile(data) {
        try {
            if (!this.isLoggedIn()) {
                this.showNotification('You must be logged in', 'error');
                return false;
            }
            const userId = this.getUser()?.id;
            if (!userId) return false;
            await window.API.auth.updateCurrentUserProfile(userId, data);
            await this.getCurrentUser();
            return true;
        } catch (err) {
            const errorMessage = this.parseError(err, 'Failed to update profile');
            this.showNotification(errorMessage, 'error');
            return false;
        }
    },

    // Toggle user dropdown menu
    toggleUserMenu() {
        const dropdown = document.getElementById('user-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('hidden');

            // Close dropdown when clicking outside
            const closeDropdown = (e) => {
                const userMenu = document.getElementById('user-menu');
                if (userMenu && !userMenu.contains(e.target)) {
                    dropdown.classList.add('hidden');
                    document.removeEventListener('click', closeDropdown);
                }
            };

            // Add click listener with slight delay to avoid immediate close
            setTimeout(() => {
                document.addEventListener('click', closeDropdown);
            }, 10);
        }
    },

    // Change user password (requires re-authentication)
    async changePassword(currentPassword, newPassword, confirmPassword) {
        try {
            if (!this.isLoggedIn()) {
                this.showNotification('You must be logged in', 'error');
                return false;
            }
            const user = await this.getCurrentUser();
            if (!user?.id) return false;
            await window.API.auth.changePassword(user.id, currentPassword, newPassword, confirmPassword);
            this.showNotification('Password changed successfully!', 'success');
            return true;
        } catch (err) {
            const errorMessage = this.parseError(err, 'Failed to change password');
            this.showNotification(errorMessage, 'error');
            return false;
        }
    },

    // Navigation - Uses Applications menu as primary navigation
    updateNav() {
        const nav = document.getElementById('nav-menu');
        const heroActions = document.getElementById('hero-actions');

        if (!nav) return;

        if (this.isLoggedIn()) {
            const user = this.getUser();
            const displayName = user?.display_name || user?.name || user?.email || 'User';
            nav.innerHTML = `
                <button class="apps-btn" onclick="Layout.toggleAppsMenu()" data-testid="apps-menu-btn">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                        <path d="M4 8h4V4H4v4zm6 12h4v-4h-4v4zm-6 0h4v-4H4v4zm0-6h4v-4H4v4zm6 0h4v-4h-4v4zm6-10v4h4V4h-4zm-6 4h4V4h-4v4zm6 6h4v-4h-4v4zm0 6h4v-4h-4v4z"/>
                    </svg>
                    <span>Applications</span>
                </button>
                <div class="relative ml-4" id="user-menu">
                    <button onclick="App.toggleUserMenu()" class="flex items-center gap-2 text-gray-700 font-medium hover:text-gray-900 transition">
                        <div class="w-8 h-8 bg-gray-700 text-white rounded-full flex items-center justify-center font-bold text-sm">
                            ${(displayName).charAt(0).toUpperCase()}
                        </div>
                        <span class="hidden sm:inline">${displayName}</span>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" class="text-gray-400">
                            <path d="M7 10l5 5 5-5z"/>
                        </svg>
                    </button>
                    <div id="user-dropdown" class="hidden absolute right-0 top-full mt-2 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-1 z-50">
                        <a href="/pages/account.html" class="flex items-center gap-2 px-4 py-2.5 text-gray-700 hover:bg-gray-50 transition">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" class="text-gray-400">
                                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                            </svg>
                            My Account
                        </a>
                        <hr class="my-1 border-gray-100">
                        <button onclick="App.logout()" class="flex items-center gap-2 w-full px-4 py-2.5 text-red-600 hover:bg-red-50 transition text-left">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" class="text-red-400">
                                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
                            </svg>
                            Sign Out
                        </button>
                    </div>
                </div>
            `;
            // Initialize Layout for Applications overlay if not already done
            if (window.Layout && !document.getElementById('apps-overlay')) {
                Layout.renderAppsOverlay();
            }
            if (heroActions) {
                heroActions.innerHTML = `
                    <a href="/pages/dashboard.html" class="bg-gray-900 text-white px-8 py-3 rounded-lg font-semibold hover:bg-gray-800 transition">Go to Dashboard</a>
                `;
            }
        } else {
            nav.innerHTML = `
                <a href="/pages/login.html" class="text-gray-600 hover:text-gray-900 font-medium">Login</a>
                <a href="/pages/register.html" class="bg-gray-900 text-white px-4 py-2 rounded-lg font-medium hover:bg-gray-800 transition">Get Started</a>
            `;
        }
    },

    // Check if user has admin access to any organization
    async checkAdminAccess() {
        try {
            if (!this.isLoggedIn()) return { isOrgAdmin: false, isSuperadmin: false };

            const orgs = await this.getOrganizations();
            const isOrgAdmin = orgs.some(org =>
                org.user_role === 'owner' || org.user_role === 'admin'
            );

            // Check superadmin by trying to access app settings
            let isSuperadmin = false;
            try {
                await window.API.admin.getAppSettings();
                isSuperadmin = true;
            } catch (e) {
                isSuperadmin = false;
            }

            return { isOrgAdmin, isSuperadmin };
        } catch (err) {
            console.error('Failed to check admin access:', err);
            return { isOrgAdmin: false, isSuperadmin: false };
        }
    },

    // Update admin menu visibility based on user permissions
    async updateAdminMenuVisibility() {
        const adminMenu = document.getElementById('admin-menu');
        const superadminLink = document.getElementById('admin-app-settings-link');
        const superadminDivider = document.getElementById('admin-superadmin-divider');

        if (!adminMenu) return;

        const { isOrgAdmin, isSuperadmin } = await this.checkAdminAccess();

        // Show/hide entire admin menu based on org admin status
        if (isOrgAdmin || isSuperadmin) {
            adminMenu.style.display = '';
        } else {
            adminMenu.style.display = 'none';
        }

        // Show/hide superadmin link
        if (isSuperadmin && superadminLink && superadminDivider) {
            superadminLink.style.display = '';
            superadminDivider.style.display = '';
        }
    },

    // API Methods
    async getOrganizations() {
        try {
            // Use new v1 API endpoint
            const data = await window.API.organizations.list(1,50);
            return data.items || [];
        } catch (err) {
            console.error('Failed to fetch organizations:', err);
            return [];
        }
    },

    async getOrganization(id) {
        try {
            // Use new v1 API endpoint
            return await window.API.organizations.getOne(id);
        } catch (err) {
            console.error('Failed to fetch organization:', err);
            return null;
        }
    },

    async createOrganization(data) {
        try {
            // Use new v1 API endpoint
            const record = await window.API.organizations.create(data);
            this.showNotification('Organization created!', 'success');
            return record;
        } catch (err) {
            const errorMessage = this.parseError(err, 'Failed to create organization');
            this.showNotification(errorMessage, 'error');
            return null;
        }
    },

    async deleteOrganization(id) {
        try {
            // Use new v1 API endpoint
            await window.API.organizations.delete(id);
            this.showNotification('Organization deleted!', 'success');
            return true;
        } catch (err) {
            console.error('Delete error:', err);
            const errorMessage = this.parseError(err, 'Failed to delete organization');
            this.showNotification(errorMessage, 'error');
            return false;
        }
    },

    // ========================================
    // MEETINGS - v1 API
    // ========================================

    async getMeetings(filter = '') {
        try {
            // Use new v1 API endpoint
            const params = new URLSearchParams({ page: '1', perPage: '50' });
            if (filter) {
                // Parse legacy filter format and add appropriate params
                // e.g., "committee = 'xyz'" or "status = 'scheduled'"
                if (filter.includes('committee')) {
                    const match = filter.match(/committee\s*=\s*['"]([^'"]+)['"]/);
                    if (match) params.append('committee_id', match[1]);
                }
                if (filter.includes('status')) {
                    const match = filter.match(/status\s*=\s*['"]([^'"]+)['"]/);
                    if (match) params.append('status', match[1]);
                }
            }

            const data = await window.API.governance.meetings.list(Object.fromEntries(params.entries()));
            return data.items || [];
        } catch (err) {
            console.error('Failed to fetch meetings:', err);
            return [];
        }
    },

    async getMeeting(id) {
        try {
            // Use new v1 API endpoint
            return await window.API.governance.meetings.get(id);
        } catch (err) {
            console.error('Failed to fetch meeting:', err);
            return null;
        }
    },

    async createMeeting(data) {
        try {
            // Use new v1 API endpoint
            const meetingData = {
                title: data.title,
                description: data.description,
                start_time: data.start_time,
                end_time: data.end_time,
                status: 'scheduled',
                meeting_type: data.meeting_type || 'general',
                committee_id: data.committee,
                quorum_required: data.quorum_required || 0,
            };

            const record = await window.API.governance.meetings.create(meetingData);
            this.showNotification('Meeting created!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create meeting', 'error');
            return null;
        }
    },

    async updateMeeting(id, data) {
        try {
            const updated = await window.API.governance.meetings.update(id, data);
            this.showNotification('Meeting updated!', 'success');
            return updated;
        } catch (err) {
            this.showNotification(err.message || 'Failed to update meeting', 'error');
            return null;
        }
    },

    async updateMeetingStatus(id, status) {
        try {
            // Use the appropriate v1 endpoint based on status
            if (status === 'completed') {
                await window.API.governance.meetings.close(id);
                return true;
            } else if (status === 'in_progress') {
                await window.API.governance.meetings.update(id, { status });
                return true;
            } else {
                await window.API.governance.meetings.update(id, { status });
                return true;
            }
        } catch (err) {
            this.showNotification(err.message || 'Failed to update meeting', 'error');
            return false;
        }
    },

    async deleteMeeting(id) {
        try {
            await window.API.governance.meetings.delete(id);
            this.showNotification('Meeting deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete meeting', 'error');
            return false;
        }
    },

    // ========================================
    // AGENDA ITEMS - v1 API
    // ========================================

    async getAgendaItems(meetingId) {
        try {
            const data = await window.API.governance.agenda.list(meetingId);
            // Map v1 response to legacy format for backward compatibility
            return (data.items || []).map(item => ({
                ...item,
                meeting: item.meeting_id  // Map meeting_id to meeting for compatibility
            }));
        } catch (err) {
            console.error('Failed to fetch agenda items:', err);
            return [];
        }
    },

    async createAgendaItem(data) {
        try {
            const record = await window.API.governance.agenda.create({
                meeting_id: data.meeting,
                title: data.title,
                description: data.description,
                order: data.order || 0,
                duration_minutes: data.duration_minutes || 0,
                item_type: data.item_type || 'topic',
                status: data.status || 'pending'
            });
            this.showNotification('Agenda item added!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create agenda item', 'error');
            return null;
        }
    },

    async updateAgendaItem(id, data) {
        try {
            return await window.API.governance.agenda.update(id, data);
        } catch (err) {
            this.showNotification(err.message || 'Failed to update agenda item', 'error');
            return null;
        }
    },

    async deleteAgendaItem(id) {
        try {
            await window.API.governance.agenda.delete(id);
            this.showNotification('Agenda item deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete agenda item', 'error');
            return false;
        }
    },

    // ========================================
    // MOTIONS - v1 API
    // ========================================

    async getMotions(meetingId) {
        try {
            const data = await window.API.governance.motions.list(meetingId);
            // Map v1 response to legacy format for backward compatibility
            return (data.items || []).map(motion => ({
                ...motion,
                meeting: motion.meeting_id,
                submitter: motion.submitter_id,
                agenda_item: motion.agenda_item_id,
            }));
        } catch (err) {
            console.error('Failed to fetch motions:', err);
            return [];
        }
    },

    async createMotion(data) {
        try {
            const record = await window.API.governance.motions.create({
                meeting_id: data.meeting,
                agenda_item_id: data.agenda_item,
                title: data.title,
                text: data.text,
                reason: data.reason,
                category: data.category,
            });
            this.showNotification('Motion created!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to submit motion', 'error');
            return null;
        }
    },

    async updateMotion(id, data) {
        try {
            return await window.API.governance.motions.update(id, data);
        } catch (err) {
            this.showNotification(err.message || 'Failed to update motion', 'error');
            return null;
        }
    },

    async deleteMotion(id) {
        try {
            await window.API.governance.motions.delete(id);
            this.showNotification('Motion deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete motion', 'error');
            return false;
        }
    },

    // ========================================
    // POLLS - v1 API
    // ========================================

    async getPolls(meetingId) {
        try {
            const data = await window.API.governance.polls.list(meetingId);
            // Map v1 response to legacy format for backward compatibility
            return (data.items || []).map(poll => ({
                ...poll,
                meeting: poll.meeting_id,
                motion: poll.motion_id,
                created_by: poll.created_by_id,
            }));
        } catch (err) {
            console.error('Failed to fetch polls:', err);
            return [];
        }
    },

    async createPoll(data) {
        try {
            const record = await window.API.governance.polls.create({
                meeting_id: data.meeting,
                motion_id: data.motion,
                title: data.title,
                description: data.description,
                poll_type: data.poll_type || 'yes_no',
                options: data.options,
                anonymous: data.anonymous || false,
            });
            this.showNotification('Poll created!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create poll', 'error');
            return null;
        }
    },

    async deletePoll(id) {
        try {
            await window.API.governance.polls.delete(id);
            this.showNotification('Poll deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete poll', 'error');
            return false;
        }
    },

    // ========================================
    // VOTES - v1 API
    // ========================================

    async submitVote(pollId, value) {
        try {
            const result = await window.API.governance.votes.create({
                poll_id: pollId,
                value: typeof value === 'object' ? value : { choice: value }
            });
            this.showNotification('Vote submitted!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to submit vote', 'error');
            return null;
        }
    },

    async getVotes(pollId) {
        try {
            const data = await window.API.governance.votes.list(pollId);
            return data.items || [];
        } catch (err) {
            console.error('Failed to fetch votes:', err);
            return [];
        }
    },

    // ========================================
    // COMMITTEES - v1 API
    // ========================================

    async getCommittees(organizationId) {
        try {
            const data = await window.API.governance.committees.list(organizationId);
            // Map v1 response to legacy format for backward compatibility
            return (data.items || []).map(c => ({
                ...c,
                organization: c.organization_id,
                admins: c.admin_ids || [],
            }));
        } catch (err) {
            console.error('Failed to fetch committees:', err);
            return [];
        }
    },

    async getCommittee(id) {
        try {
            const data = await window.API.governance.committees.get(id);
            return {
                ...data,
                organization: data.organization_id,
                admins: data.admin_ids || [],
            };
        } catch (err) {
            console.error('Failed to fetch committee:', err);
            return null;
        }
    },

    async createCommittee(data) {
        try {
            const result = await window.API.governance.committees.create({
                organization_id: data.organization,
                name: data.name,
                description: data.description,
            });
            this.showNotification('Committee created!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create committee', 'error');
            return null;
        }
    },

    async updateCommittee(id, data) {
        try {
            const result = await window.API.governance.committees.update(id, data);
            this.showNotification('Committee updated!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to update committee', 'error');
            return null;
        }
    },

    async deleteCommittee(id) {
        try {
            await window.API.governance.committees.delete(id);
            this.showNotification('Committee deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete committee', 'error');
            return false;
        }
    },

    // ========================================
    // PARTICIPANTS (Attendance) - v1 API
    // ========================================

    // Get participants for a meeting
    async getParticipants(meetingId) {
        try {
            const data = await window.API.governance.participants.list(meetingId);
            // Map v1 response to legacy format for backward compatibility
            return (data.items || []).map(p => ({
                ...p,
                meeting: p.meeting_id,
                user: p.user_id,
                expand: p.user_name ? { user: { name: p.user_name, email: p.user_email } } : undefined,
            }));
        } catch (err) {
            console.error('Failed to fetch participants:', err);
            return [];
        }
    },

    // Add participant to meeting
    async addParticipant(data) {
        try {
            const result = await window.API.governance.participants.create({
                meeting_id: data.meeting,
                user_id: data.user,
                role: data.role || 'member',
                can_vote: data.can_vote !== false,
                vote_weight: data.vote_weight || 1,
            });
            this.showNotification('Participant added!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to add participant', 'error');
            return null;
        }
    },

    // Update participant (mark present, etc.)
    async updateParticipant(id, data) {
        try {
            return await window.API.governance.participants.update(id, data);
        } catch (err) {
            this.showNotification(err.message || 'Failed to update participant', 'error');
            return null;
        }
    },

    // Remove participant from meeting
    async removeParticipant(id) {
        try {
            await window.API.governance.participants.delete(id);
            this.showNotification('Participant removed!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to remove participant', 'error');
            return false;
        }
    },

    // Mark participant as present
    async markParticipantPresent(id) {
        try {
            return await window.API.governance.participants.markPresent(id);
        } catch (err) {
            this.showNotification(err.message || 'Failed to mark present', 'error');
            return null;
        }
    },

    // Mark participant as absent
    async markParticipantAbsent(id) {
        try {
            return await window.API.governance.participants.markAbsent(id);
        } catch (err) {
            this.showNotification(err.message || 'Failed to mark absent', 'error');
            return null;
        }
    },

    // Calculate and update quorum for a meeting (uses v1 API)
    async recalculateQuorum(meetingId) {
        try {
            const meeting = await this.getMeeting(meetingId);
            if (!meeting) return null;

            const participants = await this.getParticipants(meetingId);
            // Use attendance_status for quorum (with is_present fallback for backward compatibility)
            const presentVoters = participants.filter(p => (p.attendance_status === 'present' || p.is_present) && p.can_vote);
            const quorumRequired = meeting.quorum_required || 0;
            const quorumMet = quorumRequired > 0 ? presentVoters.length >= quorumRequired : true;

            // Update meeting via v1 API
            await this.updateMeeting(meetingId, { quorum_met: quorumMet });

            return {
                total_participants: participants.length,
                present_voters: presentVoters.length,
                quorum_required: quorumRequired,
                quorum_met: quorumMet
            };
        } catch (err) {
            this.showNotification(err.message || 'Failed to recalculate quorum', 'error');
            return null;
        }
    },

    // Motion workflow state transitions
    getMotionTransitions(currentState) {
        const transitions = {
            'draft': ['submitted', 'withdrawn'],
            'submitted': ['screening', 'discussion', 'withdrawn'],
            'screening': ['discussion', 'rejected', 'withdrawn'],
            'discussion': ['voting', 'referred', 'withdrawn'],
            'voting': ['accepted', 'rejected'],
            'accepted': [],
            'rejected': [],
            'withdrawn': [],
            'referred': ['discussion']
        };
        return transitions[currentState] || [];
    },

    // Get allowed transitions for a motion (uses v1 API)
    async getMotionAllowedTransitions(motionId) {
        try {
            return await window.API.governance.motionTransitions.list(motionId);
        } catch (err) {
            console.error('Failed to get transitions:', err);
            return { current_state: 'unknown', allowed_transitions: [] };
        }
    },

    // Transition motion to new state (uses v1 API)
    async transitionMotion(motionId, newState) {
        try {
            const result = await window.API.governance.motionTransitions.transition(motionId, newState);
            this.showNotification(`Motion moved to ${newState}`, 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to transition motion', 'error');
            return null;
        }
    },

    // Update motion with vote result (uses v1 API)
    async updateMotionVoteResult(motionId, voteResult) {
        try {
            return await this.updateMotion(motionId, { vote_result: voteResult });
        } catch (err) {
            this.showNotification(err.message || 'Failed to update motion result', 'error');
            return null;
        }
    },

    // Poll operations (use v1 API)
    async openPoll(pollId) {
        try {
            const result = await window.API.governance.polls.open(pollId);
            this.showNotification('Poll opened!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to open poll', 'error');
            return null;
        }
    },

    async closePoll(pollId) {
        try {
            const result = await window.API.governance.polls.close(pollId);
            this.showNotification('Poll closed!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to close poll', 'error');
            return null;
        }
    },

    calculatePollResults(votes) {
        const results = {
            total_votes: votes.length,
            breakdown: {}
        };

        votes.forEach(vote => {
            const choice = vote.value?.choice || vote.value;
            if (choice) {
                results.breakdown[choice] = (results.breakdown[choice] || 0) + (vote.weight || 1);
            }
        });

        return results;
    },

    async getPollResults(pollId) {
        try {
            return await window.API.governance.polls.results(pollId);
        } catch (err) {
            console.error('Failed to get poll results:', err);
            return null;
        }
    },

    // ========================================
    // Meeting Templates (FastAPI v1 API)
    // ========================================

    async getTemplates(organizationId = null) {
        try {
            const params = { include_global: true };
            if (organizationId) params.organization_id = organizationId;
            const data = await window.API.governance.templates.list(params);
            return data.items || [];
        } catch (err) {
            console.error('Failed to fetch templates:', err);
            return [];
        }
    },

    async getTemplate(id) {
        try {
            return await window.API.governance.templates.get(id);
        } catch (err) {
            console.error('Failed to fetch template:', err);
            return null;
        }
    },

    async createMeetingFromTemplate(templateId, meetingData) {
        try {
            const template = await this.getTemplate(templateId);
            if (!template) throw new Error('Template not found');

            // Create meeting with template defaults using v1 API
            const meetingPayload = {
                title: meetingData.title || template.default_meeting_title || 'Meeting',
                meeting_type: meetingData.meeting_type || template.default_meeting_type || 'general',
                status: 'scheduled',
                quorum_required: template.settings?.default_quorum || 0,
                start_time: meetingData.start_time,
                end_time: meetingData.end_time,
                description: meetingData.description,
                committee_id: meetingData.committee_id
            };

            const meeting = await window.API.governance.meetings.create(meetingPayload);

            // Create agenda items from template using v1 API
            if (template.default_agenda) {
                const agenda = typeof template.default_agenda === 'string'
                    ? JSON.parse(template.default_agenda)
                    : template.default_agenda;

                for (let i = 0; i < agenda.length; i++) {
                    const item = agenda[i];
                    await window.API.governance.agenda.create({
                        meeting_id: meeting.id,
                        title: item.title,
                        description: item.description || '',
                        item_type: item.item_type || 'topic',
                        duration_minutes: item.duration || 0,
                        order_index: i,
                        status: 'pending'
                    });
                }
            }

            this.showNotification('Meeting created from template!', 'success');
            return meeting;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create meeting from template', 'error');
            return null;
        }
    },

    async createTemplate(organizationId, data) {
        try {
            const result = await window.API.governance.templates.create({
                organization_id: organizationId,
                ...data
            });
            this.showNotification('Template created!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create template', 'error');
            return null;
        }
    },

    // ========================================
    // Meeting Minutes (FastAPI v1 API)
    // ========================================

    async getMeetingMinutes(meetingId) {
        try {
            return await window.API.governance.minutes.getByMeeting(meetingId);
        } catch (err) {
            if (err.status === 404) return null;
            console.error('Failed to fetch minutes:', err);
            return null;
        }
    },

    async generateMinutes(meetingId) {
        try {
            // Fetch all meeting data
            const meeting = await this.getMeeting(meetingId);
            if (!meeting) throw new Error('Meeting not found');

            const participants = await this.getParticipants(meetingId);
            const agendaItems = await this.getAgendaItems(meetingId);
            const motions = await this.getMotions(meetingId);
            const polls = await this.getPolls(meetingId);

            // Build minutes content
            const content = this.buildMinutesContent(meeting, participants, agendaItems, motions, polls);
            const decisions = this.extractDecisions(motions, polls);
            const attendanceSnapshot = this.buildAttendanceSnapshot(participants);

            // Use upsert endpoint - creates or updates minutes
            const record = await window.API.governance.minutes.upsert({
                meeting_id: meetingId,
                content,
                decisions,
                attendance_snapshot: attendanceSnapshot,
                status: 'draft'
            });

            this.showNotification('Minutes generated!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to generate minutes', 'error');
            return null;
        }
    },

    buildMinutesContent(meeting, participants, agendaItems, motions, polls) {
        // Use attendance_status with is_present fallback for backward compatibility
        const presentParticipants = participants.filter(p => p.attendance_status === 'present' || p.is_present);
        const lines = [];

        lines.push(`# ${meeting.title}`);
        lines.push('');
        lines.push(`**Date:** ${this.formatDate(meeting.start_time)}`);
        if (meeting.end_time) {
            lines.push(`**End Time:** ${this.formatDate(meeting.end_time)}`);
        }
        lines.push(`**Meeting Type:** ${meeting.meeting_type || 'General'}`);
        lines.push(`**Status:** ${meeting.status}`);
        lines.push('');

        // Attendance
        lines.push('## Attendance');
        lines.push('');
        if (presentParticipants.length > 0) {
            lines.push('**Present:**');
            presentParticipants.forEach(p => {
                const name = p.expand?.user?.name || p.expand?.user?.email || 'Unknown';
                lines.push(`- ${name} (${p.role}${p.can_vote ? ', voting' : ''})`);
            });
        }
        // Use attendance_status with fallback - absent includes 'absent', 'excused', or not present
        const absentParticipants = participants.filter(p =>
            p.attendance_status === 'absent' || p.attendance_status === 'excused' ||
            (!p.attendance_status && !p.is_present)
        );
        if (absentParticipants.length > 0) {
            lines.push('');
            lines.push('**Absent:**');
            absentParticipants.forEach(p => {
                const name = p.expand?.user?.name || p.expand?.user?.email || 'Unknown';
                lines.push(`- ${name}`);
            });
        }
        lines.push('');

        // Quorum
        lines.push('## Quorum');
        const votingPresent = presentParticipants.filter(p => p.can_vote).length;
        lines.push(`- Voting members present: ${votingPresent}`);
        lines.push(`- Quorum required: ${meeting.quorum_required || 'Not specified'}`);
        lines.push(`- Quorum status: ${meeting.quorum_met ? '**Met**' : '**Not Met**'}`);
        lines.push('');

        // Agenda
        if (agendaItems.length > 0) {
            lines.push('## Agenda');
            lines.push('');
            agendaItems.forEach((item, i) => {
                lines.push(`${i + 1}. **${item.title}** (${item.item_type})${item.status === 'completed' ? ' ✓' : ''}`);
                if (item.description) {
                    lines.push(`   ${item.description}`);
                }
            });
            lines.push('');
        }

        // Motions
        if (motions.length > 0) {
            lines.push('## Motions');
            lines.push('');
            motions.forEach(motion => {
                lines.push(`### ${motion.number || 'Motion'}: ${motion.title}`);
                lines.push(`**Status:** ${motion.workflow_state}`);
                lines.push(`**Submitted by:** ${motion.expand?.submitter?.name || 'Unknown'}`);
                lines.push('');
                lines.push(motion.text);
                if (motion.reason) {
                    lines.push('');
                    lines.push(`**Reason:** ${motion.reason}`);
                }
                if (motion.vote_result) {
                    lines.push('');
                    lines.push('**Vote Result:**');
                    const result = motion.vote_result;
                    if (result.breakdown) {
                        Object.entries(result.breakdown).forEach(([choice, count]) => {
                            lines.push(`- ${choice}: ${count}`);
                        });
                    }
                }
                lines.push('');
            });
        }

        // Polls
        const completedPolls = polls.filter(p => p.status === 'closed' || p.status === 'published');
        if (completedPolls.length > 0) {
            lines.push('## Voting Results');
            lines.push('');
            completedPolls.forEach(poll => {
                lines.push(`### ${poll.title}`);
                lines.push(`**Type:** ${poll.poll_type}`);
                if (poll.results) {
                    lines.push(`**Total Votes:** ${poll.results.total_votes || 0}`);
                    if (poll.results.breakdown) {
                        Object.entries(poll.results.breakdown).forEach(([choice, count]) => {
                            lines.push(`- ${choice}: ${count}`);
                        });
                    }
                }
                lines.push('');
            });
        }

        lines.push('---');
        lines.push(`*Minutes generated by OrgMeet on ${new Date().toLocaleString()}*`);

        return lines.join('\n');
    },

    extractDecisions(motions, polls) {
        const decisions = [];

        motions.forEach(motion => {
            if (['accepted', 'rejected'].includes(motion.workflow_state)) {
                decisions.push({
                    type: 'motion',
                    id: motion.id,
                    title: motion.title,
                    result: motion.workflow_state,
                    vote_result: motion.vote_result,
                    notes: motion.final_notes
                });
            }
        });

        polls.forEach(poll => {
            if (poll.status === 'closed' || poll.status === 'published') {
                decisions.push({
                    type: poll.poll_category || 'poll',
                    id: poll.id,
                    title: poll.title,
                    result: poll.results,
                    winning_option: poll.winning_option
                });
            }
        });

        return decisions;
    },

    buildAttendanceSnapshot(participants) {
        return participants.map(p => ({
            user_id: p.user,
            name: p.expand?.user?.name || p.expand?.user?.email,
            role: p.role,
            attendance_status: p.attendance_status || (p.is_present ? 'present' : 'invited'),
            is_present: p.is_present, // Keep for backward compatibility
            can_vote: p.can_vote,
            joined_at: p.joined_at,
            left_at: p.left_at
        }));
    },

    async updateMinutes(minutesId, data) {
        try {
            const result = await window.API.governance.minutes.update(minutesId, data);
            this.showNotification('Minutes updated!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to update minutes', 'error');
            return null;
        }
    },

    // Download minutes as markdown
    downloadMinutesAsMarkdown(minutes, meeting) {
        const blob = new Blob([minutes.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${meeting.title.replace(/[^a-z0-9]/gi, '_')}_minutes.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    // ========================================
    // Decision Log
    // ========================================

    async getDecisionLog(organizationId, limit = 50) {
        try {
            // Get all completed motions for meetings in this organization's committees
            const committees = await this.getCommittees(organizationId);
            if (committees.length === 0) return [];

            const committeeIds = committees.map(c => c.id);
            const committeeFilter = committeeIds.map(id => `committee = "${id}"`).join(' || ');

            const meetings = await window.API.meetings.list(`(${committeeFilter}) && status = "completed"`, 1, 100, '-start_time');

            const decisions = [];
            for (const meeting of meetings.items) {
                const motions = await this.getMotions(meeting.id);
                const decidedMotions = motions.filter(m => ['accepted', 'rejected'].includes(m.workflow_state));

                decidedMotions.forEach(motion => {
                    decisions.push({
                        meeting_id: meeting.id,
                        meeting_title: meeting.title,
                        meeting_date: meeting.start_time,
                        motion_id: motion.id,
                        motion_title: motion.title,
                        motion_number: motion.number,
                        result: motion.workflow_state,
                        vote_result: motion.vote_result
                    });
                });
            }

            return decisions.slice(0, limit);
        } catch (err) {
            console.error('Failed to fetch decision log:', err);
            return [];
        }
    },

    // ========================================
    // Calendar (ICS) Generation
    // ========================================

    generateICS(meeting) {
        const start = new Date(meeting.start_time);
        const end = meeting.end_time ? new Date(meeting.end_time) : new Date(start.getTime() + 60 * 60 * 1000);

        const formatDate = (date) => {
            return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
        };

        const escapeText = (text) => {
            if (!text) return '';
            return text.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n');
        };

        const uid = `${meeting.id}@orgmeet`;
        const now = formatDate(new Date());
        const meetingUrl = `${window.APP_CONFIG.SITE_URL}/pages/meeting.html?id=${meeting.id}`;

        const ics = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//OrgMeet//Meeting//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            'BEGIN:VEVENT',
            `UID:${uid}`,
            `DTSTAMP:${now}`,
            `DTSTART:${formatDate(start)}`,
            `DTEND:${formatDate(end)}`,
            `SUMMARY:${escapeText(meeting.title)}`,
            `DESCRIPTION:${escapeText(meeting.description || '')}\\n\\nJoin meeting: ${meetingUrl}`,
            `URL:${meetingUrl}`,
            meeting.jitsi_room ? `LOCATION:Online via OrgMeet (Jitsi)` : '',
            'STATUS:CONFIRMED',
            'END:VEVENT',
            'END:VCALENDAR'
        ].filter(Boolean).join('\r\n');

        return ics;
    },

    downloadICS(meeting) {
        const ics = this.generateICS(meeting);
        const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${meeting.title.replace(/[^a-z0-9]/gi, '_')}.ics`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    // ========================================
    // Email Notifications
    // ========================================

    async createNotification(meetingId, recipientId, type) {
        try {
            const record = await window.API.meeting_notifications.create({
                meeting: meetingId,
                recipient_user: recipientId,
                notification_type: type,
                scheduled_at: new Date().toISOString()
            });
            return record;
        } catch (err) {
            console.error('Failed to create notification:', err);
            return null;
        }
    },

    async sendMeetingInvitations(meetingId) {
        try {
            const participants = await this.getParticipants(meetingId);
            let created = 0;

            for (const participant of participants) {
                const notification = await this.createNotification(meetingId, participant.user, 'invitation');
                if (notification) created++;
            }

            this.showNotification(`${created} invitation(s) queued!`, 'success');
            return created;
        } catch (err) {
            this.showNotification(err.message || 'Failed to send invitations', 'error');
            return 0;
        }
    },

    async getNotifications(meetingId) {
        try {
            const resp = await window.API.meeting_notifications.list(`meeting="${meetingId}"`);
            return resp.items || [];
        } catch (err) {
            console.error('Failed to fetch notifications:', err);
            return [];
        }
    },

    // Jitsi Integration
    initJitsi(containerId, roomName, userName) {
        const container = document.getElementById(containerId);
        if (!container) return null;

        const domain = this.jitsiDomain;
        const options = {
            roomName: roomName,
            width: '100%',
            height: '100%',
            parentNode: container,
            configOverwrite: {
                startWithAudioMuted: true,
                startWithVideoMuted: false,
                disableDeepLinking: true,
                prejoinPageEnabled: false
            },
            interfaceConfigOverwrite: {
                TOOLBAR_BUTTONS: [
                    'microphone', 'camera', 'desktop', 'fullscreen',
                    'fodeviceselection', 'hangup', 'chat', 'recording',
                    'settings', 'raisehand', 'videoquality', 'tileview',
                    'participants-pane'
                ],
                SHOW_JITSI_WATERMARK: false,
                SHOW_WATERMARK_FOR_GUESTS: false,
                SHOW_BRAND_WATERMARK: false,
                MOBILE_APP_PROMO: false
            },
            userInfo: {
                displayName: userName
            }
        };

        return new JitsiMeetExternalAPI(domain, options);
    },

    // Utility methods

    // Parse API error into user-friendly message
    parseError(err, defaultMessage = 'An error occurred') {
        if (!err) return defaultMessage;

        // API errors may have response.data with field errors
        if (err.response?.data) {
            const fieldErrors = Object.entries(err.response.data)
                .map(([field, errObj]) => {
                    const msg = typeof errObj === 'object' ? (errObj.message || errObj.code || JSON.stringify(errObj)) : errObj;
                    // Make messages more user-friendly
                    if (msg === 'Value must be unique' || (typeof msg === 'string' && msg.includes('unique'))) {
                        return `An item with this ${field} already exists`;
                    }
                    if (msg === 'cannot be blank') {
                        return `${field.charAt(0).toUpperCase() + field.slice(1)} is required`;
                    }
                    return `${field}: ${msg}`;
                })
                .join('. ');
            if (fieldErrors) return fieldErrors;
        }

        // Check for message property
        if (err.message) {
            // Clean up common database error messages
            if (err.message.includes('UNIQUE constraint failed')) {
                return 'This record already exists';
            }
            return err.message;
        }

        // Fallback to string representation
        if (typeof err === 'string') return err;

        return defaultMessage;
    },

    // ========================================
    // UI HELPERS (delegated to UI module for backward compatibility)
    // New code should use window.UI directly.
    // ========================================

    showNotification(message, type = 'info') {
        return window.UI.showNotification(message, type);
    },

    formatDate(dateStr) {
        return window.UI.formatDate(dateStr);
    },

    formatShortDate(dateStr) {
        return window.UI.formatShortDate(dateStr);
    },

    getStatusBadgeClass(status) {
        return window.UI.getStatusBadgeClass(status);
    },

    // Require authentication
    requireAuth() {
        if (!this.isLoggedIn()) {
            window.location.href = '/pages/login.html';
            return false;
        }
        return true;
    },

    // Get URL parameter (delegates to UI)
    getUrlParam(param) {
        return window.UI.getUrlParam(param);
    },

    // ========================================
    // Permissions & Roles System
    // ========================================

    // Get user's membership in an organization (FastAPI v1 API)
    async getOrgMembership(organizationId, userId = null) {
        try {
            const uid = userId || this.getUser()?.id;
            if (!uid) return null;

            const membership = await window.API.governance.orgMemberships.check(organizationId);
            // Map to legacy format for backward compatibility
            return {
                ...membership,
                organization: membership.organization_id,
                user: membership.user_id
            };
        } catch (err) {
            if (err.status === 404) return null;
            console.error('Failed to fetch org membership:', err);
            return null;
        }
    },

    // Get all memberships for current user (FastAPI v1 API)
    async getUserMemberships() {
        try {
            const userId = this.getUser()?.id;
            if (!userId) return [];

            const data = await window.API.governance.orgMemberships.my();
            // Map to legacy format for backward compatibility
            return (data.items || []).map(m => ({
                ...m,
                organization: m.organization_id,
                user: m.user_id,
                expand: m.organization ? { organization: m.organization } : {}
            }));
        } catch (err) {
            console.error('Failed to fetch user memberships:', err);
            return [];
        }
    },

    // Get all members of an organization (FastAPI v1 API)
    async getOrgMembers(organizationId) {
        try {
            const data = await window.API.governance.orgMemberships.listByOrg(organizationId);
            // Map to legacy format for backward compatibility
            return (data.items || []).map(m => ({
                ...m,
                organization: m.organization_id,
                user: m.user_id,
                expand: m.user ? { user: m.user } : {}
            }));
        } catch (err) {
            console.error('Failed to fetch org members:', err);
            return [];
        }
    },

    // Add a member to organization (FastAPI v1 API)
    async addOrgMember(organizationId, userEmail, role = 'member') {
        try {
            const membership = await window.API.governance.orgMemberships.addByEmail(organizationId, {
                email: userEmail,
                role: role
            });
            this.showNotification('Member added successfully!', 'success');

            // Map to legacy format
            return {
                ...membership,
                organization: membership.organization_id,
                user: membership.user_id
            };
        } catch (err) {
            if (err.status === 404) {
                this.showNotification('User not found with that email', 'error');
                return null;
            }
            if (err.status === 400) {
                this.showNotification(err.message || 'User is already a member', 'error');
                return null;
            }
            this.showNotification(err.message || 'Failed to add member', 'error');
            return null;
        }
    },

    // Update member role (FastAPI v1 API)
    async updateMemberRole(membershipId, newRole) {
        try {
            const membership = await window.API.governance.orgMemberships.update(membershipId, { role: newRole });
            this.showNotification('Member role updated!', 'success');

            // Map to legacy format
            return {
                ...membership,
                organization: membership.organization_id,
                user: membership.user_id
            };
        } catch (err) {
            this.showNotification(err.message || 'Failed to update member role', 'error');
            return null;
        }
    },

    // Remove member from organization (FastAPI v1 API)
    async removeOrgMember(membershipId) {
        try {
            await window.API.governance.orgMemberships.delete(membershipId);
            this.showNotification('Member removed!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to remove member', 'error');
            return false;
        }
    },

    // Check if user has permission for an action
    async hasPermission(organizationId, requiredRole = 'member') {
        const membership = await this.getOrgMembership(organizationId);
        if (!membership) {
            // Check if user is org owner (fallback)
            const org = await this.getOrganization(organizationId);
            if (org && org.owner === this.getUser()?.id) {
                return true;
            }
            return false;
        }

        const roleHierarchy = ['viewer', 'member', 'admin', 'owner'];
        const userRoleIndex = roleHierarchy.indexOf(membership.role);
        const requiredRoleIndex = roleHierarchy.indexOf(requiredRole);

        return userRoleIndex >= requiredRoleIndex;
    },

    // Get user's effective role in an organization
    async getUserRole(organizationId) {
        const org = await this.getOrganization(organizationId);
        if (org && org.owner === this.getUser()?.id) {
            return 'owner';
        }

        const membership = await this.getOrgMembership(organizationId);
        return membership?.role || null;
    },

    // ========================================
    // File/Document Management
    // ========================================

    // Get files for organization/meeting/agenda/motion
    async getFiles(filters = {}) {
        try {
            const parts = [];
            if (filters.organization) parts.push(`organization = "${filters.organization}"`);
            if (filters.meeting) parts.push(`meeting = "${filters.meeting}"`);
            if (filters.agenda_item) parts.push(`agenda_item = "${filters.agenda_item}"`);
            if (filters.motion) parts.push(`motion = "${filters.motion}"`);
            const filter = parts.length ? parts.join(' && ') : '';
            const resp = await window.API.files.listFiles(filter);
            return resp.items || [];
        } catch (err) {
            console.error('Failed to fetch files:', err);
            return [];
        }
    },

    // Upload a file
    async uploadFile(fileInput, metadata) {
        try {
            const f = fileInput.files[0];
            const formData = new FormData();
            formData.append('upload', f); // Router expects 'upload'
            formData.append('organization', metadata.organization);
            formData.append('name', metadata.name || f.name);
            if (metadata.meeting) formData.append('meeting', metadata.meeting);
            if (metadata.agenda_item) formData.append('agenda_item', metadata.agenda_item);
            if (metadata.motion) formData.append('motion', metadata.motion);
            if (metadata.description) formData.append('description', metadata.description);
            // Infer file_type
            const mime = f.type;
            let fileType = 'other';
            if (mime.includes('pdf') || mime.includes('document') || mime.includes('word')) fileType = 'document';
            else if (mime.includes('spreadsheet') || mime.includes('excel')) fileType = 'spreadsheet';
            else if (mime.includes('presentation') || mime.includes('powerpoint')) fileType = 'presentation';
            else if (mime.includes('image')) fileType = 'image';
            formData.append('file_type', fileType);
            const record = await window.API.files.uploadFile(formData);
            this.showNotification('File uploaded successfully!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to upload file', 'error');
            return null;
        }
    },

    // Delete a file
    async deleteFile(fileId) {
        try {
            await window.API.files.deleteFile(fileId);
            this.showNotification('File deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete file', 'error');
            return false;
        }
    },

    // Get file URL
    getFileUrl(record, filename) {
        // New download path
        return `/api/collections/files/records/${record.id}/download`;
    },

    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // ========================================
    // AI Integrations
    // ========================================

    // Get AI integration for organization
    async getAIIntegration(organizationId) {
        try {
            const resp = await window.API.ai_integrations.list(`organization="${organizationId}"`);
            return (resp.items || []).find(i => i.is_active) || null;
        } catch (err) {
            console.error('Failed to fetch AI integration:', err);
            return null;
        }
    },

    // Get all AI integrations for organization
    async getAIIntegrations(organizationId) {
        try {
            const resp = await window.API.ai_integrations.list(`organization="${organizationId}"`);
            return resp.items || [];
        } catch (err) {
            console.error('Failed to fetch AI integrations:', err);
            return [];
        }
    },

    // Create AI integration
    async createAIIntegration(data) {
        try {
            const record = await window.API.ai_integrations.create({
                organization: data.organization,
                provider: data.provider,
                api_key: data.api_key,
                model: data.model || null,
                settings: data.settings || null
            });
            this.showNotification('AI integration added!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to add AI integration', 'error');
            return null;
        }
    },

    // Update AI integration
    async updateAIIntegration(id, data) {
        try {
            const record = await window.API.ai_integrations.update(id, data);
            this.showNotification('AI integration updated!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to update AI integration', 'error');
            return null;
        }
    },

    // Delete AI integration
    async deleteAIIntegration(id) {
        try {
            await window.API.ai_integrations.delete(id);
            this.showNotification('AI integration removed!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to remove AI integration', 'error');
            return false;
        }
    },

    // Call AI for meeting summary/assistance (client-side implementation)
    async callAI(organizationId, prompt, context = {}) {
        try {
            const integration = await this.getAIIntegration(organizationId);
            if (!integration) {
                this.showNotification('No AI integration configured for this organization', 'error');
                return null;
            }

            // Update usage
            await window.API.ai_integrations.update(integration.id, {
                last_used_at: new Date().toISOString(),
                usage_count: (integration.usage_count || 0) + 1
            });

            // Make API call based on provider
            let response;
            const model = integration.model || this.getDefaultModel(integration.provider);

            if (integration.provider === 'openai') {
                response = await this.callOpenAI(integration.api_key, model, prompt, context);
            } else if (integration.provider === 'anthropic') {
                response = await this.callAnthropic(integration.api_key, model, prompt, context);
            } else {
                throw new Error('Unsupported AI provider');
            }

            return response;
        } catch (err) {
            this.showNotification(err.message || 'AI request failed', 'error');
            return null;
        }
    },

    getDefaultModel(provider) {
        const defaults = {
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'google': 'gemini-pro'
        };
        return defaults[provider] || 'gpt-4o-mini';
    },

    async callOpenAI(apiKey, model, prompt, context) {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: model,
                messages: [
                    {
                        role: 'system',
                        content: 'You are a helpful meeting assistant for OrgMeet, a governance and meeting management platform. Help with meeting summaries, agenda suggestions, motion drafting, and general meeting assistance.'
                    },
                    {
                        role: 'user',
                        content: context.meetingContext
                            ? `Meeting Context:\n${JSON.stringify(context.meetingContext, null, 2)}\n\nRequest: ${prompt}`
                            : prompt
                    }
                ],
                max_tokens: 2000,
                temperature: 0.7
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'OpenAI API error');
        }

        const data = await response.json();
        return data.choices[0]?.message?.content || '';
    },

    async callAnthropic(apiKey, model, prompt, context) {
        const response = await fetch('https://api.anthropic.com/v1/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'anthropic-version': '2023-06-01',
                'anthropic-dangerous-direct-browser-access': 'true'
            },
            body: JSON.stringify({
                model: model,
                max_tokens: 2000,
                system: 'You are a helpful meeting assistant for OrgMeet, a governance and meeting management platform. Help with meeting summaries, agenda suggestions, motion drafting, and general meeting assistance.',
                messages: [
                    {
                        role: 'user',
                        content: context.meetingContext
                            ? `Meeting Context:\n${JSON.stringify(context.meetingContext, null, 2)}\n\nRequest: ${prompt}`
                            : prompt
                    }
                ]
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Anthropic API error');
        }

        const data = await response.json();
        return data.content[0]?.text || '';
    },

    // AI helper functions
    async generateAgendaSuggestions(organizationId, meetingType) {
        return await this.callAI(organizationId,
            `Suggest a standard agenda for a ${meetingType} meeting. Provide 6-8 agenda items with titles and estimated durations.`,
            {}
        );
    },

    async generateMotionDraft(organizationId, topic, context) {
        return await this.callAI(organizationId,
            `Draft a formal motion about: ${topic}. Include a title, motion text, and rationale.`,
            { meetingContext: context }
        );
    },

    async generateMeetingSummary(organizationId, meetingData) {
        return await this.callAI(organizationId,
            'Generate a concise executive summary of this meeting, highlighting key decisions, action items, and next steps.',
            { meetingContext: meetingData }
        );
    },

    // ========================================
    // Recording Management
    // ========================================

    // Get recordings for a meeting
    async getRecordings(meetingId) {
        try {
            const resp = await window.API.recordings.list(`meeting = "${meetingId}"`, 1, 50, '-recording_date');
            return resp.items || [];
        } catch (err) {
            console.error('Failed to fetch recordings:', err);
            return [];
        }
    },

    // Create recording metadata
    async createRecording(data) {
        try {
            const record = await window.API.recordings.create({
                ...data,
                created_by: this.getUser().id,
                status: data.status || 'ready'
            });
            this.showNotification('Recording added!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to add recording', 'error');
            return null;
        }
    },

    // Upload recording file
    async uploadRecording(fileInput, metadata) {
        try {
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('title', metadata.title);
            formData.append('meeting', metadata.meeting);
            formData.append('created_by', this.getUser().id);
            formData.append('status', 'processing');
            formData.append('provider', 'local');
            formData.append('file_size', fileInput.files[0].size);
            formData.append('recording_date', metadata.recording_date || new Date().toISOString());

            if (metadata.description) formData.append('description', metadata.description);
            if (metadata.visibility) formData.append('visibility', metadata.visibility);

            const record = await window.API.recordings.create(formData);
            await window.API.recordings.update(record.id, { status: 'ready' });

            this.showNotification('Recording uploaded!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to upload recording', 'error');
            return null;
        }
    },

    // Update recording
    async updateRecording(id, data) {
        try {
            const record = await window.API.recordings.update(id, data);
            this.showNotification('Recording updated!', 'success');
            return record;
        } catch (err) {
            this.showNotification(err.message || 'Failed to update recording', 'error');
            return null;
        }
    },

    // Delete recording
    async deleteRecording(id) {
        try {
            await window.API.recordings.delete(id);
            this.showNotification('Recording deleted!', 'success');
            return true;
        } catch (err) {
            this.showNotification(err.message || 'Failed to delete recording', 'error');
            return false;
        }
    },

    // Format duration
    formatDuration(seconds) {
        if (!seconds) return '0:00';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    },

    // ========================================
    // Enhanced Email Notifications
    // ========================================

    // Create notification with email content
    async createEmailNotification(meetingId, recipientId, type, options = {}) {
        try {
            const meeting = await this.getMeeting(meetingId);
            if (!meeting) throw new Error('Meeting not found');

            const notificationData = {
                meeting: meetingId,
                recipient_user: recipientId,
                notification_type: type,
                status: 'pending',
                scheduled_at: options.scheduled_at || new Date().toISOString(),
                delivery_method: options.delivery_method || 'both',
                include_ics: options.include_ics !== false
            };

            // Generate email content based on type
            if (type === 'invitation') {
                notificationData.email_subject = `You're invited: ${meeting.title}`;
                notificationData.email_body = this.generateInvitationEmail(meeting);
            } else if (type === 'reminder') {
                notificationData.email_subject = `Reminder: ${meeting.title}`;
                notificationData.email_body = this.generateReminderEmail(meeting);
            } else if (type === 'update') {
                notificationData.email_subject = `Updated: ${meeting.title}`;
                notificationData.email_body = this.generateUpdateEmail(meeting, options.changes);
            } else if (type === 'cancelled') {
                notificationData.email_subject = `Cancelled: ${meeting.title}`;
                notificationData.email_body = this.generateCancelledEmail(meeting);
            } else if (type === 'minutes_ready') {
                notificationData.email_subject = `Minutes Available: ${meeting.title}`;
                notificationData.email_body = this.generateMinutesReadyEmail(meeting);
            }

            const record = await window.API.meeting_notifications.create(notificationData);
            return record;
        } catch (err) {
            console.error('Failed to create email notification:', err);
            return null;
        }
    },

    generateInvitationEmail(meeting) {
        const meetingUrl = `${window.APP_CONFIG.SITE_URL}/pages/meeting.html?id=${meeting.id}`;
        return `
<h2>You're Invited to a Meeting</h2>
<p><strong>${meeting.title}</strong></p>
<p><strong>Date:</strong> ${this.formatDate(meeting.start_time)}</p>
${meeting.end_time ? `<p><strong>End:</strong> ${this.formatDate(meeting.end_time)}</p>` : ''}
${meeting.meeting_type ? `<p><strong>Type:</strong> ${meeting.meeting_type}</p>` : ''}
${meeting.description ? `<p>${meeting.description}</p>` : ''}
<p><a href="${meetingUrl}" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">View Meeting</a></p>
<p>Add to your calendar using the attached .ics file.</p>
<hr>
<p style="color:#6B7280;font-size:12px;">Sent via OrgMeet</p>
        `.trim();
    },

    generateReminderEmail(meeting) {
        const meetingUrl = `${window.APP_CONFIG.SITE_URL}/pages/meeting.html?id=${meeting.id}`;
        return `
<h2>Meeting Reminder</h2>
<p>This is a reminder about the upcoming meeting:</p>
<p><strong>${meeting.title}</strong></p>
<p><strong>Date:</strong> ${this.formatDate(meeting.start_time)}</p>
<p><a href="${meetingUrl}" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">Join Meeting</a></p>
<hr>
<p style="color:#6B7280;font-size:12px;">Sent via OrgMeet</p>
        `.trim();
    },

    generateUpdateEmail(meeting, changes) {
        const meetingUrl = `${window.APP_CONFIG.SITE_URL}/pages/meeting.html?id=${meeting.id}`;
        return `
<h2>Meeting Updated</h2>
<p>The following meeting has been updated:</p>
<p><strong>${meeting.title}</strong></p>
<p><strong>New Date:</strong> ${this.formatDate(meeting.start_time)}</p>
${changes ? `<p><strong>Changes:</strong> ${changes}</p>` : ''}
<p><a href="${meetingUrl}" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">View Meeting</a></p>
<hr>
<p style="color:#6B7280;font-size:12px;">Sent via OrgMeet</p>
        `.trim();
    },

    generateCancelledEmail(meeting) {
        return `
<h2>Meeting Cancelled</h2>
<p>The following meeting has been cancelled:</p>
<p><strong>${meeting.title}</strong></p>
<p><strong>Originally scheduled:</strong> ${this.formatDate(meeting.start_time)}</p>
<hr>
<p style="color:#6B7280;font-size:12px;">Sent via OrgMeet</p>
        `.trim();
    },

    generateMinutesReadyEmail(meeting) {
        const meetingUrl = `${window.APP_CONFIG.SITE_URL}/pages/meeting.html?id=${meeting.id}`;
        return `
<h2>Meeting Minutes Available</h2>
<p>The minutes for the following meeting are now available:</p>
<p><strong>${meeting.title}</strong></p>
<p><strong>Date:</strong> ${this.formatDate(meeting.start_time)}</p>
<p><a href="${meetingUrl}" style="display:inline-block;background:#3B82F6;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">View Minutes</a></p>
<hr>
<p style="color:#6B7280;font-size:12px;">Sent via OrgMeet</p>
        `.trim();
    },

    // Send invitations with email content
    async sendMeetingInvitationsWithEmail(meetingId) {
        try {
            const participants = await this.getParticipants(meetingId);
            let created = 0;

            for (const participant of participants) {
                const notification = await this.createEmailNotification(
                    meetingId,
                    participant.user,
                    'invitation',
                    { include_ics: true }
                );
                if (notification) created++;
            }

            this.showNotification(`${created} invitation(s) queued with calendar attachments!`, 'success');
            return created;
        } catch (err) {
            this.showNotification(err.message || 'Failed to send invitations', 'error');
            return 0;
        }
    },

    // ========================================
    // Organization Plan/Features
    // ========================================

    // Get organization with plan info
    async getOrganizationWithPlan(id) {
        try {
            const org = await window.API.organizations.getOne(id);
            // Set defaults for plan fields
            org.plan = org.plan || 'free';
            org.features = org.features || this.getDefaultFeatures(org.plan);
            org.max_members = org.max_members || this.getPlanLimits(org.plan).max_members;
            return org;
        } catch (err) {
            console.error('Failed to fetch organization:', err);
            return null;
        }
    },

    getDefaultFeatures(plan) {
        const features = {
            free: {
                max_meetings_per_month: 5,
                max_files_mb: 100,
                ai_enabled: false,
                recordings_enabled: false,
                custom_templates: false,
                email_notifications: true,
                calendar_sync: true
            },
            pro: {
                max_meetings_per_month: -1, // unlimited
                max_files_mb: 5000,
                ai_enabled: true,
                recordings_enabled: true,
                custom_templates: true,
                email_notifications: true,
                calendar_sync: true
            },
            enterprise: {
                max_meetings_per_month: -1,
                max_files_mb: -1, // unlimited
                ai_enabled: true,
                recordings_enabled: true,
                custom_templates: true,
                email_notifications: true,
                calendar_sync: true,
                sso_enabled: true,
                audit_logs: true
            }
        };
        return features[plan] || features.free;
    },

    getPlanLimits(plan) {
        const limits = {
            free: { max_members: 10, max_committees: 3 },
            pro: { max_members: 100, max_committees: -1 },
            enterprise: { max_members: -1, max_committees: -1 }
        };
        return limits[plan] || limits.free;
    },

    // Check if feature is enabled for organization
    async isFeatureEnabled(organizationId, feature) {
        const org = await this.getOrganizationWithPlan(organizationId);
        if (!org) return false;
        return org.features?.[feature] === true || org.features?.[feature] === -1;
    },

    // ========================================
    // Membership Module API Methods
    // ========================================

    // Get members for an organization
    async getMembers(organizationId, options = {}) {
        try {
            return await window.API.membership.members.list(organizationId, {
                page: options.page || 1,
                perPage: options.perPage || 30,
                status: options.status,
                search: options.search
            });
        } catch (err) {
            console.error('Failed to fetch members:', err);
            return { items: [], totalItems: 0, totalPages: 0 };
        }
    },

    // Create a new member
    async createMember(organizationId, data) {
        try {
            const result = await window.API.membership.members.create(organizationId, data);
            this.showNotification('Member created!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create member', 'error');
            return null;
        }
    },

    // Get contacts for an organization
    async getContacts(organizationId, options = {}) {
        try {
            return await window.API.membership.contacts.list(organizationId, {
                page: options.page || 1,
                perPage: options.perPage || 30,
                contact_type: options.contact_type,
                search: options.search
            });
        } catch (err) {
            console.error('Failed to fetch contacts:', err);
            return { items: [], totalItems: 0, totalPages: 0 };
        }
    },

    // Create a new contact
    async createContact(organizationId, data) {
        try {
            const result = await window.API.membership.contacts.create(organizationId, data);
            this.showNotification('Contact created!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create contact', 'error');
            return null;
        }
    },

    // ========================================
    // Finance Module API Methods
    // ========================================

    // Get accounts (chart of accounts)
    async getAccounts(organizationId, options = {}) {
        try {
            return await window.API.finance.accounts.list(organizationId, {
                page: options.page || 1,
                perPage: options.perPage || 100,
                account_type: options.account_type,
                is_active: options.is_active,
                search: options.search
            });
        } catch (err) {
            console.error('Failed to fetch accounts:', err);
            return { items: [], totalItems: 0, totalPages: 0 };
        }
    },

    // Create a new account
    async createAccount(organizationId, data) {
        try {
            const result = await window.API.finance.accounts.create(organizationId, data);
            this.showNotification('Account created!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create account', 'error');
            return null;
        }
    },

    // Get journal entries
    async getJournalEntries(organizationId, options = {}) {
        try {
            return await window.API.finance.journal.list(organizationId, {
                page: options.page || 1,
                perPage: options.perPage || 30,
                status: options.status,
                start_date: options.start_date,
                end_date: options.end_date
            });
        } catch (err) {
            console.error('Failed to fetch journal entries:', err);
            return { items: [], totalItems: 0, totalPages: 0 };
        }
    },

    // Create a journal entry
    async createJournalEntry(organizationId, data) {
        try {
            const result = await window.API.finance.journal.create(organizationId, data);
            this.showNotification('Journal entry created!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to create journal entry', 'error');
            return null;
        }
    },

    // Post a journal entry
    async postJournalEntry(organizationId, entryId) {
        try {
            const result = await window.API.finance.journal.post(organizationId, entryId);
            this.showNotification('Journal entry posted!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to post journal entry', 'error');
            return null;
        }
    },

    // Void a journal entry
    async voidJournalEntry(organizationId, entryId, reason) {
        try {
            const result = await window.API.finance.journal.void(organizationId, entryId);
            this.showNotification('Journal entry voided!', 'success');
            return result;
        } catch (err) {
            this.showNotification(err.message || 'Failed to void journal entry', 'error');
            return null;
        }
    },

    // Format currency
    formatCurrency(amount, currency = 'USD') {
        const num = parseFloat(amount) || 0;
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(num);
    },

    // Get member status badge class
    getMemberStatusBadgeClass(status) {
        const classes = {
            active: 'bg-green-100 text-green-700',
            inactive: 'bg-gray-100 text-gray-700',
            pending: 'bg-yellow-100 text-yellow-700',
            alumni: 'bg-blue-100 text-blue-700',
            guest: 'bg-purple-100 text-purple-700',
            honorary: 'bg-pink-100 text-pink-700',
            suspended: 'bg-red-100 text-red-700'
        };
        return classes[status] || 'bg-gray-100 text-gray-700';
    },

    // Get account type badge class
    getAccountTypeBadgeClass(type) {
        const classes = {
            asset: 'bg-blue-100 text-blue-700',
            liability: 'bg-red-100 text-red-700',
            equity: 'bg-purple-100 text-purple-700',
            revenue: 'bg-green-100 text-green-700',
            expense: 'bg-orange-100 text-orange-700'
        };
        return classes[type] || 'bg-gray-100 text-gray-700';
    }
};

// Make App globally available
window.App = App;
