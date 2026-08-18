/* ARGUS 2.0 - Core Frontend API Client & View Controller */

let currentProjectId = null;
let activeStatusFilter = 'ALL';
let currentDeleteProjectId = null;

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

// Global project selector loader for navbar/footer
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
        }
    } catch (err) {
        console.error('Failed to load project selector:', err);
    }
}

// --- PROJECTS PAGE CONTROLLER ---
async function loadProjectsPage() {
    const grid = document.getElementById('projectsGrid');
    if (!grid) return;

    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted); font-family: var(--font-mono);">Fetching assessment projects...</div>';

    const search = document.getElementById('projectSearchInput')?.value || '';
    let url = `/api/v1/projects?status=${activeStatusFilter}`;
    if (search.trim()) {
        url += `&search=${encodeURIComponent(search.strip ? search.strip() : search.trim())}`;
    }

    try {
        const res = await fetch(url);
        const data = await res.json();

        if (data.success) {
            renderProjectsGrid(data.projects);
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
            <div class="project-card-3d">
                <div>
                    <!-- Header Row: ID Tag & Status Badge -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem;">
                        <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-purple); background: rgba(168,85,247,0.1); padding: 3px 8px; border-radius: 6px; border: 1px solid var(--border);">
                            <i class="fa-solid fa-hashtag" style="font-size: 0.65rem;"></i> ${p.id}
                        </span>
                        <span class="badge" style="${badgeStyle} font-family: var(--font-mono); font-size: 0.7rem; padding: 3px 10px; border-radius: 20px; font-weight: 600;">
                            ${p.status}
                        </span>
                    </div>
                    
                    <!-- Title -->
                    <h3 style="margin-bottom: 0.6rem;">
                        <a href="/projects/${p.id}" class="card-title-link">${escapeHtml(p.name)}</a>
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
                            <span style="display: block; color: var(--text-muted); font-size: 0.68rem; uppercase;">Targets</span>
                            <strong style="color: var(--accent-purple); font-size: 0.95rem;">${p.target_count || 0}</strong>
                        </div>
                        <div style="width: 1px; background: var(--border);"></div>
                        <div style="text-align: center; flex: 1;">
                            <span style="display: block; color: var(--text-muted); font-size: 0.68rem; uppercase;">Assets</span>
                            <strong style="color: var(--text-primary); font-size: 0.95rem;">${p.asset_count || 0}</strong>
                        </div>
                        <div style="width: 1px; background: var(--border);"></div>
                        <div style="text-align: center; flex: 1;">
                            <span style="display: block; color: var(--text-muted); font-size: 0.68rem; uppercase;">Findings</span>
                            <strong style="color: var(--accent-magenta); font-size: 0.95rem;">${p.finding_count || 0}</strong>
                        </div>
                    </div>

                    <!-- Bottom Action Bar -->
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px; margin-top: 4px;">
                        <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono); display: flex; align-items: center; gap: 5px; min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="Last Scan: ${lastScanText}">
                            <i class="fa-regular fa-clock" style="font-size: 0.7rem; color: var(--accent-purple); flex-shrink: 0;"></i> <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${lastScanText}</span>
                        </span>
                        <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
                            <a href="/projects/${p.id}" class="btn-open-3d">
                                Open <i class="fa-solid fa-arrow-right" style="font-size: 0.68rem;"></i>
                            </a>
                            <button onclick="openEditProjectModal(${p.id}, '${escapeHtml(p.name)}', '${escapeHtml(p.description || '')}', '${p.status}')" class="btn-action-icon" title="Edit Project">
                                <i class="fa-solid fa-pen"></i>
                            </button>
                            <button onclick="archiveProject(${p.id})" class="btn-action-icon btn-archive" title="Archive Project">
                                <i class="fa-solid fa-box-archive"></i>
                            </button>
                            <button onclick="deleteProject(${p.id})" class="btn-action-icon btn-delete" title="Delete Project">
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
    const modal = document.getElementById('createProjectModal');
    if (modal) modal.style.display = 'flex';
}

function closeCreateProjectModal() {
    const modal = document.getElementById('createProjectModal');
    if (modal) modal.style.display = 'none';
}

async function handleCreateProjectSubmit(event) {
    event.preventDefault();
    const name = document.getElementById('projectName').value;
    const description = document.getElementById('projectDesc').value;
    const status = document.getElementById('projectStatus').value;

    try {
        const res = await fetch('/api/v1/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, status })
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
    document.getElementById('editProjectId').value = id;
    document.getElementById('editProjectName').value = name;
    document.getElementById('editProjectDesc').value = description;
    document.getElementById('editProjectStatus').value = status;
    document.getElementById('editProjectModal').style.display = 'flex';
}

function closeEditProjectModal() {
    document.getElementById('editProjectModal').style.display = 'none';
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

async function archiveProject(id) {
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

// Delete Protection handling
async function deleteProject(id, force = false) {
    currentDeleteProjectId = id;
    try {
        const res = await fetch(`/api/v1/projects/${id}?force=${force}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            showToast('Project deleted successfully.');
            closeDeleteProtectionModal();
            loadProjectsPage();
            loadProjectSelector();
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

function closeDeleteProtectionModal() {
    const modal = document.getElementById('deleteProtectionModal');
    if (modal) modal.style.display = 'none';
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
                badge.style.cssText = 'background: rgba(251, 191, 36, 0.15); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.35);';
            } else {
                badge.style.cssText = 'background: rgba(74, 222, 128, 0.15); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.3);';
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
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        ${targets.map(t => `
                            <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                                <div style="font-family: var(--font-mono); font-weight: 600; color: var(--accent-purple);">${escapeHtml(t.target)}</div>
                                <div style="display: flex; gap: 10px; align-items: center;">
                                    <span class="badge" style="background: rgba(168,85,247,0.1); border: 1px solid var(--border-accent); color: var(--accent-purple); font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;">${t.target_type}</span>
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
    document.getElementById('addTargetModal').style.display = 'flex';
}

function closeAddTargetModal() {
    document.getElementById('addTargetModal').style.display = 'none';
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
    openAddTargetModal();
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
