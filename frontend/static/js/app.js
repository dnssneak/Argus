/* ARGUS 2.0 - Core Frontend API Client & View Controller */

let currentProjectId = null;
let allAssetsCache = [];
let activeStatusFilter = 'ALL';
let currentDeleteProjectId = null;
let loadedProjectsList = [];

// Initialize application state
document.addEventListener('DOMContentLoaded', () => {
    loadProjectSelector();
});

// Toast notification helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = 'background: var(--bg-card); border: 1px solid var(--border-accent); color: var(--text-primary); padding: 12px 18px; border-radius: 8px; font-size: 0.9rem; display: flex; align-items: center; gap: 10px; box-shadow: var(--shadow-lg); border-left: 4px solid var(--accent-purple);';
    toast.innerHTML = `<i class="fa-solid fa-circle-info" style="color: var(--accent-purple);"></i> <span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Global project selector loader
async function loadProjectSelector() {
    const select = document.getElementById('globalProjectSelect');
    if (!select) return;

    try {
        const res = await fetch('/api/v1/projects?status=ACTIVE');
        const data = await res.json();
        if (data.success) {
            select.innerHTML = '<option value="">All Projects Scope</option>';
            data.projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.asset_count} assets)`;
                select.appendChild(opt);
            });

            // Auto-select active project if in session
            if (currentProjectId) select.value = currentProjectId;

            select.addEventListener('change', (e) => {
                currentProjectId = e.target.value || null;
                if (typeof loadAssetsPage === 'function' && window.location.pathname === '/assets-page') {
                    loadAssetsPage();
                }
            });
        }
    } catch (err) {
        console.error('Failed to load project selector:', err);
    }
}

// --- PROJECTS PAGE CONTROLLER ---
async function loadProjectsPage() {
    const grid = document.getElementById('projectsGrid');
    const countLabel = document.getElementById('projectsCount');
    if (!grid) return;

    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted); font-family: var(--font-mono);">Fetching assessment projects...</div>';

    const search = document.getElementById('projectSearchInput')?.value || '';
    let url = `/api/v1/projects?status=${activeStatusFilter}`;
    if (search.trim()) {
        url += `&search=${encodeURIComponent(search.trim())}`;
    }

    try {
        const res = await fetch(url);
        const data = await res.json();

        if (data.success) {
            if (countLabel) {
                countLabel.textContent = `${data.projects.length} Total Projects`;
            }
            loadedProjectsList = data.projects || [];
            renderProjectsGrid(loadedProjectsList);
        }
    } catch (err) {
        showToast('Failed to load projects: ' + err.message, 'error');
    }
}

function filterProjectsByStatus(status) {
    activeStatusFilter = status;

    // Update active tab buttons styling while maintaining pill border-radius
    const tabs = { 'ACTIVE': 'tabActive', 'ARCHIVED': 'tabArchived', 'ALL': 'tabAll' };
    Object.keys(tabs).forEach(st => {
        const btn = document.getElementById(tabs[st]);
        if (btn) {
            btn.style.borderRadius = '30px';
            btn.style.padding = '8px 20px';
            if (st === status) {
                btn.style.background = 'rgba(168, 85, 247, 0.2)';
                btn.style.color = 'var(--accent-purple)';
                btn.style.borderColor = 'var(--border-accent)';
                btn.style.fontWeight = '600';
            } else {
                btn.style.background = 'rgba(0,0,0,0.3)';
                btn.style.color = 'var(--text-muted)';
                btn.style.borderColor = 'var(--border)';
                btn.style.fontWeight = '500';
            }
        }
    });

    loadProjectsPage();
}

function handleProjectSearch() {
    loadProjectsPage();
}

// Function to open project detail page
function openProjectDetail(id, event = null) {
    if (event) event.stopPropagation();
    if (id) {
        window.location.href = `/projects/${id}`;
    }
}

function openEditProjectModalById(id, event = null) {
    if (event) event.stopPropagation();
    const p = loadedProjectsList.find(item => item.id == id);
    if (p) {
        openEditProjectModal(p.id, p.name, p.description || '', p.status);
    }
}

function renderProjectsGrid(projects) {
    const grid = document.getElementById('projectsGrid');
    if (!grid) return;

    if (projects.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; background: var(--bg-card); border: 1px dashed var(--border); border-radius: 16px; padding: 4rem 2rem; text-align: center;">
                <div style="font-size: 3rem; color: var(--accent-purple); margin-bottom: 1rem;"><i class="fa-solid fa-folder-open"></i></div>
                <h3 style="font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem;">No Projects Found</h3>
                <p style="color: var(--text-muted); max-width: 450px; margin: 0 auto 1.5rem auto; font-size: 0.95rem;">
                    Create your first security assessment project to start building your attack surface and grouping target assets.
                </p>
                <button onclick="openCreateProjectModal()" style="background: linear-gradient(135deg, var(--accent-purple), var(--accent-magenta)); color: #fff; border: none; padding: 10px 22px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    <i class="fa-solid fa-plus"></i> Create Project
                </button>
            </div>
        `;
        return;
    }

    grid.innerHTML = projects.map(p => {
        const isArchived = p.status === 'ARCHIVED';
        const badgeStyle = isArchived
            ? 'background: rgba(251, 191, 36, 0.15); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.35);'
            : 'background: rgba(74, 222, 128, 0.15); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.3);';

        const lastScanText = p.last_scan ? new Date(p.last_scan).toLocaleDateString() : 'No scans yet';

        return `
            <div class="project-card-3d" onclick="openProjectDetail(${p.id}, event)">
                <div>
                    <!-- Header Row: ID Tag & Status Badge -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
                        <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-purple); background: rgba(168,85,247,0.1); padding: 3px 8px; border-radius: 6px; border: 1px solid var(--border-accent);">
                            <i class="fa-solid fa-hashtag" style="font-size: 0.65rem;"></i> ${p.id}
                        </span>
                        <span class="badge" style="${badgeStyle} font-family: var(--font-mono); font-size: 0.7rem; padding: 3px 10px; border-radius: 20px; font-weight: 600;">
                            ${p.status}
                        </span>
                    </div>
                    
                    <!-- Title -->
                    <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.6rem;">
                        <a href="/projects/${p.id}" onclick="openProjectDetail(${p.id}, event)" style="color: var(--text-primary); text-decoration: none; transition: color 0.2s ease;" onmouseover="this.style.color='var(--accent-purple)'" onmouseout="this.style.color='var(--text-primary)'">${escapeHtml(p.name)}</a>
                    </h3>

                    <!-- Description -->
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.25rem; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                        ${escapeHtml(p.description || 'No description provided for this assessment project.')}
                    </p>
                </div>

                <div>
                    <!-- Statistics Row -->
                    <div style="display: flex; justify-content: space-between; gap: 6px; margin-bottom: 1.25rem; font-family: var(--font-mono); font-size: 0.78rem; background: rgba(0,0,0,0.35); border: 1px solid var(--border); padding: 10px 14px; border-radius: 12px;">
                        <div style="text-align: center; flex: 1;">
                            <span style="display: block; color: var(--text-muted); font-size: 0.68rem; text-transform: uppercase;">Targets</span>
                            <strong style="color: var(--accent-purple); font-size: 0.95rem;">${p.target_count || 0}</strong>
                        </div>
                        <div style="width: 1px; background: var(--border);"></div>
                        <div style="text-align: center; flex: 1;">
                            <span style="display: block; color: var(--text-muted); font-size: 0.68rem; text-transform: uppercase;">Assets</span>
                            <strong style="color: var(--text-primary); font-size: 0.95rem;">${p.asset_count || 0}</strong>
                        </div>
                        <div style="width: 1px; background: var(--border);"></div>
                        <div style="text-align: center; flex: 1;">
                            <span style="display: block; color: var(--text-muted); font-size: 0.68rem; text-transform: uppercase;">Findings</span>
                            <strong style="color: var(--accent-magenta); font-size: 0.95rem;">${p.finding_count || 0}</strong>
                        </div>
                    </div>

                    <!-- Bottom Action Bar -->
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-top: 4px;">
                        <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono); display: flex; align-items: center; gap: 5px; min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="Last Scan: ${lastScanText}">
                            <i class="fa-regular fa-clock" style="font-size: 0.7rem; color: var(--accent-purple); flex-shrink: 0;"></i> <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${lastScanText}</span>
                        </span>
                        <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0; position: relative; z-index: 2;">
                            <button onclick="openProjectDetail(${p.id}, event)" class="btn-open-3d" style="cursor: pointer;">
                                Open <i class="fa-solid fa-arrow-right" style="font-size: 0.68rem;"></i>
                            </button>
                            <button onclick="openEditProjectModalById(${p.id}, event)" class="btn-action-icon" title="Edit Project" style="cursor: pointer;">
                                <i class="fa-solid fa-pen"></i>
                            </button>
                            <button onclick="archiveProject(${p.id}, event)" class="btn-action-icon btn-archive" title="Archive Project" style="cursor: pointer;">
                                <i class="fa-solid fa-box-archive"></i>
                            </button>
                            <button onclick="deleteProject(${p.id}, false, event)" class="btn-action-icon btn-delete" title="Delete Project" style="cursor: pointer;">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Modal Handlers
function openCreateProjectModal() {
    document.getElementById('createProjectModal')?.classList.add('active');
}

function closeCreateProjectModal() {
    document.getElementById('createProjectModal')?.classList.remove('active');
}

async function handleCreateProjectSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('projectName').value;
    const description = document.getElementById('projectDesc').value;

    try {
        const res = await fetch('/api/v1/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        const data = await res.json();

        if (data.success) {
            showToast(`Project '${name}' created successfully!`);
            closeCreateProjectModal();
            document.getElementById('createProjectForm').reset();
            loadProjectsPage();
            loadProjectSelector();
        } else {
            showToast(data.error || 'Failed to create project', 'error');
        }
    } catch (err) {
        showToast('Error creating project: ' + err.message, 'error');
    }
}

function openEditProjectModal(id, name, description, status) {
    const mId = document.getElementById('editProjectId');
    const mName = document.getElementById('editProjectName');
    const mDesc = document.getElementById('editProjectDesc');
    const mStatus = document.getElementById('editProjectStatus');

    if (mId) mId.value = id;
    if (mName) mName.value = name;
    if (mDesc) mDesc.value = description;
    if (mStatus) mStatus.value = status;

    document.getElementById('editProjectModal')?.classList.add('active');
}

function closeEditProjectModal() {
    document.getElementById('editProjectModal')?.classList.remove('active');
}

async function handleEditProjectSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('editProjectId').value;
    const name = document.getElementById('editProjectName').value;
    const description = document.getElementById('editProjectDesc').value;
    const status = document.getElementById('editProjectStatus').value;

    try {
        const res = await fetch(`/api/v1/projects/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, status })
        });
        const data = await res.json();

        if (data.success) {
            showToast('Project updated successfully.');
            closeEditProjectModal();
            loadProjectsPage();
            loadProjectSelector();
        } else {
            showToast(data.error || 'Failed to update project', 'error');
        }
    } catch (err) {
        showToast('Error updating project: ' + err.message, 'error');
    }
}

async function archiveProject(id, event = null) {
    if (event) event.stopPropagation();
    try {
        const res = await fetch(`/api/v1/projects/${id}/archive`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            showToast(data.message);
            loadProjectsPage();
            loadProjectSelector();
        } else {
            showToast(data.error || 'Failed to archive project', 'error');
        }
    } catch (err) {
        showToast('Error archiving project: ' + err.message, 'error');
    }
}

function closeDeleteProtectionModal() {
    const modal = document.getElementById('deleteProtectionModal');
    if (modal) modal.style.display = 'none';
}

// Delete Protection handling
async function deleteProject(id, force = false, event = null) {
    if (event) event.stopPropagation();
    currentDeleteProjectId = id;
    try {
        const res = await fetch(`/api/v1/projects/${id}?force=${force}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            showToast('Project deleted successfully.');
            loadProjectsPage();
            loadProjectSelector();
            closeDeleteProtectionModal();
        } else if (data.delete_protection) {
            // Display Delete Protection Warning Modal
            const counts = data.counts;
            document.getElementById('deleteProtectionText').textContent = data.error;
            document.getElementById('deleteCountsBox').innerHTML = `
                <div>Associated Records:</div>
                <div>• ${counts.assets} Discovered Assets</div>
                <div>• ${counts.findings} Security Findings</div>
                <div>• ${counts.scans} Pipeline Scans</div>
                <div>• ${counts.targets} Assessment Targets</div>
            `;

            document.getElementById('archiveInsteadBtn').onclick = () => {
                closeDeleteProtectionModal();
                archiveProject(id);
            };

            document.getElementById('forceDeleteBtn').onclick = () => {
                deleteProject(id, true);
            };

            document.getElementById('deleteProtectionModal').style.display = 'flex';
        } else {
            showToast(data.error || 'Failed to delete project', 'error');
        }
    } catch (err) {
        showToast('Error deleting project: ' + err.message, 'error');
    }
}

// --- ASSETS PAGE CONTROLLER ---
async function loadAssetsPage() {
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading assets...</td></tr>';

    try {
        let url = '/api/v1/assets';
        if (currentProjectId) {
            url += `?project_id=${currentProjectId}`;
        }
        const res = await fetch(url);
        const data = await res.json();

        if (data.success) {
            allAssetsCache = data.assets;
            renderAssetTable(allAssetsCache);
        }
    } catch (err) {
        showToast('Failed to load asset inventory: ' + err.message, 'error');
    }
}

// --- DEDICATED PROJECT DASHBOARD CONTROLLER ---
async function loadProjectDashboard(projectId) {
    try {
        const res = await fetch(`/api/v1/projects/${projectId}/dashboard`);
        const data = await res.json();

        if (data.success) {
            const p = data.data.project;
            const stats = data.data.stats;
            const targets = data.data.targets;
            const scans = data.data.scans;
            const activities = data.data.activities;

            document.getElementById('projNameText').textContent = p.name;
            document.getElementById('projDescText').textContent = p.description || 'No description provided.';
            document.getElementById('projStatusBadge').textContent = p.status;

            const badge = document.getElementById('projStatusBadge');
            if (p.status === 'ARCHIVED') {
                badge.style.cssText = 'display: inline-flex; align-items: center; height: 28px; background: rgba(251, 191, 36, 0.15); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.35); padding: 0 14px; border-radius: 30px; font-weight: 600; font-family: var(--font-mono); font-size: 0.75rem; line-height: 1; box-sizing: border-box;';
            } else {
                badge.style.cssText = 'display: inline-flex; align-items: center; height: 28px; background: rgba(74, 222, 128, 0.15); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.3); padding: 0 14px; border-radius: 30px; font-weight: 600; font-family: var(--font-mono); font-size: 0.75rem; line-height: 1; box-sizing: border-box;';
            }

            // Real Statistics Cards
            document.getElementById('statTargetsCount').textContent = stats.targets;
            document.getElementById('statAssetsCount').textContent = stats.assets;
            document.getElementById('statFindingsCount').textContent = stats.findings;
            document.getElementById('statScansCount').textContent = stats.scans;

            // Targets Container
            const targetsBox = document.getElementById('targetsContainer');
            if (targets.length === 0) {
                targetsBox.innerHTML = `
                    <div style="background: rgba(0,0,0,0.3); border: 1px dashed var(--border); border-radius: 12px; padding: 3rem 1.5rem; text-align: center;">
                        <div style="font-size: 2rem; color: var(--accent-purple); margin-bottom: 0.5rem;"><i class="fa-solid fa-bullseye"></i></div>
                        <h4 style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">No Targets Added Yet</h4>
                        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;">Add a domain, IP, CIDR range, or URL to begin discovering the attack surface.</p>
                        <button onclick="openAddTargetModal()" style="background: rgba(168, 85, 247, 0.15); border: 1px solid var(--border-accent); color: var(--accent-purple); padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">+ Add Target</button>
                    </div>
                `;
            } else {
                targetsBox.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
                        ${targets.map(t => `
                            <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 12px 18px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; width: 100%; box-sizing: border-box;">
                                <div style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-purple); font-size: 0.95rem;">${escapeHtml(t.target)}</div>
                                <div style="display: flex; gap: 10px; align-items: center;">
                                    <span class="badge" style="background: rgba(168,85,247,0.1); border: 1px solid var(--border-accent); color: var(--accent-purple); font-size: 0.75rem; padding: 3px 10px; border-radius: 20px;">${t.target_type}</span>
                                    <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">${new Date(t.created_at).toLocaleDateString()}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            // Scans Container
            const scansBox = document.getElementById('scansContainer');
            if (scans.length === 0) {
                scansBox.innerHTML = `
                    <div style="background: rgba(0,0,0,0.3); border: 1px dashed var(--border); border-radius: 12px; padding: 2.5rem 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
                        No scans executed for this project yet. Add a target to begin pipeline execution.
                    </div>
                `;
            } else {
                scansBox.innerHTML = scans.map(s => `
                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-family: var(--font-mono); font-weight: 600; color: var(--text-primary);">${escapeHtml(s.target)}</span>
                            <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 8px;">(${s.scan_type})</span>
                        </div>
                        <span class="badge" style="background: rgba(74, 222, 128, 0.15); color: #4ADE80; font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;">${s.status}</span>
                    </div>
                `).join('');
            }

            // Activity Timeline
            const actBox = document.getElementById('activitiesTimeline');
            if (activities.length === 0) {
                actBox.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No recent activities logged.</div>';
            } else {
                actBox.innerHTML = activities.map(act => `
                    <div style="font-size: 0.85rem; border-left: 2px solid var(--border-accent); padding-left: 12px;">
                        <div style="color: var(--accent-purple); font-weight: 600;">● ${escapeHtml(act.action)}</div>
                        <div style="color: var(--text-secondary); font-size: 0.8rem;">${escapeHtml(act.details || '')}</div>
                        <div style="color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); margin-top: 2px;">${new Date(act.created_at).toLocaleString()}</div>
                    </div>
                `).join('');
            }
        }
    } catch (err) {
        showToast('Error loading project dashboard: ' + err.message, 'error');
    }
}

function openAddTargetModal() {
    const modal = document.getElementById('addTargetModal');
    if (modal) modal.style.display = 'flex';
}

function closeAddTargetModal() {
    const modal = document.getElementById('addTargetModal');
    if (modal) modal.style.display = 'none';
}

async function handleAddTargetSubmit(event) {
    event.preventDefault();
    const projId = document.getElementById('currentProjectId')?.value;
    const target = document.getElementById('targetInput').value;
    const target_type = document.getElementById('targetTypeSelect').value;

    try {
        const res = await fetch(`/api/v1/projects/${projId}/targets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target, target_type })
        });
        const data = await res.json();

        if (data.success) {
            showToast(`Target '${target}' added to project.`);
            closeAddTargetModal();
            document.getElementById('addTargetForm').reset();
            loadProjectDashboard(projId);
        } else {
            showToast(data.error || 'Failed to add target', 'error');
        }
    } catch (err) {
        showToast('Error adding target: ' + err.message, 'error');
    }
}

function triggerProjectScan() {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId) return;

    fetch(`/api/v1/projects/${projId}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const targets = (data.project ? data.project.targets : (data.data ? data.data.targets : [])) || [];
                if (targets.length === 0) {
                    showToast('No targets in project scope yet! Please click "+ Add Target" first.', 'error');
                    openAddTargetModal();
                    return;
                }

                // Populate target select dropdown in startScanModal
                const select = document.getElementById('scanTargetSelect');
                if (select) {
                    select.innerHTML = targets.map(t => `<option value="${escapeHtml(t.target)}">${escapeHtml(t.target)} (${t.target_type})</option>`).join('');
                }

                // Show Launch Scan modal
                const modal = document.getElementById('startScanModal');
                if (modal) modal.style.display = 'flex';
            } else {
                showToast(data.error || 'Failed to load project targets', 'error');
            }
        })
        .catch(err => {
            showToast('Error loading project targets: ' + err.message, 'error');
        });
}

function closeStartScanModal() {
    const modal = document.getElementById('startScanModal');
    if (modal) modal.style.display = 'none';
}

function handleStartScanSubmit(event) {
    event.preventDefault();
    const target = document.getElementById('scanTargetSelect')?.value;
    const engine = document.getElementById('scanEngineSelect')?.value || 'recon';
    const projId = document.getElementById('currentProjectId')?.value;

    if (!target) {
        showToast('Please select a target to scan.', 'error');
        return;
    }

    showToast(`Launching ${engine.toUpperCase()} engine scan for '${target}'...`);
    closeStartScanModal();

    setTimeout(() => {
        let route = `/recon?target=${encodeURIComponent(target)}&project_id=${projId}`;
        if (engine === 'fingerprint') route = `/fingerprint?target=${encodeURIComponent(target)}&project_id=${projId}`;
        if (engine === 'subdomain') route = `/subdomain?target=${encodeURIComponent(target)}&project_id=${projId}`;
        window.location.href = route;
    }, 600);
}

function renderAssetTable(assets) {
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;

    if (assets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No assets found in scope. Click "Register Asset" to add targets.</td></tr>';
        return;
    }

    tbody.innerHTML = assets.map(a => {
        const riskClass = getRiskBadgeClass(a.risk_score);
        return `
            <tr>
                <td class="font-mono" style="font-weight: 600; color: var(--accent-cyan);">${escapeHtml(a.name)}</td>
                <td><span class="badge badge-blue">${escapeHtml(a.asset_type)}</span></td>
                <td class="font-mono">${escapeHtml(a.ip_address || '—')}</td>
                <td><span class="badge ${riskClass}">Risk ${a.risk_score}/100</span></td>
                <td>${a.service_count} Services</td>
                <td>${a.technology_count} Technologies</td>
                <td><span class="badge badge-info">${escapeHtml(a.status)}</span></td>
                <td>
                    <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="viewAssetDetail(${a.id})">
                        <i class="fa-solid fa-eye"></i> Details
                    </button>
                    <button style="background:none; border:none; color: var(--risk-critical); cursor:pointer; margin-left: 8px;" onclick="deleteAsset(${a.id})" title="Delete Asset">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAssets() {
    const search = document.getElementById('assetSearchInput')?.value.toLowerCase() || '';
    const type = document.getElementById('assetTypeFilter')?.value || '';

    const filtered = allAssetsCache.filter(a => {
        const matchesSearch = a.name.toLowerCase().includes(search) || 
                              (a.ip_address && a.ip_address.toLowerCase().includes(search));
        const matchesType = type ? a.asset_type === type : true;
        return matchesSearch && matchesType;
    });

    renderAssetTable(filtered);
}

function openRegisterAssetModal() {
    document.getElementById('registerAssetModal')?.classList.add('active');
}

function closeRegisterAssetModal() {
    document.getElementById('registerAssetModal')?.classList.remove('active');
}

async function handleRegisterAsset(event) {
    event.preventDefault();
    const name = document.getElementById('assetName').value;
    const asset_type = document.getElementById('assetType').value;
    const ip_address = document.getElementById('assetIp').value || null;
    const risk_score = parseInt(document.getElementById('assetRisk').value) || 0;

    try {
        const res = await fetch('/api/v1/assets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                asset_type,
                ip_address,
                risk_score,
                project_id: currentProjectId
            })
        });
        const data = await res.json();

        if (data.success) {
            showToast(`Asset '${name}' registered successfully!`);
            closeRegisterAssetModal();
            document.getElementById('registerAssetForm').reset();
            loadAssetsPage();
        } else {
            showToast(data.error || 'Failed to register asset', 'error');
        }
    } catch (err) {
        showToast('Error registering asset: ' + err.message, 'error');
    }
}

let currentActiveAssetId = null;
let currentAssetTags = [];

function switchAssetTab(tabId) {
    // Hide all tab panels
    document.querySelectorAll('.tab-content-panel').forEach(p => p.classList.remove('active'));
    // Deactivate all tab buttons
    document.querySelectorAll('.modal-tab-btn').forEach(b => b.classList.remove('active'));
    
    // Show selected panel
    const panel = document.getElementById(`panel-${tabId}`);
    if (panel) panel.classList.add('active');
    
    // Activate selected button
    const btn = document.getElementById(`tab-btn-${tabId}`);
    if (btn) btn.classList.add('active');
}

async function viewAssetDetail(assetId) {
    try {
        const res = await fetch(`/api/v1/assets/${assetId}`);
        const data = await res.json();

        if (data.success) {
            const asset = data.asset;
            currentActiveAssetId = asset.id;
            currentAssetTags = asset.tags || [];

            // Switch to overview tab by default
            switchAssetTab('overview');

            // Populate header elements
            document.getElementById('detailAssetName').textContent = asset.name;
            
            const statusBadge = document.getElementById('detailAssetStatusBadge');
            statusBadge.textContent = (asset.status || 'Active').toUpperCase();
            statusBadge.className = `badge ${asset.status === 'inactive' ? 'badge-medium' : 'badge-info'}`;

            document.getElementById('detailAssetType').textContent = asset.asset_type;
            
            const expBadge = document.getElementById('detailAssetExposure');
            expBadge.textContent = asset.exposure;
            expBadge.className = `badge ${asset.exposure === 'Internet-Facing' ? 'badge-critical' : 'badge-low'}`;
            
            document.getElementById('detailAssetConfidence').textContent = `Confidence: ${asset.confidence}%`;

            // Overview Tab
            // Risk Circle & Severity
            const riskCircle = document.getElementById('detailAssetRiskCircle');
            riskCircle.textContent = asset.risk_score;
            
            // Animate SVG circular progress
            const circleProgress = document.getElementById('riskProgressCircle');
            if (circleProgress) {
                const radius = 50;
                const circumference = 2 * Math.PI * radius; // ~314.16
                const offset = circumference - (asset.risk_score / 100) * circumference;
                circleProgress.style.strokeDashoffset = offset;
                
                // Color mapping matching cybersecurity categories
                let strokeColor = '#a855f7'; // var(--accent-purple) -> Critical / Default
                if (asset.risk_score < 20) strokeColor = '#4ade80'; // var(--accent-green) -> Info/Low
                else if (asset.risk_score < 40) strokeColor = '#fbbf24'; // var(--accent-yellow) -> Medium
                else if (asset.risk_score < 80) strokeColor = '#f87171'; // var(--accent-red) -> High
                
                circleProgress.style.stroke = strokeColor;
                circleProgress.style.filter = `drop-shadow(0 0 6px ${strokeColor})`;
            }
            
            let riskLabelClass = 'badge-info';
            let riskLabelText = 'INFORMATIONAL';
            if (asset.risk_score >= 80) {
                riskLabelClass = 'badge-critical';
                riskLabelText = 'CRITICAL';
            } else if (asset.risk_score >= 60) {
                riskLabelClass = 'badge-high';
                riskLabelText = 'HIGH';
            } else if (asset.risk_score >= 40) {
                riskLabelClass = 'badge-medium';
                riskLabelText = 'MEDIUM';
            } else if (asset.risk_score >= 20) {
                riskLabelClass = 'badge-low';
                riskLabelText = 'LOW';
            }
            
            const riskLabel = document.getElementById('detailAssetRiskLabel');
            riskLabel.textContent = riskLabelText;
            riskLabel.className = `badge ${riskLabelClass}`;
            
            // Details List
            document.getElementById('detailAssetId').textContent = `AST-${asset.id.toString().padStart(6, '0')}`;
            document.getElementById('detailAssetIp').textContent = asset.ip_address || 'Unresolved';
            document.getElementById('detailAssetFirstSeen').textContent = asset.first_seen ? new Date(asset.first_seen).toLocaleString() : '—';
            document.getElementById('detailAssetLastSeen').textContent = asset.last_seen ? new Date(asset.last_seen).toLocaleString() : '—';

            // Tags
            renderTags();

            // Risk Factors
            const riskFactorsList = document.getElementById('detailRiskFactorsList');
            if (asset.risk_factors && asset.risk_factors.length > 0) {
                riskFactorsList.innerHTML = asset.risk_factors.map(f => `
                    <div style="display: flex; gap: 8px; color: var(--accent-red); align-items: flex-start; margin-bottom: 4px;">
                        <i class="fa-solid fa-triangle-exclamation" style="margin-top: 3px;"></i>
                        <span>${escapeHtml(f)}</span>
                    </div>
                `).join('');
            } else {
                riskFactorsList.innerHTML = '<div style="color: var(--text-muted); font-style: italic;">No specific risk factors computed.</div>';
            }

            // Discovery Sources
            const discoverySourcesList = document.getElementById('detailDiscoverySourcesList');
            const possibleSources = ["Subdomain Discovery", "DNS Enumeration", "Certificate Transparency", "IP Resolution", "Port Scan", "HTTP Probe", "Technology Fingerprint"];
            discoverySourcesList.innerHTML = possibleSources.map(src => {
                const found = (asset.discovery_sources || []).some(s => s.toLowerCase().includes(src.split(' ')[0].toLowerCase()));
                return `
                    <div style="display: flex; align-items: center; gap: 10px; color: ${found ? 'var(--text-primary)' : 'var(--text-muted)'}; margin-bottom: 4px;">
                        <i class="fa-solid ${found ? 'fa-square-check' : 'fa-square'}" style="color: ${found ? 'var(--accent-purple)' : 'var(--text-muted)'}; font-size: 1.1rem;"></i>
                        <span>${src}</span>
                    </div>
                `;
            }).join('');

            // Infrastructure Tab
            // Services
            const servicesContainer = document.getElementById('detailServicesContainer');
            if (asset.services && asset.services.length > 0) {
                servicesContainer.innerHTML = asset.services.map(s => `
                    <div class="detail-item" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span class="font-mono" style="font-weight: 700; color: var(--accent-purple);">${s.port}/${s.protocol.toUpperCase()}</span>
                            <span style="margin-left: 8px; color: var(--text-secondary);">${escapeHtml(s.service_name)}</span>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">${escapeHtml(s.version || 'unknown version')}</div>
                        </div>
                        <div style="text-align: right;">
                            <span class="badge badge-cyan" style="font-size: 0.7rem;">${escapeHtml(s.state)}</span>
                            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">${escapeHtml(s.discovery_source || 'Scan')}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                servicesContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic; padding: 10px;">No open ports or services detected.</div>';
            }

            // Tech Stack
            const techContainer = document.getElementById('detailTechContainer');
            if (asset.technologies && asset.technologies.length > 0) {
                techContainer.innerHTML = asset.technologies.map(t => `
                    <div class="detail-item" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <strong style="color: var(--text-primary);">${escapeHtml(t.name)}</strong>
                            <span style="color: var(--text-muted); font-size: 0.8rem; margin-left: 4px;">${escapeHtml(t.version || 'detected')}</span>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">Category: ${escapeHtml(t.category || 'general')}</div>
                        </div>
                        <div style="text-align: right;">
                            <span class="badge badge-blue" style="font-size: 0.7rem;">Confidence: ${t.confidence}%</span>
                            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">Source: ${escapeHtml(t.detection_source || 'Fingerprint')}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                techContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic; padding: 10px;">No technologies fingerprinted.</div>';
            }

            // Web & Certificate Tab
            document.getElementById('detailWebUrl').textContent = asset.web_url || '—';
            document.getElementById('detailWebStatus').textContent = asset.web_status_code || '—';
            document.getElementById('detailWebTitle').textContent = asset.web_title || '—';
            document.getElementById('detailWebServerBanner').textContent = asset.web_server || '—';
            
            // Endpoints
            const endpointsContainer = document.getElementById('detailEndpointsContainer');
            if (asset.endpoints && asset.endpoints.length > 0) {
                endpointsContainer.innerHTML = asset.endpoints.map(e => `
                    <div class="font-mono" style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding: 4px 0;">
                        <span><strong style="color: var(--accent-purple);">${e.method}</strong> ${escapeHtml(e.path)}</span>
                        <span style="color: var(--accent-green);">${e.status_code || ''}</span>
                    </div>
                `).join('');
            } else {
                endpointsContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic; font-size: 0.8rem; padding: 6px;">No custom endpoints cataloged yet.</div>';
            }

            // SSL Certificate
            document.getElementById('detailCertIssuer').textContent = asset.cert_issuer || '—';
            document.getElementById('detailCertValidFrom').textContent = asset.cert_valid_from ? new Date(asset.cert_valid_from).toLocaleDateString() : '—';
            document.getElementById('detailCertExpires').textContent = asset.cert_expires ? new Date(asset.cert_expires).toLocaleDateString() : '—';
            document.getElementById('detailCertSans').textContent = (asset.cert_sans || []).join(', ') || '—';

            // Findings Tab
            const findingsContainer = document.getElementById('detailFindingsContainer');
            if (asset.findings && asset.findings.length > 0) {
                findingsContainer.innerHTML = asset.findings.map(f => {
                    let severityClass = 'badge-info';
                    if (f.severity.toLowerCase() === 'critical') severityClass = 'badge-critical';
                    else if (f.severity.toLowerCase() === 'high') severityClass = 'badge-high';
                    else if (f.severity.toLowerCase() === 'medium') severityClass = 'badge-medium';
                    else if (f.severity.toLowerCase() === 'low') severityClass = 'badge-low';

                    return `
                        <div class="card-panel" style="border-left: 4px solid var(--risk-${f.severity.toLowerCase()}); padding: 14px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <strong style="font-size: 0.95rem; color: var(--text-primary);">${escapeHtml(f.title)}</strong>
                                <span class="badge ${severityClass}">${f.severity.toUpperCase()}</span>
                            </div>
                            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px;">${escapeHtml(f.description)}</p>
                            ${f.recommendation ? `<div style="font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px; color: var(--text-muted);"><strong style="color: var(--text-secondary);">Recommendation:</strong> ${escapeHtml(f.recommendation)}</div>` : ''}
                        </div>
                    `;
                }).join('');
            } else {
                findingsContainer.innerHTML = '<div style="color: var(--text-muted); font-style: italic; text-align: center; padding: 20px;">No open security findings recorded.</div>';
            }

            // History Tab
            const historyTimeline = document.getElementById('detailHistoryTimeline');
            if (asset.history && asset.history.length > 0) {
                historyTimeline.innerHTML = asset.history.map(h => `
                    <div class="timeline-item">
                        <div class="timeline-marker"></div>
                        <div class="timeline-time">${new Date(h.created_at).toLocaleString()}</div>
                        <div class="timeline-title">${escapeHtml(h.event_name)}</div>
                        <div class="timeline-details">${escapeHtml(h.event_details || '')}</div>
                    </div>
                `).join('');
            } else {
                historyTimeline.innerHTML = `
                    <div class="timeline-item">
                        <div class="timeline-marker"></div>
                        <div class="timeline-time">${asset.first_seen ? new Date(asset.first_seen).toLocaleString() : '—'}</div>
                        <div class="timeline-title">Asset Registered</div>
                        <div class="timeline-details">Asset created in database.</div>
                    </div>
                `;
            }

            // Notes Tab
            renderNotesList(asset.notes);

            document.getElementById('assetDetailModal')?.classList.add('active');
        }
    } catch (err) {
        showToast('Error loading asset details: ' + err.message, 'error');
    }
}

function renderTags() {
    const container = document.getElementById('detailAssetTagsContainer');
    if (!container) return;

    if (currentAssetTags.length === 0) {
        container.innerHTML = '<span style="color: var(--text-muted); font-style: italic; font-size: 0.8rem;">No tags. Add some below.</span>';
        return;
    }

    container.innerHTML = currentAssetTags.map((tag, idx) => `
        <span class="badge badge-blue" style="display: inline-flex; align-items: center; gap: 6px;">
            ${escapeHtml(tag)}
            <i class="fa-solid fa-xmark" style="cursor: pointer; font-size: 0.75rem;" onclick="removeAssetTag(${idx})"></i>
        </span>
    `).join('');
}

function handleAddTagKey(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const input = document.getElementById('assetTagInput');
        const val = input.value.trim();
        if (val && !currentAssetTags.includes(val)) {
            currentAssetTags.push(val);
            renderTags();
            input.value = '';
        }
    }
}

function removeAssetTag(idx) {
    currentAssetTags.splice(idx, 1);
    renderTags();
}

async function saveAssetTags() {
    if (!currentActiveAssetId) return;

    try {
        const res = await fetch(`/api/v1/assets/${currentActiveAssetId}/tags`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags: currentAssetTags })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Asset tags saved successfully.");
            viewAssetDetail(currentActiveAssetId);
            loadAssetsPage();
        } else {
            showToast(data.error || "Failed to save tags", "error");
        }
    } catch (err) {
        showToast("Error saving tags: " + err.message, "error");
    }
}

function renderNotesList(notes) {
    const container = document.getElementById('detailNotesContainer');
    if (!container) return;

    if (!notes || notes.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-style: italic; padding: 10px; text-align: center;">No analyst notes recorded yet.</div>';
        return;
    }

    container.innerHTML = notes.map(n => `
        <div class="note-card">
            <div class="note-header">
                <strong>${escapeHtml(n.author)}</strong>
                <span>${new Date(n.created_at).toLocaleString()}</span>
            </div>
            <div class="note-content">${escapeHtml(n.content)}</div>
        </div>
    `).join('');
}

async function submitAssetNote() {
    if (!currentActiveActiveAssetId) { // Fallback check
        if (currentActiveAssetId) currentActiveActiveAssetId = currentActiveAssetId;
    }
    const targetId = currentActiveAssetId;
    if (!targetId) return;
    
    const textarea = document.getElementById('newAssetNoteContent');
    const content = textarea.value.trim();
    if (!content) {
        showToast("Please enter some note content first.", "warning");
        return;
    }

    try {
        const res = await fetch(`/api/v1/assets/${targetId}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: content,
                author: "Analyst"
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Note added successfully.");
            textarea.value = '';
            viewAssetDetail(targetId);
        } else {
            showToast(data.error || "Failed to save note", "error");
        }
    } catch (err) {
        showToast("Error adding note: " + err.message, "error");
    }
}

async function triggerAssetOnDemandScan() {
    if (!currentActiveAssetId) return;
    
    const btn = document.getElementById('btnDetailScan');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';
    
    showToast("Background scan started. Resolving IP, scanning ports, and fingerprinting technologies...");
    
    try {
        const res = await fetch(`/api/v1/assets/${currentActiveAssetId}/scan`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.success) {
            showToast("Scan completed! Attack surface updated successfully.");
            viewAssetDetail(currentActiveAssetId);
            loadAssetsPage();
        } else {
            showToast(data.error || "Scan failed.", "error");
        }
    } catch (err) {
        showToast("Error triggering scan: " + err.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function closeAssetDetailModal() {
    document.getElementById('assetDetailModal')?.classList.remove('active');
}

async function deleteAsset(id) {
    if (!confirm('Are you sure you want to remove this asset?')) return;

    try {
        const res = await fetch(`/api/v1/assets/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Asset removed.');
            loadAssetsPage();
        }
    } catch (err) {
        showToast('Error removing asset: ' + err.message, 'error');
    }
}

// Utility functions
function getRiskBadgeClass(score) {
    if (score >= 80) return 'badge-critical';
    if (score >= 60) return 'badge-high';
    if (score >= 40) return 'badge-medium';
    if (score >= 20) return 'badge-low';
    return 'badge-info';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
