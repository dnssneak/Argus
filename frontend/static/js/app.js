/* ARGUS 2.0 - Core Frontend API Client & View Controller */

let currentProjectId = null;
let allAssetsCache = [];
let activeStatusFilter = 'ALL';
let currentDeleteProjectId = null;
let loadedProjectsList = [];

// Timezone-aware date helpers
function parseUtcDate(dateStr) {
    if (!dateStr) return null;
    let s = String(dateStr).trim();
    if (!s.endsWith('Z') && !s.includes('+') && !s.includes('Z')) {
        s += 'Z';
    }
    return new Date(s);
}

function formatDateLocal(dateStr) {
    const d = parseUtcDate(dateStr);
    return d && !isNaN(d) ? d.toLocaleDateString() : '—';
}

function formatDateTimeLocal(dateStr) {
    const d = parseUtcDate(dateStr);
    return d && !isNaN(d) ? d.toLocaleString() : '—';
}

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
        const isArchived = (p.status || '').toUpperCase() === 'ARCHIVED';
        const badgeStyle = isArchived
            ? 'background: rgba(251, 191, 36, 0.15); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.35);'
            : 'background: rgba(74, 222, 128, 0.15); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.3);';

        const archiveBtnClass = isArchived ? 'btn-activate' : 'btn-archive';
        const archiveBtnTitle = isArchived ? 'Activate Project' : 'Archive Project';
        const archiveBtnIcon = isArchived ? 'fa-box-open' : 'fa-box-archive';
        const archiveBtnStyle = isArchived
            ? 'color: #4ADE80 !important; border-color: rgba(74, 222, 128, 0.4) !important; background: rgba(74, 222, 128, 0.12) !important;'
            : 'color: #FBBF24 !important; border-color: rgba(251, 191, 36, 0.4) !important; background: rgba(251, 191, 36, 0.12) !important;';

        const lastScanText = p.last_scan ? formatDateTimeLocal(p.last_scan) : 'No scans yet';

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
                            <button type="button" onclick="openProjectDetail(${p.id}, event)" class="btn-open-3d">
                                Open <i class="fa-solid fa-arrow-right" style="font-size: 0.68rem;"></i>
                            </button>
                            <button type="button" onclick="openEditProjectModalById(${p.id}, event)" class="btn-action-icon" title="Edit Project">
                                <i class="fa-solid fa-pen" style="font-size: 0.75rem;"></i>
                            </button>
                            <button type="button" onclick="archiveProject(${p.id}, event)" class="btn-action-icon ${archiveBtnClass}" title="${archiveBtnTitle}" style="${archiveBtnStyle}">
                                <i class="fa-solid ${archiveBtnIcon}" style="font-size: 0.75rem;"></i>
                            </button>
                            <button type="button" onclick="confirmDeleteProject(${p.id}, '${escapeHtml(p.name)}', event)" class="btn-action-icon btn-delete" title="Delete Project">
                                <i class="fa-solid fa-trash" style="font-size: 0.75rem;"></i>
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
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
    }
}

function closeCreateProjectModal() {
    const modal = document.getElementById('createProjectModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
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

    const modal = document.getElementById('editProjectModal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
    }
}

function closeEditProjectModal() {
    const modal = document.getElementById('editProjectModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
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
            if (document.getElementById('currentProjectId')?.value == id) {
                loadProjectDashboard(id);
            }
        } else {
            showToast(data.error || 'Failed to archive project', 'error');
        }
    } catch (err) {
        showToast('Error archiving project: ' + err.message, 'error');
    }
}

function closeDeleteProtectionModal() {
    const modal = document.getElementById('deleteProtectionModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

let targetDeleteProjectId = null;

function confirmDeleteProject(id, projectName = 'Project', event = null) {
    if (event) event.stopPropagation();
    targetDeleteProjectId = id;
    const nameElem = document.getElementById('confirmDeleteProjectName');
    if (nameElem) nameElem.textContent = projectName;
    const modal = document.getElementById('confirmDeleteProjectModal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('active');
    }
}

function closeConfirmDeleteProjectModal() {
    const modal = document.getElementById('confirmDeleteProjectModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

function proceedDeleteProject() {
    if (targetDeleteProjectId) {
        const idToDelete = targetDeleteProjectId;
        closeConfirmDeleteProjectModal();
        deleteProject(idToDelete, false);
    }
}

function closeDeleteProtectionModal() {
    const modal = document.getElementById('deleteProtectionModal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
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
            const counts = data.counts || { assets: 0, findings: 0, scans: 0, targets: 0 };
            const textElem = document.getElementById('deleteProtectionText');
            if (textElem) textElem.textContent = data.error || 'Project has active dependencies.';

            const countsElem = document.getElementById('deleteCountsBox');
            if (countsElem) {
                countsElem.innerHTML = `
                    <div>Associated Records:</div>
                    <div>• ${counts.assets || 0} Discovered Assets</div>
                    <div>• ${counts.findings || 0} Security Findings</div>
                    <div>• ${counts.scans || 0} Pipeline Scans</div>
                    <div>• ${counts.targets || 0} Assessment Targets</div>
                `;
            }

            const archiveBtn = document.getElementById('archiveInsteadBtn');
            if (archiveBtn) {
                archiveBtn.onclick = () => {
                    closeDeleteProtectionModal();
                    archiveProject(id);
                };
            }

            const forceBtn = document.getElementById('forceDeleteBtn');
            if (forceBtn) {
                forceBtn.onclick = () => {
                    deleteProject(id, true);
                };
            }

            const modal = document.getElementById('deleteProtectionModal');
            if (modal) {
                modal.style.display = 'flex';
                modal.classList.add('active');
            }
        } else {
            showToast(data.error || 'Failed to delete project', 'error');
        }
    } catch (err) {
        showToast('Error deleting project: ' + err.message, 'error');
    }
}

// --- ASSETS PAGE CONTROLLER ---
async function loadAssetsProjectFilterOptions() {
    const filterSelect = document.getElementById('assetProjectFilter');
    const modalSelect = document.getElementById('assetProject');
    if (!filterSelect && !modalSelect) return;

    try {
        const res = await fetch('/api/v1/projects');
        const data = await res.json();
        if (data.success && data.projects) {
            if (filterSelect) {
                const selectedVal = filterSelect.value || currentProjectId || '';
                filterSelect.innerHTML = '<option value="">All Projects Scope</option>' +
                    data.projects.map(p => `<option value="${p.id}" ${p.id == selectedVal ? 'selected' : ''}>${escapeHtml(p.name)}</option>`).join('');
            }
            if (modalSelect) {
                modalSelect.innerHTML = data.projects.map(p => `<option value="${p.id}" ${p.id == currentProjectId ? 'selected' : ''}>${escapeHtml(p.name)}</option>`).join('');
            }
        }
    } catch (err) {
        console.error('Error loading project options:', err);
    }
}

async function handleAssetProjectFilterChange() {
    const filterSelect = document.getElementById('assetProjectFilter');
    if (filterSelect) {
        const projId = filterSelect.value;
        currentProjectId = projId || null;
        if (projId) {
            localStorage.setItem('currentProjectId', projId);
        } else {
            localStorage.removeItem('currentProjectId');
        }
        loadAssetsPage();
    }
}

async function loadAssetsPage() {
    loadAssetsProjectFilterOptions();
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading assets...</td></tr>';

    try {
        let url = '/api/v1/assets';
        const projectFilterVal = document.getElementById('assetProjectFilter')?.value;
        const activeProjId = projectFilterVal || currentProjectId;
        if (activeProjId) {
            url += `?project_id=${activeProjId}`;
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
let currentActiveScanId = null;

// --- DEDICATED PROJECT DASHBOARD CONTROLLER ---
async function loadProjectDashboard(projectId) {
    try {
        const res = await fetch(`/api/v1/projects/${projectId}/dashboard`);
        const data = await res.json();

        if (data.success) {
            const p = data.data.project;
            const stats = data.data.stats;
            const targets = data.data.targets;
            const activities = data.data.activities;

            if (document.getElementById('projNameText')) document.getElementById('projNameText').textContent = p.name;
            if (document.getElementById('projDescText')) document.getElementById('projDescText').textContent = p.description || 'No description provided.';
            if (document.getElementById('projStatusBadge')) document.getElementById('projStatusBadge').textContent = p.status;

            const badge = document.getElementById('projStatusBadge');
            if (badge) {
                if (p.status === 'ARCHIVED') {
                    badge.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; height: 30px; background: rgba(251, 191, 36, 0.18); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.4); padding: 0 16px; border-radius: 30px; font-weight: 700; font-family: var(--font-mono); font-size: 0.78rem; line-height: 1; box-sizing: border-box; flex-shrink: 0; margin: 0 !important; vertical-align: middle;';
                } else {
                    badge.style.cssText = 'display: inline-flex; align-items: center; justify-content: center; height: 30px; background: rgba(74, 222, 128, 0.18); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.35); padding: 0 16px; border-radius: 30px; font-weight: 700; font-family: var(--font-mono); font-size: 0.78rem; line-height: 1; box-sizing: border-box; flex-shrink: 0; margin: 0 !important; vertical-align: middle;';
                }
            }

            // Real Statistics Cards
            if (document.getElementById('statTargetsCount')) document.getElementById('statTargetsCount').textContent = stats.targets;
            if (document.getElementById('statAssetsCount')) document.getElementById('statAssetsCount').textContent = stats.assets;
            if (document.getElementById('statFindingsCount')) document.getElementById('statFindingsCount').textContent = stats.findings;
            if (document.getElementById('statScansCount')) document.getElementById('statScansCount').textContent = stats.scans;

            // Targets Container
            const targetsBox = document.getElementById('targetsContainer');
            if (targetsBox) {
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
                        <div style="display: flex; flex-direction: column; gap: 10px; width: 100%;">
                            ${targets.map(t => `
                                <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 14px 18px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; width: 100%; box-sizing: border-box; flex-wrap: wrap; gap: 10px;">
                                    <div>
                                        <div style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-purple); font-size: 1rem;">${escapeHtml(t.target)}</div>
                                        <div style="display: flex; gap: 10px; align-items: center; margin-top: 4px;">
                                            <span class="badge" style="background: rgba(168,85,247,0.1); border: 1px solid var(--border-accent); color: var(--accent-purple); font-size: 0.72rem; padding: 2px 8px; border-radius: 20px;">${t.target_type}</span>
                                            <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">Added: ${formatDateLocal(t.created_at)}</span>
                                            <span style="font-size: 0.75rem; color: var(--text-secondary); font-family: var(--font-mono);">Status: ${escapeHtml(t.status || 'active')}</span>
                                        </div>
                                    </div>
                                    <div style="display: flex; gap: 8px;">
                                        <button onclick="openScanConfigModal('${escapeHtml(t.target)}')" style="background: linear-gradient(135deg, var(--accent-purple), var(--accent-magenta)); color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 0.82rem; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                                            <i class="fa-solid fa-play"></i> Scan Target
                                        </button>
                                        <button onclick="viewTargetHistory('${escapeHtml(t.target)}')" style="background: rgba(0,0,0,0.4); color: var(--text-secondary); border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;" title="View Target History">
                                            <i class="fa-solid fa-clock-rotate-left"></i>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
            }

            // Activity Timeline
            const actBox = document.getElementById('activitiesTimeline');
            if (actBox) {
                if (activities.length === 0) {
                    actBox.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No recent activities logged.</div>';
                } else {
                    actBox.innerHTML = activities.map(act => `
                        <div style="font-size: 0.85rem; border-left: 2px solid var(--border-accent); padding-left: 12px;">
                            <div style="color: var(--accent-purple); font-weight: 600;">● ${escapeHtml(act.action)}</div>
                            <div style="color: var(--text-secondary); font-size: 0.8rem;">${escapeHtml(act.details || '')}</div>
                            <div style="color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); margin-top: 2px;">${formatDateTimeLocal(act.created_at)}</div>
                        </div>
                    `).join('');
                }
            }

            // Load Scan History, Assets & Topology Graph for Project
            loadProjectScansHistory(projectId);
            loadProjectAssets(projectId);
            loadProjectTopologyGraph(projectId);
        }
    } catch (err) {
        showToast('Error loading project dashboard: ' + err.message, 'error');
    }
}

async function loadProjectAssets(projectId) {
    const box = document.getElementById('projectAssetsContainer');
    if (!box) return;

    try {
        const res = await fetch(`/api/v1/assets?project_id=${projectId}`);
        const data = await res.json();

        if (data.success && data.assets) {
            const assets = data.assets;
            if (assets.length === 0) {
                box.innerHTML = `
                    <div style="background: rgba(0,0,0,0.3); border: 1px dashed var(--border); border-radius: 12px; padding: 2rem 1.5rem; text-align: center;">
                        <div style="font-size: 1.8rem; color: var(--text-muted); margin-bottom: 0.5rem;"><i class="fa-solid fa-cubes"></i></div>
                        <h4 style="font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">No Discovered Assets Yet</h4>
                        <p style="color: var(--text-muted); font-size: 0.85rem;">Run target scans to automatically discover domains, subdomains, IPs, and services for this project.</p>
                    </div>
                `;
            } else {
                box.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; padding-right: 4px;">
                        ${assets.map(a => `
                            <div style="background: rgba(0,0,0,0.35); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                                <div>
                                    <div style="font-family: var(--font-mono); font-weight: 700; color: var(--text-primary); font-size: 0.9rem;">
                                        ${escapeHtml(a.name)}
                                        <span class="badge badge-purple" style="font-size: 0.68rem; margin-left: 6px;">${a.asset_type}</span>
                                    </div>
                                    <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">
                                        IP: ${a.ip_address || 'Unresolved'} | Ports: ${a.service_count || 0} | Risk: ${a.risk_score || 0}
                                    </div>
                                </div>
                                <button onclick="openAssetDetailModal(${a.id})" class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.75rem; border-radius: 6px; cursor: pointer;">
                                    View Profile
                                </button>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
        }
    } catch (err) {
        console.error('Error loading project assets:', err);
    }
}

// ADD TARGET MODAL CONTROLLERS
function openAddTargetModal() {
    const modal = document.getElementById('addTargetModal');
    if (modal) modal.classList.add('active');
}

function closeAddTargetModal() {
    const modal = document.getElementById('addTargetModal');
    if (modal) modal.classList.remove('active');
}

async function handleAddTargetSubmit(event) {
    event.preventDefault();
    const projId = document.getElementById('currentProjectId')?.value;
    const target = document.getElementById('targetInput')?.value;
    const target_type = document.getElementById('targetTypeSelect')?.value;

    if (!projId || !target) {
        showToast('Please enter a valid target.', 'error');
        return;
    }

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
            document.getElementById('addTargetForm')?.reset();
            loadProjectDashboard(projId);
        } else {
            showToast(data.error || 'Failed to add target', 'error');
        }
    } catch (err) {
        showToast('Error adding target: ' + err.message, 'error');
    }
}

// CLEAR SCAN HISTORY CONTROLLERS
function confirmClearScanHistory() {
    const modal = document.getElementById('clearScanHistoryModal');
    if (modal) modal.classList.add('active');
}

function closeClearScanHistoryModal() {
    const modal = document.getElementById('clearScanHistoryModal');
    if (modal) modal.classList.remove('active');
}

async function executeClearScanHistory() {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId) return;

    try {
        const res = await fetch(`/api/v1/projects/${projId}/scans`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message || 'Scan history cleared.');
            closeClearScanHistoryModal();
            loadProjectDashboard(projId);
        } else {
            showToast(data.error || 'Failed to clear scan history', 'error');
        }
    } catch (err) {
        showToast('Error clearing scan history: ' + err.message, 'error');
    }
}

async function loadProjectScansHistory(projectId) {
    const box = document.getElementById('scansHistoryContainer');
    if (!box) return;

    try {
        const res = await fetch(`/api/v1/projects/${projectId}/scans`);
        const data = await res.json();

        if (data.success) {
            const scans = data.scans || [];
            if (scans.length === 0) {
                box.innerHTML = `
                    <div style="background: rgba(0,0,0,0.3); border: 1px dashed var(--border); border-radius: 12px; padding: 2.5rem 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
                        No scans executed for this project yet. Click "Scan Target" on a target above to start a scan.
                    </div>
                `;
            } else {
                box.innerHTML = scans.map(s => {
                    const statusClass = s.status === 'completed'
                        ? 'background: rgba(74, 222, 128, 0.15); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.3);'
                        : 'background: rgba(248, 113, 113, 0.15); color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3);';

                    const dateStr = s.start_time ? formatDateTimeLocal(s.start_time) : 'N/A';

                    return `
                        <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-family: var(--font-mono); font-weight: 700; color: var(--text-primary); font-size: 0.95rem;">#${s.id} — ${escapeHtml(s.target)}</span>
                                    <span class="badge" style="${statusClass} font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; text-transform: uppercase;">${s.status}</span>
                                </div>
                                <div style="font-size: 0.78rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 3px;">
                                    Capabilities: <span style="color: var(--accent-purple);">${escapeHtml(s.scan_type)}</span> | Date: ${dateStr}
                                </div>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button onclick="viewHistoricalScan(${s.id})" style="background: rgba(168, 85, 247, 0.15); border: 1px solid var(--border-accent); color: var(--accent-purple); padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                                    <i class="fa-solid fa-eye"></i> View
                                </button>
                                <button onclick="rerunScan(${s.id})" style="background: rgba(0,0,0,0.4); border: 1px solid var(--border); color: var(--text-primary); padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                                    <i class="fa-solid fa-rotate-right"></i> Re-run
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        }
    } catch (err) {
        console.error('Error loading scan history:', err);
    }
}

// SCAN CONFIGURATION & EXECUTION MODAL CONTROLLERS
function openScanConfigModal(targetName = '', preselectedCaps = null) {
    const modal = document.getElementById('scanConfigModal');
    if (!modal) return;

    if (targetName) {
        document.getElementById('scanConfigTargetText').textContent = targetName;
        document.getElementById('scanConfigTargetInput').value = targetName;
    }

    if (preselectedCaps && Array.isArray(preselectedCaps)) {
        document.getElementById('capSubdomain').checked = preselectedCaps.includes('subdomain');
        document.getElementById('capPorts').checked = preselectedCaps.includes('ports');
        document.getElementById('capRecon').checked = preselectedCaps.includes('recon');
        document.getElementById('capWeb').checked = preselectedCaps.includes('web');
    } else {
        document.getElementById('capSubdomain').checked = true;
        document.getElementById('capPorts').checked = true;
        document.getElementById('capRecon').checked = true;
        document.getElementById('capWeb').checked = true;
    }

    togglePortConfigDisplay();

    document.getElementById('scanConfigStep').style.display = 'block';
    document.getElementById('scanProgressStep').style.display = 'none';
    modal.classList.add('active');
}

function closeScanConfigModal() {
    const modal = document.getElementById('scanConfigModal');
    if (modal) modal.classList.remove('active');
}

function togglePortConfigDisplay() {
    const cb = document.getElementById('capPorts');
    const opts = document.getElementById('portConfigOptions');
    if (cb && opts) {
        opts.style.display = cb.checked ? 'block' : 'none';
    }
}

function toggleCmdOutput(cap) {
    const box = document.getElementById(`cmdBox-${cap}`);
    const chevron = document.getElementById(`cmdChevron-${cap}`);
    if (box) {
        const isHidden = box.style.display === 'none';
        box.style.display = isHidden ? 'block' : 'none';
        if (chevron) {
            chevron.className = isHidden ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
        }
    }
}

function generateCmdLogText(cap, target, status, results) {
    if (cap === 'subdomain') {
        if (status === 'running') {
            return `$ argus-subdomain-enum --target ${target} --mode deep\n[+] Initializing Subdomain Discovery Engine v2.0...\n[+] Querying DNS A/AAAA records & Certificate Transparency logs...\n[+] Enumerating subdomains for ${target}...`;
        }
        const subData = results?.subdomain || {};
        const subs = subData.subdomains || [];
        let out = `$ argus-subdomain-enum --target ${target} --mode deep\n[+] Initializing Subdomain Discovery Engine v2.0...\n[+] Querying DNS A/AAAA records & Certificate Transparency logs...\n[+] Discovered ${subs.length} active subdomains:\n`;
        if (subs.length === 0) {
            out += `    └── ${target} (Primary target resolved)\n`;
        } else {
            subs.slice(0, 8).forEach((s, idx) => {
                const isLast = idx === Math.min(subs.length, 8) - 1;
                const prefix = isLast ? '    └── ' : '    ├── ';
                const name = typeof s === 'object' ? (s.name || s.domain) : s;
                out += `${prefix}${name}\n`;
            });
            if (subs.length > 8) out += `    ... and ${subs.length - 8} more subdomains.\n`;
        }
        out += `[+] Subdomain Enumeration Completed. [Exit Code: 0]`;
        return out;
    }

    if (cap === 'ports') {
        if (status === 'running') {
            return `$ nmap -sV -p 1-1024,1433,3306,3389,5432,8080,8443 --open ${target}\n[+] Starting Nmap 7.94 service detection...\n[+] Scanning 1,030 ports against ${target}...`;
        }
        const portData = results?.ports || {};
        const services = portData.services || [];
        let out = `$ nmap -sV -p 1-1024,1433,3306,3389,5432,8080,8443 --open ${target}\n[+] Starting Nmap 7.94 ( https://nmap.org ) service scan...\n[+] Target host: ${target} [Status: ${portData.host_status || 'Up'}]\n[+] Discovered Open Ports & Services:\n`;
        if (services.length === 0) {
            out += `    └── No open ports found in scanned range.\n`;
        } else {
            services.forEach((s, idx) => {
                const isLast = idx === services.length - 1;
                const prefix = isLast ? '    └── ' : '    ├── ';
                out += `${prefix}${s.port}/${s.protocol || 'tcp'}  OPEN  ${s.name || s.service_name || 'service'}  ${s.version || ''}\n`;
            });
        }
        out += `[+] Nmap scan report complete. [Exit Code: 0]`;
        return out;
    }

    if (cap === 'recon') {
        if (status === 'running') {
            return `$ argus-recon --whois --dns-harvest --geo-ip ${target}\n[+] Initiating Passive Reconnaissance & Intelligence Gathering...\n[+] Harvesting DNS records, WHOIS registry data, and IP WHOIS...`;
        }
        const reconData = results?.recon || {};
        let out = `$ argus-recon --whois --dns-harvest --geo-ip ${target}\n[+] Initiating Passive Reconnaissance & Intelligence Gathering...\n`;
        out += `[+] WHOIS Lookup: Registrar: ${reconData.registrar || 'MarkMonitor Inc.'}\n`;
        out += `[+] DNS Records: IP: ${reconData.resolved_ip || 'Resolved'} | MX: ${reconData.mx_records ? reconData.mx_records.length : '1'} records\n`;
        out += `[+] IP Geolocation: ${reconData.geolocation || 'United States (AS15169 Google LLC)'}\n`;
        out += `[+] Security Headers: ${reconData.security_headers ? Object.keys(reconData.security_headers).join(', ') : 'Strict-Transport-Security, X-Frame-Options'}\n`;
        out += `[+] Reconnaissance Complete. [Exit Code: 0]`;
        return out;
    }

    if (cap === 'web') {
        if (status === 'running') {
            return `$ argus-fingerprint --url http://${target} --stack --security-headers\n[+] Sending HTTP GET request to http://${target}...\n[+] Inspecting HTTP response headers and DOM fingerprints...`;
        }
        const webData = results?.web || {};
        let out = `$ argus-fingerprint --url http://${target} --stack --security-headers\n[+] Sending HTTP GET request to http://${target}...\n`;
        out += `[+] HTTP Response Status: ${webData.status_code || 200} OK\n`;
        out += `[+] Web Server Detected: ${webData.server || 'gws / Nginx'}\n`;
        const techs = webData.technologies ? webData.technologies.map(t => typeof t === 'object' ? t.name : t).join(', ') : 'Web Server, HSTS, HTTP/2';
        out += `[+] Tech Stack Fingerprints: [${techs}]\n`;
        out += `[+] Web Footprinting Completed. [Exit Code: 0]`;
        return out;
    }

    return `$ executing ${cap} on ${target}...`;
}

async function handleExecuteProjectScanSubmit(event) {
    event.preventDefault();
    const projId = document.getElementById('currentProjectId')?.value;
    const target = document.getElementById('scanConfigTargetInput')?.value;

    if (!projId || !target) {
        showToast('Invalid project or target selected for scan.', 'error');
        return;
    }

    const capabilities = [];
    if (document.getElementById('capSubdomain')?.checked) capabilities.push('subdomain');
    if (document.getElementById('capPorts')?.checked) capabilities.push('ports');
    if (document.getElementById('capRecon')?.checked) capabilities.push('recon');
    if (document.getElementById('capWeb')?.checked) capabilities.push('web');

    if (capabilities.length === 0) {
        showToast('Please select at least one scan capability to run.', 'error');
        return;
    }

    const config = {
        port_scan_type: document.getElementById('portScanTypeSelect')?.value || 'full'
    };

    // Transition modal view to Progress step
    document.getElementById('scanConfigStep').style.display = 'none';
    document.getElementById('scanProgressStep').style.display = 'block';
    document.getElementById('progressTargetText').textContent = `Target: ${target}`;
    document.getElementById('viewResultsBtn').style.display = 'none';

    // Build progress items with collapsible CMD terminal drawers
    const progressContainer = document.getElementById('progressItemsContainer');
    const capNames = {
        'subdomain': 'Subdomain Discovery',
        'ports': 'Port Scanning',
        'recon': 'Reconnaissance',
        'web': 'Web Footprinting'
    };

    progressContainer.innerHTML = capabilities.map(cap => `
        <div id="progItem-${cap}" style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; overflow: hidden;">
            <div style="padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-weight: 600; color: var(--text-primary); font-size: 0.92rem;">${capNames[cap]}</span>
                    <span class="prog-status-badge badge" style="background: rgba(251, 191, 36, 0.15); color: #FBBF24; font-size: 0.75rem; border: 1px solid rgba(251, 191, 36, 0.3);">Running...</span>
                </div>
                <button type="button" onclick="toggleCmdOutput('${cap}')" id="cmdToggleBtn-${cap}" style="background: rgba(168, 85, 247, 0.12); border: 1px solid var(--border-accent); color: var(--accent-purple); width: 32px; height: 32px; border-radius: 8px; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease;" title="Toggle Command Execution Console">
                    <i class="fa-solid fa-chevron-down" id="cmdChevron-${cap}"></i>
                </button>
            </div>
            <div id="cmdBox-${cap}" style="display: none; background: #08090c; border-top: 1px solid rgba(255,255,255,0.08); padding: 12px 16px; font-family: 'Consolas', 'Monaco', monospace; font-size: 0.78rem; color: #4ADE80; max-height: 180px; overflow-y: auto; line-height: 1.55; box-shadow: inset 0 2px 8px rgba(0,0,0,0.5);">
                <div style="color: #6B7280; font-size: 0.72rem; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 4px;">
                    <span>[ARGUS CLI TERMINAL - ${capNames[cap].toUpperCase()}]</span>
                    <span style="color: #4ADE80; font-size: 0.68rem;">● ACTIVE EXECUTION</span>
                </div>
                <div id="cmdLogContent-${cap}" style="white-space: pre-wrap;">${generateCmdLogText(cap, target, 'running', null)}</div>
            </div>
        </div>
    `).join('');

    try {
        const res = await fetch(`/api/v1/projects/${projId}/scans`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target, capabilities, config })
        });
        const data = await res.json();

        if (data.success) {
            const scan = data.scan;
            currentActiveScanId = scan.id;

            // Mark all selected items as completed & update CMD log output with scan findings
            capabilities.forEach(cap => {
                const badge = document.querySelector(`#progItem-${cap} .prog-status-badge`);
                if (badge) {
                    badge.textContent = '✓ Completed';
                    badge.style.cssText = 'background: rgba(74, 222, 128, 0.15); color: #4ADE80; font-size: 0.75rem; border: 1px solid rgba(74, 222, 128, 0.3);';
                }
                const logBox = document.getElementById(`cmdLogContent-${cap}`);
                if (logBox) {
                    logBox.textContent = generateCmdLogText(cap, target, 'completed', scan.results_parsed);
                }
            });

            document.getElementById('overallStatusBadge').textContent = 'Overall Status: Completed';
            document.getElementById('overallStatusBadge').style.cssText = 'background: rgba(74, 222, 128, 0.15); color: #4ADE80; border: 1px solid rgba(74, 222, 128, 0.3);';
            document.getElementById('viewResultsBtn').style.display = 'inline-flex';

            showToast(`Scan #${scan.id} completed successfully for '${target}'.`);
            loadProjectDashboard(projId);
        } else {
            document.getElementById('overallStatusBadge').textContent = 'Overall Status: Failed';
            document.getElementById('overallStatusBadge').style.cssText = 'background: rgba(248, 113, 113, 0.15); color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3);';
            showToast(data.error || 'Scan execution failed.', 'error');
        }
    } catch (err) {
        showToast('Error executing project scan: ' + err.message, 'error');
    }
}

function openScanResultsFromProgress() {
    closeScanConfigModal();
    if (currentActiveScanId) {
        viewHistoricalScan(currentActiveScanId);
    }
}

async function viewHistoricalScan(scanId) {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId) return;

    try {
        const res = await fetch(`/api/v1/projects/${projId}/scans/${scanId}`);
        const data = await res.json();

        if (data.success) {
            const scan = data.scan;
            currentActiveScanId = scan.id;

            document.getElementById('resHeaderTarget').textContent = `Target: ${scan.target} | Scan #${scan.id} (${scan.scan_type})`;

            const container = document.getElementById('scanResultsContent');
            const results = scan.results_parsed || {};

            let html = '';

            // Subdomains Result Section
            if (results.subdomain) {
                const sub = results.subdomain;
                const list = sub.subdomains || [];
                html += `
                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;">
                        <h4 style="color: var(--accent-purple); font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-sitemap"></i> Subdomain Discovery (${sub.total_found || list.length} Found)
                        </h4>
                        ${list.length === 0 ? '<p style="color: var(--text-muted); font-size: 0.85rem;">No subdomains discovered.</p>' : `
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                                    <thead><tr style="text-align: left; border-bottom: 1px solid var(--border); color: var(--text-muted); font-family: var(--font-mono);"><th style="padding: 8px;">Subdomain</th><th style="padding: 8px;">Status</th><th style="padding: 8px;">IP Address</th></tr></thead>
                                    <tbody>
                                        ${list.map(s => `
                                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                                <td style="padding: 8px; font-family: var(--font-mono); color: var(--accent-purple); font-weight: 600;">${escapeHtml(s.subdomain)}</td>
                                                <td style="padding: 8px;"><span class="badge" style="background: rgba(74, 222, 128, 0.15); color: #4ADE80; font-size: 0.72rem;">${s.status}</span></td>
                                                <td style="padding: 8px; font-family: var(--font-mono);">${escapeHtml(s.ip_address)}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        `}
                    </div>
                `;
            }

            // Port Scan Result Section
            if (results.ports) {
                const p = results.ports;
                const openPorts = p.open_ports || [];
                const services = p.services || [];
                html += `
                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;">
                        <h4 style="color: var(--accent-purple); font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-network-wired"></i> Port Scanning & Services (${openPorts.length} Open Ports)
                        </h4>
                        <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 10px; font-family: var(--font-mono);">
                            Host Status: <strong style="color: #4ADE80;">${escapeHtml(p.host_status || 'Up')}</strong> | Scan Status: ${escapeHtml(p.scan_status || 'Completed')}
                        </div>
                        ${services.length === 0 ? '<p style="color: var(--text-muted); font-size: 0.85rem;">No open network services detected.</p>' : `
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                                    <thead><tr style="text-align: left; border-bottom: 1px solid var(--border); color: var(--text-muted); font-family: var(--font-mono);"><th style="padding: 8px;">Port/Proto</th><th style="padding: 8px;">Service Name</th><th style="padding: 8px;">Detected Version</th></tr></thead>
                                    <tbody>
                                        ${services.map(s => `
                                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                                <td style="padding: 8px; font-family: var(--font-mono); color: var(--accent-purple); font-weight: 600;">${s.port}/${s.protocol}</td>
                                                <td style="padding: 8px; font-weight: 600;">${escapeHtml(s.name)}</td>
                                                <td style="padding: 8px; font-family: var(--font-mono); color: var(--text-secondary);">${escapeHtml(s.version || '—')}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        `}
                    </div>
                `;
            }

            // Web Footprinting Result Section
            if (results.web) {
                const w = results.web;
                const ts = w.tech_stack || {};
                const meta = w.metadata || {};
                html += `
                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;">
                        <h4 style="color: var(--accent-purple); font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-globe"></i> Web Footprinting & Tech Stack
                        </h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.85rem;">
                            <div>
                                <strong style="color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); text-transform: uppercase;">TECHNOLOGY FINGERPRINT</strong>
                                <div style="margin-top: 6px;">Web Server: <strong>${escapeHtml(ts.web_server || w.web_server || 'Unknown')}</strong></div>
                                <div>Backend Stack: <strong>${escapeHtml(ts.backend || w.backend || 'Unknown')}</strong></div>
                                <div>CMS: <strong>${escapeHtml(ts.cms || w.cms || 'None Detected')}</strong></div>
                                <div>Frontend Frameworks: <strong>${escapeHtml(ts.frontend_frameworks || w.frontend || 'None')}</strong></div>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); text-transform: uppercase;">SCRAPED METADATA</strong>
                                <div style="margin-top: 6px;">Page Title: <strong>${escapeHtml(meta.title || 'N/A')}</strong></div>
                                <div>HTTP Status: <strong>${w.http_status || '200 OK'}</strong></div>
                            </div>
                        </div>
                    </div>
                `;
            }

            // Recon Result Section
            if (results.recon) {
                const r = results.recon;
                const whois = r.whois || {};
                const geo = r.ip_geolocation || {};
                html += `
                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem;">
                        <h4 style="color: var(--accent-purple); font-size: 1.05rem; font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                            <i class="fa-solid fa-magnifying-glass"></i> Reconnaissance & OSINT
                        </h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 0.85rem;">
                            <div>
                                <strong style="color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); text-transform: uppercase;">WHOIS INFO</strong>
                                <div style="margin-top: 6px;">Registrar: <strong>${escapeHtml(whois.registrar || 'N/A')}</strong></div>
                                <div>Created: <strong>${escapeHtml(whois.creation_date || 'N/A')}</strong></div>
                            </div>
                            <div>
                                <strong style="color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); text-transform: uppercase;">IP GEOLOCATION</strong>
                                <div style="margin-top: 6px;">IP Address: <strong>${escapeHtml(geo.ip_address || 'N/A')}</strong></div>
                                <div>Location: <strong>${escapeHtml((geo.city || '') + ' ' + (geo.country || '')) || 'N/A'}</strong></div>
                            </div>
                        </div>
                    </div>
                `;
            }

            container.innerHTML = html || '<p style="color: var(--text-muted);">No scan results recorded.</p>';

            const modal = document.getElementById('scanResultsModal');
            if (modal) modal.classList.add('active');
        }
    } catch (err) {
        showToast('Error loading scan details: ' + err.message, 'error');
    }
}

function closeScanResultsModal() {
    const modal = document.getElementById('scanResultsModal');
    if (modal) modal.classList.remove('active');
}

async function rerunScan(scanId) {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId) return;

    try {
        const res = await fetch(`/api/v1/projects/${projId}/scans/${scanId}`);
        const data = await res.json();

        if (data.success) {
            const scan = data.scan;
            const scanTypeStr = (scan.scan_type || '').toLowerCase();
            const selectedCaps = [];
            if (scanTypeStr.includes('subdomain')) selectedCaps.push('subdomain');
            if (scanTypeStr.includes('port')) selectedCaps.push('ports');
            if (scanTypeStr.includes('recon')) selectedCaps.push('recon');
            if (scanTypeStr.includes('web')) selectedCaps.push('web');

            openScanConfigModal(scan.target, selectedCaps);
        }
    } catch (err) {
        showToast('Error populating re-run configuration: ' + err.message, 'error');
    }
}

async function generateReportForCurrentScan(reportType = 'html') {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId || !currentActiveScanId) {
        showToast('No active scan selected for report generation.', 'error');
        return;
    }

    try {
        const res = await fetch(`/api/v1/projects/${projId}/scans/${currentActiveScanId}/report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ report_type: reportType })
        });
        const data = await res.json();

        if (data.success && data.download_url) {
            showToast('Generating report file...');
            window.location.href = data.download_url;
        } else {
            showToast(data.error || 'Failed to generate report', 'error');
        }
    } catch (err) {
        showToast('Error generating report: ' + err.message, 'error');
    }
}

async function viewTargetHistory(targetName) {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId) return;

    try {
        const res = await fetch(`/api/v1/projects/${projId}/scans`);
        const data = await res.json();

        if (data.success) {
            const scans = (data.scans || []).filter(s => s.target === targetName);
            document.getElementById('targetHistoryTitle').textContent = `Scan History — ${targetName}`;

            const box = document.getElementById('targetHistoryContent');
            if (scans.length === 0) {
                box.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">No scans recorded yet for '${escapeHtml(targetName)}'.</p>`;
            } else {
                box.innerHTML = scans.map(s => `
                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-family: var(--font-mono); font-weight: 700; color: var(--accent-purple);">Scan #${s.id}</span>
                            <span style="font-size: 0.8rem; color: var(--text-secondary); margin-left: 8px;">${s.scan_type}</span>
                            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 2px;">${new Date(s.start_time).toLocaleString()}</div>
                        </div>
                        <button onclick="closeTargetHistoryModal(); viewHistoricalScan(${s.id});" style="background: rgba(168, 85, 247, 0.15); border: 1px solid var(--border-accent); color: var(--accent-purple); padding: 4px 10px; border-radius: 4px; font-size: 0.78rem; cursor: pointer;">
                            View Results
                        </button>
                    </div>
                `).join('');
            }

            const modal = document.getElementById('targetHistoryModal');
            if (modal) modal.classList.add('active');
        }
    } catch (err) {
        showToast('Error fetching target history: ' + err.message, 'error');
    }
}

function closeTargetHistoryModal() {
    const modal = document.getElementById('targetHistoryModal');
    if (modal) modal.classList.remove('active');
}

function renderAssetTable(assets) {
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;

    if (assets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No discovered assets in scope yet. Run target scans under Projects to discover assets automatically.</td></tr>';
        return;
    }

    tbody.innerHTML = assets.map(a => {
        const riskClass = getRiskBadgeClass(a.risk_score);
        return `
            <tr>
                <td class="font-mono" style="font-weight: 600; color: var(--accent-cyan); white-space: nowrap;">${escapeHtml(a.name)}</td>
                <td style="white-space: nowrap;"><span class="badge badge-blue">${escapeHtml(a.asset_type)}</span></td>
                <td class="font-mono" style="white-space: nowrap;">${escapeHtml(a.ip_address || '—')}</td>
                <td style="white-space: nowrap;"><span class="badge ${riskClass}">Risk ${a.risk_score}/100</span></td>
                <td style="white-space: nowrap;">${a.service_count} Services</td>
                <td style="white-space: nowrap;">${a.technology_count} Technologies</td>
                <td style="white-space: nowrap;"><span class="badge badge-info">${escapeHtml(a.status)}</span></td>
                <td style="white-space: nowrap;">
                    <div style="display: inline-flex; align-items: center; gap: 8px;">
                        <button class="btn-action-icon" style="background: rgba(168, 85, 247, 0.15) !important; border: 1px solid var(--border-accent) !important; color: var(--accent-purple) !important; width: 32px; height: 32px; border-radius: 8px; font-size: 0.85rem; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s ease;" onclick="viewAssetDetail(${a.id})" title="View Asset Profile Details">
                            <i class="fa-solid fa-eye"></i>
                        </button>
                        <button class="btn-action-icon btn-delete" style="background: rgba(0, 0, 0, 0.4) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; color: var(--risk-critical) !important; width: 32px; height: 32px; border-radius: 8px; font-size: 0.85rem; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: all 0.2s ease;" onclick="deleteAsset(${a.id})" title="Delete Asset">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
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
    loadAssetsProjectFilterOptions();
    document.getElementById('registerAssetModal')?.classList.add('active');
}

function closeRegisterAssetModal() {
    document.getElementById('registerAssetModal')?.classList.remove('active');
}

async function handleRegisterAsset(event) {
    event.preventDefault();
    const proj_id = document.getElementById('assetProject')?.value || currentProjectId;
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
                project_id: proj_id
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

    if (tabId === 'relationships' && currentActiveAssetId) {
        loadAssetRelationshipGraph(currentActiveAssetId);
    }
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


// --- ASSET CORRELATION & RELATIONGRAPH CONTROLLER & UN-JUMBLE ENGINE ---

let currentAssetGraphData = null;
let currentProjectGraphData = null;
let activeAssetZoom = null;
let activeProjectZoom = null;
let activeFullscreenZoom = null;
let currentFullscreenScope = 'asset'; // 'asset' or 'project'
const activeSimulations = {};

function toggleFilterChip(input) {
    if (!input) return;
    const chip = input.closest('.filter-chip');
    if (!chip) return;
    if (input.checked) {
        chip.classList.add('active');
    } else {
        chip.classList.remove('active');
    }
}

async function loadAssetRelationshipGraph(assetId) {
    const spinner = document.getElementById('assetGraphSpinner');
    if (spinner) spinner.style.display = 'flex';

    try {
        const res = await fetch(`/api/v1/assets/${assetId}/graph?depth=2`);
        const data = await res.json();

        if (data.success && data.graph) {
            currentAssetGraphData = data.graph;
            renderAssetRelationshipGraph();
        } else {
            showToast(data.error || "Failed to load relationship graph", "error");
        }
    } catch (err) {
        showToast("Error loading graph: " + err.message, "error");
    } finally {
        if (spinner) spinner.style.display = 'none';
    }
}

function updateAssetGraphFilters() {
    renderAssetRelationshipGraph();
}

function resetAssetGraphZoom() {
    if (activeAssetZoom) {
        const svg = d3.select("#assetGraphSvg");
        svg.transition().duration(500).call(activeAssetZoom.transform, d3.zoomIdentity);
    }
}

async function triggerAssetGraphRecorrelate() {
    const projId = document.getElementById('assetProjectFilter')?.value || localStorage.getItem('currentProjectId');
    if (!projId) {
        if (currentActiveAssetId) loadAssetRelationshipGraph(currentActiveAssetId);
        return;
    }
    try {
        showToast("Recorrelating project assets and relationships...");
        const res = await fetch(`/api/v1/projects/${projId}/correlate`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            if (currentActiveAssetId) loadAssetRelationshipGraph(currentActiveAssetId);
        }
    } catch (err) {
        showToast("Recorrelation failed: " + err.message, "error");
    }
}

async function loadProjectTopologyGraph(projectId) {
    const spinner = document.getElementById('projectGraphSpinner');
    if (spinner) spinner.style.display = 'flex';

    try {
        const res = await fetch(`/api/v1/projects/${projectId}/graph`);
        const data = await res.json();

        if (data.success && data.graph) {
            currentProjectGraphData = data.graph;
            renderD3Graph("projectGraphSvg", data.graph, false);
        }
    } catch (err) {
        console.error("Topology graph load error:", err);
    } finally {
        if (spinner) spinner.style.display = 'none';
    }
}

function resetProjectGraphZoom() {
    if (activeProjectZoom) {
        const svg = d3.select("#projectGraphSvg");
        svg.transition().duration(500).call(activeProjectZoom.transform, d3.zoomIdentity);
    }
}

async function triggerProjectGraphRecorrelate() {
    const projId = document.getElementById('currentProjectId')?.value;
    if (!projId) return;

    try {
        showToast("Re-building project relationship graph...");
        const res = await fetch(`/api/v1/projects/${projId}/correlate`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message);
            loadProjectTopologyGraph(projId);
        }
    } catch (err) {
        showToast("Correlation error: " + err.message, "error");
    }
}

// --- FULLSCREEN EXPANDED GRAPH MODAL CONTROLLER ---

function openFullscreenGraphModal(scope = 'asset') {
    currentFullscreenScope = scope;
    const modal = document.getElementById('fullscreenGraphModal');
    if (!modal) return;

    modal.classList.add('active');

    const titleEl = document.getElementById('fullGraphModalTitle');
    const subTitleEl = document.getElementById('fullGraphModalSubtitle');

    if (scope === 'asset' && currentAssetGraphData) {
        titleEl.textContent = `Asset Relationship Graph — ${currentAssetGraphData.nodes.find(n => n.id === currentAssetGraphData.root_node_id)?.label || 'Asset Profile'}`;
        subTitleEl.textContent = "Expanded interactive topology view & entity relationship analyzer";
        renderFullscreenGraph();
    } else if (scope === 'project' && currentProjectGraphData) {
        const projName = document.getElementById('projNameText')?.textContent || 'Project Scope';
        titleEl.textContent = `Attack Surface Topology Graph — ${projName}`;
        subTitleEl.textContent = "Full project-wide network hierarchy & discovered connections";
        renderFullscreenGraph();
    }
}

function closeFullscreenGraphModal() {
    const modal = document.getElementById('fullscreenGraphModal');
    if (modal) modal.classList.remove('active');
}

function updateFullscreenGraphFilters() {
    renderFullscreenGraph();
}

function resetFullscreenGraphZoom() {
    if (activeFullscreenZoom) {
        const svg = d3.select("#fullGraphSvg");
        svg.transition().duration(500).call(activeFullscreenZoom.transform, d3.zoomIdentity);
    }
}

function unjumbleGraphLayout() {
    const sim = activeSimulations["fullGraphSvg"] || activeSimulations["assetGraphSvg"] || activeSimulations["projectGraphSvg"];
    if (sim) {
        showToast("Spreading nodes and un-jumbling topology layout...");
        sim.force("charge", d3.forceManyBody().strength(-1600));
        sim.force("collision", d3.forceCollide().radius(50));
        sim.alpha(1).restart();
    }
}

async function triggerFullscreenGraphRecorrelate() {
    if (currentFullscreenScope === 'asset') {
        await triggerAssetGraphRecorrelate();
        renderFullscreenGraph();
    } else {
        await triggerProjectGraphRecorrelate();
        renderFullscreenGraph();
    }
}

function renderFullscreenGraph() {
    const spinner = document.getElementById('fullGraphSpinner');
    if (spinner) spinner.style.display = 'flex';

    setTimeout(() => {
        if (currentFullscreenScope === 'asset' && currentAssetGraphData) {
            const showSubdomains = document.getElementById('fullGraphFilterSubdomains')?.checked ?? true;
            const showIPs = document.getElementById('fullGraphFilterIPs')?.checked ?? true;
            const showPorts = document.getElementById('fullGraphFilterPorts')?.checked ?? true;
            const showTech = document.getElementById('fullGraphFilterTech')?.checked ?? true;
            const showEndpoints = document.getElementById('fullGraphFilterEndpoints')?.checked ?? true;
            const showFindings = document.getElementById('fullGraphFilterFindings')?.checked ?? true;

            const rootId = currentAssetGraphData.root_node_id;

            const filteredNodes = currentAssetGraphData.nodes.filter(n => {
                if (n.id === rootId) return true;
                const type = (n.type || '').toLowerCase();
                if (type === 'subdomain' && !showSubdomains) return false;
                if (type === 'ip' && !showIPs) return false;
                if ((type === 'port' || type === 'service') && !showPorts) return false;
                if (type === 'technology' && !showTech) return false;
                if (type === 'endpoint' && !showEndpoints) return false;
                if (type === 'finding' && !showFindings) return false;
                return true;
            });

            const nodeIds = new Set(filteredNodes.map(n => n.id));
            const filteredEdges = currentAssetGraphData.edges.filter(e => nodeIds.has(e.source_id) && nodeIds.has(e.target_id));

            renderD3Graph("fullGraphSvg", { nodes: filteredNodes, edges: filteredEdges, root_node_id: rootId }, true, true);
        } else if (currentFullscreenScope === 'project' && currentProjectGraphData) {
            renderD3Graph("fullGraphSvg", currentProjectGraphData, false, true);
        }
        if (spinner) spinner.style.display = 'none';
    }, 50);
}

function renderAssetRelationshipGraph() {
    if (!currentAssetGraphData) return;

    const showSubdomains = document.getElementById('graphFilterSubdomains')?.checked ?? true;
    const showIPs = document.getElementById('graphFilterIPs')?.checked ?? true;
    const showPorts = document.getElementById('graphFilterPorts')?.checked ?? true;
    const showTech = document.getElementById('graphFilterTech')?.checked ?? true;
    const showEndpoints = document.getElementById('graphFilterEndpoints')?.checked ?? true;
    const showFindings = document.getElementById('graphFilterFindings')?.checked ?? true;

    const rootId = currentAssetGraphData.root_node_id;

    const filteredNodes = currentAssetGraphData.nodes.filter(n => {
        if (n.id === rootId) return true;
        const type = (n.type || '').toLowerCase();
        if (type === 'subdomain' && !showSubdomains) return false;
        if (type === 'ip' && !showIPs) return false;
        if ((type === 'port' || type === 'service') && !showPorts) return false;
        if (type === 'technology' && !showTech) return false;
        if (type === 'endpoint' && !showEndpoints) return false;
        if (type === 'finding' && !showFindings) return false;
        return true;
    });

    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = currentAssetGraphData.edges.filter(e => nodeIds.has(e.source_id) && nodeIds.has(e.target_id));

    renderD3Graph("assetGraphSvg", { nodes: filteredNodes, edges: filteredEdges, root_node_id: rootId }, true, false);
}

function getNodeColor(type) {
    switch ((type || '').toLowerCase()) {
        case 'domain':
        case 'subdomain':
            return '#a855f7'; // Purple
        case 'ip':
            return '#3b82f6'; // Blue
        case 'port':
            return '#f59e0b'; // Amber
        case 'service':
            return '#eab308'; // Yellow
        case 'technology':
            return '#10b981'; // Emerald Green
        case 'endpoint':
            return '#06b6d4'; // Cyan
        case 'certificate':
            return '#ec4899'; // Pink
        case 'finding':
            return '#ef4444'; // Red
        case 'scan':
            return '#8b5cf6'; // Violet
        case 'target':
        case 'project':
            return '#f43f5e'; // Rose
        default:
            return '#a855f7';
    }
}

function getRingRadius(type) {
    switch ((type || '').toLowerCase()) {
        case 'project':
        case 'target':
            return 0;
        case 'domain':
        case 'subdomain':
        case 'ip':
            return 160;
        case 'port':
        case 'service':
        case 'technology':
            return 280;
        case 'endpoint':
        case 'certificate':
        case 'finding':
        case 'scan':
            return 400;
        default:
            return 220;
    }
}



function renderD3Graph(svgId, graphData, isAssetScope, isFullscreen = false) {
    const svgEl = document.getElementById(svgId);
    if (!svgEl) return;

    const width = svgEl.clientWidth || (isFullscreen ? 1500 : 800);
    const height = svgEl.clientHeight || (isFullscreen ? 800 : 420);

    const svg = d3.select("#" + svgId);
    svg.selectAll("*").remove();

    if (!graphData.nodes || graphData.nodes.length === 0) {
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height / 2)
            .attr("text-anchor", "middle")
            .attr("fill", "#6b7280")
            .attr("font-family", "var(--font-mono)")
            .text("No correlated relationships discovered yet.");
        return;
    }

    const rootId = graphData.root_node_id;

    // Calculate radial initial positions to prevent node jumbling
    const nodes = graphData.nodes.map((d, idx, arr) => {
        let initX = width / 2;
        let initY = height / 2;
        if (d.id !== rootId) {
            const angle = (idx / arr.length) * 2 * Math.PI;
            const r = getRingRadius(d.type) * (isFullscreen ? 1.3 : 1.0);
            initX += r * Math.cos(angle);
            initY += r * Math.sin(angle);
        }
        return {
            x: initX,
            y: initY,
            ...d
        };
    });

    const links = graphData.edges.map(e => ({
        source: e.source_id,
        target: e.target_id,
        ...e
    }));

    // SVG Defs for Markers & Glow
    const defs = svg.append("defs");
    
    defs.append("marker")
        .attr("id", `arrow-${svgId}`)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", isFullscreen ? 26 : 22)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#6b7280");

    const filter = defs.append("filter").attr("id", `glow-${svgId}`);
    filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const containerGroup = svg.append("g");

    // Zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.2, 5])
        .on("zoom", (event) => {
            containerGroup.attr("transform", event.transform);
        });

    svg.call(zoom);
    if (isFullscreen) activeFullscreenZoom = zoom;
    else if (isAssetScope) activeAssetZoom = zoom;
    else activeProjectZoom = zoom;

    // Spaced Un-jumbled Force Simulation Setup
    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(isFullscreen ? 160 : 120))
        .force("charge", d3.forceManyBody().strength(isFullscreen ? -1100 : -750))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(d => (d.id === rootId ? 55 : (isFullscreen ? 45 : 36))))
        .force("radial", d3.forceRadial(d => getRingRadius(d.type) * (isFullscreen ? 1.2 : 0.9), width / 2, height / 2).strength(0.35));

    activeSimulations[svgId] = simulation;

    // Links
    const link = containerGroup.append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("stroke", d => d.status === 'stale' ? '#4b5563' : '#6b7280')
        .attr("stroke-opacity", d => d.status === 'stale' ? 0.35 : 0.6)
        .attr("stroke-width", isFullscreen ? 2.2 : 1.8)
        .attr("stroke-dasharray", d => d.status === 'stale' ? '4,4' : 'none')
        .attr("marker-end", `url(#arrow-${svgId})`);

    // Edge Labels
    const linkText = containerGroup.append("g")
        .selectAll("text")
        .data(links)
        .enter()
        .append("text")
        .attr("font-size", isFullscreen ? "10px" : "9px")
        .attr("font-family", "var(--font-mono)")
        .attr("fill", "#9ca3af")
        .attr("text-anchor", "middle")
        .text(d => (d.relationship_type || '').replace(/_/g, ' '));

    // Nodes
    const node = containerGroup.append("g")
        .selectAll("g")
        .data(nodes)
        .enter()
        .append("g")
        .style("cursor", "pointer")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    // Outer Circle Glow
    node.append("circle")
        .attr("r", d => d.id === rootId ? (isFullscreen ? 28 : 24) : (d.is_asset ? (isFullscreen ? 22 : 18) : (isFullscreen ? 16 : 14)))
        .attr("fill", d => getNodeColor(d.type))
        .attr("fill-opacity", 0.2)
        .attr("stroke", d => getNodeColor(d.type))
        .attr("stroke-width", d => d.id === rootId ? 3 : 1.5)
        .style("filter", `url(#glow-${svgId})`);

    // Inner Circle
    node.append("circle")
        .attr("r", d => d.id === rootId ? (isFullscreen ? 18 : 16) : (d.is_asset ? (isFullscreen ? 14 : 12) : (isFullscreen ? 11 : 9)))
        .attr("fill", d => getNodeColor(d.type))
        .attr("stroke", "#ffffff")
        .attr("stroke-width", 1.5);

    // Node Text Labels - ALWAYS single clean line, perfectly centered
    node.append("text")
        .attr("dy", d => (d.id === rootId ? (isFullscreen ? 40 : 34) : (isFullscreen ? 30 : 26)))
        .attr("text-anchor", "middle")
        .attr("font-size", d => d.id === rootId ? "12px" : (isFullscreen ? "11px" : "10px"))
        .attr("font-family", "var(--font-mono)")
        .attr("font-weight", d => d.id === rootId ? "700" : "500")
        .attr("fill", d => d.id === rootId ? "#a855f7" : "#e5e7eb")
        .text(d => {
            const raw = (d.label || d.id).replace(/[\r\n]+/g, ' ').trim();
            const maxLen = isFullscreen ? 26 : 18;
            return raw.length > maxLen ? raw.substring(0, maxLen - 2) + '…' : raw;
        });

    // Hover Highlight Effects
    node.on("mouseover", (event, d) => {
        const connectedNodeIds = new Set([d.id]);
        links.forEach(l => {
            if (l.source.id === d.id) connectedNodeIds.add(l.target.id);
            if (l.target.id === d.id) connectedNodeIds.add(l.source.id);
        });

        node.style("opacity", n => connectedNodeIds.has(n.id) ? 1 : 0.2);
        link.style("opacity", l => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.1);
        linkText.style("opacity", l => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.1);
    }).on("mouseout", () => {
        node.style("opacity", 1);
        link.style("opacity", 1);
        linkText.style("opacity", 1);
    });

    // Node Click Listener
    node.on("click", (event, d) => {
        event.stopPropagation();

        if (isFullscreen) {
            showFullscreenGraphNodeInspector(d);
        } else if (isAssetScope) {
            showGraphNodeInspector(d);
        } else {
            if (d.asset_id) {
                viewAssetDetail(d.asset_id);
            } else {
                showToast(`Selected Node: ${d.label} (${d.type})`);
            }
        }
    });

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        linkText
            .attr("x", d => (d.source.x + d.target.x) / 2)
            .attr("y", d => (d.source.y + d.target.y) / 2 - 4);

        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

function showGraphNodeInspector(node) {
    const panel = document.getElementById('graphInspectorPanel');
    if (!panel) return;

    panel.style.display = 'block';

    const titleEl = document.getElementById('inspectorTitle');
    const badgeEl = document.getElementById('inspectorBadge');
    const contentEl = document.getElementById('inspectorContent');

    titleEl.textContent = node.label || node.id;
    badgeEl.textContent = (node.type || 'Entity').toUpperCase();
    badgeEl.className = 'badge badge-purple';

    let html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;">
            <div>Node Type: <strong style="color: var(--text-primary);">${node.type}</strong></div>
            <div>Identifier: <span class="font-mono" style="color: var(--accent-cyan);">${node.id}</span></div>
            ${node.ip_address ? `<div>IP Address: <span class="font-mono">${node.ip_address}</span></div>` : ''}
            ${node.risk_score !== undefined ? `<div>Risk Score: <strong style="color: var(--accent-purple);">${node.risk_score}/100</strong></div>` : ''}
            ${node.exposure ? `<div>Exposure: <strong>${node.exposure}</strong></div>` : ''}
        </div>
    `;

    if (node.asset_id && node.asset_id !== currentActiveAssetId) {
        html += `
            <div style="margin-top: 8px; text-align: right;">
                <button class="btn btn-primary" style="font-size: 0.78rem; padding: 4px 12px;" onclick="viewAssetDetail(${node.asset_id})">
                    <i class="fa-solid fa-arrow-right-to-bracket"></i> Open Asset Profile
                </button>
            </div>
        `;
    }

    contentEl.innerHTML = html;
}

function showFullscreenGraphNodeInspector(node) {
    const titleEl = document.getElementById('fullInspectorTitle');
    const badgeEl = document.getElementById('fullInspectorBadge');
    const contentEl = document.getElementById('fullInspectorContent');

    if (!titleEl || !contentEl) return;

    titleEl.textContent = node.label || node.id;
    badgeEl.textContent = (node.type || 'Entity').toUpperCase();
    badgeEl.className = 'badge badge-purple';

    let html = `
        <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px;">
            <div><strong style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem;">NODE ID</strong><div class="font-mono" style="color: var(--accent-cyan); word-break: break-all;">${node.id}</div></div>
            <div><strong style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem;">ENTITY TYPE</strong><div>${node.type}</div></div>
            ${node.ip_address ? `<div><strong style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem;">IP ADDRESS</strong><div class="font-mono">${node.ip_address}</div></div>` : ''}
            ${node.risk_score !== undefined ? `<div><strong style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem;">RISK SCORE</strong><div><strong style="color: var(--accent-purple);">${node.risk_score}/100</strong></div></div>` : ''}
            ${node.exposure ? `<div><strong style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem;">EXPOSURE</strong><div>${node.exposure}</div></div>` : ''}
            ${node.status ? `<div><strong style="color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem;">STATUS</strong><div><span class="badge ${node.status === 'stale' ? 'badge-medium' : 'badge-info'}">${node.status.toUpperCase()}</span></div></div>` : ''}
        </div>
    `;

    if (node.asset_id) {
        html += `
            <div style="margin-top: 12px;">
                <button class="btn btn-primary" style="width: 100%; font-size: 0.8rem; padding: 8px 12px; display: flex; align-items: center; justify-content: center; gap: 6px;" onclick="closeFullscreenGraphModal(); viewAssetDetail(${node.asset_id});">
                    <i class="fa-solid fa-arrow-right-to-bracket"></i> Open Asset Profile
                </button>
            </div>
        `;
    }

    contentEl.innerHTML = html;
}


