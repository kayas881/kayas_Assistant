"""
Colab Runtime Keep-Alive Script
================================

This script needs to run in your browser's Developer Console while Colab is open.

INSTRUCTIONS:
1. Open your Colab notebook in Chrome/Edge/Firefox
2. Press F12 to open Developer Tools
3. Go to the "Console" tab
4. Copy and paste the JavaScript code below into the console
5. Press Enter to start the keep-alive script
6. The script will run in the background and keep your runtime alive

The script will:
- Click the page every 60 seconds to simulate activity
- Log status messages so you know it's working
- Run indefinitely until you close the tab or stop it manually

To stop: Just close the browser tab or refresh the page
"""

JAVASCRIPT_CODE = """
// ==================================================================
// Google Colab Runtime Keep-Alive Script
// ==================================================================
// Prevents Colab from disconnecting due to inactivity
// Run this in the browser console (F12 -> Console tab)
// ==================================================================

function KeepAlive() {
    console.log('%c⚡ Colab Keep-Alive Started', 'color: #4CAF50; font-weight: bold; font-size: 14px;');
    console.log('%cThis will keep your runtime active by simulating activity every 60 seconds', 'color: #2196F3;');
    console.log('%cTo stop: Close this tab or refresh the page\\n', 'color: #FF9800;');
    
    let clickCount = 0;
    let startTime = Date.now();
    
    // Function to simulate a click
    function simulateClick() {
        const colab = document.querySelector("body");
        if (colab) {
            const clickEvent = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true
            });
            colab.dispatchEvent(clickEvent);
        }
    }
    
    // Function to check connection status
    function checkConnection() {
        const connectButton = document.querySelector('colab-connect-button');
        if (connectButton) {
            const status = connectButton.shadowRoot.querySelector('#connect-icon');
            if (status) {
                return status.classList.contains('connected');
            }
        }
        return false;
    }
    
    // Main keep-alive loop
    const intervalId = setInterval(() => {
        simulateClick();
        clickCount++;
        
        const elapsed = Math.floor((Date.now() - startTime) / 1000 / 60);
        const isConnected = checkConnection();
        const statusIcon = isConnected ? '✅' : '⚠️';
        
        console.log(
            `%c${statusIcon} Keep-Alive Tick #${clickCount} | ` +
            `Elapsed: ${elapsed}m | ` +
            `Status: ${isConnected ? 'Connected' : 'Checking...'}`,
            `color: ${isConnected ? '#4CAF50' : '#FF9800'}; font-weight: bold;`
        );
        
        // Try to reconnect if disconnected
        if (!isConnected) {
            console.log('%c⚠️ Attempting to reconnect...', 'color: #FF9800; font-weight: bold;');
            const connectBtn = document.querySelector('colab-connect-button');
            if (connectBtn) {
                connectBtn.click();
            }
        }
    }, 60000); // Every 60 seconds
    
    // Also prevent the tab from being suspended
    const preventSuspend = setInterval(() => {
        console.log('%c💓 Heartbeat', 'color: #E91E63;');
    }, 30000); // Every 30 seconds
    
    // Store interval IDs for potential cleanup
    window.colabKeepAliveInterval = intervalId;
    window.colabHeartbeatInterval = preventSuspend;
    
    console.log('%c🚀 Keep-Alive is now running!', 'color: #4CAF50; font-weight: bold; font-size: 16px;');
    console.log('%cScript will run until you close or refresh this tab', 'color: #2196F3;');
}

// Start the keep-alive immediately
KeepAlive();

// Optional: To manually stop, run this in console:
// clearInterval(window.colabKeepAliveInterval);
// clearInterval(window.colabHeartbeatInterval);
// console.log('Keep-Alive stopped');
"""

print(__doc__)
print("\n" + "="*70)
print("COPY THE JAVASCRIPT CODE BELOW:")
print("="*70 + "\n")
print(JAVASCRIPT_CODE)
print("\n" + "="*70)
print("ALTERNATIVE METHOD - Auto-Clicker Chrome Extension:")
print("="*70)
print("""
If you prefer not to use console scripts, you can also:

1. Install a browser extension like "Auto Refresh Plus" or "Keep Google Colab Alive"
   - Chrome: https://chrome.google.com/webstore (search "colab alive")
   
2. Or use this simple PowerShell script to keep your PC awake:
   - Run: powershell -Command "$sh = New-Object -ComObject WScript.Shell; while($true){$sh.SendKeys(' '); Start-Sleep -Seconds 60}"
   - This prevents your PC from sleeping while Colab trains

3. Windows Power Settings:
   - Go to Settings > System > Power & Sleep
   - Set "Screen" and "Sleep" to "Never" temporarily
   - Remember to change it back after training!
""")
