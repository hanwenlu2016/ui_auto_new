
(function() {
    console.log("[InitAgent] Starting initialization sequence...");

    // Wait for PageAgent to be available
    const checkInterval = setInterval(() => {
        if (window.PageAgent) {
            clearInterval(checkInterval);
            console.log("[InitAgent] PageAgent class found. Initializing instance...");

            // Clean up any existing instance just in case
            if (window.pageAgent) {
                try {
                    window.pageAgent.dispose();
                } catch (e) {
                    console.warn("[InitAgent] Failed to dispose existing agent:", e);
                }
            }

            try {
                // Initialize PageAgent with internal proxy configuration
                // We use a dummy apiKey because the backend handles authentication
                // We use a specific baseURL that Playwright will intercept
                const config = {
                    model: 'gpt-4o', // Backend will decide actual model, but this keeps client happy
                    baseURL: 'https://internal-llm-proxy/v1',
                    apiKey: 'internal-proxy-key',
                    language: 'zh-CN', // Default to Chinese as per project context
                    enableMask: true
                };

                window.pageAgent = new window.PageAgent(config);
                
                // Show the panel
                if (window.pageAgent.panel) {
                    window.pageAgent.panel.show();
                }

                console.log("[InitAgent] PageAgent initialized successfully with config:", config);
                
                // Optional: Add visual indicator that agent is ready
                const badge = document.createElement('div');
                badge.style.position = 'fixed';
                badge.style.bottom = '10px';
                badge.style.right = '10px';
                badge.style.padding = '5px 10px';
                badge.style.background = '#4CAF50';
                badge.style.color = 'white';
                badge.style.borderRadius = '5px';
                badge.style.zIndex = '999999';
                badge.style.fontSize = '12px';
                badge.style.pointerEvents = 'none';
                badge.innerText = 'PageAgent Active';
                document.body.appendChild(badge);
                setTimeout(() => badge.remove(), 3000);

            } catch (err) {
                console.error("[InitAgent] Failed to initialize PageAgent:", err);
            }
        }
    }, 100);
    
    // Safety timeout to stop checking
    setTimeout(() => clearInterval(checkInterval), 10000);
})();
