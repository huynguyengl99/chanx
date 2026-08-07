// FastAPI WebSocket Chat Demo - Main JavaScript
// All functionality combined in a single file for simplicity

// =============================================================================
// WebSocket Connections
// =============================================================================

// WebSocket connections for different layer types
var wsChat = new WebSocket("ws://localhost:8080/ws/chat");
var wsNotifications = new WebSocket("ws://localhost:8080/ws/notifications");
var wsReliable = new WebSocket("ws://localhost:8080/ws/reliable");
var wsAnalytics = new WebSocket("ws://localhost:8080/ws/analytics");
var wsSystem = new WebSocket("ws://localhost:8080/ws/system");
var wsBackgroundJob = new WebSocket("ws://localhost:8080/ws/background_jobs");
var wsMux = new WebSocket("ws://localhost:8080/ws/mux"); // Several consumers, one socket
var wsRoom = null; // Dynamic room connection

// Action each multiplexed sub-consumer accepts, keyed by its envelope name
var MUX_ACTIONS = {
    system: "user_message",
    chat: "chat",
    notifications: "notification"
};

// Reuse the per-layer message classes so the routing is visible at a glance
var MUX_CLASSES = {
    system: "system",
    chat: "chat",
    notifications: "notification"
};

// =============================================================================
// WebSocket Event Handlers
// =============================================================================

// Handle chat messages (JSON format)
wsChat.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        if (data.action === "chat_notification") {
            addMessage("Chat: " + data.payload.message, "chat");
        } else if (data.action === "error") {
            addMessage("Chat Error: " + data.payload.detail, "chat");
        } else {
            addMessage("Chat: " + event.data, "chat");
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addMessage("Chat: " + event.data, "chat");
    }
};

// Handle notifications (JSON format)
wsNotifications.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        if (data.action === "notification_broadcast") {
            addMessage("Notification: " + data.payload.message, "notification");
        } else if (data.action === "error") {
            addMessage("Notification Error: " + data.payload.detail, "notification");
        } else {
            addMessage("Notification: " + event.data, "notification");
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addMessage("Notification: " + event.data, "notification");
    }
};

// Handle reliable messages (JSON format)
wsReliable.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        if (data.action === "reliable_chat_notification") {
            addMessage("Reliable: " + data.payload.message, "reliable");
        } else if (data.action === "error") {
            addMessage("Reliable Error: " + data.payload.detail, "reliable");
        } else {
            addMessage("Reliable: " + event.data, "reliable");
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addMessage("Reliable: " + event.data, "reliable");
    }
};

// Handle analytics messages (JSON format)
wsAnalytics.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        if (data.action === "analytics_notification") {
            addMessage("Analytics: " + data.payload.event, "analytics");
        } else if (data.action === "error") {
            addMessage("Analytics Error: " + data.payload.detail, "analytics");
        } else {
            addMessage("Analytics: " + event.data, "analytics");
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addMessage("Analytics: " + event.data, "analytics");
    }
};

// Handle system messages (JSON format)
wsSystem.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        if (data.action === "system_echo") {
            addSystemMessage(data.payload.message);
        } else if (data.action === "error") {
            addSystemMessage("❌ System Error: " + data.payload.detail);
        } else {
            addSystemMessage(event.data);
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addSystemMessage(event.data);
    }
};

// Handle background job messages (JSON format)
wsBackgroundJob.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        if (data.action === "job_status") {
            addJobMessage(data.payload.message);
        } else if (data.action === "error") {
            addJobMessage("❌ Job Error: " + data.payload.detail);
        } else {
            addJobMessage(event.data);
        }
    } catch (e) {
        // Fallback for non-JSON messages
        addJobMessage(event.data);
    }
};

// Handle multiplexed messages. Frames produced by a sub-consumer arrive wrapped
// in an envelope naming it; the demultiplexer's own replies arrive bare.
wsMux.onmessage = function(event) {
    try {
        var data = JSON.parse(event.data);
        var consumer = data.consumer;
        var inner = consumer ? data.message : data;
        addMuxMessage(
            "[" + (consumer || "mux") + "] " + describeMuxMessage(inner),
            consumer ? MUX_CLASSES[consumer] : "system"
        );
    } catch (e) {
        // Fallback for non-JSON messages
        addMuxMessage(event.data, "system");
    }
};

// =============================================================================
// Utility Functions - Message Display
// =============================================================================

function addMessage(text, type) {
    var messages = document.getElementById('messages');
    var message = document.createElement('li');
    message.className = type;
    var content = document.createTextNode(text);
    message.appendChild(content);
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

function addSystemMessage(text, isUserMessage = false) {
    var messages = document.getElementById('systemMessages');
    var message = document.createElement('li');
    message.className = isUserMessage ? 'user-message' : 'system';
    var content = document.createTextNode(text);
    message.appendChild(content);
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

function addRoomMessage(text) {
    var messages = document.getElementById('roomMessages');
    var message = document.createElement('li');
    message.className = 'room';
    var content = document.createTextNode(text);
    message.appendChild(content);
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

function addJobMessage(text) {
    var messages = document.getElementById('jobMessages');
    var message = document.createElement('li');
    message.className = 'job';
    var content = document.createTextNode(text);
    message.appendChild(content);
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

function addMuxMessage(text, cssClass) {
    var messages = document.getElementById('muxMessages');
    var message = document.createElement('li');
    message.className = cssClass || 'user-message';
    var content = document.createTextNode(text);
    message.appendChild(content);
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

// Render the inner (un-enveloped) message of a multiplexed frame
function describeMuxMessage(message) {
    var payload = message.payload || {};
    if (message.action === "error") {
        return "❌ " + JSON.stringify(payload.detail || payload);
    }
    if (payload.message !== undefined) {
        return message.action + ": " + payload.message;
    }
    return message.action;
}

// =============================================================================
// System Chat Functions
// =============================================================================

function sendSystemMessage(event) {
    var input = document.getElementById("systemMessageText");
    var message = input.value;

    if (message.trim() === '') return;

    // Show user message first
    addSystemMessage("👤 User: " + message, true);

    // Send to system WebSocket connection in JSON format
    if (wsSystem.readyState === WebSocket.OPEN) {
        var messageData = {
            action: "user_message",
            payload: {
                message: message
            }
        };
        wsSystem.send(JSON.stringify(messageData));
    }

    input.value = '';
    event.preventDefault();
}

// =============================================================================
// Room Chat Functions
// =============================================================================

function connectToRoom() {
    var roomName = document.getElementById("roomName").value.trim();
    if (roomName === '') {
        alert('Please enter a room name');
        return;
    }

    // Close existing room connection if any
    if (wsRoom) {
        wsRoom.close();
    }

    // Create new room WebSocket connection
    wsRoom = new WebSocket("ws://localhost:8080/ws/room/" + roomName);

    wsRoom.onopen = function() {
        document.getElementById("currentRoom").textContent = "Connected to room: " + roomName;
        document.getElementById("connectBtn").style.display = "none";
        document.getElementById("disconnectBtn").style.display = "inline";
        document.getElementById("roomMessageText").disabled = false;
        document.querySelector("#roomMessageText").nextElementSibling.disabled = false;
    };

    wsRoom.onmessage = function(event) {
        try {
            var data = JSON.parse(event.data);
            if (data.action === "room_notification") {
                addRoomMessage(data.payload.message);
            } else if (data.action === "error") {
                addRoomMessage("❌ Room Error: " + data.payload.detail);
            } else {
                addRoomMessage(event.data);
            }
        } catch (e) {
            // Fallback for non-JSON messages
            addRoomMessage(event.data);
        }
    };

    wsRoom.onclose = function() {
        document.getElementById("currentRoom").textContent = "";
        document.getElementById("connectBtn").style.display = "inline";
        document.getElementById("disconnectBtn").style.display = "none";
        document.getElementById("roomMessageText").disabled = true;
        document.querySelector("#roomMessageText").nextElementSibling.disabled = true;
    };
}

function disconnectFromRoom() {
    if (wsRoom) {
        wsRoom.close();
        wsRoom = null;
    }
}

function sendRoomMessage(event) {
    var input = document.getElementById("roomMessageText");
    var message = input.value;

    if (wsRoom && wsRoom.readyState === WebSocket.OPEN && message.trim() !== '') {
        var messageData = {
            action: "room_chat",
            payload: {
                message: message
            }
        };
        wsRoom.send(JSON.stringify(messageData));
    }

    input.value = '';
    event.preventDefault();
}

// =============================================================================
// Background Jobs Functions
// =============================================================================

function sendJobMessage(event) {
    var input = document.getElementById("jobMessageText");
    var message = input.value;
    var jobType = document.getElementById("jobType").value;

    if (message.trim() === '') return;

    if (wsBackgroundJob.readyState === WebSocket.OPEN) {
        // Send structured message for different job types
        var jobData = {
            action: "job",
            payload: {
                type: jobType,
                content: message
            }
        };
        wsBackgroundJob.send(JSON.stringify(jobData));
    }

    input.value = '';
    event.preventDefault();
}

// =============================================================================
// Showcase Functions (All Layers)
// =============================================================================

function sendMessage(event) {
    var input = document.getElementById("messageText");
    var message = input.value;

    // Send to all WebSocket connections in JSON format
    if (wsChat.readyState === WebSocket.OPEN) {
        var chatData = {
            action: "chat",
            payload: {
                message: message
            }
        };
        wsChat.send(JSON.stringify(chatData));
    }
    if (wsReliable.readyState === WebSocket.OPEN) {
        var reliableData = {
            action: "reliable_chat",
            payload: {
                message: message
            }
        };
        wsReliable.send(JSON.stringify(reliableData));
    }

    input.value = '';
    event.preventDefault();
}

// =============================================================================
// Multiplex Functions
// =============================================================================

// Send an enveloped frame to the sub-consumer picked in the dropdown. The chat
// and notifications sub-consumers share their groups with the standalone
// /ws/chat and /ws/notifications routes, so replies also land in those boxes.
function sendMuxMessage(event) {
    event.preventDefault();

    var input = document.getElementById("muxMessageText");
    var message = input.value;

    if (message.trim() === '') return;

    if (wsMux.readyState === WebSocket.OPEN) {
        var target = document.getElementById("muxTarget").value;
        var frame = {
            consumer: target,
            message: {
                action: MUX_ACTIONS[target],
                payload: {
                    message: message
                }
            }
        };
        wsMux.send(JSON.stringify(frame));
        addMuxMessage("👤 " + JSON.stringify(frame), 'user-message');
    }

    input.value = '';
}

// Send a frame with no envelope: it falls through to the demultiplexer's own
// @ws_handler instead of being routed to a sub-consumer.
function sendMuxPing() {
    if (wsMux.readyState !== WebSocket.OPEN) return;

    var frame = {
        action: "ping",
        payload: null
    };
    wsMux.send(JSON.stringify(frame));
    addMuxMessage("👤 " + JSON.stringify(frame), 'user-message');
}

// =============================================================================
// Analytics Functions
// =============================================================================

function sendAnalyticsEvent() {
    if (wsAnalytics.readyState === WebSocket.OPEN) {
        var analyticsData = {
            action: "analytics",
            payload: {
                event: "page_view",
                data: {
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent,
                    url: window.location.href
                }
            }
        };
        wsAnalytics.send(JSON.stringify(analyticsData));
    }
}

// =============================================================================
// Initialization
// =============================================================================

// Send analytics event on page load
window.onload = function() {
    setTimeout(function() {
        sendAnalyticsEvent();
    }, 1000); // Wait 1 second for connection
};
