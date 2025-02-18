const socket = io();
let workoutInProgress = false;
let heartRateChart;
let workoutStartTime = null;

function initChart() {
    const ctx = document.getElementById('heartRateChart').getContext('2d');
    heartRateChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Heart Rate',
                data: [],
                borderColor: '#45ffca',
                backgroundColor: 'rgba(69,255,202,0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1f2937',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#374151',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    grid: { 
                        color: '#333',
                        drawBorder: false
                    },
                    ticks: { 
                        color: '#666',
                        maxRotation: 0
                    }
                },
                y: {
                    min: 60,
                    max: 180,
                    grid: { 
                        color: '#333',
                        drawBorder: false
                    },
                    ticks: { 
                        color: '#666',
                        stepSize: 20
                    }
                }
            }
        }
    });
}

function changeMode(newMode) {
    fetch(`/workout/change_mode/${newMode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('mode').textContent = newMode.toUpperCase();
                document.querySelectorAll('.exercise-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.textContent.toLowerCase().includes(newMode)) {
                        btn.classList.add('active');
                    }
                });
            }
        });
}

function toggleExercise() {
    const button = document.getElementById('startStop');
    const finishBtn = document.getElementById('finishWorkout');
    if (!workoutInProgress) {
        fetch('/workout/start')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Workout started successfully');
                    workoutStartTime = Date.now();
                    button.innerHTML = '<i class="bx bx-stop"></i>Stop';
                    button.classList.add('active');
                    workoutInProgress = true;
                    updateTimer();
                } else {
                    console.error('Failed to start workout:', data.error);
                    alert('Failed to start workout');
                }
            })
            .catch(error => {
                console.error('Error starting workout:', error);
                alert('Error starting workout');
            });
    } else {
        console.log('Attempting to stop workout...');
        fetch('/workout/stop')
            .then(response => {
                console.log('Stop workout response:', response);
                return response.json();
            })
            .then(data => {
                console.log('Stop workout data:', data);
                if (data.success) {
                    console.log('Workout stopped successfully');
                    workoutInProgress = false;
                    button.innerHTML = '<i class="bx bx-play"></i>Start';
                    button.classList.remove('active');
                    finishBtn.style.display = 'block';
                    workoutStartTime = null;
                    document.getElementById('time').textContent = '00:00';
                } else {
                    console.error('Failed to stop workout:', data.error);
                    alert('Failed to stop workout');
                }
            })
            .catch(error => {
                console.error('Error stopping workout:', error);
                alert('Error stopping workout');
                workoutInProgress = false;
                button.innerHTML = '<i class="bx bx-play"></i>Start';
                button.classList.remove('active');
            });
    }
}

function updateTimer() {
    if (workoutInProgress && workoutStartTime) {
        const elapsed = Math.floor((Date.now() - workoutStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        document.getElementById('time').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        requestAnimationFrame(updateTimer);
    }
}

function finishWorkout() {
    const modal = document.getElementById('workoutModal');
    document.getElementById('modalReps').textContent = document.getElementById('reps').textContent;
    document.getElementById('modalCalories').textContent = document.getElementById('calories').textContent;
    document.getElementById('modalDuration').textContent = document.getElementById('time').textContent;
    
    fetch('/workout/finish', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            total_reps: document.getElementById('reps').textContent,
            calories: document.getElementById('calories').textContent,
            heart_rate: document.getElementById('heartRate').textContent,
            duration: document.getElementById('time').textContent
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            modal.style.display = "block";
        }
    });
}

function startNewWorkout() {
    document.getElementById('workoutModal').style.display = "none";
    location.reload();
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
        characteristic.addEventListener('characteristicvaluechanged', handleHeartRateChange);
        
        document.getElementById('connectBtn').classList.add('connected');
        document.getElementById('connectBtn').innerHTML = '<i class="bx bx-heart"></i>Connected';
        
    } catch (error) {
        console.error('Error connecting:', error);
        alert('Could not connect to heart rate monitor. Please try again.');
    }
}

function handleHeartRateChange(event) {
    const heartRate = event.target.value.getUint8(1);
    updateHeartRate(heartRate);
}

function updateHeartRate(heartRate) {
    document.getElementById('heartRate').textContent = heartRate;
    const zone = getHeartRateZone(heartRate);
    const zoneElement = document.getElementById('heartRateZone');
    zoneElement.textContent = zone;
    zoneElement.className = 'zone-indicator ' + zone.toLowerCase().replace(' ', '-');
    
    updateChart(heartRate);
}

function getHeartRateZone(bpm) {
    if (bpm < 100) return "Resting";
    if (bpm < 140) return "Fat Burn";
    if (bpm < 170) return "Cardio";
    return "Peak";
}

function updateChart(heartRate) {
    const now = new Date().toLocaleTimeString();
    
    heartRateChart.data.labels.push(now);
    heartRateChart.data.datasets[0].data.push(heartRate);
    
    if (heartRateChart.data.labels.length > 15) {
        heartRateChart.data.labels.shift();
        heartRateChart.data.datasets[0].data.shift();
    }
    
    heartRateChart.update('none');
}

socket.on('update_stats', (data) => {
    document.getElementById('mode').textContent = data.mode.toUpperCase();
    document.getElementById('reps').textContent = data.reps;
    document.getElementById('calories').textContent = data.calories.toFixed(1);
    const formStatus = document.getElementById('formStatus');
    if (data.form_issues && data.form_issues.length > 0) {
        formStatus.textContent = data.form_issues.join(' & ');
        formStatus.style.color = '#ff4444';
        formStatus.parentElement.classList.remove('good');
        formStatus.parentElement.classList.add('issues');
    } else {
        formStatus.textContent = 'Good';
        formStatus.style.color = '#22c55e';
        formStatus.parentElement.classList.add('good');
        formStatus.parentElement.classList.remove('issues');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    initChart();
});

function finishWorkout() {
    const modal = document.getElementById('workoutModal');
    const totalReps = parseInt(document.getElementById('reps').textContent) || 0;
    const calories = parseFloat(document.getElementById('calories').textContent) || 0;
    const heartRate = parseInt(document.getElementById('heartRate').textContent) || 0;
    const duration = document.getElementById('time').textContent;
    document.getElementById('modalReps').textContent = totalReps;
    document.getElementById('modalCalories').textContent = calories.toFixed(1);
    document.getElementById('modalDuration').textContent = duration;

    fetch('/workout/finish', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            total_reps: totalReps,
            calories: calories,
            heart_rate: heartRate,
            duration: duration
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Workout saved successfully:', data);
            modal.style.display = "block";
        } else {
            console.error('Failed to save workout:', data.message);
            alert('Failed to save workout: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error saving workout:', error);
        alert('Error saving workout');
    });
}

function showCategory(category) {
    const bodyweightExercises = document.querySelector('.bodyweight-exercises');
    const weightsExercises = document.querySelector('.weights-exercises');
    const categoryBtns = document.querySelectorAll('.category-btn');
    
    if (category === 'bodyweight') {
        bodyweightExercises.style.display = 'grid';
        weightsExercises.style.display = 'none';
    } else {
        bodyweightExercises.style.display = 'none';
        weightsExercises.style.display = 'grid';
    }
    
    categoryBtns.forEach(btn => {
        btn.classList.toggle('active', 
            btn.textContent.toLowerCase().includes(category));
    });
}

function changeMode(newMode) {
    fetch(`/workout/change_mode/${newMode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('mode').textContent = newMode.toUpperCase();
                document.querySelectorAll('.exercise-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.getAttribute('data-mode') === newMode) {
                        btn.classList.add('active');
                    }
                });
            }
        })
        .catch(error => console.error('Error changing mode:', error));
}