// Main module that initializes all components of the WebSocket Playground

import { initEndpoints, loadEndpoints } from './endpoints.js';
import { initConnection } from './connection.js';
import { initMessaging, addStatusMessage } from './messages.js';
import { initUI } from './ui.js';
import { initParameters } from './parameters.js';

// Shared state across modules
export const state = {
    socket: null,
    currentEndpoint: null,
    originalPathPattern: null,
    pathParameters: [], // Added to store path parameter definitions
    selectedFile: null,
    availableEndpoints: []
};

// DOM Elements - used across modules
export const elements = {};

// Main initialization function
export function initMain(websocketInfoUrl) {
    // Cache DOM elements
    cacheElements();

    // Initialize all modules
    initUI(elements);
    initEndpoints(websocketInfoUrl, elements, state);
    initConnection(elements, state);
    initMessaging(elements, state);
    initParameters(elements, state);

    // Initial load of endpoints
    loadEndpoints(elements, state);

    // Initial status message
    addStatusMessage('WebSocket Playground Ready');
}

// Cache all DOM elements for use across modules
function cacheElements() {
    // Connection elements
    elements.wsEndpointSelect = document.getElementById('wsEndpoint');
    elements.endpointDescription = document.getElementById('endpointDescription');
    elements.endpointsLoading = document.getElementById('endpointsLoading');
    elements.refreshEndpointsBtn = document.getElementById('refreshEndpoints');
    elements.wsUrlInput = document.getElementById('wsUrl');
    elements.realUrlDisplay = document.getElementById('realUrlDisplay');
    elements.connectBtn = document.getElementById('connectBtn');
    elements.disconnectBtn = document.getElementById('disconnectBtn');
    elements.connectionStatus = document.getElementById('connectionStatus');

    // Message elements
    elements.messageInput = document.getElementById('messageInput');
    elements.jsonInput = document.getElementById('jsonInput');
    elements.fileInput = document.getElementById('fileInput');
    elements.fileInfo = document.getElementById('fileInfo');
    elements.jsonError = document.getElementById('jsonError');
    elements.sendRawBtn = document.getElementById('sendRawBtn');
    elements.formatJsonBtn = document.getElementById('formatJsonBtn');
    elements.sendJsonBtn = document.getElementById('sendJsonBtn');
    elements.sendFileBtn = document.getElementById('sendFileBtn');
    elements.messageLog = document.getElementById('messageLog');

    // Tab elements
    elements.tabs = document.querySelectorAll('.tab');
    elements.tabContents = document.querySelectorAll('.tab-content');
    elements.connectionTabButtons = document.querySelectorAll('.tab-button');
    elements.connectionTabContents = document.querySelectorAll('.connection-tab-content');

    // Parameter elements
    elements.pathParamsList = document.getElementById('pathParamsList');
    elements.pathParamsTabButton = document.getElementById('pathParamsTabButton');
    elements.queryParamsList = document.getElementById('queryParamsList');
    elements.addQueryParamBtn = document.getElementById('addQueryParamBtn');
    elements.addPathParamBtn = document.getElementById('addPathParamBtn');

    // Message Examples elements
    elements.messageExampleSelect = document.getElementById('messageExampleSelect');
    elements.messageExampleDescription = document.getElementById('messageExampleDescription');
    elements.messageExamplesLoading = document.getElementById('messageExamplesLoading');
}
