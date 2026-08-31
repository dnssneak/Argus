// Argus — Authentication Logic (Frontend Only)

document.addEventListener('DOMContentLoaded', () => {
    try { initAuthForms(); } catch (e) { console.error('initAuthForms:', e); }
    try { initPurpleGlobe(); } catch (e) { console.error('initPurpleGlobe:', e); }
    try { initBinaryStream(); } catch (e) { console.error('initBinaryStream:', e); }
    try { initArgusNeonSweep(); } catch (e) { console.error('initArgusNeonSweep:', e); }
    try { initScrambledText(); } catch (e) { console.error('initScrambledText:', e); }
    try { initArgusParticleText(); } catch (e) { console.error('initArgusParticleText:', e); }
});

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        container.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 10px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const borderColor = type === 'error' ? 'var(--accent-red)' : type === 'success' ? 'var(--accent-green)' : 'var(--accent-purple)';
    const iconClass = type === 'error' ? 'fa-circle-exclamation' : type === 'success' ? 'fa-circle-check' : 'fa-circle-info';
    const iconColor = type === 'error' ? 'var(--accent-red)' : type === 'success' ? 'var(--accent-green)' : 'var(--accent-purple)';

    toast.className = 'toast';
    toast.style.cssText = `background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary); padding: 12px 18px; border-radius: 8px; font-size: 0.9rem; display: flex; align-items: center; gap: 10px; box-shadow: var(--shadow-lg); border-left: 4px solid ${borderColor}; transition: opacity 0.3s ease;`;
    toast.innerHTML = `<i class="fa-solid ${iconClass}" style="color: ${iconColor};"></i> <span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Toggle password visibility
function togglePasswordVisibility(inputFieldId, buttonEl) {
    const input = document.getElementById(inputFieldId);
    if (!input) return;
    
    const icon = buttonEl.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        input.type = 'password';
        if (icon) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

// Password Strength Indicator
function evaluatePasswordStrength(password) {
    const wrap = document.getElementById('strength-wrap');
    const bar = document.getElementById('strength-bar');
    const label = document.getElementById('strength-label');
    
    if (!wrap || !bar || !label) return;

    if (!password || password.length === 0) {
        wrap.style.display = 'none';
        return;
    }

    wrap.style.display = 'flex';

    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    if (password.length < 8 || score <= 1) {
        bar.style.width = '33%';
        bar.style.backgroundColor = 'var(--accent-red)';
        label.textContent = 'Weak';
        label.style.color = 'var(--accent-red)';
    } else if (score === 2 || score === 3) {
        bar.style.width = '66%';
        bar.style.backgroundColor = 'var(--accent-yellow)';
        label.textContent = 'Medium';
        label.style.color = 'var(--accent-yellow)';
    } else {
        bar.style.width = '100%';
        bar.style.backgroundColor = 'var(--accent-green)';
        label.textContent = 'Strong';
        label.style.color = 'var(--accent-green)';
    }
}

// Forgot Password interaction
function handleForgotPassword(e) {
    e.preventDefault();
    const emailInput = document.getElementById('login-email');
    const emailVal = emailInput ? emailInput.value.trim() : '';

    if (emailVal && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
        showToast(`Password reset link sent to ${emailVal}`, 'success');
    } else {
        showToast('Please enter your email address to receive reset instructions.', 'info');
        if (emailInput) emailInput.focus();
    }
}

// Terms notice
function showTermsNotice(e) {
    e.preventDefault();
    showToast('Argus Terms: Account is for authorized security testing and education.', 'info');
}

function showAuthAlert(message) {
    const alertEl = document.getElementById('auth-alert');
    const alertText = document.getElementById('auth-alert-text');
    if (alertEl && alertText) {
        alertText.textContent = message;
        alertEl.classList.add('visible');
    } else {
        showToast(message, 'error');
    }
}

// Form Validation & Submission with Backend API
function initAuthForms() {
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');

    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearFieldErrors(loginForm);

            const emailInput = document.getElementById('login-email');
            const passwordInput = document.getElementById('login-password');
            const rememberMeCheckbox = document.getElementById('remember-me');
            const submitBtn = document.getElementById('login-submit-btn');

            const emailVal = emailInput ? emailInput.value.trim() : '';
            const passwordVal = passwordInput ? passwordInput.value : '';
            const rememberMe = rememberMeCheckbox ? rememberMeCheckbox.checked : false;

            let hasError = false;

            if (!emailVal || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
                showFieldError('login-email', 'email-error');
                hasError = true;
            }

            if (!passwordVal) {
                showFieldError('login-password', 'password-error');
                hasError = true;
            }

            if (hasError) return;

            setButtonLoading(submitBtn, true, 'Logging in...');
            disableFormInputs(loginForm, true);

            fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: emailVal,
                    password: passwordVal,
                    remember_me: rememberMe
                })
            })
            .then(res => res.json().then(data => ({ status: res.status, data })))
            .then(({ status, data }) => {
                if (data.success && data.token) {
                    localStorage.setItem('argus_token', data.token);
                    localStorage.setItem('argus_user', JSON.stringify(data.user));
                    localStorage.setItem('argus_logged_in', 'true');
                    showToast('Welcome back! Logged in successfully.', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 500);
                } else {
                    setButtonLoading(submitBtn, false);
                    disableFormInputs(loginForm, false);
                    showAuthAlert(data.error || 'Invalid credentials.');
                }
            })
            .catch(err => {
                setButtonLoading(submitBtn, false);
                disableFormInputs(loginForm, false);
                showAuthAlert('Network error. Failed to connect to server.');
            });
        });
    }

    if (signupForm) {
        signupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            clearFieldErrors(signupForm);

            const nameInput = document.getElementById('signup-name');
            const emailInput = document.getElementById('signup-email');
            const passwordInput = document.getElementById('signup-password');
            const confirmPasswordInput = document.getElementById('signup-confirm-password');
            const termsCheckbox = document.getElementById('terms-checkbox');
            const submitBtn = document.getElementById('signup-submit-btn');

            const nameVal = nameInput ? nameInput.value.trim() : '';
            const emailVal = emailInput ? emailInput.value.trim() : '';
            const passwordVal = passwordInput ? passwordInput.value : '';
            const confirmPasswordVal = confirmPasswordInput ? confirmPasswordInput.value : '';

            let hasError = false;

            if (!nameVal || nameVal.length < 2) {
                showFieldError('signup-name', 'name-error');
                hasError = true;
            }

            if (!emailVal || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
                showFieldError('signup-email', 'email-error');
                hasError = true;
            }

            if (!passwordVal || passwordVal.length < 8) {
                showFieldError('signup-password', 'password-error');
                hasError = true;
            }

            if (!confirmPasswordVal || confirmPasswordVal !== passwordVal) {
                showFieldError('signup-confirm-password', 'confirm-password-error');
                hasError = true;
            }

            if (termsCheckbox && !termsCheckbox.checked) {
                showFieldError(null, 'terms-error');
                hasError = true;
            }

            if (hasError) return;

            setButtonLoading(submitBtn, true, 'Creating account...');
            disableFormInputs(signupForm, true);

            fetch('/api/v1/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: nameVal,
                    email: emailVal,
                    password: passwordVal,
                    confirm_password: confirmPasswordVal
                })
            })
            .then(res => res.json().then(data => ({ status: res.status, data })))
            .then(({ status, data }) => {
                if (data.success && data.token) {
                    localStorage.setItem('argus_token', data.token);
                    localStorage.setItem('argus_user', JSON.stringify(data.user));
                    localStorage.setItem('argus_logged_in', 'true');
                    showToast('Account created successfully! Redirecting...', 'success');
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 500);
                } else {
                    setButtonLoading(submitBtn, false);
                    disableFormInputs(signupForm, false);
                    showAuthAlert(data.error || 'Registration failed.');
                }
            })
            .catch(err => {
                setButtonLoading(submitBtn, false);
                disableFormInputs(signupForm, false);
                showAuthAlert('Network error. Failed to connect to server.');
            });
        });
    }
}

function showFieldError(inputId, errorId) {
    if (inputId) {
        const input = document.getElementById(inputId);
        if (input) input.classList.add('is-invalid');
    }
    if (errorId) {
        const errorEl = document.getElementById(errorId);
        if (errorEl) errorEl.classList.add('visible');
    }
}

function clearFieldErrors(form) {
    const inputs = form.querySelectorAll('.auth-input');
    inputs.forEach(input => input.classList.remove('is-invalid'));

    const errors = form.querySelectorAll('.field-error-msg');
    errors.forEach(err => err.classList.remove('visible'));

    const alert = document.getElementById('auth-alert');
    if (alert) alert.classList.remove('visible');
}

function setButtonLoading(button, isLoading, loadingText = 'Processing...') {
    if (!button) return;
    const btnText = button.querySelector('.btn-text');
    const spinner = button.querySelector('.btn-spinner');

    if (isLoading) {
        button.disabled = true;
        if (btnText) btnText.textContent = loadingText;
        if (spinner) spinner.style.display = 'inline-block';
    } else {
        button.disabled = false;
        if (spinner) spinner.style.display = 'none';
    }
}

function disableFormInputs(form, disabled) {
    const inputs = form.querySelectorAll('input, button');
    inputs.forEach(el => {
        if (!el.classList.contains('btn-spinner')) {
            el.disabled = disabled;
        }
    });
}

// ============================================
// 3D PURPLE INTERACTIVE WARFARE GLOBE FOR AUTH
// ============================================

const landPolygons = [
    // North America
    [[70, -160], [70, -60], [80, -60], [80, -80], [70, -100], [50, -50], [45, -60], [25, -80], [15, -90], [15, -100], [20, -105], [30, -115], [32, -118], [48, -125], [60, -140], [65, -168]],
    // Greenland
    [[80, -70], [82, -60], [83, -40], [83, -10], [75, -20], [70, -20], [60, -40], [60, -50], [65, -60]],
    // South America
    [[12, -72], [10, -60], [5, -50], [-5, -35], [-20, -40], [-40, -60], [-55, -70], [-55, -73], [-45, -75], [-20, -70], [-5, -80], [5, -75]],
    // Africa
    [[35, -10], [37, 10], [32, 30], [30, 32], [15, 40], [12, 43], [12, 51], [-5, 40], [-34, 20], [-34, 18], [-20, 12], [5, 9], [5, -8], [15, -17], [20, -17]],
    // Madagascar
    [[-12, 49], [-16, 50], [-25, 47], [-25, 43], [-15, 47]],
    // Eurasia / Europe
    [[70, 20], [70, 100], [75, 120], [70, 170], [60, 170], [60, 140], [40, 120], [30, 120], [22, 110], [20, 105], [10, 108], [15, 96], [20, 90], [10, 78], [25, 68], [12, 44], [30, 32], [40, 26], [40, 35], [36, 40], [30, 35], [25, 40], [35, 15], [38, 26], [45, 13], [36, -5], [43, -9], [50, -5], [60, 5], [65, 15]],
    // Australia
    [[-10, 142], [-20, 148], [-35, 150], [-38, 145], [-35, 138], [-35, 115], [-22, 113], [-15, 125], [-12, 130], [-12, 136]],
    // Antarctica
    [[-65, -180], [-65, 180], [-90, 180], [-90, -180]]
];

let scene, camera, renderer, globeGroup, stars;
let landPointsList = [];
let attackArcs = [];
let isHolding = false;
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };
let spawnTimer = null;

function initPurpleGlobe() {
    const canvasEl = document.getElementById('authGlobeCanvas');
    if (!canvasEl || typeof THREE === 'undefined') return;

    const container = canvasEl.parentElement;
    const w = container.clientWidth || window.innerWidth / 2;
    const h = container.clientHeight || window.innerHeight;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 1000);
    camera.position.set(0, 0, 17.5);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({
        canvas: canvasEl,
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
    });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);

    globeGroup = new THREE.Group();
    globeGroup.rotation.y = 0.8;
    globeGroup.rotation.x = 0.15;
    scene.add(globeGroup);

    buildPurpleGlobeLayers();
    setupGlobeEventListeners(canvasEl);

    animateGlobe();
}

function buildPurpleGlobeLayers() {
    const R = 4.4;

    // Occlusion Core
    const occlusionGeom = new THREE.SphereGeometry(4.3, 64, 64);
    const occlusionMat = new THREE.MeshBasicMaterial({
        color: 0x070710,
        transparent: true,
        opacity: 0.95,
        depthWrite: true
    });
    const occlusionSphere = new THREE.Mesh(occlusionGeom, occlusionMat);
    globeGroup.add(occlusionSphere);

    // Meridian & Parallel Coordinate Grid (Purple)
    const meridianSteps = 64;
    const gridMat = new THREE.LineBasicMaterial({
        color: 0x7c3aed,
        transparent: true,
        opacity: 0.25,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });

    for (let i = 0; i < 20; i++) {
        const theta = (i * Math.PI * 2) / 20;
        const points = [];
        for (let s = 0; s <= meridianSteps; s++) {
            const phi = (s * Math.PI) / meridianSteps;
            const x = R * Math.sin(phi) * Math.cos(theta);
            const y = R * Math.cos(phi);
            const z = R * Math.sin(phi) * Math.sin(theta);
            points.push(new THREE.Vector3(x, y, z));
        }
        const geom = new THREE.BufferGeometry().setFromPoints(points);
        globeGroup.add(new THREE.Line(geom, gridMat));
    }

    const parallelLats = [-60, -40, -20, 0, 20, 40, 60];
    parallelLats.forEach(latDeg => {
        const alpha = latDeg * (Math.PI / 180);
        const r_alpha = R * Math.cos(alpha);
        const y_alpha = R * Math.sin(alpha);
        const points = [];
        for (let s = 0; s <= meridianSteps; s++) {
            const beta = (s * Math.PI * 2) / meridianSteps;
            points.push(new THREE.Vector3(r_alpha * Math.cos(beta), y_alpha, r_alpha * Math.sin(beta)));
        }
        const geom = new THREE.BufferGeometry().setFromPoints(points);
        globeGroup.add(new THREE.Line(geom, gridMat));
    });

    // Continental Landmass Matrix (Purple Dots: 0xa855f7)
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = 1024;
    maskCanvas.height = 512;
    const maskCtx = maskCanvas.getContext('2d');
    maskCtx.fillStyle = '#000000';
    maskCtx.fillRect(0, 0, 1024, 512);

    maskCtx.fillStyle = '#ffffff';
    landPolygons.forEach(poly => {
        maskCtx.beginPath();
        poly.forEach((pt, idx) => {
            const x = (pt[1] + 180) * (1024 / 360);
            const y = (90 - pt[0]) * (512 / 180);
            if (idx === 0) maskCtx.moveTo(x, y);
            else maskCtx.lineTo(x, y);
        });
        maskCtx.closePath();
        maskCtx.fill();
    });

    const maskData = maskCtx.getImageData(0, 0, 1024, 512).data;
    landPointsList = [];

    const numSamples = 18000;
    for (let i = 0; i < numSamples; i++) {
        const phi = Math.acos(-1 + (2 * i) / numSamples);
        const theta = Math.sqrt(numSamples * Math.PI) * phi;

        const x = R * Math.cos(theta) * Math.sin(phi);
        const y = R * Math.sin(theta) * Math.sin(phi);
        const z = R * Math.cos(phi);

        const lat = Math.asin(y / R) * (180 / Math.PI);
        let lon = Math.atan2(z, x) * (180 / Math.PI);
        lon = ((lon + 180) % 360 + 360) % 360 - 180;

        const px = Math.floor((lon + 180) * (1024 / 360));
        const py = Math.floor((90 - lat) * (512 / 180));
        const idx = (py * 1024 + px) * 4;

        if (maskData[idx] > 128) {
            const rx = -(R * Math.sin(phi) * Math.cos(theta));
            const ry = R * Math.cos(phi);
            const rz = R * Math.sin(phi) * Math.sin(theta);
            landPointsList.push(new THREE.Vector3(rx, ry, rz));
        }
    }

    const pointGeom = new THREE.BufferGeometry();
    const positions = new Float32Array(landPointsList.length * 3);
    const colors = new Float32Array(landPointsList.length * 3);
    const purpColor = new THREE.Color(0xa855f7);

    for (let i = 0; i < landPointsList.length; i++) {
        positions[i * 3] = landPointsList[i].x;
        positions[i * 3 + 1] = landPointsList[i].y;
        positions[i * 3 + 2] = landPointsList[i].z;

        colors[i * 3] = purpColor.r;
        colors[i * 3 + 1] = purpColor.g;
        colors[i * 3 + 2] = purpColor.b;
    }

    pointGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pointGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const pointMat = new THREE.PointsMaterial({
        size: 0.065,
        vertexColors: true,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });

    globeGroup.add(new THREE.Points(pointGeom, pointMat));

    // Atmospheric Limb Glow
    const glowGeom = new THREE.SphereGeometry(R * 1.03, 64, 64);
    const glowMat = new THREE.MeshBasicMaterial({
        color: 0xa855f7,
        transparent: true,
        opacity: 0.16,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
        depthWrite: false
    });
    globeGroup.add(new THREE.Mesh(glowGeom, glowMat));

    // Stars Field
    const starGeom = new THREE.BufferGeometry();
    const starCount = 300;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
        const r = 25 + Math.random() * 30;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        starPositions[i] = r * Math.sin(phi) * Math.cos(theta);
        starPositions[i+1] = r * Math.sin(phi) * Math.sin(theta);
        starPositions[i+2] = r * Math.cos(phi);
    }
    starGeom.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    stars = new THREE.Points(starGeom, new THREE.PointsMaterial({
        color: 0xdedcff,
        size: 0.07,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    }));
    scene.add(stars);
}

// Spawn Attack Beams on Hold
function spawnPurpleAttackBeam() {
    if (landPointsList.length < 10) return;

    if (attackArcs.length >= 8) {
        clearOldestArc();
    }

    const originIdx = Math.floor(Math.random() * landPointsList.length);
    let targetIdx = Math.floor(Math.random() * landPointsList.length);
    
    let tries = 0;
    while (tries < 15 && (targetIdx === originIdx || landPointsList[originIdx].distanceTo(landPointsList[targetIdx]) < 2.0)) {
        targetIdx = Math.floor(Math.random() * landPointsList.length);
        tries++;
    }

    const pStart = landPointsList[originIdx];
    const pEnd = landPointsList[targetIdx];
    const R = 4.4;

    const pMid = new THREE.Vector3().addVectors(pStart, pEnd).multiplyScalar(0.5);
    const d = pStart.distanceTo(pEnd);
    const mElevated = pMid.clone().normalize().multiplyScalar(R + 2.6 + d * 0.5);

    const dir = new THREE.Vector3().subVectors(pEnd, pStart).normalize();
    const up = mElevated.clone().normalize();
    const side = new THREE.Vector3().crossVectors(dir, up).normalize();
    mElevated.add(side.multiplyScalar((Math.random() - 0.5) * d * 0.2));

    const curve = new THREE.QuadraticBezierCurve3(pStart, mElevated, pEnd);

    // Purple Magenta Laser Arc
    const linePoints = curve.getPoints(48);
    const lineGeom = new THREE.BufferGeometry().setFromPoints(linePoints);
    const arcMat = new THREE.LineBasicMaterial({
        color: 0xd946ef,
        transparent: true,
        opacity: 0.85,
        blending: THREE.AdditiveBlending,
        depthWrite: false
    });
    const lineMesh = new THREE.Line(lineGeom, arcMat);
    globeGroup.add(lineMesh);

    // Glowing energy pulse packet
    const pGeom = new THREE.SphereGeometry(0.09, 8, 8);
    const pMat = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        blending: THREE.AdditiveBlending
    });
    const pMesh = new THREE.Mesh(pGeom, pMat);
    globeGroup.add(pMesh);

    // Trail nodes
    const trailGroup = new THREE.Group();
    globeGroup.add(trailGroup);
    const trailNodes = [];
    for (let t = 0; t < 3; t++) {
        const trGeom = new THREE.SphereGeometry(0.06 * (1 - t / 3), 6, 6);
        const trMat = new THREE.MeshBasicMaterial({
            color: 0xa855f7,
            transparent: true,
            opacity: 0.7 * (1 - t / 3),
            blending: THREE.AdditiveBlending
        });
        const trMesh = new THREE.Mesh(trGeom, trMat);
        trailGroup.add(trMesh);
        trailNodes.push(trMesh);
    }

    attackArcs.push({
        curve: curve,
        lineMesh: lineMesh,
        packetMesh: pMesh,
        trailGroup: trailGroup,
        trailNodes: trailNodes,
        progress: 0,
        speed: 0.22 + Math.random() * 0.1
    });
}

function clearOldestArc() {
    if (attackArcs.length === 0) return;
    const oldest = attackArcs.shift();
    if (oldest.lineMesh) {
        globeGroup.remove(oldest.lineMesh);
        oldest.lineMesh.geometry.dispose();
        oldest.lineMesh.material.dispose();
    }
    if (oldest.packetMesh) {
        globeGroup.remove(oldest.packetMesh);
        oldest.packetMesh.geometry.dispose();
        oldest.packetMesh.material.dispose();
    }
    if (oldest.trailGroup) {
        globeGroup.remove(oldest.trailGroup);
        oldest.trailNodes.forEach(n => {
            n.geometry.dispose();
            n.material.dispose();
        });
    }
}

function clearAllAttackBeams() {
    while (attackArcs.length > 0) {
        clearOldestArc();
    }
}

function setupGlobeEventListeners(canvasEl) {
    const parent = canvasEl.parentElement;

    function startHold(e) {
        isHolding = true;
        isDragging = true;
        previousMousePosition = {
            x: e.clientX || (e.touches && e.touches[0].clientX) || 0,
            y: e.clientY || (e.touches && e.touches[0].clientY) || 0
        };

        spawnPurpleAttackBeam();
        if (spawnTimer) clearInterval(spawnTimer);
        spawnTimer = setInterval(spawnPurpleAttackBeam, 180);
    }

    function stopHold() {
        isHolding = false;
        isDragging = false;
        if (spawnTimer) {
            clearInterval(spawnTimer);
            spawnTimer = null;
        }

        clearAllAttackBeams();
    }

    function onMove(e) {
        if (!isDragging || !globeGroup) return;

        const currentX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
        const currentY = e.clientY || (e.touches && e.touches[0].clientY) || 0;

        const deltaX = currentX - previousMousePosition.x;
        const deltaY = currentY - previousMousePosition.y;

        globeGroup.rotation.y += deltaX * 0.005;
        globeGroup.rotation.x += deltaY * 0.005;
        globeGroup.rotation.x = Math.max(-0.85, Math.min(0.85, globeGroup.rotation.x));

        previousMousePosition = { x: currentX, y: currentY };
    }

    parent.addEventListener('mousedown', startHold);
    window.addEventListener('mouseup', stopHold);
    parent.addEventListener('mousemove', onMove);

    parent.addEventListener('touchstart', startHold, { passive: true });
    window.addEventListener('touchend', stopHold);
    window.addEventListener('touchcancel', stopHold);
    parent.addEventListener('touchmove', onMove, { passive: true });

    window.addEventListener('resize', () => {
        if (!renderer || !camera || !parent) return;
        const w = parent.clientWidth;
        const h = parent.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    });
}

function animateGlobe() {
    requestAnimationFrame(animateGlobe);

    if (globeGroup && !isDragging) {
        globeGroup.rotation.y += 0.0015;
    }

    for (let i = attackArcs.length - 1; i >= 0; i--) {
        const arc = attackArcs[i];
        arc.progress += arc.speed * 0.04;

        if (arc.progress > 1.0) {
            arc.progress = 0;
        }

        const point = arc.curve.getPoint(arc.progress);
        if (arc.packetMesh) {
            arc.packetMesh.position.copy(point);
        }

        if (arc.trailNodes) {
            for (let t = 0; t < arc.trailNodes.length; t++) {
                const trailProg = Math.max(0, arc.progress - (t + 1) * 0.04);
                const trailPoint = arc.curve.getPoint(trailProg);
                arc.trailNodes[t].position.copy(trailPoint);
            }
        }
    }

    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
}

// ============================================
// REACT BITS LETTERGLITCH COMPONENT FOR LOGIN PAGE
// Colors: Purple, Gray & Green
// ============================================
let binaryCanvas, binaryCtx, binaryAnimId;

function initBinaryStream() {
    binaryCanvas = document.getElementById('authBinaryCanvas');
    if (!binaryCanvas) return;

    const parent = binaryCanvas.parentElement;
    binaryCtx = binaryCanvas.getContext('2d');

    const glitchColors = [
        '#a855f7', // Vivid Purple
        '#8b5cf6', // Indigo Purple
        '#c084fc', // Soft Purple
        '#64748b', // Slate Gray
        '#94a3b8', // Cool Gray
        '#cbd5e1', // Light Gray
        '#22c55e', // Emerald Green
        '#10b981', // Mint Green
        '#4ade80'  // Bright Neon Green
    ];

    const glitchSpeed = 50;
    const smooth = true;
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$&*()-_+=/[]{};:<>.,0123456789';
    const lettersAndSymbols = Array.from(characters);

    const fontSize = 16;
    const charWidth = 10;
    const charHeight = 20;

    let letters = [];
    let gridCols = 0;
    let gridRows = 0;
    let lastGlitchTime = Date.now();

    const getRandomChar = () => lettersAndSymbols[Math.floor(Math.random() * lettersAndSymbols.length)];
    const getRandomColor = () => glitchColors[Math.floor(Math.random() * glitchColors.length)];

    const hexToRgb = (hex) => {
        if (!hex) return null;
        const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, (m, r, g, b) => r + r + g + g + b + b);
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result
            ? {
                  r: parseInt(result[1], 16),
                  g: parseInt(result[2], 16),
                  b: parseInt(result[3], 16)
              }
            : null;
    };

    const bleedWidth = 140; // Bleed ~140px leftwards over seam into form side

    const calculateGrid = (width, height) => {
        const columns = Math.ceil(width / charWidth);
        const rows = Math.ceil(height / charHeight);
        return { columns, rows };
    };

    const initializeLetters = (columns, rows) => {
        gridCols = columns;
        gridRows = rows;
        const totalLetters = columns * rows;
        letters = Array.from({ length: totalLetters }, () => {
            const startColor = getRandomColor();
            const targetColor = getRandomColor();
            const startRgb = hexToRgb(startColor);
            const targetRgb = hexToRgb(targetColor);
            return {
                char: getRandomChar(),
                color: startColor,
                currentColorRgb: startRgb,
                startColorRgb: startRgb,
                targetColorRgb: targetRgb,
                colorProgress: 1
            };
        });
    };

    const drawLetters = () => {
        if (!binaryCtx || letters.length === 0 || !binaryCanvas || !parent) return;
        const rect = parent.getBoundingClientRect();
        const canvasWidth = rect.width + bleedWidth;
        const canvasHeight = rect.height;

        binaryCtx.clearRect(0, 0, canvasWidth, canvasHeight);
        binaryCtx.font = `${fontSize}px monospace`;
        binaryCtx.textBaseline = 'top';

        letters.forEach((letter, index) => {
            const x = (index % gridCols) * charWidth;
            const y = Math.floor(index / gridCols) * charHeight;

            // Subtle bleed & sparsification gradient towards left form side ("teeny tiny bits")
            if (x < bleedWidth) {
                const fadeRatio = x / bleedWidth;
                const alphaFactor = Math.pow(fadeRatio, 2.0); // smooth curve dissolving to 0 at left edge
                if (alphaFactor < 0.03) return; // skip drawing faint edge bits

                // Sparsify bits so only a few letters drift past the seam
                if ((index % 3 !== 0) && fadeRatio < 0.65) return;

                binaryCtx.globalAlpha = alphaFactor;
            } else {
                binaryCtx.globalAlpha = 1.0;
            }

            binaryCtx.fillStyle = letter.color;
            binaryCtx.fillText(letter.char, x, y);
        });
        binaryCtx.globalAlpha = 1.0;
    };

    const updateLetters = () => {
        if (!letters || letters.length === 0) return;
        const updateCount = Math.max(1, Math.floor(letters.length * 0.05));

        for (let i = 0; i < updateCount; i++) {
            const index = Math.floor(Math.random() * letters.length);
            if (!letters[index]) continue;

            letters[index].char = getRandomChar();
            const newTargetColor = getRandomColor();
            letters[index].startColorRgb = letters[index].currentColorRgb || hexToRgb(letters[index].color);
            letters[index].targetColorRgb = hexToRgb(newTargetColor);

            if (!smooth) {
                letters[index].color = newTargetColor;
                letters[index].currentColorRgb = letters[index].targetColorRgb;
                letters[index].colorProgress = 1;
            } else {
                letters[index].colorProgress = 0;
            }
        }
    };

    const handleSmoothTransitions = () => {
        let needsRedraw = false;
        letters.forEach(letter => {
            if (letter.colorProgress < 1) {
                letter.colorProgress += 0.05;
                if (letter.colorProgress > 1) letter.colorProgress = 1;

                if (letter.startColorRgb && letter.targetColorRgb) {
                    letter.currentColorRgb = {
                        r: Math.round(letter.startColorRgb.r + (letter.targetColorRgb.r - letter.startColorRgb.r) * letter.colorProgress),
                        g: Math.round(letter.startColorRgb.g + (letter.targetColorRgb.g - letter.startColorRgb.g) * letter.colorProgress),
                        b: Math.round(letter.startColorRgb.b + (letter.targetColorRgb.b - letter.startColorRgb.b) * letter.colorProgress)
                    };
                    letter.color = `rgb(${letter.currentColorRgb.r}, ${letter.currentColorRgb.g}, ${letter.currentColorRgb.b})`;
                    needsRedraw = true;
                }
            }
        });

        if (needsRedraw) {
            drawLetters();
        }
    };

    const resizeCanvas = () => {
        if (!binaryCanvas || !parent) return;
        const dpr = window.devicePixelRatio || 1;
        const rect = parent.getBoundingClientRect();

        const canvasWidth = rect.width + bleedWidth;
        const canvasHeight = rect.height;

        binaryCanvas.width = canvasWidth * dpr;
        binaryCanvas.height = canvasHeight * dpr;

        binaryCanvas.style.position = 'absolute';
        binaryCanvas.style.left = `-${bleedWidth}px`;
        binaryCanvas.style.top = '0px';
        binaryCanvas.style.width = `${canvasWidth}px`;
        binaryCanvas.style.height = `${canvasHeight}px`;

        if (binaryCtx) {
            binaryCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        const { columns, rows } = calculateGrid(canvasWidth, canvasHeight);
        initializeLetters(columns, rows);

        drawLetters();
    };

    const animate = () => {
        const now = Date.now();
        if (now - lastGlitchTime >= glitchSpeed) {
            updateLetters();
            drawLetters();
            lastGlitchTime = now;
        }

        if (smooth) {
            handleSmoothTransitions();
        }

        binaryAnimId = requestAnimationFrame(animate);
    };

    resizeCanvas();
    animate();

    let resizeTimeout;
    const handleResize = () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if (binaryAnimId) cancelAnimationFrame(binaryAnimId);
            resizeCanvas();
            animate();
        }, 100);
    };

    window.addEventListener('resize', handleResize);
}

// ============================================
// REACT BITS SCRAMBLEDTEXT COMPONENT FOR SIGNUP PAGE
// ============================================
function initScrambledText() {
    const container = document.getElementById('signupScrambledText');
    if (!container) return;

    const radius = 120;
    const scrambleChars = '.:!@#$&*()-_+=/[]{};:<>.,0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';

    function splitElementText(el) {
        if (!el) return [];
        const nodes = Array.from(el.childNodes);
        el.innerHTML = '';
        const charSpans = [];

        nodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.nodeValue;
                for (let i = 0; i < text.length; i++) {
                    const char = text[i];
                    if (char === '\n' || char === '\r') continue;
                    const span = document.createElement('span');
                    if (char === ' ') {
                        span.className = 'scramble-space';
                        span.innerHTML = '&nbsp;';
                        el.appendChild(span);
                    } else {
                        span.className = 'scramble-char';
                        span.dataset.content = char;
                        span.innerText = char;
                        span.style.display = 'inline-block';
                        span.style.willChange = 'transform, color';
                        charSpans.push(span);
                        el.appendChild(span);
                    }
                }
            } else if (node.nodeName === 'BR') {
                el.appendChild(document.createElement('br'));
            } else {
                const childSpans = splitElementText(node);
                charSpans.push(...childSpans);
                el.appendChild(node);
            }
        });
        return charSpans;
    }

    const titleEl = container.querySelector('.scrambled-title');
    const subtitleEl = container.querySelector('.scrambled-subtitle');

    let allCharSpans = [];
    if (titleEl) allCharSpans = allCharSpans.concat(splitElementText(titleEl));
    if (subtitleEl) allCharSpans = allCharSpans.concat(splitElementText(subtitleEl));

    // Pointer move mouse proximity scramble
    const handleMove = (e) => {
        const pointerX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
        const pointerY = e.clientY || (e.touches && e.touches[0].clientY) || 0;

        allCharSpans.forEach(span => {
            if (span.dataset.isScrambling === 'true') return;

            const rect = span.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return;
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dist = Math.hypot(pointerX - cx, pointerY - cy);

            if (dist < radius) {
                span.dataset.isScrambling = 'true';
                const originalChar = span.dataset.content;
                const duration = Math.max(300, 1000 * (1 - dist / radius));
                const startTime = Date.now();

                const scrambleInterval = setInterval(() => {
                    const elapsed = Date.now() - startTime;
                    if (elapsed >= duration) {
                        clearInterval(scrambleInterval);
                        span.innerText = originalChar;
                        span.style.color = '';
                        delete span.dataset.isScrambling;
                    } else {
                        const randomChar = scrambleChars[Math.floor(Math.random() * scrambleChars.length)];
                        span.innerText = randomChar;
                        span.style.color = Math.random() < 0.5 ? '#c084fc' : '#61dca3';
                    }
                }, 40);
            }
        });
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('mousemove', handleMove);

    // Initial entrance scramble sweep
    setTimeout(() => {
        allCharSpans.forEach((span, idx) => {
            setTimeout(() => {
                const original = span.dataset.content;
                let count = 0;
                const sweep = setInterval(() => {
                    count++;
                    if (count > 6) {
                        clearInterval(sweep);
                        span.innerText = original;
                        span.style.color = '';
                    } else {
                        span.innerText = scrambleChars[Math.floor(Math.random() * scrambleChars.length)];
                        span.style.color = '#c084fc';
                    }
                }, 40);
            }, idx * 15);
        });
    }, 150);
}

// ============================================
// ORIGINKIT SHATTER & REASSEMBLE PARTICLE "ARGUS" FOR SIGNUP PAGE
// ============================================
function initArgusParticleText() {
    const canvas = document.getElementById('argusParticleCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let W = 0, H = 0, dpr = 1;
    let particles = [];
    let bgNodes = [];
    let state = 'active'; // 'active', 'shattered', 'gathering'
    let shatterTimeout = null;

    // Argus Electric Violet Theme Palette
    const BASE_COLOR = 'rgba(168, 85, 247, 0.78)';   // #A855F7 at 78% opacity
    const HOVER_COLOR = 'rgba(192, 132, 252, 0.96)';  // #C084FC at 96% opacity
    const SHADOW_COLOR = 'rgba(168, 85, 247, 0.40)';
    const HOVER_SHADOW_COLOR = 'rgba(192, 132, 252, 0.75)';

    // Prominent Ambient Cyber Network Nodes
    function initBgNodes() {
        bgNodes = [];
        const nodeCount = Math.floor(Math.min((W * H) / 24000, 60));
        for (let i = 0; i < nodeCount; i++) {
            bgNodes.push({
                x: Math.random() * W,
                y: Math.random() * H,
                vx: (Math.random() - 0.5) * 0.25,
                vy: (Math.random() - 0.5) * 0.25,
                radius: 1.4 + Math.random() * 1.0,
                baseAlpha: 0.25 + Math.random() * 0.18,
                pulseOffset: Math.random() * Math.PI * 2
            });
        }
    }

    function renderBgNodes(time) {
        const nodeCount = bgNodes.length;

        // Prominent connecting cyber network lines between nearby nodes
        for (let i = 0; i < nodeCount; i++) {
            const n1 = bgNodes[i];
            for (let j = i + 1; j < nodeCount; j++) {
                const n2 = bgNodes[j];
                const dx = n1.x - n2.x;
                const dy = n1.y - n2.y;
                const distSq = dx * dx + dy * dy;
                const maxDistSq = 25600; // ~160px
                if (distSq < maxDistSq) {
                    const dist = Math.sqrt(distSq);
                    const lineAlpha = (1 - dist / 160) * 0.22;
                    ctx.shadowBlur = 0;
                    ctx.strokeStyle = `rgba(168, 85, 247, ${lineAlpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.beginPath();
                    ctx.moveTo(n1.x, n1.y);
                    ctx.lineTo(n2.x, n2.y);
                    ctx.stroke();
                }
            }
        }

        // Glowing cyber node points
        bgNodes.forEach(n => {
            n.x += n.vx;
            n.y += n.vy;
            if (n.x < 0) n.x = W; if (n.x > W) n.x = 0;
            if (n.y < 0) n.y = H; if (n.y > H) n.y = 0;

            const alpha = n.baseAlpha + Math.sin(time * 0.002 + n.pulseOffset) * 0.10;
            ctx.shadowColor = 'rgba(168, 85, 247, 0.6)';
            ctx.shadowBlur = 5;
            ctx.fillStyle = `rgba(192, 132, 252, ${Math.max(0.15, alpha)})`;
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.shadowBlur = 0;
    }

    function drawStaticText() {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, W, H);

        const isDesktop = window.innerWidth > 992;
        const textCenterX = isDesktop ? W * 0.25 : W * 0.5;
        const textCenterY = H * 0.5;
        const fontSize = Math.round(Math.min(W * 0.15, 175));

        ctx.fillStyle = BASE_COLOR;
        ctx.font = `900 ${fontSize}px "Poppins", "Outfit", "Plus Jakarta Sans", sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Argus', textCenterX, textCenterY);
    }

    function createParticleMatrix() {
        if (!canvas) return;
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = window.innerWidth;
        H = window.innerHeight;

        canvas.width = W * dpr;
        canvas.height = H * dpr;
        canvas.style.width = `${W}px`;
        canvas.style.height = `${H}px`;

        initBgNodes();
        drawStaticText();

        let imgData;
        try {
            imgData = ctx.getImageData(0, 0, W * dpr, H * dpr).data;
        } catch (e) {
            console.error('Canvas getImageData failed:', e);
            return;
        }

        particles = [];
        // Moderately refined sampling gap for crisp, clean, separated particles
        const gap = Math.max(4, Math.floor(4.2 * dpr));

        for (let y = 0; y < H * dpr; y += gap) {
            for (let x = 0; x < W * dpr; x += gap) {
                const idx = (y * (W * dpr) + x) * 4;
                if (imgData[idx + 3] > 70) {
                    // Controlled size variation for 4-5.5px clean circular particles
                    const rand = Math.random();
                    let radius;
                    if (rand < 0.82) {
                        radius = 2.10; // Primary size (~4.2px diameter)
                    } else if (rand < 0.92) {
                        radius = 1.70; // Slightly smaller (~3.4px diameter)
                    } else {
                        radius = 2.50; // Slightly larger (~5.0px diameter)
                    }

                    particles.push({
                        x: x / dpr,
                        y: y / dpr,
                        homeX: x / dpr,
                        homeY: y / dpr,
                        vx: 0,
                        vy: 0,
                        baseRadius: radius,
                        hoverRatio: 0
                    });
                }
            }
        }

        ctx.clearRect(0, 0, W, H);
    }

    function shatter() {
        if (particles.length === 0) {
            createParticleMatrix();
        }
        state = 'shattered';
        clearTimeout(shatterTimeout);

        // High-velocity explosion scattering across full 100vw x 100vh viewport
        particles.forEach(p => {
            const angle = Math.random() * Math.PI * 2;
            const speed = 25 + Math.random() * 45;
            p.vx = Math.cos(angle) * speed;
            p.vy = Math.sin(angle) * speed;
        });

        shatterTimeout = setTimeout(() => {
            state = 'gathering';
        }, 1700);
    }

    let mouseX = -9999, mouseY = -9999;
    const handlePointerMove = (e) => {
        mouseX = e.clientX || (e.touches && e.touches[0].clientX) || -9999;
        mouseY = e.clientY || (e.touches && e.touches[0].clientY) || -9999;
    };

    const handlePointerLeave = () => {
        mouseX = -9999;
        mouseY = -9999;
    };

    window.addEventListener('click', (e) => {
        const isDesktop = window.innerWidth > 992;
        const targetWidth = isDesktop ? W * 0.52 : W;
        if (e.clientX < targetWidth || state === 'shattered') {
            shatter();
        }
    });

    window.addEventListener('mousemove', handlePointerMove);
    window.addEventListener('mouseleave', handlePointerLeave);
    window.addEventListener('touchstart', (e) => {
        handlePointerMove(e);
        const isDesktop = window.innerWidth > 992;
        if (e.touches && e.touches[0].clientX < (isDesktop ? W * 0.52 : W)) {
            shatter();
        }
    });

    let animId = null;

    function render(time = 0) {
        if (!ctx) return;
        ctx.clearRect(0, 0, W, H);

        // Render ambient background cyber network nodes & faint links
        renderBgNodes(time);

        if (particles.length === 0) {
            drawStaticText();
            animId = requestAnimationFrame(render);
            return;
        }

        let allSettled = true;

        particles.forEach(p => {
            if (state === 'shattered') {
                p.x += p.vx;
                p.y += p.vy;
                p.vx *= 0.95;
                p.vy *= 0.95;

                if (p.x < 0 || p.x > W) p.vx *= -0.7;
                if (p.y < 0 || p.y > H) p.vy *= -0.7;

                allSettled = false;
            } else if (state === 'gathering') {
                const dx = p.homeX - p.x;
                const dy = p.homeY - p.y;
                p.x += dx * 0.08;
                p.y += dy * 0.08;

                if (Math.hypot(dx, dy) > 0.4) {
                    allSettled = false;
                }
            } else {
                let isNearMouse = false;
                if (mouseX > -9000) {
                    const dx = p.x - mouseX;
                    const dy = p.y - mouseY;
                    const dist = Math.hypot(dx, dy);
                    const repelRadius = 80;

                    if (dist < repelRadius && dist > 0) {
                        isNearMouse = true;
                        const force = (1 - dist / repelRadius) * 5.5;
                        p.x += (dx / dist) * force;
                        p.y += (dy / dist) * force;
                    }
                }

                p.x += (p.homeX - p.x) * 0.12;
                p.y += (p.homeY - p.y) * 0.12;

                const targetHover = isNearMouse ? 1 : 0;
                p.hoverRatio += (targetHover - p.hoverRatio) * 0.15;
            }

            // Calculate visuals based on hover ratio
            const currentAlpha = 0.75 + (p.hoverRatio || 0) * 0.21;
            const currentRadius = p.baseRadius * (1 + (p.hoverRatio || 0) * 0.14);
            const blurAmount = 4 + (p.hoverRatio || 0) * 5;

            // Render crisp, smooth anti-aliased violet particle with subtle halo
            ctx.shadowColor = p.hoverRatio > 0.3 ? HOVER_SHADOW_COLOR : SHADOW_COLOR;
            ctx.shadowBlur = blurAmount;

            ctx.fillStyle = p.hoverRatio > 0.3 
                ? `rgba(192, 132, 252, ${currentAlpha})`
                : `rgba(168, 85, 247, ${currentAlpha})`;

            ctx.beginPath();
            ctx.arc(p.x, p.y, currentRadius, 0, Math.PI * 2);
            ctx.fill();
        });

        // Reset shadow state for clean canvas loop
        ctx.shadowBlur = 0;

        if (state === 'gathering' && allSettled) {
            state = 'active';
        }

        animId = requestAnimationFrame(render);
    }

    createParticleMatrix();
    render();

    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => {
            createParticleMatrix();
        });
    }
    setTimeout(createParticleMatrix, 150);
    setTimeout(createParticleMatrix, 400);

    window.addEventListener('resize', () => {
        if (animId) cancelAnimationFrame(animId);
        createParticleMatrix();
        render();
    });
}

// Auto-run if script loads after DOM
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    try { initArgusParticleText(); } catch (e) {}
}
