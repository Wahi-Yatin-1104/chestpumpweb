const socket = io();
let isExercising = false;

initChart();
setupEventListeners();

function initChart() {
    const ctx = document.getElementById('heartRateChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                data: [],
                borderColor: '#45ffca',
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    grid: { color: '#222' },
                    ticks: { color: '#666' }
                },
                y: {
                    min: 40,
                    max: 200,
                    grid: { color: '#222' },
                    ticks: { color: '#666' }
                }
            }
        }
    });
}

function changeMode(mode) {
    fetch(`/workout/change_mode/${mode}`);
}

function toggleExercise() {
    const button = document.getElementById('startStop');
    const icon = button.querySelector('i');
    
    if (!isExercising) {
        fetch('/workout/start');
        button.textContent = 'Stop';
        button.classList.add('stop');
        icon.className = 'bx bx-stop';
    } else {
        fetch('/workout/stop');
        button.textContent = 'Start';
        button.classList.remove('stop');
        icon.className = 'bx bx-play';
    }
    isExercising = !isExercising;
}

async function connectHR() {
    try {
        const device = await navigator.bluetooth.requestDevice({
            filters: [{ services: ['heart_rate'] }]
        });

        const server = await device.gatt.connect();
        const service = await server.getPrimaryService('heart_rate');
        const characteristic = await service.getCharacteristic('heart_rate_measurement');

        await characteristic.startNotifications();
        characteristic.addEventListener('characteristicvaluechanged', handleHeartRate);
    } catch (error) {
        console.error('Connection failed:', error);
    }
}

function handleHeartRate(event) {
    const heartRate = event.target.value.getUint8(1);
    updateHeartRateDisplay(heartRate);
}

function updateHeartRateDisplay(heartRate) {
    document.getElementById('heartRate').textContent = heartRate;
    const zone = getHeartRateZone(heartRate);
    document.getElementById('heartRateZone').textContent = zone;
}

function getHeartRateZone(bpm) {
    if (bpm < 100) return 'Resting';
    if (bpm < 140) return 'Fat Burn';
    if (bpm < 170) return 'Cardio';
    return 'Peak';
}

function setupEventListeners() {
    socket.on('update_stats', data => {
        document.getElementById('mode').textContent = data.mode.toUpperCase();
        document.getElementById('reps').textContent = data.reps;
        document.getElementById('calories').textContent = data.calories.toFixed(1);
    });
}