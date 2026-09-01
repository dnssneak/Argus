// ============================================
// ARGUS - INTERACTIONS & ANIMATIONS (v2.0)
// ============================================

document.addEventListener('DOMContentLoaded', function () {
    // Mobile menu toggle
    window.toggleMenu = function () {
        const navLinks = document.querySelector('.nav-links');
        navLinks.classList.toggle('active');
    };

    // Initialize all custom animations & widgets
    initTerminalSimulator();
    initBackgroundCanvas();
    initHeroParallax();
    initWorkflowSteps();
    initScrollReveal();
    initFaqAccordion();
    initMicroInteractions();
    initCustomSelects();
});

// 1. Terminal Simulator Typewriter Sequence & Micro-Presets
function initTerminalSimulator() {
    const cmdEl = document.getElementById('terminal-cmd');
    const outputsEl = document.getElementById('terminal-outputs');
    if (!cmdEl || !outputsEl) return;

    const presetCommands = {
        'nmap -sV target.com': [
            { text: 'Starting Nmap 7.95 ( https://nmap.org ) at 2026-08-22 01:46 UTC', delay: 350 },
            { text: 'Nmap scan report for target.com (104.244.42.1)', delay: 450 },
            { text: 'Host is up (0.042s latency).', delay: 350 },
            { text: 'PORT     STATE SERVICE VERSION', delay: 500, class: 'highlight' },
            { text: '22/tcp   open  ssh     OpenSSH 8.9p1 Ubuntu 3ubuntu0.1', delay: 350, class: 'output-line' },
            { text: '80/tcp   open  http    nginx 1.18.0', delay: 300, class: 'output-line' },
            { text: '443/tcp  open  https   nginx 1.18.0', delay: 300, class: 'output-line' },
            { text: 'Nmap done: 1 IP address (1 host up) scanned in 2.84 seconds', delay: 600, class: 'success' }
        ],
        'argus --recon target.com': [
            { text: 'ARGUS RECON ENGINE v2.0 - Passive Target Discovery', delay: 350 },
            { text: 'Querying CT Logs & DNS Archives...', delay: 450, class: 'highlight' },
            { text: '[+] Subdomain: api.target.com (104.244.42.5) [ACTIVE]', delay: 350, class: 'output-line' },
            { text: '[+] Subdomain: dev.target.com (104.244.42.9) [ACTIVE]', delay: 300, class: 'output-line' },
            { text: '[+] Subdomain: mail.target.com (104.244.42.12) [ACTIVE]', delay: 300, class: 'output-line' },
            { text: 'Reconnaissance complete: 3 active subdomains identified.', delay: 600, class: 'success' }
        ],
        'argus --export-pdf': [
            { text: 'Compiling project scope: "Network Security Audit"', delay: 350 },
            { text: 'Generating compliance matrix report & host advisories...', delay: 450, class: 'highlight' },
            { text: '[✓] Asset Inventory Snapshot attached.', delay: 350, class: 'output-line' },
            { text: '[✓] Executive PDF generated: /api/v1/projects/report.pdf', delay: 500, class: 'success' }
        ]
    };

    let currentCmdKey = 'nmap -sV target.com';
    let cmdIdx = 0;
    let timerId = null;

    function typeCommand() {
        const commandText = currentCmdKey;
        if (cmdIdx < commandText.length) {
            cmdEl.textContent += commandText.charAt(cmdIdx);
            cmdIdx++;
            timerId = setTimeout(typeCommand, 40 + Math.random() * 60);
        } else {
            timerId = setTimeout(renderOutputs, 400);
        }
    }

    let outputIdx = 0;
    function renderOutputs() {
        const outputs = presetCommands[currentCmdKey] || presetCommands['nmap -sV target.com'];
        if (outputIdx < outputs.length) {
            const line = outputs[outputIdx];
            const div = document.createElement('div');
            div.className = 'terminal-line ' + (line.class || 'output-line');

            const terminalWindow = document.querySelector('.terminal-window');
            if (terminalWindow) {
                terminalWindow.style.borderColor = 'rgba(168, 85, 247, 0.45)';
                setTimeout(() => {
                    terminalWindow.style.borderColor = 'rgba(168, 85, 247, 0.15)';
                }, 150);
            }

            div.textContent = line.text;
            outputsEl.appendChild(div);

            const body = document.getElementById('terminal-body');
            if (body) body.scrollTop = body.scrollHeight;

            outputIdx++;
            timerId = setTimeout(renderOutputs, line.delay);
        } else {
            timerId = setTimeout(resetTerminal, 6000);
        }
    }

    function resetTerminal() {
        if (timerId) clearTimeout(timerId);
        cmdEl.textContent = '';
        outputsEl.innerHTML = '';
        cmdIdx = 0;
        outputIdx = 0;
        typeCommand();
    }

    // Micro-Preset Buttons Listener
    const presetBtns = document.querySelectorAll('.term-preset-btn');
    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            presetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const cmdKey = btn.getAttribute('data-cmd');
            if (cmdKey && presetCommands[cmdKey]) {
                currentCmdKey = cmdKey;
                resetTerminal();
            }
        });
    });

    typeCommand();
}

// Interactive Micro-Element Handlers (Hero Badge Ping & Card Status Toggles)
function initMicroInteractions() {
    // 1. Hero Badge Telemetry Ping
    const badgeBtn = document.getElementById('hero-badge-click');
    const badgeText = document.getElementById('hero-badge-text');
    if (badgeBtn && badgeText) {
        badgeBtn.addEventListener('click', () => {
            badgeText.textContent = 'Telemetry Ping 14ms • Operational';
            badgeBtn.style.borderColor = '#4ade80';
            badgeBtn.style.boxShadow = '0 0 20px rgba(74, 222, 128, 0.4)';
            setTimeout(() => {
                badgeText.textContent = 'v2.0 Active • Click to Ping';
                badgeBtn.style.borderColor = '';
                badgeBtn.style.boxShadow = '';
            }, 3000);
        });
    }

    // 2. Minimalist Card Status Pill Toggles
    const statusPills = document.querySelectorAll('.card-status-pill');
    statusPills.forEach(pill => {
        let state = 0;
        const states = [
            { text: 'ENFORCED', class: '' },
            { text: 'ACTIVE SCAN', class: 'state-scanning' },
            { text: 'VERIFIED', class: 'state-verified' }
        ];
        pill.addEventListener('click', (e) => {
            e.stopPropagation();
            state = (state + 1) % states.length;
            const cur = states[state];
            pill.innerHTML = `<span class="status-dot"></span> ${cur.text}`;
            pill.className = `card-status-pill ${cur.class}`;
        });
    });
}

// 2. Canvas-based Particles Network Background
// 2. High-DPI Retina Canvas Particles Background
function initBackgroundCanvas() {
    const canvas = document.getElementById('bg-network-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = window.innerWidth;
    let height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resizeCanvas() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.scale(dpr, dpr);
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let particles = [];
    const maxParticles = 65;
    const maxDistance = 140;
    let mouse = { x: null, y: null, radius: 180 };

    window.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
    });

    window.addEventListener('mouseleave', () => {
        mouse.x = null;
        mouse.y = null;
    });

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.25;
            this.vy = (Math.random() - 0.5) * 0.25;
            this.baseRadius = Math.random() * 2 + 1.2;
            this.radius = this.baseRadius;
            this.pulseSpeed = 0.02 + Math.random() * 0.02;
            this.pulseAngle = Math.random() * Math.PI * 2;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            if (this.x < 0) this.x = width;
            if (this.x > width) this.x = 0;
            if (this.y < 0) this.y = height;
            if (this.y > height) this.y = 0;

            // Organic pulse
            this.pulseAngle += this.pulseSpeed;
            this.radius = this.baseRadius + Math.sin(this.pulseAngle) * 0.5;

            // Mouse repulsion & interaction
            if (mouse.x !== null && mouse.y !== null) {
                const dx = this.x - mouse.x;
                const dy = this.y - mouse.y;
                const dist = Math.hypot(dx, dy);
                if (dist < mouse.radius) {
                    const force = (mouse.radius - dist) / mouse.radius;
                    const angle = Math.atan2(dy, dx);
                    this.x += Math.cos(angle) * force * 1.2;
                    this.y += Math.sin(angle) * force * 1.2;
                }
            }
        }

        draw() {
            // Anti-aliased glowing radial node
            ctx.save();
            const grad = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.radius * 2.5);
            grad.addColorStop(0, 'rgba(233, 213, 255, 0.95)');
            grad.addColorStop(0.4, 'rgba(168, 85, 247, 0.6)');
            grad.addColorStop(1, 'rgba(168, 85, 247, 0)');

            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius * 2.5, 0, Math.PI * 2);
            ctx.fillStyle = grad;
            ctx.fill();

            // Core point
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius * 0.7, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.restore();
        }
    }

    for (let i = 0; i < maxParticles; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // Draw smooth constellation lines
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const p1 = particles[i];
                const p2 = particles[j];
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dist = Math.hypot(dx, dy);

                if (dist < maxDistance) {
                    const alpha = (1 - dist / maxDistance) * 0.18;
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(168, 85, 247, ${alpha})`;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }
        }

        particles.forEach(p => {
            p.update();
            p.draw();
        });

        requestAnimationFrame(animate);
    }

    animate();
}

// 3. Subtle Hero Mouse Parallax
function initHeroParallax() {
    const hero = document.querySelector('.hero');
    const heroContent = document.querySelector('.hero-content');
    const heroVisual = document.querySelector('.hero-visual');
    if (!hero || !heroContent || !heroVisual) return;

    hero.addEventListener('mousemove', (e) => {
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;

        const mx1 = (dx / cx) * 5;
        const my1 = (dy / cy) * 5;
        const mx2 = (dx / cx) * -3;
        const my2 = (dy / cy) * -3;

        heroContent.style.transform = `translate(${mx1}px, ${my1}px)`;
        heroVisual.style.transform = `translate(${mx2}px, ${my2}px)`;
    });

    hero.addEventListener('mouseleave', () => {
        heroContent.style.transform = 'translate(0px, 0px)';
        heroVisual.style.transform = 'translate(0px, 0px)';
    });
}

// 4. Interactive Workflow Steps Switching
function initWorkflowSteps() {
    const steps = document.querySelectorAll('.step-item');
    const filenameEl = document.getElementById('inspector-filename');
    const codeEl = document.getElementById('inspector-code');
    if (steps.length === 0 || !filenameEl || !codeEl) return;

    const data = {
        '1': {
            filename: 'target_scope.yaml',
            code: `# Target Scope Configuration
project: "Network Security Audit"
id: "proj_92a1_recon"
targets:
  - domain: "target.com"
    ips: ["104.244.42.1"]
    policy: "stealth"`
        },
        '2': {
            filename: 'passive_discovery.json',
            code: `{
  "domain": "target.com",
  "subdomains_found": [
    {"host": "api.target.com", "ip": "104.244.42.5"},
    {"host": "dev.target.com", "ip": "104.244.42.9"},
    {"host": "mail.target.com", "ip": "104.244.42.12"}
  ]
}`
        },
        '3': {
            filename: 'active_scan_results.xml',
            code: `<!-- Nmap 7.95 Scan Output -->
<host addr="104.244.42.1">
  <ports>
    <port protocol="tcp" portid="22" state="open" service="ssh"/>
    <port protocol="tcp" portid="80" state="open" service="http"/>
    <port protocol="tcp" portid="443" state="open" service="https"/>
  </ports>
</host>`
        },
        '4': {
            filename: 'web_security_audit.json',
            code: `{
  "target": "https://target.com",
  "nikto_scan": "Completed (0 critical vulnerabilities)",
  "security_headers": {"HSTS": true, "CSP": true, "X-Frame-Options": "SAMEORIGIN"},
  "ssl_tls": "TLS 1.3 (Strong Ciphers)",
  "cors_policy": "Restricted (*)"
}`
        },
        '5': {
            filename: 'osint_intelligence.json',
            code: `{
  "wayback_machine": "1,420 historical URLs harvested",
  "search_osint": "8 public document leaks found",
  "email_harvest": ["security@target.com", "admin@target.com"],
  "archived_endpoints": ["/api/v1/beta", "/backup.zip"]
}`
        },
        '6': {
            filename: 'audit_summary.txt',
            code: `===========================================
ARGUS AUDIT REPORT SUMMARY
===========================================
Target Domain : target.com (104.244.42.1)
Open Ports    : 22/tcp, 80/tcp, 443/tcp
Nikto Status  : Clean (Header & TLS Verified)
OSINT Records : 1,420 archived endpoints
Report PDF    : /api/v1/projects/report.pdf`
        }
    };

    steps.forEach(step => {
        step.addEventListener('click', () => {
            steps.forEach(s => s.classList.remove('active'));
            step.classList.add('active');

            const stepId = step.getAttribute('data-step');
            if (data[stepId]) {
                filenameEl.textContent = data[stepId].filename;
                codeEl.textContent = data[stepId].code;

                // Move code inspector panel vertically to align with clicked step item, clamped inside section
                const workflowVisual = document.querySelector('.workflow-visual');
                const stepsContainer = document.querySelector('.workflow-steps');
                const panel = document.querySelector('.inspector-panel');

                if (workflowVisual && stepsContainer) {
                    const stepTop = step.offsetTop;
                    const containerHeight = stepsContainer.offsetHeight;
                    const panelHeight = panel ? panel.offsetHeight : 320;
                    const maxTranslate = Math.max(0, containerHeight - panelHeight);
                    const targetY = Math.min(stepTop, maxTranslate);

                    workflowVisual.style.transform = `translateY(${targetY}px)`;
                }

                // Faint purple glow pulse on inspector border
                if (panel) {
                    panel.style.borderColor = 'rgba(168, 85, 247, 0.65)';
                    panel.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.6), 0 0 35px rgba(168, 85, 247, 0.3)';
                    setTimeout(() => {
                        panel.style.borderColor = 'rgba(168, 85, 247, 0.3)';
                        panel.style.boxShadow = '0 25px 50px rgba(0, 0, 0, 0.6), 0 0 20px rgba(168, 85, 247, 0.15)';
                    }, 400);
                }
            }
        });
    });
}

// 5. Scroll reveal animation for section elements
function initScrollReveal() {
    const elements = document.querySelectorAll('.step-item, .section-header, .tech-ribbon, .target-mode-card, .faq-item');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    elements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(25px)';
        el.style.transition = 'opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1), transform 0.8s cubic-bezier(0.16, 1, 0.3, 1)';
        observer.observe(el);
    });
}

// 6. FAQ Accordion Logic
function initFaqAccordion() {
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        const answer = item.querySelector('.faq-answer');
        if (!question || !answer) return;

        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');

            // Close all active items
            faqItems.forEach(otherItem => {
                otherItem.classList.remove('active');
                otherItem.querySelector('.faq-answer').style.maxHeight = null;
            });

            if (!isActive) {
                item.classList.add('active');
                answer.style.maxHeight = answer.scrollHeight + 'px';
            }
        });
    });
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Helper: safe HTML escaper
function safeEscapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Universal Custom Cyber Select Enhancer System
function initCustomSelects() {
    const selects = document.querySelectorAll('select');

    selects.forEach(select => {
        if (select.dataset.customSelectInit === 'true') {
            updateCustomSelectWrapper(select);
            return;
        }

        select.dataset.customSelectInit = 'true';
        select.style.display = 'none';

        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper';
        if (select.classList.contains('cyber-select-pill')) {
            wrapper.classList.add('pill-mode');
        }
        if (select.classList.contains('cyber-select-sm')) {
            wrapper.classList.add('sm-mode');
        }

        // Inherit width / flex properties from select inline styles or classes
        if (select.style.width === '100%' || select.classList.contains('form-control')) {
            wrapper.style.width = '100%';
        }
        if (select.style.flex) {
            wrapper.style.flex = select.style.flex;
        }

        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        if (select.style.width === '100%' || select.classList.contains('form-control')) {
            trigger.style.width = '100%';
            trigger.style.justifyContent = 'space-between';
        }

        const iconClass = getSelectIconClass(select);
        let iconHtml = '';
        if (iconClass) {
            iconHtml = `<i class="fa-solid ${iconClass} custom-select-icon"></i>`;
        }

        const selectedOpt = select.options[select.selectedIndex] || select.options[0];
        const labelText = selectedOpt ? selectedOpt.text : 'Select...';

        trigger.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; overflow: hidden;">
                ${iconHtml}
                <span class="custom-select-label">${safeEscapeHtml(labelText)}</span>
            </div>
            <i class="fa-solid fa-chevron-down custom-select-chevron"></i>
        `;

        const menu = document.createElement('div');
        menu.className = 'custom-select-menu';

        wrapper._menu = menu;
        menu._wrapper = wrapper;
        menu._select = select;
        menu._trigger = trigger;

        buildCustomSelectMenuOptions(select, menu, trigger, wrapper);

        wrapper.appendChild(trigger);
        wrapper.appendChild(menu);

        select.parentNode.insertBefore(wrapper, select);

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isCurrentlyOpen = wrapper.classList.contains('open');

            closeAllCustomSelects();

            if (!isCurrentlyOpen) {
                openCustomSelect(wrapper);
            }
        });

        const observer = new MutationObserver(() => {
            buildCustomSelectMenuOptions(select, menu, trigger, wrapper);
            if (wrapper.classList.contains('open')) {
                positionCustomSelectMenu(wrapper);
            }
        });
        observer.observe(select, { childList: true, subtree: true, attributes: true });

        select.addEventListener('change', () => {
            updateCustomSelectTriggerLabel(select, trigger);
            highlightSelectedOption(select, menu);
        });
    });
}

function openCustomSelect(wrapper) {
    if (!wrapper || !wrapper._menu) return;
    const menu = wrapper._menu;

    wrapper.classList.add('open');

    // Move menu to document.body so it is completely free of card/modal transforms & overflow scrollbars
    if (menu.parentNode !== document.body) {
        document.body.appendChild(menu);
    }

    positionCustomSelectMenu(wrapper);

    menu.style.display = 'block';
    menu.style.opacity = '1';
    menu.style.visibility = 'visible';
    menu.style.pointerEvents = 'auto';
}

function closeCustomSelect(wrapper) {
    if (!wrapper) return;
    wrapper.classList.remove('open');
    wrapper.style.zIndex = '';

    const menu = wrapper._menu;
    if (menu) {
        menu.style.display = 'none';
        menu.style.opacity = '0';
        menu.style.visibility = 'hidden';
        menu.style.pointerEvents = 'none';

        if (menu.parentNode === document.body) {
            wrapper.appendChild(menu);
        }
    }
}

function closeAllCustomSelects() {
    document.querySelectorAll('.custom-select-wrapper.open').forEach(w => closeCustomSelect(w));
    document.querySelectorAll('body > .custom-select-menu').forEach(menu => {
        if (menu._wrapper) {
            closeCustomSelect(menu._wrapper);
        }
    });
}

function positionCustomSelectMenu(wrapper) {
    if (!wrapper || !wrapper._menu) return;
    const trigger = wrapper.querySelector('.custom-select-trigger');
    const menu = wrapper._menu;
    if (!trigger || !menu) return;

    const rect = trigger.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.top = (rect.bottom + 6) + 'px';
    menu.style.left = rect.left + 'px';
    menu.style.width = Math.max(rect.width, 180) + 'px';
    menu.style.minWidth = rect.width + 'px';
    menu.style.zIndex = '99999999';
}

function getSelectIconClass(select) {
    if (select.dataset.icon) return select.dataset.icon;
    const id = (select.id || '').toLowerCase();
    if (id.includes('project')) return 'fa-folder-tree';
    if (id.includes('type')) return 'fa-shapes';
    if (id.includes('severity')) return 'fa-shield-halved';
    if (id.includes('sort')) return 'fa-arrow-down-wide-short';
    if (id.includes('status')) return 'fa-circle-dot';
    if (id.includes('scan')) return 'fa-radar';
    return null;
}

function updateCustomSelectTriggerLabel(select, trigger) {
    const selectedOpt = select.options[select.selectedIndex];
    const labelSpan = trigger.querySelector('.custom-select-label');
    if (labelSpan && selectedOpt) {
        labelSpan.textContent = selectedOpt.text;
    }
}

function highlightSelectedOption(select, menu) {
    const val = select.value;
    const items = menu.querySelectorAll('.custom-select-option');
    items.forEach(item => {
        if (item.dataset.value === val) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

function updateCustomSelectWrapper(select) {
    const wrapper = select.previousElementSibling;
    if (wrapper && wrapper.classList.contains('custom-select-wrapper')) {
        const trigger = wrapper.querySelector('.custom-select-trigger');
        const menu = wrapper._menu || wrapper.querySelector('.custom-select-menu');
        if (trigger && menu) {
            buildCustomSelectMenuOptions(select, menu, trigger, wrapper);
            if (wrapper.classList.contains('open')) {
                positionCustomSelectMenu(wrapper);
            }
        }
    }
}

function buildCustomSelectMenuOptions(select, menu, trigger, wrapper) {
    menu.innerHTML = '';
    const currentVal = select.value;

    Array.from(select.options).forEach(opt => {
        const item = document.createElement('div');
        item.className = 'custom-select-option' + (opt.value === currentVal ? ' selected' : '');
        item.dataset.value = opt.value;

        const text = opt.text;
        let badgeHtml = '';
        const upperText = text.toUpperCase();

        if (upperText.includes('CRITICAL')) {
            badgeHtml = `<span class="opt-badge critical">CRITICAL</span>`;
        } else if (upperText.includes('HIGH')) {
            badgeHtml = `<span class="opt-badge high">HIGH</span>`;
        } else if (upperText.includes('MEDIUM')) {
            badgeHtml = `<span class="opt-badge medium">MEDIUM</span>`;
        } else if (upperText.includes('LOW')) {
            badgeHtml = `<span class="opt-badge low">LOW</span>`;
        } else if (upperText.includes('INFORMATIONAL') || upperText.includes('INFO')) {
            badgeHtml = `<span class="opt-badge info">INFO</span>`;
        }

        item.innerHTML = `
            <span>${safeEscapeHtml(text)}</span>
            <div style="display: flex; align-items: center; gap: 8px;">
                ${badgeHtml}
                <i class="fa-solid fa-check opt-check"></i>
            </div>
        `;

        item.addEventListener('click', (e) => {
            e.stopPropagation();
            select.value = opt.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            updateCustomSelectTriggerLabel(select, trigger);
            highlightSelectedOption(select, menu);
            closeCustomSelect(wrapper);
        });

        menu.appendChild(item);
    });

    updateCustomSelectTriggerLabel(select, trigger);
}

function wrapperClosest(el, className) {
    while (el && el !== document) {
        if (el.classList && el.classList.contains(className)) return el;
        el = el.parentNode;
    }
    return null;
}

// Reposition open menu on scroll or resize
window.addEventListener('scroll', () => {
    document.querySelectorAll('.custom-select-wrapper.open').forEach(wrapper => {
        positionCustomSelectMenu(wrapper);
    });
}, true);

window.addEventListener('resize', () => {
    document.querySelectorAll('.custom-select-wrapper.open').forEach(wrapper => {
        positionCustomSelectMenu(wrapper);
    });
});

// Global click to close custom dropdowns
document.addEventListener('click', () => {
    closeAllCustomSelects();
});
