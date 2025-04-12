const socket = io();
let workoutInProgress = false;
let heartRateChart;
let workoutStartTime = null;
let elapsedSeconds = 0;
let timerInterval = null;

function startTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    elapsedSeconds = 0;
    document.getElementById('time').textContent = '00:00';
    timerInterval = setInterval(() => {
        elapsedSeconds++;
        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = elapsedSeconds % 60;
        document.getElementById('time').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        console.log(`Timer tick: ${minutes}:${seconds} (${elapsedSeconds} seconds total)`);
    }, 1000);
    
    console.log('Timer started');
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
        console.log(`Timer stopped at ${elapsedSeconds} seconds`);
    }
}

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

function toggleExercise() {
    const button = document.getElementById('startStop');
    const finishBtn = document.getElementById('finishWorkout');
    
    if (!workoutInProgress) {
        startCountdown(function() {
            startWorkoutAfterCountdown();
        });
        
        button.disabled = true;
    } else {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        
        fetch('/workout/stop')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    workoutInProgress = false;
                    button.innerHTML = '<i class="bx bx-play"></i>Start';
                    button.classList.remove('active');
                    finishBtn.style.display = 'block';
                }
            });
    }
}

function startCountdown(callback) {
    const overlay = document.getElementById('countdownOverlay');
    const countdownText = document.getElementById('countdownText');
    let count = 3;
    
    overlay.classList.add('active');
    countdownText.textContent = count;
    countdownText.classList.add('countdown-number');
    

    const countdownInterval = setInterval(() => {
        count--;
        
        countdownText.classList.remove('countdown-number');
        void countdownText.offsetWidth; 
        if (count > 0) {
            countdownText.textContent = count;
            countdownText.classList.add('countdown-number');
        } else if (count === 0) {
            countdownText.textContent = "GO!";
            countdownText.classList.add('countdown-go');
        } else {
            clearInterval(countdownInterval);
            overlay.classList.remove('active');
            
            callback();
        }
    }, 1000);
}

function startWorkoutAfterCountdown() {
    const button = document.getElementById('startStop');
    const finishBtn = document.getElementById('finishWorkout');
    
    fetch('/workout/start')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Workout started successfully');
                workoutStartTime = Date.now();
                workoutInProgress = true;
                button.innerHTML = '<i class="bx bx-stop"></i>Stop';
                button.classList.add('active');
                button.disabled = false;
                elapsedSeconds = 0;
                
                if (timerInterval) {
                    clearInterval(timerInterval);
                }
                
                timerInterval = setInterval(() => {
                    elapsedSeconds = Math.floor((Date.now() - workoutStartTime) / 1000);
                    const minutes = Math.floor(elapsedSeconds / 60);
                    const seconds = elapsedSeconds % 60;
                    
                    document.getElementById('time').textContent = 
                        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                }, 1000);
                
                finishBtn.style.display = 'none';
            } else {
                button.disabled = false;
                alert('Failed to start workout. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error starting workout:', error);
            button.disabled = false;
        });
}



function updateTimer() {
    if (workoutInProgress && workoutStartTime) {
        elapsedSeconds = Math.floor((Date.now() - workoutStartTime) / 1000);
        const minutes = Math.floor(elapsedSeconds / 60);
        const seconds = elapsedSeconds % 60;

        document.getElementById('time').textContent = 
            `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        console.log(`Timer updated: ${minutes}:${seconds} (${elapsedSeconds} seconds total)`);
        
        requestAnimationFrame(updateTimer);
    }
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

const weightedExercises = ["dl", "fs", "br", "op", "cu", "bp"];
let currentWeight = 0;
let currentReps = 0;
let ormChart = null;
let historyData = [];

document.addEventListener('DOMContentLoaded', () => {
    const savedWeight = sessionStorage.getItem('currentWeight');
    if (savedWeight) {
        currentWeight = parseFloat(savedWeight);
    }

    document.querySelectorAll('.exercise-btn').forEach(btn => {
        const mode = btn.getAttribute('data-mode');
        if (weightedExercises.includes(mode)) {
            btn.classList.add('weighted');
        }
    });

    document.getElementById('ormForm').addEventListener('submit', function(event) {
        event.preventDefault();
        const weight = parseFloat(document.getElementById('ormWeight').value);
        
        if (isNaN(weight) || weight <= 0) {
            alert('Please enter a valid weight');
            return;
        }

        const reps = currentReps;
        if (reps <= 0) {
            alert('You need to complete at least 1 rep first');
            return;
        }

        const oneRepMax = calculateBrzycki(weight, reps);
        document.getElementById('ormValue').textContent = Math.round(oneRepMax);
        document.getElementById('ormResult').style.display = 'block';
        saveOneRepMax(weight, reps, oneRepMax);
    });

    const controlButtons = document.querySelector('.workout-controls.control-buttons');
    if (controlButtons) {
        const oneRepMaxButton = document.createElement('button');
        oneRepMaxButton.className = 'control-btn';
        oneRepMaxButton.innerHTML = '<i class="bx bx-dumbbell"></i> One Rep Max';
        oneRepMaxButton.onclick = function() { calculateOneRepMax(); };
        controlButtons.appendChild(oneRepMaxButton);
    }
});

function changeMode(newMode) {
    const weightedExercises = ["dl", "fs", "br", "op", "cu", "bp"];
    
    fetch(`/workout/change_mode/${newMode}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('mode').textContent = newMode.toUpperCase();
                
                const modeBadge = document.getElementById('currentMode');
                const isWeightedExercise = weightedExercises.includes(newMode);
                
                if (isWeightedExercise) {
                    modeBadge.classList.add('weighted');
                    updateWeightInputDisplay(true);
                } else {
                    modeBadge.classList.remove('weighted');
                    updateWeightInputDisplay(false);
                }
                
                document.querySelectorAll('.exercise-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.getAttribute('data-mode') === newMode);
                });
                
                currentReps = 0;
                
                if (typeof OneRepMax !== 'undefined' && OneRepMax.handleModeChange) {
                    OneRepMax.handleModeChange(newMode);
                }
            }
        })
        .catch(error => {
            console.error('Error changing mode:', error);
            showToast('Error changing exercise mode. Please try again.', 'error');
        });
}

socket.on('update_stats', (data) => {
    document.getElementById('mode').textContent = data.mode.toUpperCase();
    document.getElementById('reps').textContent = data.reps;
    document.getElementById('calories').textContent = data.calories.toFixed(1);
    currentReps = data.reps;
    
    const formStatus = document.getElementById('formStatus');
    if (data.form_issues && data.form_issues.length > 0) {
        formStatus.textContent = data.form_issues.join(' & ');
        formStatus.style.color = '#ff4444';
        formStatus.parentElement.classList.remove('good');
        formStatus.parentElement.classList.add('issues');

        if (data.weight_recommendation) {
            if (!document.getElementById('weightRecommendationDialog')) {
                showWeightRecommendation(data.weight_recommendation);
            }
        }
    } else {
        formStatus.textContent = 'Good';
        formStatus.style.color = '#22c55e';
        formStatus.parentElement.classList.add('good');
        formStatus.parentElement.classList.remove('issues');

        const dialog = document.getElementById('weightRecommendationDialog');
        if (dialog) {
            dialog.remove();
        }
    }
});

function showWeightRecommendation(recommendation) {
    const dialog = document.createElement('div');
    dialog.id = 'weightRecommendationDialog';
    dialog.className = 'weight-recommendation-dialog';

    dialog.innerHTML = `
        <div class="weight-dialog-content">
            <div class="weight-dialog-icon">
                <i class='bx bx-shield-quarter'></i>
            </div>
            <div class="weight-dialog-message">
                <h4>Form Check</h4>
                <p>${recommendation}</p>
            </div>
            <button class="weight-dialog-close">
                <i class='bx bx-x'></i>
            </button>
        </div>
    `;

    document.body.appendChild(dialog);

    setTimeout(() => {
        dialog.classList.add('show');
    }, 10);

    const closeBtn = dialog.querySelector('.weight-dialog-close');
    closeBtn.addEventListener('click', () => {
        dialog.classList.remove('show');
        setTimeout(() => {
            dialog.remove();
        }, 300);
    });

    setTimeout(() => {
        if (dialog.parentNode) {
            dialog.classList.remove('show');
            setTimeout(() => {
                if (dialog.parentNode) {
                    dialog.remove();
                }
            }, 300);
        }
    }, 5000);
}

function showWeightInput() {
    hideWeightInput();
    const weightInput = document.createElement('div');
    weightInput.id = 'weightInput';
    weightInput.className = 'weight-input';
    weightInput.innerHTML = `
        <label for="exerciseWeight">Weight:</label>
        <input type="number" id="exerciseWeight" min="0" step="2.5" value="${currentWeight}" onChange="updateWeight(this.value)">
        <span class="weight-input-unit">lbs</span>
    `;
e
    const modeBadge = document.getElementById('currentMode');
    modeBadge.parentNode.insertBefore(weightInput, modeBadge.nextSibling);

    document.getElementById('exerciseWeight').addEventListener('change', function() {
        updateWeight(this.value);
    });
}

function hideWeightInput() {
    const existingInput = document.getElementById('weightInput');
    if (existingInput) {
        existingInput.remove();
    }
}

function updateWeight(weight) {
    const weightValue = parseFloat(weight);
    
    if (isNaN(weightValue) || weightValue < 0) return;
    
    currentWeight = weightValue;
    localStorage.setItem('currentWeight', weightValue);
    
    fetch('/api/update_exercise_weight', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ weight: weightValue })
    })
    .catch(error => console.error('Error updating weight:', error));
    
    if (typeof OneRepMax !== 'undefined' && OneRepMax.updateWeight) {
        OneRepMax.updateWeight(weightValue);
    }
}

function calculateBrzycki(weight, reps) {
    return weight * (36 / (37 - reps));
}

function calculateOneRepMax() {
    const currentExercise = document.getElementById('mode').textContent.toLowerCase();

    if (!weightedExercises.includes(currentExercise.toLowerCase())) {
        alert('One Rep Max calculation is only available for weighted exercises.');
        return;
    }

    if (currentReps <= 0) {
        alert('You need to complete at least 1 rep before calculating One Rep Max.');
        return;
    }

    openModal('oneRepMaxModal');
    document.getElementById('ormWeight').value = currentWeight;
}

async function saveOneRepMax(weight, reps, oneRepMax) {
    const currentExercise = document.getElementById('mode').textContent.toLowerCase();
    
    try {
        const response = await fetch('/api/save_one_rep_max', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                exercise: currentExercise,
                weight: weight,
                reps: reps,
                formQuality: 'good',
                estimated_one_rep_max: oneRepMax
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Your one rep max of ${Math.round(oneRepMax)} lbs has been saved!`);

            setTimeout(() => {
                closeModal('oneRepMaxModal');
            }, 2000);
        } else {
            alert('Failed to save your one rep max: ' + data.error);
        }
    } catch (error) {
        console.error('Error saving one rep max:', error);
        alert('An error occurred while saving your one rep max');
    }
}
s
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function finishWorkout() {
    const modal = document.getElementById('workoutModal');
    const totalReps = parseInt(document.getElementById('reps').textContent) || 0;
    const calories = parseFloat(document.getElementById('calories').textContent) || 0;
    const durationSeconds = elapsedSeconds;
    console.log(`Finishing workout with exact duration: ${durationSeconds} seconds`);
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = durationSeconds % 60;
    const formattedDuration = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('modalReps').textContent = totalReps;
    document.getElementById('modalCalories').textContent = calories.toFixed(1);
    document.getElementById('modalDuration').textContent = formattedDuration;

    fetch('/workout/finish', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            total_reps: totalReps,
            calories_burned: calories,
            duration: durationSeconds,
            is_completed: true
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Workout saved with duration:', durationSeconds);
            sessionStorage.setItem('forceRefresh', 'true');
            modal.style.display = "block";
        } else {
            alert('Failed to save workout: ' + (data.message || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error saving workout:', error);
        alert('Error saving workout: ' + error);
    });
}

document.getElementById('refresh-stats-btn').addEventListener('click', function() {
    fetch('/api/dashboard-stats-raw-sql')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('workouts-count').textContent = data.stats.workouts_count;
                document.getElementById('total-calories').textContent = data.stats.total_calories.toFixed(1);
                document.getElementById('total-duration').textContent = data.stats.total_duration;
            } else {
                alert('Failed to refresh stats: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error refreshing stats:', error);
            alert('Error refreshing stats');
        });
});

function updateWeightInputDisplay(show) {
    const existingInput = document.getElementById('weightInput');
    if (existingInput) {
        existingInput.remove();
    }
    
    if (show) {
        const weightInput = document.createElement('div');
        weightInput.id = 'weightInput';
        weightInput.className = 'weight-input';
        
        const savedWeight = localStorage.getItem('currentWeight') || 0;
        
        weightInput.innerHTML = `
            <label for="exerciseWeight">Weight:</label>
            <input type="number" id="exerciseWeight" min="0" step="2.5" value="${savedWeight}">
            <span class="weight-input-unit">lbs</span>
        `;
        
        const modeBadge = document.getElementById('currentMode');
        modeBadge.parentNode.insertBefore(weightInput, modeBadge.nextSibling);
        
        document.getElementById('exerciseWeight').addEventListener('change', function() {
            updateWeight(this.value);
        });
    }
}


function goToDashboard() {
    sessionStorage.setItem('forceRefresh', 'true');
    window.location.href = '/dashboard?t=' + Date.now();
}
