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
    if (!currentActiveAssetId) return;
    
    const textarea = document.getElementById('newAssetNoteContent');
    const content = textarea.value.trim();
    if (!content) {
        showToast("Please enter some note content first.", "warning");
        return;
    }

    try {
        const res = await fetch(`/api/v1/assets/${currentActiveAssetId}/notes`, {
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
            viewAssetDetail(currentActiveAssetId);
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
