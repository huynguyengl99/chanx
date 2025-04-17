// Module for handling UI interactions

// Initialize the UI module
export function initUI(elements) {
    // Initialize tab functionality
    initTabs(elements.tabs, elements.tabContents);

    // Initialize connection tabs
    initConnectionTabs(elements.connectionTabButtons, elements.connectionTabContents);
}

// Handle tab switching functionality
function initTabs(tabs, tabContents) {
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to selected tab and content
            tab.classList.add('active');
            const tabId = 'tab-' + tab.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// Handle connection tab switching functionality
function initConnectionTabs(connectionTabButtons, connectionTabContents) {
    connectionTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            connectionTabButtons.forEach(btn => btn.classList.remove('active'));
            connectionTabContents.forEach(content => content.classList.remove('active'));

            // Add active class to selected tab and content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
}
