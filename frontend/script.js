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
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.reconnectDelay = 1000;

        // Audio configuration - optimized for backend compatibility
        this.chunkDuration = 100; // ms
        this.chunkSize = 4096; // bytes - increased for better streaming
        this.sampleRate = 16000; // Hz - match backend configuration
        this.channels = 1; // Mono

        // DOM elements
        this.connectBtn = document.getElementById('connectBtn');
        this.recordBtn = document.getElementById('recordBtn');
        this.streamBtn = document.getElementById('streamBtn');
        this.pauseResumeBtn = document.getElementById('pauseResumeBtn'); // Add this
        this.clearBtn = document.getElementById('clearBtn');
        this.statusDiv = document.getElementById('status');
        this.statusText = document.getElementById('statusText');
        this.conversationDiv = document.getElementById('conversation');
        this.statsDiv = document.getElementById('stats');

        // Bind event listeners
        this.connectBtn.addEventListener('click', () => this.toggleConnection());
        this.recordBtn.addEventListener('click', () => this.toggleRecording());
        // Hide streaming functionality for now
        // this.streamBtn.addEventListener('click', () => this.toggleStreaming());
        // this.pauseResumeBtn.addEventListener('click', () => this.toggleStreamingPause());
        this.clearBtn.addEventListener('click', () => this.clearConversation());

        // Initialize
        this.updateStatus('disconnected');
        this.detectBackendUrl();

        // Add new properties for real-time streaming
        this.streamingBuffer = [];
        this.processingThreshold = 2000; // 2 seconds of audio
        this.lastProcessingTime = 0;
        this.processingInterval = null;
        this.isStreamingPaused = false; // Track if streaming is paused
        this.autoPauseEnabled = true; // Enable auto-pause feature
    }

    /**
     * Detect backend URL based on current environment
     */
    detectBackendUrl() {
        // For development: if running on localhost, assume backend is on port 8000
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            this.backendUrl = `ws://${window.location.hostname}:8000`;
        } else {
            // For production: use same host with wss protocol
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.backendUrl = `${protocol}//${window.location.host}`;
        }
        console.log('Detected backend URL:', this.backendUrl);
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

            // Use detected backend URL
            const wsUrl = `${this.backendUrl}/ws/voice`;
            console.log('Connecting to:', wsUrl);

            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                this.isConnected = true;
                this.connectionStartTime = Date.now();
                this.reconnectAttempts = 0;
                this.updateStatus('connected');
                this.connectBtn.textContent = 'Disconnect';
                this.connectBtn.disabled = false;
                this.recordBtn.disabled = false;
                // Hide streaming button for now
                // this.streamBtn.disabled = false;
                this.clearBtn.disabled = false;
                this.showStats();
                this.startKeepAlive();
                console.log('Connected to EchoAI server');
            };

            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Failed to parse message:', error);
                    this.addMessage('error', 'Received invalid message from server');
                }
            };

            this.websocket.onclose = (event) => {
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
                this.stopKeepAlive();

                // Attempt reconnection if not manually disconnected
                if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }

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
            this.addMessage('error', `Connection failed: ${error.message}`);
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        this.addMessage('system', `Reconnecting in ${delay / 1000}s... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.websocket) {
            this.websocket.close(1000, 'User disconnected');
        }
        this.isConnected = false;
        this.isStreaming = false;
        this.stopChunkInterval();
        this.stopKeepAlive();
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
     * Handle voice response with auto-pause
     */
    handleResponse(message) {
        console.log('Response received, auto-pause enabled:', this.autoPauseEnabled);
        console.log('Streaming state:', this.isStreaming);

        // Pause streaming when AI starts responding
        if (this.autoPauseEnabled && this.isStreaming) {
            console.log('Auto-pausing streaming...');
            this.pauseStreaming();
        } else {
            console.log('Not auto-pausing - conditions not met');
        }

        const { transcription, response_text, audio, latency } = message;

        // Add user transcription
        if (transcription) {
            this.addMessage('user', transcription);
            this.totalMessages++;
        }

        // Add AI response
        if (response_text) {
            this.addMessage('ai', response_text);
            this.totalMessages++;
        }

        // Play audio response and resume streaming when done
        if (audio) {
            this.playAudioWithResume(audio);
        } else {
            // If no audio, resume immediately
            this.resumeStreaming();
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
            this.totalMessages++;
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

            const audioBlob = new Blob([audioArray], { type: 'audio/webm;codecs=opus' });
            const audioUrl = URL.createObjectURL(audioBlob);

            const audio = new Audio(audioUrl);
            audio.play().catch(error => {
                console.error('Failed to play audio:', error);
                this.addMessage('error', 'Failed to play audio response');
            });

            // Clean up URL after playing
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
            };

        } catch (error) {
            console.error('Failed to decode audio:', error);
            this.addMessage('error', 'Failed to decode audio response');
        }
    }

    /**
     * Play audio and resume streaming when finished
     */
    playAudioWithResume(audioBase64) {
        try {
            // Decode base64 audio
            const binaryString = atob(audioBase64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // Create audio blob and play
            const audioBlob = new Blob([bytes], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            // Resume streaming when audio finishes playing
            audio.onended = () => {
                if (this.autoPauseEnabled && this.isStreaming) {
                    this.resumeStreaming();
                }
                URL.revokeObjectURL(audioUrl); // Clean up
            };

            // Resume streaming if audio is interrupted
            audio.onpause = () => {
                if (this.autoPauseEnabled && this.isStreaming) {
                    this.resumeStreaming();
                }
            };

            // Resume streaming if there's an error
            audio.onerror = () => {
                if (this.autoPauseEnabled && this.isStreaming) {
                    this.resumeStreaming();
                }
            };

            // Play the audio
            audio.play().catch(error => {
                console.error('Failed to play audio:', error);
                // Resume streaming if audio fails to play
                if (this.autoPauseEnabled && this.isStreaming) {
                    this.resumeStreaming();
                }
            });

        } catch (error) {
            console.error('Failed to decode audio:', error);
            this.addMessage('error', 'Failed to decode audio response');
            // Resume streaming if audio fails
            if (this.autoPauseEnabled && this.isStreaming) {
                this.resumeStreaming();
            }
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
                    sampleRate: this.sampleRate,
                    channelCount: this.channels,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Use WebM with Opus codec for better browser compatibility
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
     * Start streaming audio with real-time processing and auto-pause
     */
    async startStreaming() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: this.channels,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Create audio context for streaming - real-time processing
            const audioContext = new AudioContext({ sampleRate: this.sampleRate });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(this.chunkSize, 1, 1);

            this.streamingBuffer = [];
            this.isStreaming = true;
            this.isStreamingPaused = false; // Reset pause state
            this.streamBtn.textContent = '⏹️ Stop Streaming';
            this.streamBtn.classList.add('streaming');

            // Show pause/resume button
            this.pauseResumeBtn.style.display = 'inline-block';
            this.pauseResumeBtn.textContent = '⏸️ Pause';
            this.pauseResumeBtn.classList.remove('paused');

            // Send start streaming message
            this.websocket.send(JSON.stringify({
                type: 'start_streaming'
            }));

            // Process audio data - in real-time
            processor.onaudioprocess = (event) => {
                if (!this.isStreaming || this.isStreamingPaused) return; // Check pause state

                const inputData = event.inputBuffer.getChannelData(0);
                const audioChunk = this.convertFloat32ToInt16(inputData);

                // Add to streaming buffer
                this.streamingBuffer.push(audioChunk);

                // Check if we should process the buffer
                this.checkAndProcessStreamingBuffer();
            };

            source.connect(processor);
            processor.connect(audioContext.destination);

            // Store references for cleanup
            this.audioContext = audioContext;
            this.audioProcessor = processor;
            this.audioSource = source;
            this.audioStream = stream;

            // Start periodic processing check
            this.startPeriodicProcessing();

            console.log('Started real-time streaming audio with auto-pause');

        } catch (error) {
            console.error('Failed to start streaming:', error);
            this.addMessage('error', 'Failed to start streaming. Please check microphone permissions.');
        }
    }

    /**
     * Pause streaming (stop collecting audio but keep connection)
     */
    pauseStreaming() {
        if (this.isStreaming && !this.isStreamingPaused) {
            this.isStreamingPaused = true;
            this.pauseResumeBtn.textContent = '▶️ Resume';
            this.pauseResumeBtn.classList.add('paused');
            console.log('Streaming paused - waiting for AI response');
        }
    }

    /**
     * Resume streaming (continue collecting audio)
     */
    resumeStreaming() {
        if (this.isStreaming && this.isStreamingPaused) {
            this.isStreamingPaused = false;
            this.pauseResumeBtn.textContent = '⏸️ Pause';
            this.pauseResumeBtn.classList.remove('paused');
            console.log('Streaming resumed - listening for user input');
        }
    }

    /**
     * Check if streaming buffer should be processed
     */
    checkAndProcessStreamingBuffer() {
        const now = Date.now();
        const bufferDuration = this.estimateBufferDuration();

        // Process if buffer has enough audio or enough time has passed
        if (bufferDuration >= this.processingThreshold ||
            (now - this.lastProcessingTime) >= 3000) { // 3 seconds max wait

            this.processStreamingBuffer();
        }
    }

    /**
     * Estimate duration of audio in buffer
     */
    estimateBufferDuration() {
        // Rough estimation: each chunk is ~100ms based on your chunkSize
        return this.streamingBuffer.length * 100;
    }

    /**
     * Process current streaming buffer
     */
    processStreamingBuffer() {
        if (this.streamingBuffer.length === 0) return;

        // Combine all chunks in buffer
        const combinedChunk = this.combineAudioChunks(this.streamingBuffer);

        // Send for processing
        this.sendStreamingBuffer(combinedChunk);

        // Clear buffer after sending
        this.streamingBuffer = [];
        this.lastProcessingTime = Date.now();
    }

    /**
     * Combine multiple audio chunks into one
     */
    combineAudioChunks(chunks) {
        // Calculate total length
        let totalLength = 0;
        chunks.forEach(chunk => {
            totalLength += chunk.byteLength;
        });

        // Create combined buffer
        const combined = new ArrayBuffer(totalLength);
        const view = new Uint8Array(combined);
        let offset = 0;

        chunks.forEach(chunk => {
            const chunkView = new Uint8Array(chunk);
            view.set(chunkView, offset);
            offset += chunk.byteLength;
        });

        return combined;
    }

    /**
     * Send streaming buffer for processing
     */
    sendStreamingBuffer(audioData) {
        if (!this.isConnected || !this.isStreaming) {
            return;
        }

        try {
            const base64Audio = btoa(String.fromCharCode(...new Uint8Array(audioData)));

            const message = {
                type: 'streaming_buffer',
                audio: base64Audio,
                buffer_duration: this.estimateBufferDuration(),
                timestamp: Date.now()
            };

            this.websocket.send(JSON.stringify(message));
            console.log(`Sent streaming buffer: ${audioData.byteLength} bytes`);

        } catch (error) {
            console.error('Failed to send streaming buffer:', error);
        }
    }

    /**
     * Start periodic processing check
     */
    startPeriodicProcessing() {
        this.processingInterval = setInterval(() => {
            if (this.isStreaming && this.streamingBuffer.length > 0) {
                this.checkAndProcessStreamingBuffer();
            }
        }, 1000); // Check every second
    }

    /**
     * Stop streaming audio
     */
    stopStreaming() {
        if (this.isStreaming) {
            this.isStreaming = false;
            this.isStreamingPaused = false; // Reset pause state
            this.streamBtn.textContent = '🌊 Start Streaming';
            this.streamBtn.classList.remove('streaming');

            // Hide pause/resume button
            this.pauseResumeBtn.style.display = 'none';
            this.pauseResumeBtn.classList.remove('paused');

            // Process any remaining audio in buffer
            if (this.streamingBuffer.length > 0) {
                this.processStreamingBuffer();
            }

            // Stop periodic processing
            if (this.processingInterval) {
                clearInterval(this.processingInterval);
                this.processingInterval = null;
            }

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
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm;codecs=opus' });
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
            const clearUrl = this.backendUrl.replace('ws://', 'http://').replace('wss://', 'https://');
            fetch(`${clearUrl}/clear-conversation`, { method: 'POST' })
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
            <p><strong>Mode:</strong> Traditional Recording</p>
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

    /**
     * Stop keep-alive ping
     */
    stopKeepAlive() {
        if (this.keepAliveInterval) {
            clearInterval(this.keepAliveInterval);
            this.keepAliveInterval = null;
        }
    }

    /**
     * Toggle streaming pause/resume
     */
    toggleStreamingPause() {
        if (!this.isStreaming) return;

        if (this.isStreamingPaused) {
            this.resumeStreaming();
        } else {
            this.pauseStreaming();
        }
    }
}

// Initialize client when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.echoAIClient = new EchoAIClient();
}); 