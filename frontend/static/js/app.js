/* ARGUS 2.0 - Core Frontend API Client & View Controller */

let currentProjectId = null;
let allAssetsCache = [];

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
    toast.innerHTML = `<i class="fa-solid fa-circle-info" style="color: var(--accent-cyan);"></i> <span>${message}</span>`;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Global project selector loader
async function loadProjectSelector() {
    const select = document.getElementById('globalProjectSelect');
    if (!select) return;

    try {
        const res = await fetch('/api/v1/projects');
        const data = await res.json();
        if (data.success) {
            select.innerHTML = '<option value="">All Projects</option>';
            data.projects.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.name} (${p.asset_count} assets)`;
                select.appendChild(opt);
            });

            select.addEventListener('change', (e) => {
                currentProjectId = e.target.value ? parseInt(e.target.value) : null;
                // Reload current view if on assets or dashboard
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

    grid.innerHTML = '<div class="metric-sub">Loading assessment projects...</div>';

    try {
        const res = await fetch('/api/v1/projects');
        const data = await res.json();

        if (data.success) {
            countLabel.textContent = `${data.projects.length} Total Projects`;

            if (data.projects.length === 0) {
                grid.innerHTML = '<div class="metric-sub">No projects found. Click "New Project" to create one.</div>';
                return;
            }

            grid.innerHTML = data.projects.map(p => `
                <div class="metric-card">
                    <div class="metric-header">
                        <span style="font-weight: 700; font-size: 16px; color: var(--text-primary);">${escapeHtml(p.name)}</span>
                        <button onclick="deleteProject(${p.id})" style="background:none; border:none; color: var(--risk-critical); cursor:pointer;" title="Delete Project">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                    <p class="metric-sub">${escapeHtml(p.description || 'No description provided.')}</p>
                    <div style="display: flex; gap: 12px; margin-top: 8px;">
                        <span class="badge badge-cyan">${p.asset_count} Assets</span>
                        <span class="badge badge-blue">${p.scan_count} Scans</span>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        showToast('Failed to load projects: ' + err.message, 'error');
    }
}

function openCreateProjectModal() {
    document.getElementById('createProjectModal')?.classList.add('active');
}

function closeCreateProjectModal() {
    document.getElementById('createProjectModal')?.classList.remove('active');
}

async function handleCreateProject(event) {
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

async function deleteProject(id) {
    if (!confirm('Are you sure you want to delete this project and all associated assets?')) return;

    try {
        const res = await fetch(`/api/v1/projects/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast('Project deleted successfully.');
            loadProjectsPage();
            loadProjectSelector();
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

async function viewAssetDetail(assetId) {
    try {
        const res = await fetch(`/api/v1/assets/${assetId}`);
        const data = await res.json();

        if (data.success) {
            const asset = data.asset;
            document.getElementById('detailAssetName').textContent = asset.name;

            const content = document.getElementById('assetDetailContent');
            content.innerHTML = `
                <div style="display: flex; gap: 12px;">
                    <span class="badge badge-blue">Type: ${escapeHtml(asset.asset_type)}</span>
                    <span class="badge ${getRiskBadgeClass(asset.risk_score)}">Risk Score: ${asset.risk_score}/100</span>
                    <span class="badge badge-cyan">IP: ${asset.ip_address || 'Unresolved'}</span>
                </div>

                <div class="card-panel" style="padding: 16px;">
                    <h4 style="margin-bottom: 8px; font-size: 14px;">Open Services (${asset.services.length})</h4>
                    ${asset.services.length === 0 ? '<p class="metric-sub">No services detected yet.</p>' : 
                        asset.services.map(s => `<div class="font-mono" style="font-size: 12px; padding: 4px 0;">${s.port}/${s.protocol} - ${s.service_name} (${s.version || 'unknown'})</div>`).join('')
                    }
                </div>

                <div class="card-panel" style="padding: 16px;">
                    <h4 style="margin-bottom: 8px; font-size: 14px;">Detected Tech Stack (${asset.technologies.length})</h4>
                    ${asset.technologies.length === 0 ? '<p class="metric-sub">No technologies fingerprinted yet.</p>' : 
                        asset.technologies.map(t => `<span class="badge badge-cyan" style="margin-right: 6px;">${t.name} ${t.version || ''}</span>`).join('')
                    }
                </div>

                <div class="card-panel" style="padding: 16px;">
                    <h4 style="margin-bottom: 8px; font-size: 14px;">Associated Findings (${asset.findings.length})</h4>
                    ${asset.findings.length === 0 ? '<p class="metric-sub">No security findings recorded.</p>' : 
                        asset.findings.map(f => `<div style="font-size: 12px; margin-bottom: 4px;"><strong>[${f.severity}]</strong> ${f.title}</div>`).join('')
                    }
                </div>
            `;

            document.getElementById('assetDetailModal')?.classList.add('active');
        }
    } catch (err) {
        showToast('Error loading asset details: ' + err.message, 'error');
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
