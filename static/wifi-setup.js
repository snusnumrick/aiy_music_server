// WiFi Setup JavaScript

// DOM Elements
const loadingEl = document.getElementById('loading');
const errorEl = document.getElementById('error-message');
const formEl = document.getElementById('wifi-setup-form');
const networkSelectEl = document.getElementById('network-select');
const networkInfoEl = document.getElementById('network-info');
const selectedSsidEl = document.getElementById('selected-ssid');
const securityTypeEl = document.getElementById('security-type');
const passwordEl = document.getElementById('wifi-password');
const togglePasswordBtn = document.getElementById('toggle-password');
const connectBtn = document.getElementById('connect-btn');
const successMessageEl = document.getElementById('success-message');
const restartBtn = document.getElementById('restart-btn');
const statusMessageEl = document.getElementById('status-message');

// State
let networks = [];
let selectedNetwork = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadNetworks();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Network selection
    networkSelectEl.addEventListener('change', handleNetworkSelection);

    // Toggle password visibility
    togglePasswordBtn.addEventListener('click', togglePasswordVisibility);

    // Connect button
    connectBtn.addEventListener('click', connectToWiFi);

    // Restart button
    restartBtn.addEventListener('click', restartServer);
}

// Load available WiFi networks
async function loadNetworks() {
    try {
        const response = await fetch('/api/wifi/networks');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load networks');
        }

        networks = data.networks || [];
        displayNetworks();
        hideLoading();
        showForm();

    } catch (error) {
        console.error('Error loading networks:', error);
        showError(`Failed to load WiFi networks: ${error.message}`);
        hideLoading();
    }
}

// Display networks in dropdown
function displayNetworks() {
    if (networks.length === 0) {
        networkSelectEl.innerHTML = '<option value="">No networks found</option>';
        return;
    }

    networkSelectEl.innerHTML = '<option value="">Select a network...</option>';

    networks.forEach(network => {
        const option = document.createElement('option');
        option.value = network.ssid;

        let security = 'Open';
        if (network.security) {
            security = network.security;
        } else if (network.encryption === 'on') {
            security = 'WPA/WPA2';
        }

        // Add signal strength indicator
        let signalIndicator = '';
        if (network.signal) {
            const quality = network.signal.split('/')[0];
            const level = parseInt(quality);
            if (level >= 70) signalIndicator = '📶📶📶';
            else if (level >= 40) signalIndicator = '📶📶';
            else signalIndicator = '📶';
        }

        // Mark hidden networks
        if (network.hidden) {
            option.textContent = `${signalIndicator} [Hidden Network] (${security})`;
        } else {
            option.textContent = `${signalIndicator} ${network.ssid} (${security})`;
        }

        networkSelectEl.appendChild(option);
    });
}

// Handle network selection
function handleNetworkSelection() {
    const selectedSsid = networkSelectEl.value;

    if (!selectedSsid) {
        networkInfoEl.style.display = 'none';
        selectedNetwork = null;
        return;
    }

    // Find selected network
    selectedNetwork = networks.find(n => n.ssid === selectedSsid);

    if (selectedNetwork) {
        // Handle hidden network
        if (selectedNetwork.hidden) {
            // Show dialog to enter SSID
            const actualSsid = prompt('Enter the hidden network name (SSID):');
            if (!actualSsid) {
                networkSelectEl.value = '';
                return;
            }
            // Create a new network object with the actual SSID
            selectedNetwork = {
                ...selectedNetwork,
                ssid: actualSsid,
                actualSsid: actualSsid
            };
        }

        selectedSsidEl.textContent = selectedNetwork.actualSsid || selectedNetwork.ssid;

        let security = 'Open';
        if (selectedNetwork.security) {
            security = selectedNetwork.security;
        } else if (selectedNetwork.encryption === 'on') {
            security = 'WPA/WPA2';
        }

        securityTypeEl.textContent = security;
        networkInfoEl.style.display = 'block';

        // Focus on password field if network requires password
        if (selectedNetwork.encryption === 'on' || selectedNetwork.security) {
            setTimeout(() => passwordEl.focus(), 100);
        }
    }
}

// Toggle password visibility
function togglePasswordVisibility() {
    const type = passwordEl.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordEl.setAttribute('type', type);

    const icon = togglePasswordBtn.querySelector('i');
    if (type === 'text') {
        icon.setAttribute('data-lucide', 'eye-off');
    } else {
        icon.setAttribute('data-lucide', 'eye');
    }
    lucide.createIcons();
}

// Connect to WiFi
async function connectToWiFi() {
    if (!selectedNetwork) {
        showError('Please select a WiFi network');
        return;
    }

    const password = passwordEl.value;

    // Check if password is required
    if ((selectedNetwork.encryption === 'on' || selectedNetwork.security) && !password) {
        showError('This network requires a password');
        passwordEl.focus();
        return;
    }

    // Show loading state
    setConnectButtonLoading(true);
    hideError();
    hideSuccess();

    try {
        const response = await fetch('/api/wifi/configure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ssid: selectedNetwork.ssid,
                password: password || ''
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to configure WiFi');
        }

        // Check if reboot is required (wlan0 not available - normal in hotspot mode)
        if (data.reboot_required) {
            showRebootError('Pi is in hotspot mode. Reboot required to connect to WiFi.');
            return;
        }

        showSuccess('WiFi configuration applied successfully!');

    } catch (error) {
        console.error('Error configuring WiFi:', error);
        showError(`Failed to configure WiFi: ${error.message}`);
    } finally {
        setConnectButtonLoading(false);
    }
}

// Show reboot error with button
function showRebootError(message) {
    errorEl.innerHTML = `
        <div class="flex flex-col gap-4">
            <div>${message}</div>
            <button id="reboot-btn" class="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-xl transition-all">
                <span class="flex items-center justify-center gap-2">
                    <i data-lucide="power" class="w-6 h-6"></i>
                    Reboot Now
                </span>
            </button>
        </div>
    `;
    errorEl.style.display = 'block';

    // Add reboot button listener
    const rebootBtn = document.getElementById('reboot-btn');
    if (rebootBtn) {
        rebootBtn.addEventListener('click', async () => {
            rebootBtn.disabled = true;
            rebootBtn.innerHTML = '<span class="flex items-center justify-center gap-2"><div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>Rebooting...</span>';

            try {
                await fetch('/api/wifi/reboot', { method: 'POST' });
                // Redirect after reboot
                setTimeout(() => {
                    window.location.href = '/';
                }, 10000);
            } catch (error) {
                alert('Please reboot manually: sudo reboot');
            }
        });
        lucide.createIcons();
    }
}

// Set connect button loading state
function setConnectButtonLoading(loading) {
    if (loading) {
        connectBtn.disabled = true;
        connectBtn.innerHTML = '<span class="flex items-center justify-center gap-2"><div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>Connecting...</span>';
    } else {
        connectBtn.disabled = false;
        connectBtn.innerHTML = '<span class="flex items-center justify-center gap-2"><i data-lucide="wifi" class="w-6 h-6"></i>Connect</span>';
        lucide.createIcons();
    }
}

// Restart server
async function restartServer() {
    // Show confirmation
    if (!confirm('Restart the server now to connect to the new WiFi network?')) {
        return;
    }

    restartBtn.disabled = true;
    restartBtn.innerHTML = '<span class="flex items-center justify-center gap-2"><div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>Restarting...</span>';

    try {
        // Call the restart API
        const response = await fetch('/api/wifi/restart', {
            method: 'POST'
        });

        if (response.ok) {
            // Server will restart, wait and then redirect
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            throw new Error('Failed to restart server');
        }
    } catch (error) {
        console.error('Error restarting server:', error);
        alert('Failed to restart server. Please restart manually: sudo systemctl restart music-server');
        restartBtn.disabled = false;
        restartBtn.innerHTML = '<span class="flex items-center justify-center gap-2"><i data-lucide="rotate-cw" class="w-6 h-6"></i>Restart Server</span>';
        lucide.createIcons();
    }
}

// Show error message
function showError(message) {
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    hideStatusMessage();
}

// Hide error message
function hideError() {
    errorEl.style.display = 'none';
}

// Show success message
function showSuccess(message) {
    successMessageEl.style.display = 'block';
    successMessageEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Hide success message
function hideSuccess() {
    successMessageEl.style.display = 'none';
}

// Show status message
function showStatusMessage(message) {
    statusMessageEl.textContent = message;
    statusMessageEl.style.display = 'block';
}

// Hide status message
function hideStatusMessage() {
    statusMessageEl.style.display = 'none';
}

// Hide loading
function hideLoading() {
    loadingEl.style.display = 'none';
}

// Show form
function showForm() {
    formEl.style.display = 'block';
}
