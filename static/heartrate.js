const socket = io();

let isExercising = false;

function changeMode(mode) {
    fetch(`/workout/change_mode/${mode}`);
}

function toggleExercise() {
    const button = document.getElementById('startStop');
    if (!isExercising) {
        fetch('/workout/start');
        button.textContent = 'Stop';
        button.classList.replace('start', 'stop');
    } else {
        fetch('/workout/stop');
        button.textContent = 'Start';
        button.classList.replace('stop', 'start');
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
        characteristic.addEventListener('characteristicvaluechanged', (event) => {
            const heartRate = event.target.value.getUint8(1);
            document.getElementById('heartRate').textContent = heartRate;
            socket.emit('send_heart_rate', { heartRate, time: new Date().toLocaleTimeString() });
        });
    } catch (error) {
        console.error('Failed to connect to HR monitor:', error);
    }
}

socket.on('update_heart_rate', (data) => {
    document.getElementById('heartRate').textContent = data.heartRate;
    document.getElementById('heartRateZone').textContent = getHeartRateZone(data.heartRate);
});

function getHeartRateZone(bpm) {
    if (bpm < 100) return 'Resting';
    if (bpm < 140) return 'Fat Burn';
    if (bpm < 170) return 'Cardio';
    return 'Peak';
}