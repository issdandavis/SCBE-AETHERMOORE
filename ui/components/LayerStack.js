// SCBE AetherMoore 14-Layer Stack UI Controller
const LAYERS = [
    { id: 1, name: 'Initialization', description: 'Vector normalization & preprocessing', icon: '⚡' },
    { id: 2, name: 'Realification', description: 'Complex to real domain mapping', icon: '🔄' },
    { id: 3, name: 'Weighted Transform', description: 'Adaptive weight application', icon: '⚖️' },
    { id: 4, name: 'Poincaré Embedding', description: 'Hyperbolic space embedding', icon: '🌀' },
    { id: 5, name: 'Hyperbolic Distance', description: 'Geodesic distance calculation', icon: '📐' },
    { id: 6, name: 'Breathing Transform', description: 'Dynamic expansion/contraction', icon: '🫁' },
    { id: 7, name: 'Phase Transform', description: 'Isometric phase shifting', icon: '🌙' },
    { id: 8, name: 'Realm Distance', description: 'Multi-realm distance metrics', icon: '🌐' },
    { id: 9, name: 'Spectral Coherence', description: 'Frequency domain analysis', icon: '📊' },
    { id: 10, name: 'Spin Coherence', description: 'Quantum spin alignment', icon: '🔮' },
    { id: 11, name: 'Triadic Temporal', description: 'Time-based triadic analysis', icon: '⏱️' },
    { id: 12, name: 'Harmonic Scaling', description: 'Musical harmonic amplification', icon: '🎵' },
    { id: 13, name: 'Risk Decision', description: 'Security risk assessment', icon: '🛡️' },
    { id: 14, name: 'Audio Axis', description: 'Final audio output mapping', icon: '🔊' }
];

class LayerStackUI {
    constructor() {
        this.layers = LAYERS.map(l => ({...l, status: 'idle', metrics: {}}));
        this.isRunning = false;
        this.currentLayer = 0;
        this.init();
    }

    init() {
        this.renderLayers();
        this.renderMetrics();
        this.bindEvents();
    }

    renderLayers() {
        const container = document.getElementById('layerStack');
        container.innerHTML = this.layers.map(layer => `
            <div class="layer-card" data-layer="${layer.id}" id="layer-${layer.id}">
                <div class="layer-number">${layer.icon} Layer ${layer.id}</div>
                <div class="layer-name">${layer.name}</div>
                <div class="layer-status">
                    <span class="status-dot idle" id="status-${layer.id}"></span>
                    <span id="status-text-${layer.id}">Idle</span>
                </div>
            </div>
        `).join('');
    }

    renderMetrics() {
        const container = document.getElementById('metricsDisplay');
        const metrics = [
            { label: 'Processing Time', value: '0.00ms', id: 'procTime' },
            { label: 'Coherence Score', value: '0.000', id: 'coherence' },
            { label: 'Risk Level', value: 'N/A', id: 'riskLevel' },
            { label: 'Throughput', value: '0 ops/s', id: 'throughput' },
            { label: 'Memory Usage', value: '0 MB', id: 'memory' },
            { label: 'Active Layers', value: '0/14', id: 'activeLayers' }
        ];
        container.innerHTML = metrics.map(m => `
            <div class="metric-card">
                <div class="metric-label">${m.label}</div>
                <div class="metric-value" id="metric-${m.id}">${m.value}</div>
            </div>
        `).join('');
    }

    bindEvents() {
        document.getElementById('runAll').addEventListener('click', () => this.runAllLayers());
        document.getElementById('stopAll').addEventListener('click', () => this.stop());
        document.getElementById('resetAll').addEventListener('click', () => this.reset());
        document.getElementById('processInput').addEventListener('click', () => this.processInput());
        document.querySelectorAll('.layer-card').forEach(card => {
            card.addEventListener('click', (e) => this.selectLayer(parseInt(e.currentTarget.dataset.layer)));
        });
    }

    async runAllLayers() {
        if (this.isRunning) return;
        this.isRunning = true;
        const startTime = performance.now();
        
        for (let i = 0; i < this.layers.length; i++) {
            if (!this.isRunning) break;
            this.currentLayer = i;
            await this.runLayer(i);
        }
        
        const totalTime = (performance.now() - startTime).toFixed(2);
        this.updateMetric('procTime', `${totalTime}ms`);
        this.updateMetric('activeLayers', `${this.isRunning ? 14 : this.currentLayer}/14`);
        this.isRunning = false;
        this.log(`✅ Pipeline complete in ${totalTime}ms`);
    }

    async runLayer(index) {
        const layer = this.layers[index];
        this.setLayerStatus(layer.id, 'running');
        this.log(`🔄 Running ${layer.name}...`);
        
        await this.delay(200 + Math.random() * 300);
        
        layer.metrics = {
            time: (Math.random() * 50).toFixed(2),
            coherence: (0.85 + Math.random() * 0.15).toFixed(3)
        };
        
        this.setLayerStatus(layer.id, 'complete');
        this.updateMetric('coherence', layer.metrics.coherence);
        this.updateMetric('activeLayers', `${index + 1}/14`);
    }

    setLayerStatus(id, status) {
        const dot = document.getElementById(`status-${id}`);
        const text = document.getElementById(`status-text-${id}`);
        const card = document.getElementById(`layer-${id}`);
        dot.className = `status-dot ${status}`;
        text.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        card.classList.remove('active', 'error');
        if (status === 'running') card.classList.add('active');
        if (status === 'error') card.classList.add('error');
    }

    updateMetric(id, value) {
        const el = document.getElementById(`metric-${id}`);
        if (el) el.textContent = value;
    }

    stop() {
        this.isRunning = false;
        this.log('⏹ Pipeline stopped');
    }

    reset() {
        this.isRunning = false;
        this.currentLayer = 0;
        this.layers.forEach(l => {
            l.status = 'idle';
            l.metrics = {};
            this.setLayerStatus(l.id, 'idle');
        });
        document.getElementById('outputDisplay').innerHTML = '';
        this.renderMetrics();
        this.log('↻ Reset complete');
    }

    selectLayer(id) {
        const layer = this.layers.find(l => l.id === id);
        this.log(`📍 Selected: Layer ${id} - ${layer.name}\n   ${layer.description}`);
    }

    processInput() {
        const input = document.getElementById('inputData').value;
        if (!input.trim()) {
            this.log('⚠️ Please enter input data');
            return;
        }
        this.log(`📥 Processing input: ${input.substring(0, 50)}...`);
        this.runAllLayers();
    }

    log(message) {
        const output = document.getElementById('outputDisplay');
        const time = new Date().toLocaleTimeString();
        output.innerHTML += `<div>[${time}] ${message}</div>`;
        output.scrollTop = output.scrollHeight;
    }

    delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
}

document.addEventListener('DOMContentLoaded', () => new LayerStackUI());
