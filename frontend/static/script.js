// ============================================
// ARGUS - INTERACTIONS & ANIMATIONS (v2.0)
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    window.toggleMenu = function() {
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
});

// 1. Terminal Simulator Typewriter Sequence
function initTerminalSimulator() {
    const cmdEl = document.getElementById('terminal-cmd');
    const outputsEl = document.getElementById('terminal-outputs');
    if (!cmdEl || !outputsEl) return;

    const command = 'nmap -sV target.com';
    const outputs = [
        { text: 'Starting Nmap 7.95 ( https://nmap.org ) at 2026-08-22 01:46 UTC', delay: 400 },
        { text: 'Nmap scan report for target.com (104.244.42.1)', delay: 600 },
        { text: 'Host is up (0.042s latency).', delay: 400 },
        { text: 'rDNS record for 104.244.42.1: dns.target.com', delay: 500 },
        { text: 'Not shown: 997 closed tcp ports (reset)', delay: 400 },
        { text: 'PORT     STATE SERVICE VERSION', delay: 600, class: 'highlight' },
        { text: '22/tcp   open  ssh     OpenSSH 8.9p1 Ubuntu 3ubuntu0.1', delay: 400, class: 'output-line' },
        { text: '80/tcp   open  http    nginx 1.18.0', delay: 300, class: 'output-line' },
        { text: '443/tcp  open  https   nginx 1.18.0', delay: 300, class: 'output-line' },
        { text: 'Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel', delay: 500 },
        { text: 'Nmap done: 1 IP address (1 host up) scanned in 3.42 seconds', delay: 800, class: 'success' }
    ];

    let cmdIdx = 0;
    
    function typeCommand() {
        if (cmdIdx < command.length) {
            cmdEl.textContent += command.charAt(cmdIdx);
            cmdIdx++;
            setTimeout(typeCommand, 50 + Math.random() * 100); // realistic typing rhythm
        } else {
            setTimeout(renderOutputs, 500);
        }
    }

    let outputIdx = 0;
    function renderOutputs() {
        if (outputIdx < outputs.length) {
            const line = outputs[outputIdx];
            const div = document.createElement('div');
            div.className = 'terminal-line ' + (line.class || 'output-line');
            
            // Faint purple glow pulse border on output change
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
            setTimeout(renderOutputs, line.delay);
        } else {
            setTimeout(resetTerminal, 5000); // Wait 5s before loop restart
        }
    }

    function resetTerminal() {
        cmdEl.textContent = '';
        outputsEl.innerHTML = '';
        cmdIdx = 0;
        outputIdx = 0;
        typeCommand();
    }

    typeCommand();
}

// 2. Canvas-based Particles Network Background
function initBackgroundCanvas() {
    const canvas = document.getElementById('bg-network-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    let particles = [];
    const maxParticles = 60;
    const maxDistance = 120;

    let mouse = { x: null, y: null, radius: 150 };

    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });

    window.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    window.addEventListener('mouseleave', () => {
        mouse.x = null;
        mouse.y = null;
    });

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.3; // slow moving
            this.vy = (Math.random() - 0.5) * 0.3;
            this.radius = Math.random() * 2 + 1;
            this.alpha = Math.random() * 0.4 + 0.1;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;

            // Mouse parallax push/interaction
            if (mouse.x !== null && mouse.y !== null) {
                const dx = this.x - mouse.x;
                const dy = this.y - mouse.y;
                const dist = Math.hypot(dx, dy);
                if (dist < mouse.radius) {
                    const force = (mouse.radius - dist) / mouse.radius;
                    const angle = Math.atan2(dy, dx);
                    this.x += Math.cos(angle) * force * 0.8;
                    this.y += Math.sin(angle) * force * 0.8;
                }
            }
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(168, 85, 247, ${this.alpha})`;
            ctx.fill();
        }
    }

    for (let i = 0; i < maxParticles; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const p1 = particles[i];
                const p2 = particles[j];
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dist = Math.hypot(dx, dy);

                if (dist < maxDistance) {
                    const alpha = (1 - dist / maxDistance) * 0.08;
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(168, 85, 247, ${alpha})`;
                    ctx.lineWidth = 0.8;
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
project:
  name: "Internal Network Security Audit"
  id: "proj_92a1_recon"
targets:
  - domain: "target.com"
    ips: ["104.244.42.1"]
    scan_policy: "stealth"
    interval: "daily"`
        },
        '2': {
            filename: 'passive_discovery.json',
            code: `{
  "domain": "target.com",
  "dns_servers": ["8.8.8.8", "1.1.1.1"],
  "subdomains_found": [
    {"host": "api.target.com", "source": "CT Logs", "ip": "104.244.42.5"},
    {"host": "dev.target.com", "source": "DNS Lookup", "ip": "104.244.42.9"},
    {"host": "mail.target.com", "source": "MX Query", "ip": "104.244.42.12"}
  ]
}`
        },
        '3': {
            filename: 'active_scan_results.xml',
            code: `<!-- Nmap 7.95 Scan XML Output excerpt -->
<host starttime="1787345502">
  <address addr="104.244.42.1" addrtype="ipv4"/>
  <ports>
    <port protocol="tcp" portid="22">
      <state state="open"/>
      <service name="ssh" product="OpenSSH" version="8.9p1"/>
    </port>
    <port protocol="tcp" portid="80">
      <state state="open"/>
      <service name="http" product="nginx" version="1.18.0"/>
    </port>
  </ports>
</host>`
        },
        '4': {
            filename: 'web_fingerprint.json',
            code: `{
  "url": "https://target.com",
  "http_version": "1.1",
  "server": "nginx/1.18.0",
  "powered_by": "PHP/8.1.2",
  "cms": "WordPress 6.4",
  "security_headers": {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "missing"
  }
}`
        },
        '5': {
            filename: 'audit_summary.txt',
            code: `===========================================
ARGUS SECURITY AUDIT REPORT SUMMARY
===========================================
Project Scope : Internal Network Security Audit
Target Domain : target.com (104.244.42.1)
Open Ports    : 22/tcp (ssh), 80/tcp (http), 443/tcp (https)
Risk Rating   : LOW (2 warning advisories)
Download URL  : /api/v1/projects/proj_92a1/report.pdf
===========================================`
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

                // Faint purple glow pulse on inspector border
                const panel = document.querySelector('.inspector-panel');
                if (panel) {
                    panel.style.borderColor = 'rgba(168, 85, 247, 0.45)';
                    panel.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.5), 0 0 25px rgba(168, 85, 247, 0.15)';
                    setTimeout(() => {
                        panel.style.borderColor = 'rgba(168, 85, 247, 0.15)';
                        panel.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.5)';
                    }, 250);
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
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});