document.addEventListener('DOMContentLoaded', () => {
    // GSAP Setup
    gsap.registerPlugin(TextPlugin);

    // Elements
    const personaSelect = document.getElementById('persona-select');
    const formContainer = document.getElementById('dynamic-form-container');
    const forms = {
        shopper: document.getElementById('form-shopper'),
        rider: document.getElementById('form-rider'),
        patient: document.getElementById('form-patient')
    };
    const findDealBtn = document.getElementById('find-deal-btn');
    const cursorDot = document.querySelector('.cursor-dot');
    const cursorOutline = document.querySelector('.cursor-outline');

    // Lenis Smooth Scroll
    const lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        direction: 'vertical',
        gestureDirection: 'vertical',
        smooth: true,
        mouseMultiplier: 1,
        smoothTouch: false,
        touchMultiplier: 2,
    });

    function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
    }

    requestAnimationFrame(raf);

    // Init Animations
    const initTimeline = gsap.timeline({ paused: true });

    initTimeline
        .from('.reveal-text', {
            y: 100,
            opacity: 0,
            duration: 1.2,
            stagger: 0.1,
            ease: 'power4.out'
        })
        .from('.hero-subtitle', {
            opacity: 0,
            y: 20,
            duration: 1
        }, '-=0.8')
        .from('.interaction-area', {
            opacity: 0,
            x: 30, // Came from right due to split layout
            duration: 1
        }, '-=0.6');

    // Preloader Sequence
    const counterElement = document.querySelector('.counter');
    const preloaderElement = document.querySelector('.preloader');

    let count = { val: 0 };

    gsap.to(count, {
        val: 100,
        duration: 2.5,
        ease: 'power2.inOut',
        onUpdate: () => {
            counterElement.textContent = Math.floor(count.val).toString().padStart(3, '0'); // 001, 002 format? or just 0

            // Zoom Effect during count
            const progress = count.val / 100;
            // Responsive Multiplier: 15 for Desktop, 5 for Mobile
            const isMobile = window.innerWidth < 768;
            const multiplier = isMobile ? 5 : 15;

            const baseSize = isMobile ? 3 : 5; // Base rem size
            const size = baseSize + (progress * multiplier);

            counterElement.style.fontSize = `${size}rem`;
        },
        onComplete: () => {
            // Reveal App
            const preloaderTimeline = gsap.timeline();

            preloaderTimeline
                .to(counterElement, {
                    scale: 1.1,
                    duration: 0.2,
                    ease: "power1.out"
                })
                .to(preloaderElement, {
                    yPercent: -100,
                    duration: 1,
                    ease: "power4.inOut"
                })
                .add(() => {
                    initTimeline.play();
                }, "-=0.5");
        }
    });


    // Custom Cursor
    window.addEventListener('mousemove', (e) => {
        const posX = e.clientX;
        const posY = e.clientY;

        cursorDot.style.left = `${posX}px`;
        cursorDot.style.top = `${posY}px`;

        // Smooth follow for outline
        cursorOutline.animate({
            left: `${posX - 20}px`,
            top: `${posY - 20}px`
        }, { duration: 500, fill: "forwards" });
    });

    // Custom Dropdown Logic
    const dropdownTrigger = document.querySelector('.dropdown-trigger');
    const dropdownOptions = document.querySelector('.dropdown-options');
    const options = document.querySelectorAll('.dropdown-option');
    const selectedText = document.querySelector('.selected-text');
    const hiddenInput = document.getElementById('persona-select-value');

    // Toggle Dropdown
    dropdownTrigger.addEventListener('click', () => {
        dropdownOptions.classList.toggle('active');

        // Rotate arrow
        const arrow = dropdownTrigger.querySelector('.dropdown-arrow');
        if (dropdownOptions.classList.contains('active')) {
            gsap.to(arrow, { rotation: 225, duration: 0.3 });
        } else {
            gsap.to(arrow, { rotation: 45, duration: 0.3 });
        }
    });

    // Option Selection
    options.forEach(option => {
        option.addEventListener('click', () => {
            const value = option.dataset.value;
            const text = option.textContent;

            // Update UI
            selectedText.textContent = text;
            hiddenInput.value = value;
            dropdownOptions.classList.remove('active');

            // Reset arrow
            const arrow = dropdownTrigger.querySelector('.dropdown-arrow');
            gsap.to(arrow, { rotation: 45, duration: 0.3 });

            // Trigger Form Switch
            switchForm(value);
        });
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.custom-dropdown-container')) {
            dropdownOptions.classList.remove('active');
            const arrow = dropdownTrigger.querySelector('.dropdown-arrow');
            gsap.to(arrow, { rotation: 45, duration: 0.3 });
        }
    });

    function switchForm(persona) {
        // Animate out current forms
        const currentVisible = formContainer.querySelector('.form-content:not(.hidden)');
        if (currentVisible) {
            gsap.to(currentVisible.children, {
                y: -20,
                opacity: 0,
                stagger: 0.05,
                duration: 0.4,
                ease: 'power2.in',
                onComplete: () => {
                    currentVisible.classList.add('hidden');
                    showNewForm(persona);
                }
            });
        } else {
            showNewForm(persona);
        }
    }

    function showNewForm(persona) {
        const activeForm = forms[persona];
        if (activeForm) {
            activeForm.classList.remove('hidden');
            // Reset state
            gsap.set(activeForm.children, { y: 30, opacity: 0 });

            // Stagger in
            gsap.to(activeForm.children, {
                y: 0,
                opacity: 1,
                stagger: 0.1,
                duration: 0.8,
                ease: 'power3.out',
                delay: 0.1
            });
        }
    }

    // Button Magnetic Fill Effect
    findDealBtn.addEventListener('mousemove', (e) => {
        const rect = findDealBtn.getBoundingClientRect();
        const fill = findDealBtn.querySelector('.btn-fill');

        // Calculate mouse position relative to button
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        gsap.to(fill, {
            left: x,
            top: y,
            duration: 0.3,
            ease: 'power2.out'
        });
    });

    // API & WebSocket Interaction
    findDealBtn.addEventListener('click', async () => {
        const persona = hiddenInput.value;
        if (!persona) {
            console.warn('Please select a persona first.');
            // Shake button or show error visual could go here
            return;
        }

        const payload = {
            persona: persona,
            timestamp: new Date().toISOString()
        };

        // Gather specific data
        if (persona === 'shopper') {
            payload.product = document.getElementById('product-name').value;
        } else if (persona === 'rider') {
            payload.pickup = document.getElementById('pickup-location').value;
            payload.drop = document.getElementById('drop-location').value;
        } else if (persona === 'patient') {
            payload.medicine = document.getElementById('medicine-name').value;
        }

        logStatus(`Starting sequence for ${persona}...`);

        try {
            const response = await fetch('http://localhost:8000/task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                logStatus('Task sent successfully. Enforcing protocol...');
            } else {
                logStatus('Server responded with error.', 'error');
            }
        } catch (error) {
            logStatus(`Connection failed: ${error.message}. (Is backend running?)`, 'error');
        }
    });

    // WebSocket Connection
    function connectWebSocket() {
        const ws = new WebSocket('ws://localhost:8000/ws');

        ws.onopen = () => {
            logStatus('Live Uplink Established.');
        };

        ws.onmessage = (event) => {
            logStatus(`> ${event.data}`);
        };

        ws.onerror = (error) => {
            // Silently handle error to avoid console span if no server
            console.log('WS Connect Error');
        };

        ws.onclose = () => {
            logStatus('Uplink Disconnected. Retrying in 5s...');
            setTimeout(connectWebSocket, 5000);
        };
    }

    // Helper: Log Status
    function logStatus(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        if (type === 'error') {
            console.error(`[${timestamp}] ${message}`);
        } else {
            console.log(`[${timestamp}] ${message}`);
        }
    }

    // Initialize WS
    connectWebSocket();
});
