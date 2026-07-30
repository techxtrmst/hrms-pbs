/**
 * HRMS Clock-Out Reminder System
 * ================================
 * - Polls /employees/api/location/status/ every 60 seconds
 * - When user has been clocked in for >= 8h 55m → fires:
 *     1. Urgent beep sound (Web Audio API — no file needed)
 *     2. OS-level Browser Notification (works even when tab is not active)
 *     3. In-page popup card (visible when user is on any HRMS page)
 * - "Remind in 5 min" snoozes the alert for 5 minutes
 * - Clears itself once user clocks out
 */

(function () {
    'use strict';

    // ── Config ─────────────────────────────────────────────────────────────────
    const STATUS_API      = '/employees/api/location/status/';
    const POLL_INTERVAL   = 60 * 1000;          // check every 60 s
    const REMINDER_THRESHOLD = (8 * 60 + 55) * 60 * 1000; // 8h 55m in ms
    const SNOOZE_DURATION    = 5 * 60 * 1000;              // 5 min snooze
    const NOTIF_TAG          = 'hrms-clockout-reminder';

    let pollTimer        = null;
    let snoozeUntil      = 0;          // epoch ms — 0 means not snoozed
    let lastFiredAt      = 0;          // prevent re-firing in same minute
    let swRegistration   = null;

    // ── Boot ───────────────────────────────────────────────────────────────────
    function init() {
        injectPopupHTML();
        requestNotifPermission();
        registerSW();
        startPolling();
    }

    // ── Service Worker registration ────────────────────────────────────────────
    function registerSW() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then(reg => {
                swRegistration = reg;
            }).catch(() => {});
        }
    }

    // ── Notification permission ────────────────────────────────────────────────
    function requestNotifPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }

    // ── Polling ────────────────────────────────────────────────────────────────
    function startPolling() {
        checkStatus();                             // immediate first check
        pollTimer = setInterval(checkStatus, POLL_INTERVAL);
    }

    function checkStatus() {
        fetch(STATUS_API, { credentials: 'same-origin' })
            .then(r => r.json())
            .then(data => {
                if (!data.is_clocked_in || !data.clock_in_time) {
                    hidePopup();   // user is clocked out — hide any open popup
                    return;
                }

                const clockInMs  = new Date(data.clock_in_time).getTime();
                const elapsedMs  = Date.now() - clockInMs;
                const nowMs      = Date.now();

                // ── Guard: don't re-fire within 5-min cooldown ────────────────
                const cooldownPassed = nowMs - lastFiredAt >= 5 * 60 * 1000;
                const notSnoozed     = nowMs >= snoozeUntil;

                let shouldFire   = false;
                let fireReason   = '';

                // ── Trigger 1: Dynamic 8h 55m ─────────────────────────────────
                if (elapsedMs >= REMINDER_THRESHOLD) {
                    shouldFire = true;
                    fireReason = 'dynamic';
                }

                // ── Trigger 2: Scheduled shift-end (5 min before) ─────────────
                if (!shouldFire && data.shift_end_time) {
                    const shiftEndMs = new Date(data.shift_end_time).getTime();
                    const msUntilEnd = shiftEndMs - nowMs;

                    // Fire window: between -60s (past end) and 5 min 30s before end
                    // This catches the poll that lands closest to the 5-min mark
                    if (msUntilEnd <= 5 * 60 * 1000 + 30000 && msUntilEnd >= -60000) {
                        shouldFire = true;
                        fireReason = 'shift_end';
                    }
                }

                if (shouldFire && cooldownPassed && notSnoozed) {
                    lastFiredAt = nowMs;
                    triggerReminder(elapsedMs, fireReason, data.shift_end_time);
                } else if (!shouldFire) {
                    hidePopup();
                }
            })
            .catch(() => {});    // silently ignore network errors
    }

    // ── Main trigger ──────────────────────────────────────────────────────────
    // reason: 'dynamic' | 'shift_end'
    // shiftEndTime: ISO string or undefined
    function triggerReminder(elapsedMs, reason, shiftEndTime) {
        playUrgentBeeps();
        showOSNotification(elapsedMs, reason, shiftEndTime);
        showInPagePopup(elapsedMs, reason, shiftEndTime);
    }

    // ── Sound: Urgent Beeps (Web Audio API) ───────────────────────────────────
    function playUrgentBeeps() {
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctx = new AudioCtx();

            function beep(freq, startSec, durSec, vol) {
                const osc  = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.type = 'square';
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(vol, ctx.currentTime + startSec);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startSec + durSec);
                osc.start(ctx.currentTime + startSec);
                osc.stop(ctx.currentTime + startSec + durSec);
            }

            // Pattern: fast triple beep × 2, then a long high note
            beep(1400, 0.00, 0.14, 0.25);
            beep(1400, 0.18, 0.14, 0.25);
            beep(1400, 0.36, 0.14, 0.25);
            beep(1400, 0.60, 0.14, 0.25);
            beep(1400, 0.78, 0.14, 0.25);
            beep(1400, 0.96, 0.14, 0.25);
            beep(1700, 1.20, 0.55, 0.22);   // final high tone
        } catch (e) {
            // Web Audio not available — silent fallback
        }
    }

    // ── OS-level Browser Notification ────────────────────────────────────────
    function showOSNotification(elapsedMs, reason, shiftEndTime) {
        const hoursStr  = formatElapsed(elapsedMs);
        const isShiftEnd = reason === 'shift_end';
        const title  = '⏰ Time to Clock Out!';
        let   body;

        if (isShiftEnd && shiftEndTime) {
            const endFmt = new Date(shiftEndTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            body = `Your shift ends at ${endFmt} — in about 5 minutes!\nPlease clock out before your shift ends.`;
        } else {
            body = `You've been clocked in for ${hoursStr}.\nHead to HRMS and click "Clock Out".`;
        }

        // Prefer Service Worker notification (works when tab is hidden/minimised)
        if (swRegistration && swRegistration.showNotification) {
            swRegistration.showNotification(title, {
                body,
                icon: '/static/img/petabytz_logo.jpg',
                badge: '/static/img/petabytz_logo.jpg',
                tag: NOTIF_TAG,
                requireInteraction: true,
                vibrate: [200, 100, 200, 100, 400],
                actions: [
                    { action: 'goto', title: '🕒 Go to HRMS' },
                    { action: 'dismiss', title: 'Dismiss' }
                ]
            }).catch(() => fallbackNotification(title, body));
        } else {
            fallbackNotification(title, body);
        }
    }

    function fallbackNotification(title, body) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const n = new Notification(title, {
                body,
                icon: '/static/img/petabytz_logo.jpg',
                tag: NOTIF_TAG,
                requireInteraction: true
            });
            n.onclick = () => { window.focus(); n.close(); };
        }
    }

    // ── In-page Popup ─────────────────────────────────────────────────────────
    function showInPagePopup(elapsedMs, reason, shiftEndTime) {
        const popup = document.getElementById('hrms-clockout-popup');
        if (!popup) return;

        const isShiftEnd = reason === 'shift_end';
        const elapsedEl  = document.getElementById('hrms-clockout-elapsed');
        const bodyEl     = document.getElementById('hrms-clockout-body');

        if (isShiftEnd && shiftEndTime) {
            const endFmt = new Date(shiftEndTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            elapsedEl.textContent = endFmt;
            bodyEl.innerHTML = `Your shift ends at <strong>${endFmt}</strong> — in about 5 minutes.<br>Please clock out before your shift closes.`;
        } else {
            elapsedEl.textContent = formatElapsed(elapsedMs);
            bodyEl.innerHTML = `You've been clocked in for <strong id="hrms-clockout-elapsed">${formatElapsed(elapsedMs)}</strong>.<br>Your shift is almost done — don't forget to clock out.`;
        }

        popup.classList.add('hrms-popup-visible');
        popup.setAttribute('aria-hidden', 'false');

        // Pulse the popup border to draw attention
        popup.classList.remove('hrms-popup-pulse');
        void popup.offsetWidth;   // reflow trick to restart animation
        popup.classList.add('hrms-popup-pulse');
    }

    function hidePopup() {
        const popup = document.getElementById('hrms-clockout-popup');
        if (popup) {
            popup.classList.remove('hrms-popup-visible', 'hrms-popup-pulse');
            popup.setAttribute('aria-hidden', 'true');
        }
    }

    // ── Snooze ────────────────────────────────────────────────────────────────
    window._hrmsClockoutSnooze = function () {
        snoozeUntil = Date.now() + SNOOZE_DURATION;
        hidePopup();
        // Re-check after snooze expires
        setTimeout(checkStatus, SNOOZE_DURATION + 1000);
    };

    // ── Helpers ───────────────────────────────────────────────────────────────
    function formatElapsed(ms) {
        const totalMin = Math.floor(ms / 60000);
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        if (h > 0) return `${h} hour${h > 1 ? 's' : ''} ${m} min`;
        return `${m} min`;
    }

    // ── Inject popup HTML into <body> ─────────────────────────────────────────
    function injectPopupHTML() {
        // Avoid duplicates if script loaded twice
        if (document.getElementById('hrms-clockout-popup')) return;

        const style = document.createElement('style');
        style.id = 'hrms-clockout-styles';
        style.textContent = `
            #hrms-clockout-popup {
                display: none;
                position: fixed;
                bottom: 28px;
                right: 28px;
                width: 320px;
                background: linear-gradient(145deg, #0f172a, #1e1b4b);
                border: 1.5px solid #6c63ff;
                border-radius: 18px;
                padding: 20px 22px 18px;
                box-shadow: 0 8px 40px rgba(108,99,255,0.35), 0 2px 12px rgba(0,0,0,0.6);
                z-index: 99999;
                font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
                color: #fff;
                animation: hrmsSlideIn 0.4s cubic-bezier(.22,1,.36,1) forwards;
            }
            #hrms-clockout-popup.hrms-popup-visible {
                display: block;
            }
            #hrms-clockout-popup.hrms-popup-pulse {
                animation: hrmsSlideIn 0.4s cubic-bezier(.22,1,.36,1) forwards,
                           hrmsPulse 1.2s ease 0.4s 3;
            }
            @keyframes hrmsSlideIn {
                from { opacity: 0; transform: translateX(60px) scale(0.95); }
                to   { opacity: 1; transform: translateX(0)    scale(1);    }
            }
            @keyframes hrmsPulse {
                0%,100% { box-shadow: 0 8px 40px rgba(108,99,255,0.35); }
                50%      { box-shadow: 0 8px 55px rgba(220,38,38,0.65); border-color: #ef4444; }
            }
            .hrms-popup-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 10px;
            }
            .hrms-popup-icon {
                font-size: 1.6rem;
                line-height: 1;
            }
            .hrms-popup-title {
                font-size: 1rem;
                font-weight: 700;
                color: #fff;
                letter-spacing: -0.2px;
            }
            .hrms-popup-close {
                margin-left: auto;
                background: none;
                border: none;
                color: #64748b;
                font-size: 1rem;
                cursor: pointer;
                padding: 2px 5px;
                border-radius: 4px;
                transition: color 0.2s;
                line-height: 1;
            }
            .hrms-popup-close:hover { color: #fff; }
            .hrms-popup-body {
                font-size: 0.83rem;
                color: #94a3b8;
                line-height: 1.55;
                margin-bottom: 16px;
            }
            .hrms-popup-body strong { color: #c4b5fd; }
            .hrms-popup-actions {
                display: flex;
                gap: 10px;
            }
            .hrms-btn-clockout {
                flex: 1;
                padding: 10px 8px;
                background: linear-gradient(135deg, #6c63ff, #a855f7);
                border: none;
                border-radius: 9px;
                color: #fff;
                font-size: 0.84rem;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s, transform 0.15s;
                letter-spacing: 0.2px;
            }
            .hrms-btn-clockout:hover { opacity: 0.88; transform: translateY(-1px); }
            .hrms-btn-snooze {
                flex: 1;
                padding: 10px 8px;
                background: transparent;
                border: 1px solid #334155;
                border-radius: 9px;
                color: #94a3b8;
                font-size: 0.82rem;
                cursor: pointer;
                transition: border-color 0.2s, color 0.2s;
            }
            .hrms-btn-snooze:hover { border-color: #64748b; color: #cbd5e1; }
        `;
        document.head.appendChild(style);

        const popup = document.createElement('div');
        popup.id = 'hrms-clockout-popup';
        popup.setAttribute('role', 'alertdialog');
        popup.setAttribute('aria-hidden', 'true');
        popup.setAttribute('aria-label', 'Clock-out reminder');
        popup.innerHTML = `
            <div class="hrms-popup-header">
                <span class="hrms-popup-icon">⏰</span>
                <span class="hrms-popup-title">Time to Clock Out!</span>
                <button class="hrms-popup-close" onclick="window._hrmsClockoutSnooze()" aria-label="Close reminder">✕</button>
            </div>
            <div class="hrms-popup-body" id="hrms-clockout-body">
                You've been clocked in for <strong id="hrms-clockout-elapsed">8 h 55 min</strong>.<br>
                Your shift is almost done — don't forget to clock out.
            </div>
            <div class="hrms-popup-actions">
                <button class="hrms-btn-clockout" id="hrms-clockout-btn" onclick="window._hrmsGoClockOut()">
                    🕒 Clock Out Now
                </button>
                <button class="hrms-btn-snooze" onclick="window._hrmsClockoutSnooze()">
                    Remind in 5 min
                </button>
            </div>
        `;
        document.body.appendChild(popup);

        // Navigate to HRMS personal home (where clock-out button lives)
        window._hrmsGoClockOut = function () {
            const base = window.location.origin;
            window.location.href = base + '/';   // adjust if your home URL is different
        };
    }

    // ── Start ─────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
