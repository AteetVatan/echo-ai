/**
 * EchoAI Voice Chat Client
 * 
 * Handles WebSocket communication, audio recording, and real-time voice chat
 * with the AI assistant.
 */

class EchoAIClient {
    constructor() {
        this.websocket = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.isConnected = false;
        this.connectionStartTime = null;
        this.totalMessages = 0;
        this.latencies = [];

        // DOM elements
        this.connectBtn = document.getElementById('connectBtn');
        this.recordBtn = document.getElementById('recordBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.statusDiv = document.getElementById('status');
        this.statusText = document.getElementById('statusText');
        this.conversationDiv = document.getElementById('conversation');
        this.statsDiv = document.getElementById('stats');

        // Bind event listeners
        this.connectBtn.addEventListener('click', () => this.toggleConnection());
        this.recordBtn.addEventListener('click', () => this.toggleRecording());
        this.clearBtn.addEventListener('click', () => this.clearConversation());

        // Initialize
        this.updateStatus('disconnected');
    }

    /**
     * Toggle WebSocket connection
     */
    async toggleConnection() {
        if (this.isConnected) {
            this.disconnect();
        } else {
            await this.connect();
        }
    }

    /**
     * Connect to WebSocket server
     */
    async connect() {
        try {
            this.updateStatus('connecting');
            this.connectBtn.disabled = true;
            this.connectBtn.textContent = 'Connecting...';

            // Get WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.hostname;
            const port = window.location.port || (protocol === 'wss:' ? '443' : '8000');
            const wsUrl = `${protocol}//${host}:${port}/ws/voice`;

            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                this.isConnected = true;
                this.connectionStartTime = Date.now();
                this.updateStatus('connected');
                this.connectBtn.textContent = 'Disconnect';
                this.connectBtn.disabled = false;
                this.recordBtn.disabled = false;
                this.clearBtn.disabled = false;
                this.showStats();
                console.log('Connected to EchoAI server');
            };

            this.websocket.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };

            this.websocket.onclose = () => {
                this.isConnected = false;
                this.updateStatus('disconnected');
                this.connectBtn.textContent = 'Connect';
                this.connectBtn.disabled = false;
                this.recordBtn.disabled = true;
                this.recordBtn.textContent = '🎤 Start Recording';
                this.recordBtn.classList.remove('recording');
                this.isRecording = false;
                console.log('Disconnected from EchoAI server');
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('disconnected');
                this.connectBtn.textContent = 'Connect';
                this.connectBtn.disabled = false;
            };

        } catch (error) {
            console.error('Failed to connect:', error);
            this.updateStatus('disconnected');
            this.connectBtn.textContent = 'Connect';
            this.connectBtn.disabled = false;
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.websocket) {
            this.websocket.close();
        }
        if (this.isRecording) {
            this.stopRecording();
        }
    }

    /**
     * Update connection status
     */
    updateStatus(status) {
        this.statusDiv.className = `status ${status}`;
        switch (status) {
            case 'connected':
                this.statusText.textContent = 'Connected to EchoAI';
                break;
            case 'disconnected':
                this.statusText.textContent = 'Disconnected';
                break;
            case 'connecting':
                this.statusText.textContent = 'Connecting...';
                break;
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(message) {
        console.log('Received message:', message);

        switch (message.type) {
            case 'connection':
                this.addMessage('ai', `Connected! Session ID: ${message.session_id}`);
                break;

            case 'processing':
                this.addMessage('processing', message.message);
                break;

            case 'response':
                this.handleResponse(message);
                break;

            case 'error':
                this.addMessage('error', `Error: ${message.message}`);
                break;

            case 'pong':
                // Keep-alive response
                break;

            default:
                console.log('Unknown message type:', message.type);
        }
    }

    /**
     * Handle AI response
     */
    handleResponse(message) {
        // Remove processing message
        const processingMsg = this.conversationDiv.querySelector('.message.processing');
        if (processingMsg) {
            processingMsg.remove();
        }

        // Add user transcription
        if (message.transcription) {
            this.addMessage('user', message.transcription, 'You said:');
        }

        // Add AI response
        this.addMessage('ai', message.response_text, 'AI Assistant:');

        // Play audio response
        if (message.audio) {
            this.playAudio(message.audio);
        }

        // Update stats
        this.totalMessages++;
        if (message.latency && message.latency.pipeline) {
            this.latencies.push(message.latency.pipeline);
            this.updateStats();
        }

        console.log('Response processed:', message);
    }

    /**
     * Add message to conversation
     */
    addMessage(type, text, prefix = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        if (prefix) {
            messageDiv.innerHTML = `<strong>${prefix}</strong> ${text}`;
        } else {
            messageDiv.textContent = text;
        }

        this.conversationDiv.appendChild(messageDiv);
        this.conversationDiv.scrollTop = this.conversationDiv.scrollHeight;
    }

    /**
     * Play audio response
     */
    playAudio(audioBase64) {
        try {
            const audioData = atob(audioBase64);
            const audioArray = new Uint8Array(audioData.length);
            for (let i = 0; i < audioData.length; i++) {
                audioArray[i] = audioData.charCodeAt(i);
            }

            const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' });
            const audioUrl = URL.createObjectURL(audioBlob);

            const audio = new Audio(audioUrl);
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
            };
            audio.play().catch(error => {
                console.error('Failed to play audio:', error);
            });

        } catch (error) {
            console.error('Failed to decode audio:', error);
        }
    }

    /**
     * Toggle audio recording
     */
    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    /**
     * Start audio recording
     */
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.sendAudio();
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.recordBtn.textContent = '⏹️ Stop Recording';
            this.recordBtn.classList.add('recording');

            console.log('Started recording');

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.addMessage('error', 'Failed to access microphone. Please check permissions.');
        }
    }

    /**
     * Stop audio recording
     */
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.isRecording = false;
            this.recordBtn.textContent = '🎤 Start Recording';
            this.recordBtn.classList.remove('recording');
            console.log('Stopped recording');
        }
    }

    /**
     * Send audio data to server
     */
    async sendAudio() {
        if (!this.isConnected || this.audioChunks.length === 0) {
            return;
        }

        try {
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64Audio = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

            const message = {
                type: 'audio',
                audio: base64Audio
            };

            this.websocket.send(JSON.stringify(message));
            console.log('Audio sent to server');

        } catch (error) {
            console.error('Failed to send audio:', error);
            this.addMessage('error', 'Failed to send audio to server.');
        }
    }

    /**
     * Clear conversation history
     */
    clearConversation() {
        this.conversationDiv.innerHTML = `
            <div class="message ai">
                <strong>AI Assistant:</strong> Conversation cleared. How can I help you?
            </div>
        `;
        this.totalMessages = 0;
        this.latencies = [];
        this.updateStats();
    }

    /**
     * Show performance stats
     */
    showStats() {
        this.statsDiv.classList.remove('hidden');
        this.updateStats();
    }

    /**
     * Update performance stats
     */
    updateStats() {
        const avgLatency = this.latencies.length > 0
            ? (this.latencies.reduce((a, b) => a + b, 0) / this.latencies.length).toFixed(2)
            : '-';

        const connectionTime = this.connectionStartTime
            ? Math.floor((Date.now() - this.connectionStartTime) / 1000)
            : '-';

        document.getElementById('avgLatency').textContent = `${avgLatency}s`;
        document.getElementById('totalMessages').textContent = this.totalMessages;
        document.getElementById('connectionTime').textContent = `${connectionTime}s`;
    }

    /**
     * Send keep-alive ping
     */
    startKeepAlive() {
        if (this.isConnected) {
            this.websocket.send(JSON.stringify({ type: 'ping' }));
        }
    }
}

// Initialize client when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.echoAIClient = new EchoAIClient();

    // Start keep-alive ping every 30 seconds
    setInterval(() => {
        if (window.echoAIClient) {
            window.echoAIClient.startKeepAlive();
        }
    }, 30000);
}); 