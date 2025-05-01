let workoutChartInstance = null;
let dailyNutrition = { calories: 0, proteins: 0, carbs: 0, fats: 0 };

document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();

    if (typeof Chart === 'undefined') {
        console.error("Chart.js library is not loaded!");
        displayChartError("Chart.js library not loaded");
    } else {
        try {
            initializeWorkoutChart();
        } catch (err) {
            console.error("Error initializing workout chart on DOMContentLoaded:", err);
            displayChartError("Error initializing chart: " + err.message);
        }
    }

    initializeNutritionTracking();
    refreshDashboardStats();

    const refreshButton = document.getElementById('refresh-stats-btn');
    if (refreshButton) {
        refreshButton.removeAttribute('onclick');
        refreshButton.addEventListener('click', refreshDashboardStats);
    } else {
        console.warn('Refresh stats button not found.');
    }
});

function displayChartError(message) {
    const chartContainer = document.querySelector('.chart-card');
    if (chartContainer) {
        const canvas = document.getElementById('workoutChart');
        if (canvas) canvas.style.display = 'none';
        let errorDiv = chartContainer.querySelector('.chart-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'chart-error';
            chartContainer.appendChild(errorDiv);
        }
        errorDiv.innerHTML = `
            <div class="error-icon"><i class='bx bx-error-circle'></i></div>
            <p>${message}</p>
            <p>Try refreshing the page or contact support if the issue persists.</p>
        `;
    } else {
        console.error("Chart container not found for displaying error.");
    }
}

function initializeWorkoutChart() {
    const canvas = document.getElementById('workoutChart');
    if (!canvas) {
        displayChartError("Chart canvas element not found."); return;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        displayChartError("Could not get canvas context."); return;
    }
    if (workoutChartInstance) {
        workoutChartInstance.destroy();
        workoutChartInstance = null;
    }

    let workoutData;
    try {
        const dataElement = document.getElementById('workout-data');
        if (!dataElement || !dataElement.textContent) {
            workoutData = { dates: ["No Data"], calories: [0], durations: [0] };
        } else {
            try {
                 workoutData = JSON.parse(dataElement.textContent);
                 if (!workoutData || typeof workoutData !== 'object') throw new Error("Parsed data is not valid object.");
                 if (!Array.isArray(workoutData.dates)) workoutData.dates = ["No Data"];
                 if (!Array.isArray(workoutData.calories)) workoutData.calories = [0];
                 if (!Array.isArray(workoutData.durations)) workoutData.durations = [0];
                 if (workoutData.dates[0] !== "No Data") {
                    const len = workoutData.dates.length;
                    if(len === 0) { workoutData.dates = ["No Data"]; workoutData.calories = [0]; workoutData.durations = [0]; }
                    else {
                        if (workoutData.calories.length !== len) workoutData.calories = Array(len).fill(0);
                        if (workoutData.durations.length !== len) workoutData.durations = Array(len).fill(0);
                    }
                 } else {
                     if(workoutData.calories.length === 0) workoutData.calories = [0];
                     if(workoutData.durations.length === 0) workoutData.durations = [0];
                 }
            } catch(parseError) {
                 displayChartError("Failed to parse workout data.");
                 workoutData = { dates: ["Error"], calories: [0], durations: [0] };
            }
        }
    } catch (err) {
        displayChartError("Error loading workout data.");
        workoutData = { dates: ["Error"], calories: [0], durations: [0] };
    }

    canvas.style.display = 'block';
    canvas.style.height = '320px';
    const chartContainer = document.querySelector('.chart-card');
    const existingError = chartContainer?.querySelector('.chart-error');
    if (existingError) existingError.remove();

    try {
        workoutChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                 labels: workoutData.dates,
                 datasets: [
                    { label: 'Calories Burned', data: workoutData.calories, borderColor: '#45ffca', backgroundColor: 'rgba(69, 255, 202, 0.2)', borderWidth: 2, tension: 0.4, fill: true, pointRadius: 3, pointHoverRadius: 5 },
                    { label: 'Duration (mins)', data: workoutData.durations, borderColor: '#ff4d4d', backgroundColor: 'rgba(255, 77, 77, 0.1)', borderWidth: 2, tension: 0.4, fill: false, hidden: true, pointRadius: 3, pointHoverRadius: 5 }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { color: '#ccc', padding: 15, boxWidth: 12, usePointStyle: true } },
                    tooltip: {
                        backgroundColor: 'rgba(33, 33, 33, 0.9)', titleColor: '#fff', bodyColor: '#eee', borderColor: '#555', borderWidth: 1, padding: 10, displayColors: false,
                        callbacks: {
                             label: function(context) {
                                let label = context.dataset.label || ''; if (label) label += ': ';
                                if (context.parsed.y !== null) {
                                     if (context.dataset.label === 'Calories Burned') label += context.parsed.y + ' cal';
                                     else if (context.dataset.label === 'Duration (mins)') label += context.parsed.y + ' min';
                                     else label += context.parsed.y;
                                } return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: '#333' }, ticks: { color: '#999', maxRotation: 45, minRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
                    y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#999' } }
                },
                animation: { duration: 500, easing: 'easeInOutQuad' }
            }
        });
    } catch (chartError) {
        displayChartError("Failed to create chart: " + chartError.message);
    }
}

function initializeCalendar() {
    try {
        if (typeof window.currentCalendarDate === 'undefined') {
             window.currentCalendarDate = new Date();
        }
        const calendarDataElement = document.getElementById('calendar-data');
        if (!calendarDataElement) { return; }
        const calendarData = JSON.parse(calendarDataElement.textContent || '{}');
        renderCalendar(calendarData);
        updateCalendarHeaderDisplay(window.currentCalendarDate);
    } catch (e) { console.error("Error initializing calendar:", e); }
}

function updateCalendarHeaderDisplay(dateToDisplay) {
     const monthElement = document.getElementById('currentMonth');
     const yearElement = document.getElementById('currentYear');
     if (monthElement && yearElement) {
        monthElement.textContent = dateToDisplay.toLocaleString('default', { month: 'long' });
        yearElement.textContent = dateToDisplay.getFullYear();
     }
}

function renderCalendar(calendarData) {
    const dateToRender = window.currentCalendarDate || new Date();
    const year = dateToRender.getFullYear();
    const month = dateToRender.getMonth();
    updateCalendarHeaderDisplay(dateToRender);
    const firstDayOfMonth = new Date(year, month, 1);
    const lastDayOfMonth = new Date(year, month + 1, 0);
    const daysInMonth = lastDayOfMonth.getDate();
    const startingDay = firstDayOfMonth.getDay();
    const calendarGrid = document.getElementById('calendarDays');
    if (!calendarGrid) { return; }
    calendarGrid.innerHTML = '';
    for (let i = 0; i < startingDay; i++) { calendarGrid.appendChild(createEmptyDay()); }
    for (let day = 1; day <= daysInMonth; day++) {
        const currentDayDate = new Date(year, month, day);
        const dateString = formatDate(currentDayDate);
        const workout = calendarData[dateString];
        calendarGrid.appendChild(createDayCell(day, workout, dateString));
    }
     const totalCells = startingDay + daysInMonth;
     const remainingCells = (7 - (totalCells % 7)) % 7;
     for (let i = 0; i < remainingCells; i++) { calendarGrid.appendChild(createEmptyDay()); }
}

function createEmptyDay() {
    const cell = document.createElement('div');
    cell.className = 'calendar-day empty'; return cell;
}

function createDayCell(day, workout, dateString) {
    const cell = document.createElement('div');
    cell.className = `calendar-day${workout ? ' has-workout' : ''}`;
    cell.setAttribute('data-date', dateString);
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day;
    cell.appendChild(dayNumber);
    if (workout) {
        const info = document.createElement('div');
        info.className = 'day-info';
        info.innerHTML = `<div class="workout-indicator" title="${workout.calories_burned} cal"><i class='bx bx-dumbbell'></i></div>`;
        cell.appendChild(info);
        cell.title = `Workout on ${dateString}`;
    }
    const today = new Date();
    if (dateString === formatDate(today)) { cell.classList.add('today'); }
    return cell;
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function initializeNutritionTracking() {
    const progressRing = document.querySelector('.progress-ring-circle');
    if (progressRing) {
        const radius = progressRing.r?.baseVal?.value ?? 90;
        const circumference = 2 * Math.PI * radius;
        progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
        progressRing.style.strokeDashoffset = circumference;
    } else { console.error('Progress ring element not found'); }
    const mealList = document.getElementById('mealList');
    if (!mealList) { console.error('Meal list element not found'); return; }
    fetchTodaysMeals();
}

async function fetchTodaysMeals() {
    try {
        const response = await fetch('/api/meals/today');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (data.success) {
            if (!Array.isArray(data.meals)) { updateMealList([]); resetNutritionTotals(); }
            else { updateMealList(data.meals); calculateDailyTotals(data.meals); }
            const calorieGoalElement = document.getElementById('calorieGoalValue');
            const calorieGoalDisplayElement = document.getElementById('calorieGoalDisplay');
            if (data.calorie_goal != null) {
                if (calorieGoalElement) calorieGoalElement.textContent = data.calorie_goal;
                if (calorieGoalDisplayElement) calorieGoalDisplayElement.textContent = data.calorie_goal;
            } else {
                if (calorieGoalElement) calorieGoalElement.textContent = '2000';
                if (calorieGoalDisplayElement) calorieGoalDisplayElement.textContent = '2000';
            }
            updateNutritionUI();
        } else { updateMealList([]); resetNutritionTotals(); }
    } catch (error) {
        console.error('Error fetching meals:', error);
        updateMealList([]); resetNutritionTotals();
    }
}

function calculateDailyTotals(meals) {
    dailyNutrition = { calories: 0, proteins: 0, carbs: 0, fats: 0 };
    if (!Array.isArray(meals)) { updateNutritionUI(); return; }
    meals.forEach(meal => {
        dailyNutrition.calories += parseFloat(meal.calories) || 0;
        dailyNutrition.proteins += parseFloat(meal.proteins) || 0;
        dailyNutrition.carbs += parseFloat(meal.carbs) || 0;
        dailyNutrition.fats += parseFloat(meal.fats) || 0;
    });
    updateNutritionUI();
}

function resetNutritionTotals() {
    dailyNutrition = { calories: 0, proteins: 0, carbs: 0, fats: 0 };
    updateNutritionUI();
}

function updateNutritionUI() {
    const calorieGoalElement = document.getElementById('calorieGoalValue');
    const calorieGoalDisplayElement = document.getElementById('calorieGoalDisplay');
    let calorieGoal = 2000;
    if (calorieGoalElement && calorieGoalElement.textContent) {
        const parsedGoal = parseInt(calorieGoalElement.textContent, 10);
        if (!isNaN(parsedGoal) && parsedGoal > 0) { calorieGoal = parsedGoal; }
    }
    if (calorieGoalDisplayElement) { calorieGoalDisplayElement.textContent = calorieGoal; }
    let percentage = 0;
    const currentCalories = dailyNutrition?.calories ?? 0;
    if (calorieGoal > 0) { percentage = Math.min(Math.max((currentCalories / calorieGoal) * 100, 0), 100); }
    const progressRing = document.querySelector('.progress-ring-circle');
    if (progressRing) {
        const radius = progressRing.r?.baseVal?.value ?? 90;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;
        progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
        progressRing.style.strokeDashoffset = offset;
    }
    const caloriesElement = document.getElementById('currentCalories');
    if (caloriesElement) caloriesElement.textContent = Math.round(currentCalories);
    const proteinElement = document.getElementById('proteinTotal');
    if (proteinElement) proteinElement.textContent = `${Math.round(dailyNutrition?.proteins ?? 0)}g`;
    const carbsElement = document.getElementById('carbsTotal');
    if (carbsElement) carbsElement.textContent = `${Math.round(dailyNutrition?.carbs ?? 0)}g`;
    const fatsElement = document.getElementById('fatsTotal');
    if (fatsElement) fatsElement.textContent = `${Math.round(dailyNutrition?.fats ?? 0)}g`;
}

function updateMealList(meals) {
    const mealList = document.getElementById('mealList');
    if (!mealList) { return; }
    if (!Array.isArray(meals) || meals.length === 0) {
        mealList.innerHTML = '<div class="empty-meals">No meals logged today</div>'; return;
    }
    mealList.innerHTML = meals.map(meal => createMealItemHTML(meal)).join('');
}

function createMealItemHTML(meal) {
    const mealType = meal?.meal_type?.toLowerCase() || 'unknown';
    const foodName = meal?.food_name || 'Unnamed Food';
    const calories = Math.round(parseFloat(meal?.calories) || 0);
    const proteins = meal?.proteins ? `P: ${parseFloat(meal.proteins).toFixed(1)}g` : '';
    const carbs = meal?.carbs ? `C: ${parseFloat(meal.carbs).toFixed(1)}g` : '';
    const fats = meal?.fats ? `F: ${parseFloat(meal.fats).toFixed(1)}g` : '';
    const macros = [proteins, carbs, fats].filter(Boolean).join(' &nbsp; ');
    return `
    <div class="meal-item">
        <div class="meal-type ${mealType}">${mealType.charAt(0).toUpperCase() + mealType.slice(1)}</div>
        <div class="meal-info">
            <div class="meal-name">${foodName}</div>
            ${macros ? `<div class="meal-macros">${macros}</div>` : ''}
        </div>
        <div class="meal-calories">${calories} cal</div>
    </div>`;
}

function addMealToUI(meal) {
     const mealList = document.getElementById('mealList');
     if (!mealList) return;
     const emptyMessage = mealList.querySelector('.empty-meals');
     if (emptyMessage) { emptyMessage.remove(); }
     const mealItemHTML = createMealItemHTML(meal);
     mealList.insertAdjacentHTML('afterbegin', mealItemHTML);
}

function updateTotalsLocally(addedMeal) {
    dailyNutrition.calories += parseFloat(addedMeal.calories) || 0;
    dailyNutrition.proteins += parseFloat(addedMeal.proteins) || 0;
    dailyNutrition.carbs += parseFloat(addedMeal.carbs) || 0;
    dailyNutrition.fats += parseFloat(addedMeal.fats) || 0;
}

function addMeal() {
    const modal = document.getElementById('addMealModal');
    if (modal) modal.style.display = 'block';
}

function closeModal(modalId) {
     const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

async function saveMeal(event) {
    event.preventDefault();
    const mealData = {
        meal_type: document.getElementById('mealType')?.value,
        food_name: document.getElementById('foodName')?.value,
        calories: parseFloat(document.getElementById('calories')?.value) || 0,
        proteins: parseFloat(document.getElementById('proteins')?.value) || 0,
        carbs: parseFloat(document.getElementById('carbs')?.value) || 0,
        fats: parseFloat(document.getElementById('fats')?.value) || 0
    };

    if (mealData.calories > 5000) {
        alert("Calories cannot exceed 5000 for a single meal.");
        return;
    }

    if (!mealData.meal_type || !mealData.food_name || mealData.calories <= 0) {
         alert("Please fill in Meal Type, Food Name, and a valid Calorie amount (up to 5000).");
         return;
    }

    addMealToUI(mealData);
    updateTotalsLocally(mealData);
    updateNutritionUI();
    closeModal('addMealModal');
    document.getElementById('mealForm')?.reset();

    try {
        const response = await fetch('/api/meals/add', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                 ...mealData, proteins: mealData.proteins || 0, carbs: mealData.carbs || 0, fats: mealData.fats || 0
            })
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
             alert(`Failed to save meal: ${data.message || 'Server error'}. Reverting UI.`);
             await fetchTodaysMeals();
        }
    } catch (error) {
        alert(`Error saving meal: ${error.message || 'Network error'}. Reverting UI.`);
         await fetchTodaysMeals();
    }
}

async function refreshDashboardStats() {
    try {
        const response = await fetch('/api/dashboard-stats-raw-sql');
        if (!response.ok) throw new Error(`Network response was not ok (${response.status})`);
        const data = await response.json();
        if (data.success && data.stats) {
            const { workouts_count, total_calories, total_duration, streak_count } = data.stats;
            const workoutsCountEl = document.getElementById('workouts-count');
            const totalCaloriesEl = document.getElementById('total-calories');
            const totalDurationEl = document.getElementById('total-duration');
            const streakCounterEl = document.querySelector('.streak-counter span');
            if (workoutsCountEl) workoutsCountEl.textContent = workouts_count ?? 0;
            if (totalCaloriesEl) totalCaloriesEl.textContent = (total_calories ?? 0).toFixed(1);
            if (totalDurationEl) totalDurationEl.textContent = total_duration ?? 0;
            if (streakCounterEl) {
                 const streakContainer = streakCounterEl.closest('.streak-counter');
                 if (streak_count !== undefined && streak_count > 0) {
                    streakCounterEl.textContent = `${streak_count} Day Streak`;
                    if(streakContainer) streakContainer.style.display = 'flex';
                 } else { if(streakContainer) streakContainer.style.display = 'none'; }
            }
        } else { console.error('Failed to get stats from API:', data.message); }
    } catch (error) {
        console.error('Error refreshing dashboard stats:', error);
        const statsGrid = document.querySelector('.stats-grid');
        if(statsGrid && !statsGrid.querySelector('.api-error-message')) {
             const errorMsg = document.createElement('p');
             errorMsg.textContent = 'Error loading stats.'; errorMsg.style.color = 'red';
             errorMsg.style.gridColumn = '1 / -1'; errorMsg.className = 'api-error-message';
             statsGrid.prepend(errorMsg);
        }
    }
}

function editCalorieGoal() {
    const modal = document.getElementById('calorieGoalModal');
    if (modal) {
         const currentGoal = document.getElementById('calorieGoalValue')?.textContent || '2000';
         const input = document.getElementById('newCalorieGoal');
         if (input) input.value = currentGoal;
        modal.style.display = 'block';
    }
}

async function updateCalorieGoal(event) {
    event.preventDefault();
    const inputElement = document.getElementById('newCalorieGoal');
    if (!inputElement) return;
    const newGoal = parseInt(inputElement.value, 10);
    if (isNaN(newGoal) || newGoal < 1200 || newGoal > 10000) {
        alert('Please enter valid calorie goal between 1200 and 10000.'); return;
    }
    const calorieGoalValue = document.getElementById('calorieGoalValue');
    const calorieGoalDisplay = document.getElementById('calorieGoalDisplay');
    const oldGoal = calorieGoalValue ? calorieGoalValue.textContent : '2000';
    if (calorieGoalValue) calorieGoalValue.textContent = newGoal;
    if (calorieGoalDisplay) calorieGoalDisplay.textContent = newGoal;
    closeModal('calorieGoalModal');
    updateNutritionUI();
    try {
        const response = await fetch(`/api/update-calorie-goal`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ calorie_goal: newGoal })
        });
        const responseData = await response.json();
        if (!response.ok || !responseData.success) {
            alert(`Failed to save calorie goal: ${responseData.message || 'Server error'}`);
            if (calorieGoalValue) calorieGoalValue.textContent = oldGoal;
            if (calorieGoalDisplay) calorieGoalDisplay.textContent = oldGoal;
            updateNutritionUI();
        }
    } catch (error) {
        alert(`Error updating calorie goal: ${error.message || 'Network error'}`);
        if (calorieGoalValue) calorieGoalValue.textContent = oldGoal;
        if (calorieGoalDisplay) calorieGoalDisplay.textContent = oldGoal;
        updateNutritionUI();
    }
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) { closeModal(event.target.id); }
};
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => closeModal(modal.id));
    }
});
document.querySelectorAll('.btn[href]').forEach(btn => {
    if (!btn.onclick && !btn.id?.includes('refresh')) {
        btn.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href && href !== '#' && href !== '' && !href.startsWith('javascript:')) {
                e.preventDefault(); window.location.href = href;
            }
        });
    }
});

function calculateBMI() {
    const heightInput = document.getElementById('height');
    const weightInput = document.getElementById('weight');
    const height = parseFloat(heightInput?.value);
    const weight = parseFloat(weightInput?.value);
    if (!height || !weight || height <= 0 || weight <= 0) {
        alert('Please enter valid height (cm) and weight (kg) values'); return;
    }
    const heightInMeters = height / 100;
    const bmi = weight / (heightInMeters * heightInMeters);
    displayBMIResults(bmi); saveBMIData(height, weight, bmi);
}
function displayBMIResults(bmi) {
    const resultDiv = document.getElementById('bmiResult');
    const bmiValue = document.getElementById('bmiValue');
    const bmiCategory = document.getElementById('bmiCategory');
    if (!resultDiv || !bmiValue || !bmiCategory) { return; }
    bmiValue.textContent = bmi.toFixed(1); let category;
    bmiCategory.className = 'category';
    if (bmi < 18.5) { category = 'Underweight'; bmiCategory.classList.add('underweight'); }
    else if (bmi < 25) { category = 'Normal'; bmiCategory.classList.add('normal'); }
    else if (bmi < 30) { category = 'Overweight'; bmiCategory.classList.add('overweight'); }
    else { category = 'Obese'; bmiCategory.classList.add('obese'); }
    bmiCategory.textContent = category; resultDiv.style.display = 'block';
}
async function saveBMIData(height, weight, bmi) {
    try {
        const response = await fetch('/api/save-bmi', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ height: height, weight: weight, bmi: bmi })
        });
        const data = await response.json();
        if (!data.success) { console.error('Failed to save BMI data:', data.message); }
    } catch (error) { console.error('Error saving BMI data:', error); }
}

function previousMonth() {
    if (window.currentCalendarDate) {
        window.currentCalendarDate.setMonth(window.currentCalendarDate.getMonth() - 1);
        initializeCalendar();
    }
}
function nextMonth() {
     if (window.currentCalendarDate) {
        window.currentCalendarDate.setMonth(window.currentCalendarDate.getMonth() + 1);
        initializeCalendar();
    }
}
function currentMonth() {
     if (window.currentCalendarDate) {
        window.currentCalendarDate = new Date();
        initializeCalendar();
    }
}