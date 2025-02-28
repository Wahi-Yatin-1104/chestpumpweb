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
        
        if (isWeightedExercise(currentMode)) {
            addToggleButton();
        }
        
        listenForStatsUpdates();
        setupFormHandler();
        
        if (localStorage.getItem('ormEnabled') === 'true') {
            enableFeature();
        }
        
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
    
    function addToggleButton() {
        const controlButtons = document.querySelector('.workout-controls.control-buttons');
        if (!controlButtons) {
            return;
        }
        
        const toggleButton = document.createElement('button');
        toggleButton.id = 'ormToggleButton';
        toggleButton.className = 'control-btn';
        toggleButton.innerHTML = '<i class="bx bx-dumbbell"></i> Enable 1RM Tracking';
        toggleButton.onclick = toggleFeature;
        
        controlButtons.appendChild(toggleButton);
    }
    
    function toggleFeature() {
        if (isEnabled) {
            disableFeature();
        } else {
            enableFeature();
        }
    }
    
    function enableFeature() {
        isEnabled = true;
        localStorage.setItem('ormEnabled', 'true');
        
        const toggleButton = document.getElementById('ormToggleButton');
        if (toggleButton) {
            toggleButton.innerHTML = '<i class="bx bx-dumbbell"></i> Disable 1RM Tracking';
            toggleButton.classList.add('active');
        }
        
        const savedWeight = localStorage.getItem('currentWeight');
        if (savedWeight) {
            currentWeight = parseFloat(savedWeight);
        }
        
        if (isWeightedExercise(currentMode)) {
            addWeightInput();
        }
        
        console.log('One Rep Max tracking enabled');
    }
    
    function disableFeature() {
        isEnabled = false;
        localStorage.setItem('ormEnabled', 'false');
        
        const toggleButton = document.getElementById('ormToggleButton');
        if (toggleButton) {
            toggleButton.innerHTML = '<i class="bx bx-dumbbell"></i> Enable 1RM Tracking';
            toggleButton.classList.remove('active');
        }
        
        removeWeightInput();
        
        document.getElementById('weightToastContainer').innerHTML = '';
        
        console.log('One Rep Max tracking disabled');
    }
    
    function addWeightInput() {
        if (document.getElementById('weightInput')) {
            return;
        }
        
        const inputContainer = document.createElement('div');
        inputContainer.id = 'weightInput';
        inputContainer.className = 'weight-input';
        inputContainer.innerHTML = `
            <label for="exerciseWeight">Weight:</label>
            <input type="number" id="exerciseWeight" min="0" step="2.5" value="${currentWeight}">
            <span class="weight-input-unit">lbs</span>
        `;
        
        const modeBadge = document.getElementById('currentMode');
        if (modeBadge) {
            modeBadge.parentNode.insertBefore(inputContainer, modeBadge.nextSibling);
        } else {
            const cardHeader = document.querySelector('.card-header');
            if (cardHeader) {
                cardHeader.appendChild(inputContainer);
            }
        }
        
        document.getElementById('exerciseWeight').addEventListener('change', function() {
            updateWeight(this.value);
        });
    }
    
    function removeWeightInput() {
        const input = document.getElementById('weightInput');
        
		if (input) {
            input.remove();
        }
    }
    
    function updateWeight(weight) {
        currentWeight = parseFloat(weight);
        localStorage.setItem('currentWeight', currentWeight);
        console.log('Weight updated to:', currentWeight);
    }
    
    function showWeightReduction() {
        if (currentWeight <= 10) return;
        
        const reducedWeight = Math.max(0, currentWeight - 10);
        const container = document.getElementById('weightToastContainer');
        container.innerHTML = '';
        const toast = document.createElement('div');
        toast.className = 'weight-toast';
        toast.innerHTML = `
            <div class="toast-icon"><i class='bx bx-shield-quarter'></i></div>
            <div class="toast-content">
                <h4>Form Check</h4>
                <p>Your form needs improvement. Try reducing the weight by 10 lbs to ${reducedWeight} lbs.</p>
            </div>
            <button class="toast-action" onclick="OneRepMax.reduceWeight(${reducedWeight})">Apply</button>
            <button class="toast-close" onclick="this.parentNode.remove()"><i class='bx bx-x'></i></button>
        `;
        container.appendChild(toast);
        
		setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, 8000);
    }
    
    function reduceWeight(newWeight) {
        const weightInput = document.getElementById('exerciseWeight');
        if (weightInput) {
            weightInput.value = newWeight;
            updateWeight(newWeight);
        }
        
        document.getElementById('weightToastContainer').innerHTML = '';
    }
    
    function listenForStatsUpdates() {
        if (typeof socket !== 'undefined') {
            socket.on('update_stats', (data) => {
                currentReps = data.reps;
                currentMode = data.mode.toLowerCase();
                const ormRepsElement = document.getElementById('ormReps');
                if (ormRepsElement) {
                    ormRepsElement.textContent = currentReps;
                }
                
                const isWeighted = isWeightedExercise(currentMode);
                handleToggleButtonVisibility(isWeighted);
                
                if (!isEnabled) return;
                if (isWeighted) {
                    addWeightInput();
                } else {
                    removeWeightInput();
                }
                
                if (isWeighted && data.form_issues && data.form_issues.length > 0) {
                    formIssues = true;
                    
                    if (currentWeight > 10) {
                        if (!document.querySelector('.weight-toast')) {
                            showWeightReduction();
                        }
                    }
                } else {
                    formIssues = false;
                }
            });
        }
    }
    
    function handleToggleButtonVisibility(isWeightedExercise) {
        removeExistingButtons();
        
        if (isWeightedExercise) {
            addToggleButton();
            
            if (isEnabled) {
                const toggleButton = document.getElementById('ormToggleButton');
                if (toggleButton) {
                    toggleButton.innerHTML = '<i class="bx bx-dumbbell"></i> Disable 1RM Tracking';
                    toggleButton.classList.add('active');
                }
            }
        } else {
            removeWeightInput();
        }
    }
    
    function openCalculator() {
        if (!isWeightedExercise(currentMode)) {
            alert('One Rep Max calculation is only available for weighted exercises.');
            return;
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
        const oneRepMax = weight*(36/(37-currentReps));
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
        
        console.log('Saving One Rep Max:', {
            exercise: currentMode,
            weight: weight,
            reps: currentReps,
            estimated_one_rep_max: oneRepMax
        });
    }
    
    function calculateBrzycki(weight, reps) {
        return weight * (36 / (37 - reps));
    }
    
    return {
        init: initialize,
        openCalculator: openCalculator,
        closeModal: closeModal,
        reduceWeight: reduceWeight,
        enableFeature: enableFeature,
        disableFeature: disableFeature,
        toggleFeature: toggleFeature
    };
})();
document.addEventListener('DOMContentLoaded', function() {
    OneRepMax.init();
});