/**
 * EchoAI Voice Chat Client
 * 
 * Handles WebSocket communication, audio recording, and real-time voice chat
 * with the AI assistant. Supports both traditional and streaming audio modes.
 */

class EchoAIClient {
    constructor() {
        this.websocket = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.isConnected = false;
        this.isStreaming = false;
        this.connectionStartTime = null;
        this.totalMessages = 0;
        this.latencies = [];
        this.chunkInterval = null;
        this.streamingChunks = [];

        // Audio configuration
        this.chunkDuration = 100; // ms
        this.chunkSize = 1024; // bytes

        // DOM elements
        this.connectBtn = document.getElementById('connectBtn');
        this.recordBtn = document.getElementById('recordBtn');
        this.streamBtn = document.getElementById('streamBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.statusDiv = document.getElementById('status');
        this.statusText = document.getElementById('statusText');
        this.conversationDiv = document.getElementById('conversation');
        this.statsDiv = document.getElementById('stats');

        // Bind event listeners
        this.connectBtn.addEventListener('click', () => this.toggleConnection());
        this.recordBtn.addEventListener('click', () => this.toggleRecording());
        this.streamBtn.addEventListener('click', () => this.toggleStreaming());
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
                this.streamBtn.disabled = false;
                this.clearBtn.disabled = false;
                this.showStats();
                console.log('Connected to EchoAI server');
            };

            this.websocket.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };

            this.websocket.onclose = () => {
                this.isConnected = false;
                this.isStreaming = false;
                this.updateStatus('disconnected');
                this.connectBtn.textContent = 'Connect';
                this.connectBtn.disabled = false;
                this.recordBtn.disabled = true;
                this.streamBtn.disabled = true;
                this.recordBtn.textContent = '🎤 Start Recording';
                this.streamBtn.textContent = '🌊 Start Streaming';
                this.recordBtn.classList.remove('recording');
                this.streamBtn.classList.remove('streaming');
                this.isRecording = false;
                this.stopChunkInterval();
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
        this.isConnected = false;
        this.isStreaming = false;
        this.stopChunkInterval();
    }

    /**
     * Update connection status
     */
    updateStatus(status) {
        this.statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        this.statusDiv.className = `status ${status}`;
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(message) {
        console.log('Received message:', message.type);

        switch (message.type) {
            case 'connection':
                this.addMessage('system', message.message);
                break;
            case 'processing':
                this.addMessage('system', message.message);
                break;
            case 'response':
            case 'streaming_response':
                this.handleResponse(message);
                break;
            case 'text_response':
                this.handleTextResponse(message);
                break;
            case 'chunk_received':
                console.log(`Chunk received: ${message.chunk_size} bytes, buffer: ${message.buffer_size} chunks`);
                break;
            case 'streaming_started':
                this.addMessage('system', message.message);
                break;
            case 'error':
                this.addMessage('error', message.message);
                break;
            case 'pong':
                // Keep-alive response
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    /**
     * Handle voice response
     */
    handleResponse(message) {
        const { transcription, response_text, audio, latency } = message;

        // Add user transcription
        if (transcription) {
            this.addMessage('user', transcription);
        }

        // Add AI response
        if (response_text) {
            this.addMessage('ai', response_text);
        }

        // Play audio response
        if (audio) {
            this.playAudio(audio);
        }

        // Update stats
        if (latency) {
            this.updateLatencyStats(latency);
        }

        this.updateStats();
    }

    /**
     * Handle text response
     */
    handleTextResponse(message) {
        const { response_text, audio, latency } = message;

        // Add AI response
        if (response_text) {
            this.addMessage('ai', response_text);
        }

        // Play audio response
        if (audio) {
            this.playAudio(audio);
        }

        // Update stats
        if (latency) {
            this.updateLatencyStats(latency);
        }

        this.updateStats();
    }

    /**
     * Add message to conversation
     */
    addMessage(type, text, prefix = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const timestamp = new Date().toLocaleTimeString();
        const formattedText = prefix ? `${prefix} ${text}` : text;

        messageDiv.innerHTML = `
            <strong>${type === 'user' ? 'You' : type === 'ai' ? 'AI Assistant' : 'System'}:</strong> 
            ${formattedText}
            <small>${timestamp}</small>
        `;

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

            const audioBlob = new Blob([audioArray], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);

            const audio = new Audio(audioUrl);
            audio.play().catch(error => {
                console.error('Failed to play audio:', error);
            });

            // Clean up URL after playing
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
            };

        } catch (error) {
            console.error('Failed to decode audio:', error);
        }
    }

    /**
     * Toggle traditional recording
     */
    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    /**
     * Start traditional audio recording
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

            console.log('Started traditional recording');

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.addMessage('error', 'Failed to access microphone. Please check permissions.');
        }
    }

    /**
     * Stop traditional audio recording
     */
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.isRecording = false;
            this.recordBtn.textContent = '🎤 Start Recording';
            this.recordBtn.classList.remove('recording');
            console.log('Stopped traditional recording');
        }
    }

    /**
     * Toggle streaming audio
     */
    async toggleStreaming() {
        if (this.isStreaming) {
            this.stopStreaming();
        } else {
            await this.startStreaming();
        }
    }

    /**
     * Start streaming audio
     */
    async startStreaming() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Create audio context for streaming - real-time processing.
            const audioContext = new AudioContext();
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);

            this.streamingChunks = [];
            this.isStreaming = true;
            this.streamBtn.textContent = '⏹️ Stop Streaming';
            this.streamBtn.classList.add('streaming');

            // Send start streaming message
            this.websocket.send(JSON.stringify({
                type: 'start_streaming'
            }));

            // Process audio data - in real-time
            processor.onaudioprocess = (event) => {
                if (!this.isStreaming) return;

                const inputData = event.inputBuffer.getChannelData(0);
                const audioChunk = this.convertFloat32ToInt16(inputData);

                // Send audio chunk
                this.sendAudioChunk(audioChunk);
            };

            source.connect(processor);
            processor.connect(audioContext.destination);

            // Store references for cleanup
            this.audioContext = audioContext;
            this.audioProcessor = processor;
            this.audioSource = source;
            this.audioStream = stream;

            console.log('Started streaming audio');

        } catch (error) {
            console.error('Failed to start streaming:', error);
            this.addMessage('error', 'Failed to start streaming. Please check microphone permissions.');
        }
    }

    /**
     * Stop streaming audio
     */
    stopStreaming() {
        if (this.isStreaming) {
            this.isStreaming = false;
            this.streamBtn.textContent = '🌊 Start Streaming';
            this.streamBtn.classList.remove('streaming');

            // Clean up audio resources
            if (this.audioProcessor) {
                this.audioProcessor.disconnect();
            }
            if (this.audioSource) {
                this.audioSource.disconnect();
            }
            if (this.audioContext) {
                this.audioContext.close();
            }
            if (this.audioStream) {
                this.audioStream.getTracks().forEach(track => track.stop());
            }

            // Send stop streaming message
            this.websocket.send(JSON.stringify({
                type: 'stop_streaming'
            }));

            console.log('Stopped streaming audio');
        }
    }

    /**
     * Convert Float32 audio data to Int16
     */
    convertFloat32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array.buffer;
    }

    /**
     * Send audio chunk to server
     */
    sendAudioChunk(audioChunk) {
        if (!this.isConnected || !this.isStreaming) {
            return;
        }

        try {
            const base64Chunk = btoa(String.fromCharCode(...new Uint8Array(audioChunk)));

            const message = {
                type: 'audio_chunk',
                audio_chunk: base64Chunk
            };

            this.websocket.send(JSON.stringify(message));

        } catch (error) {
            console.error('Failed to send audio chunk:', error);
        }
    }

    /**
     * Send complete audio to server (legacy)
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
     * Stop chunk interval
     */
    stopChunkInterval() {
        if (this.chunkInterval) {
            clearInterval(this.chunkInterval);
            this.chunkInterval = null;
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

        // Send clear conversation request to server
        if (this.isConnected) {
            fetch('/clear-conversation', { method: 'POST' })
                .then(response => response.json())
                .then(data => console.log('Conversation cleared:', data))
                .catch(error => console.error('Failed to clear conversation:', error));
        }
    }

    /**
     * Show performance statistics
     */
    showStats() {
        this.statsDiv.style.display = 'block';
        this.updateStats();
    }

    /**
     * Update latency statistics
     */
    updateLatencyStats(latency) {
        if (latency.pipeline) {
            this.latencies.push(latency.pipeline);
            if (this.latencies.length > 10) {
                this.latencies.shift();
            }
        }
    }

    /**
     * Update performance statistics
     */
    updateStats() {
        if (!this.isConnected) return;

        const avgLatency = this.latencies.length > 0
            ? (this.latencies.reduce((a, b) => a + b, 0) / this.latencies.length).toFixed(2)
            : 'N/A';

        const uptime = this.connectionStartTime
            ? Math.floor((Date.now() - this.connectionStartTime) / 1000)
            : 0;

        this.statsDiv.innerHTML = `
            <h3>Performance Stats</h3>
            <p><strong>Connection:</strong> ${uptime}s</p>
            <p><strong>Messages:</strong> ${this.totalMessages}</p>
            <p><strong>Avg Latency:</strong> ${avgLatency}ms</p>
            <p><strong>Mode:</strong> ${this.isStreaming ? 'Streaming' : 'Traditional'}</p>
        `;
    }

    /**
     * Start keep-alive ping
     */
    startKeepAlive() {
        if (this.keepAliveInterval) {
            clearInterval(this.keepAliveInterval);
        }

        this.keepAliveInterval = setInterval(() => {
            if (this.isConnected && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Send ping every 30 seconds
    }
}

// Initialize client when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.echoAIClient = new EchoAIClient();
}); 