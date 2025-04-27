const OneRepMax = (function() {
    const weightedExercises = ["dl", "fs", "br", "op", "cu", "bp"];
    let currentWeight = 0;
    let currentReps = 0;
    let formIssues = false;
    let isEnabled = false;
    let currentMode = "";
    
    function initialize() {
        removeExistingButtons();
        currentMode = document.getElementById('mode')?.textContent.toLowerCase() || "";

        const isWeighted = isWeightedExercise(currentMode);
        const container = document.getElementById('oneRepMaxContainer');
        if (container) {
            container.style.display = isWeighted ? 'block' : 'none';
        }
            
        if (isWeighted && localStorage.getItem('ormEnabled') === 'true') {
            enableFeature();
            const toggleBtn = document.getElementById('oneRepMaxToggle');
            if (toggleBtn) {
                toggleBtn.textContent = 'Disable 1RM Tracking';
                toggleBtn.classList.add('active');
            }
        } else if (!isWeighted) {
            disableFeature();
        }

        listenForStatsUpdates();
        setupFormHandler();
        
        console.log('One Rep Max module initialized');
    }
    
    function isWeightedExercise(mode) {
        return weightedExercises.includes(mode);
    }
    
    function removeExistingButtons() {
        const buttons = document.querySelectorAll('.control-btn');
        buttons.forEach(button => {
            const text = button.innerText || button.textContent;
            if (text && (text.includes('1RM') || text.includes('One Rep Max') || text.toLowerCase().includes('rep max'))) {
                console.log('Removing existing button:', text);
                button.remove();
            }
        });
    }
    
    function setupFormHandler() {
        const form = document.getElementById('ormForm');
        if (form) {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                calculateAndSave();
            });
        }
    }
    
    function toggleOneRepMax() {
        if (isEnabled) {
            disableFeature();
            const toggleBtn = document.getElementById('oneRepMaxToggle');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="bx bx-dumbbell"></i> Enable 1RM Tracking';
                toggleBtn.classList.remove('active');
            }
        } else {
            enableFeature();
            const toggleBtn = document.getElementById('oneRepMaxToggle');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="bx bx-dumbbell"></i> Disable 1RM Tracking';
                toggleBtn.classList.add('active');
            }
        }
    }
    
    function enableFeature() {
        isEnabled = true;
        localStorage.setItem('ormEnabled', 'true');
        
        const savedWeight = localStorage.getItem('currentWeight');
        if (savedWeight) {
            currentWeight = parseFloat(savedWeight);
        }
        
        if (isWeightedExercise(currentMode)) {
            const weightInput = document.getElementById('weightInputContainer');
            if (weightInput) {
                weightInput.style.display = 'block';
                
                const exerciseWeightInput = document.getElementById('exerciseWeight');
                if (exerciseWeightInput) {
                    if (!exerciseWeightInput.hasAttribute('data-user-modified')) {
                        exerciseWeightInput.value = currentWeight > 0 ? currentWeight : 45;
                    }
                    
                    if (!exerciseWeightInput.hasAttribute('data-has-listener')) {
                        exerciseWeightInput.setAttribute('data-has-listener', 'true');
                        exerciseWeightInput.addEventListener('input', function() {
                            this.setAttribute('data-user-modified', 'true');
                            currentWeight = parseFloat(this.value);
                            localStorage.setItem('currentWeight', currentWeight);
                        });
                    }
                }
            }
        }
        
        console.log('One Rep Max tracking enabled');
    }
    
    function disableFeature() {
        isEnabled = false;
        localStorage.setItem('ormEnabled', 'false');
        
        const weightInput = document.getElementById('weightInputContainer');
        if (weightInput) {
            weightInput.style.display = 'none';
        }
        
        document.getElementById('weightToastContainer').innerHTML = '';
        
        console.log('One Rep Max tracking disabled');
    }
    
    function showWeightReduction() {
        const container = document.getElementById('weightToastContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        const toast = document.createElement('div');
        toast.className = 'weight-toast';
        toast.innerHTML = `
            <i class='bx bx-error-circle toast-icon'></i>
            <div class="toast-content">
                <h4>Form Issue Detected</h4>
                <p>Try reducing the weight for better form.</p>
            </div>
            <button class="toast-action" onclick="OneRepMax.reduceWeight()">Reduce</button>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class='bx bx-x'></i>
            </button>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    }
    
    function reduceWeight() {
        const weightInput = document.getElementById('exerciseWeight');
        if (!weightInput) return;
        
        const currentVal = parseFloat(weightInput.value);
        if (isNaN(currentVal)) return;

        const reduction = Math.max(currentVal * 0.1, 5);
        const newWeight = Math.max(5, currentVal - reduction);
        
        weightInput.value = newWeight.toFixed(1);
        weightInput.setAttribute('data-user-modified', 'true');
        
        currentWeight = newWeight;
        localStorage.setItem('currentWeight', currentWeight);
        
        const toast = document.querySelector('.weight-toast');
        if (toast) {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }
    }
    
    function listenForStatsUpdates() {
        if (typeof socket !== 'undefined') {
            socket.on('update_stats', (data) => {
                console.log('Received stats update:', data);
                
                if (data.reps) {
                    currentReps = parseInt(data.reps);
                    
                    const ormRepsElement = document.getElementById('ormReps');
                    if (ormRepsElement) {
                        ormRepsElement.textContent = currentReps;
                    }
                }
                
                const mode = document.getElementById('mode')?.textContent.toLowerCase() || "";
                currentMode = mode;
                const isWeighted = isWeightedExercise(mode);
                
                const ormContainer = document.getElementById('oneRepMaxContainer');
                if (ormContainer) {
                    ormContainer.style.display = isWeighted ? 'block' : 'none';
                }
                
                const weightInput = document.getElementById('weightInputContainer');
                
                if (weightInput && isEnabled && isWeighted) {
                    weightInput.style.display = 'block';
                    
                    const exerciseWeightInput = document.getElementById('exerciseWeight');
                    if (exerciseWeightInput) {
                        if (!exerciseWeightInput.hasAttribute('data-user-modified') && currentWeight > 0) {
                            exerciseWeightInput.value = currentWeight;
                        }
                        
                        if (!exerciseWeightInput.hasAttribute('data-has-listener')) {
                            exerciseWeightInput.setAttribute('data-has-listener', 'true');
                            exerciseWeightInput.addEventListener('input', function() {
                                this.setAttribute('data-user-modified', 'true');
                                currentWeight = parseFloat(this.value);
                                localStorage.setItem('currentWeight', currentWeight);
                            });
                        }
                    }

                    const dynamicWeightInput = document.getElementById('weightInput');
                    if (dynamicWeightInput) {
                        dynamicWeightInput.remove();
                    }
                    
                    if (data.form_issues && data.form_issues.length > 0) {
                        console.log('Form issues detected:', data.form_issues);
                        formIssues = true;
                        
                        if (exerciseWeightInput) {
                            currentWeight = parseFloat(exerciseWeightInput.value) || currentWeight;
                        }
                        
                        console.log('Current weight:', currentWeight);
                        if (currentWeight > 10) {
                            console.log('Showing weight reduction notification');
                            showWeightReduction();
                        }
                    } else {
                        formIssues = false;
                    }
                } else if (weightInput) {
                    weightInput.style.display = 'none';
                }
            });
        }
    }
    
    function openCalculator() {
        if (!isWeightedExercise(currentMode)) {
            alert('One Rep Max calculation is only available for weighted exercises.');
            return;
        }
        
        const weightInput = document.getElementById('exerciseWeight');
        if (weightInput) {
            currentWeight = parseFloat(weightInput.value) || 0;
        }
        
        if (currentWeight <= 0) {
            alert('Please set a weight value first.');
            return;
        }

        if (currentReps <= 0) {
            alert('You need to complete at least 1 rep before calculating One Rep Max.');
            return;
        }

        const ormRepsElement = document.getElementById('ormReps');
        if (ormRepsElement) {
            ormRepsElement.textContent = currentReps;
        }

        const ormWeightElement = document.getElementById('ormWeight');
        if (ormWeightElement) {
            ormWeightElement.value = currentWeight;
        }

        const modalElement = document.getElementById('oneRepMaxModal');
        if (modalElement) {
            modalElement.style.display = 'block';
        }
    }

    function closeModal() {
        const modalElement = document.getElementById('oneRepMaxModal');
        if (modalElement) {
            modalElement.style.display = 'none';
        }
    }

    function calculateAndSave() {
        const weightInput = document.getElementById('ormWeight');
        if (!weightInput) return;
        
        const weight = parseFloat(weightInput.value);
        
        if (isNaN(weight) || weight <= 0) {
            alert('Please enter a valid weight');
            return;
        }

        const oneRepMax = calculateBrzycki(weight, currentReps);
        const ormValueElement = document.getElementById('ormValue');
        const ormResultElement = document.getElementById('ormResult');
        
        if (ormValueElement) {
            ormValueElement.textContent = Math.round(oneRepMax);
        }
        
        if (ormResultElement) {
            ormResultElement.style.display = 'block';

            ormResultElement.classList.add('success');

            setTimeout(() => {
                ormResultElement.classList.remove('success');
            }, 2000);
        }

        saveOneRepMax(weight, currentReps, oneRepMax);
    }

    function calculateBrzycki(weight, reps) {
        return weight * (36 / (37 - reps));
    }
    
    async function saveOneRepMax(weight, reps, oneRepMax) {
        try {
            const response = await fetch('/api/save-one-rep-max', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    exercise: currentMode,
                    weight: weight,
                    reps: reps,
                    estimated_one_rep_max: oneRepMax
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('One rep max saved successfully:', data);
            } else {
                console.error('Failed to save one rep max:', data.message);
            }
        } catch (error) {
            console.error('Error saving one rep max:', error);
        }
    }
    
    return {
        init: initialize,
        openCalculator: openCalculator,
        closeModal: closeModal,
        reduceWeight: reduceWeight,
        enableFeature: enableFeature,
        disableFeature: disableFeature,
        toggleFeature: toggleOneRepMax,
        updateWeight: function(weight) {
            if (!isNaN(parseFloat(weight))) {
                currentWeight = parseFloat(weight);
                localStorage.setItem('currentWeight', currentWeight);
            }
        }
    };
})();

window.toggleOneRepMax = function() {
    OneRepMax.toggleFeature();
};

document.addEventListener('DOMContentLoaded', function() {
    OneRepMax.init();
});