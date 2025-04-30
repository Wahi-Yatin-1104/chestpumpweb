document.addEventListener('DOMContentLoaded', function() {
    console.log("Dashboard loading...");
    
    if (typeof Chart === 'undefined') {
        console.error("Chart.js library is not loaded! Please check your script includes.");
        displayChartError("Chart.js library not loaded");
        return;
    }

    try {
        initializeWorkoutChart();
        console.log("Chart initialized successfully");
    } catch (err) {
        console.error("Error initializing workout chart:", err);
        displayChartError("Error initializing chart: " + err.message);
    }
});

function displayChartError(message) {
    const chartContainer = document.querySelector('.chart-card');
    if (chartContainer) {
        const canvas = document.getElementById('workoutChart');
        if (canvas) {
            canvas.style.display = 'none';
        }
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'chart-error';
        errorDiv.innerHTML = `
            <div class="error-icon"><i class='bx bx-error-circle'></i></div>
            <p>${message}</p>
            <p>Try refreshing the page or contact support if the issue persists.</p>
        `;
        chartContainer.appendChild(errorDiv);
    }
}

document.addEventListener('DOMContentLoaded', async function() {
    console.log('Dashboard page loaded, initializing stats...');
    const forceRefresh = sessionStorage.getItem('forceRefresh');
    if (forceRefresh === 'true') {
        console.log('Force refresh detected, clearing cache...');
        sessionStorage.removeItem('forceRefresh');
    }
    
    await ensureUserProfile();
    
    initializeWorkoutChart();
    initializeCalendar();
    initializeNutritionTracking();
    refreshDashboardStats();
    checkUserProfile();
    
    const refreshButton = document.getElementById('refresh-stats-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshDashboardStats);
    } else {
        const statsSection = document.querySelector('.stats-grid');
        if (statsSection) {
            const refreshButton = document.createElement('button');
            refreshButton.id = 'refresh-stats-btn';
            refreshButton.className = 'btn outline';
            refreshButton.innerHTML = '<i class="bx bx-refresh"></i> Refresh Stats';
            refreshButton.addEventListener('click', refreshDashboardStats);
            
            statsSection.parentNode.insertBefore(refreshButton, statsSection);
        }
    }
});

function initializeWorkoutChart() {
    console.log("Initializing workout chart...");
    
    const canvas = document.getElementById('workoutChart');
    if (!canvas) {
        console.error("Chart canvas element not found");
        return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error("Could not get canvas context");
        return;
    }
    
    canvas.style.display = 'block';
    canvas.style.height = '320px';
    
    let workoutData;
    try {
        const dataElement = document.getElementById('workout-data');
        
        if (!dataElement) {
            console.warn("Workout data element not found, using default data");
            workoutData = {
                dates: ["2025-03-01"],
                calories: [0],
                durations: [0]
            };
        } else {
            workoutData = JSON.parse(dataElement.textContent);
        }
        
        if (!workoutData.dates || !workoutData.calories || !workoutData.durations) {
            throw new Error("Invalid workout data structure");
        }
    } catch (err) {
        console.error("Data parsing error:", err);
        workoutData = {
            dates: ["2025-03-01"],
            calories: [0],
            durations: [0]
        };
    }
    
    window.workoutChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: workoutData.dates,
            datasets: [
                {
                    label: 'Calories Burned',
                    data: workoutData.calories,
                    borderColor: '#45ffca',
                    backgroundColor: 'rgba(69, 255, 202, 0.2)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Duration (mins)',
                    data: workoutData.durations,
                    borderColor: '#ff4d4d',
                    backgroundColor: 'rgba(255, 77, 77, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#fff'
                    }
                }
            }
        }
    });
}

function calculateBMI() {
    const height = parseFloat(document.getElementById('height').value);
    const weight = parseFloat(document.getElementById('weight').value);
    
    if (!height || !weight || height <= 0 || weight <= 0) {
        alert('Please enter valid height and weight values');
        return;
    }
    const heightInMeters = height / 100;
    const bmi = weight / (heightInMeters * heightInMeters);
    
    displayBMIResults(bmi);
    saveBMIData(height, weight, bmi);
}

function displayBMIResults(bmi) {
    const resultDiv = document.getElementById('bmiResult');
    const bmiValue = document.getElementById('bmiValue');
    const bmiCategory = document.getElementById('bmiCategory');
    bmiValue.textContent = bmi.toFixed(1);
    let category;
    bmiCategory.classList.remove('underweight', 'normal', 'overweight', 'obese');
    
    if (bmi < 18.5) {
        category = 'Underweight';
        bmiCategory.classList.add('underweight');
    } else if (bmi < 25) {
        category = 'Normal';
        bmiCategory.classList.add('normal');
    } else if (bmi < 30) {
        category = 'Overweight';
        bmiCategory.classList.add('overweight');
    } else {
        category = 'Obese';
        bmiCategory.classList.add('obese');
    }
    
    bmiCategory.textContent = category;
    resultDiv.style.display = 'block';
}

async function saveBMIData(height, weight, bmi) {
    try {
        const response = await fetch('/api/save-bmi', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                height: height,
                weight: weight,
                bmi: bmi
            })
        });
        
        const data = await response.json();
        if (!data.success) {
            console.error('Failed to save BMI data');
        }
    } catch (error) {
        console.error('Error saving BMI data:', error);
    }
}

let dailyNutrition = {
    calories: 0,
    proteins: 0,
    carbs: 0,
    fats: 0
};

function initializeNutritionTracking() {
    console.log('Initializing Nutrition Tracking');
    
    const progressRing = document.querySelector('.progress-ring-circle');
    if (!progressRing) {
        console.error('Progress ring element not found');
        return;
    }
    
    const mealList = document.getElementById('mealList');
    if (!mealList) {
        console.error('Meal list element not found');
        return;
    }
    
    const circumference = 2 * Math.PI * 90;
    progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
    progressRing.style.strokeDashoffset = circumference; // Start with empty ring
    
    console.log('Nutrition elements initialized');
    fetchTodaysMeals();
}

async function fetchTodaysMeals() {
    try {
        console.log('Fetching today\'s meals...');
        
        const response = await fetch('/api/meals/today');
        const data = await response.json();
        
        console.log('API Response:', data);
        
        if (data.success) {
            if (!data.meals || !Array.isArray(data.meals)) {
                console.error('No meals array in response');
                updateMealList([]);
                resetNutritionTotals();
                return;
            }
            
            updateMealList(data.meals);
            calculateDailyTotals(data.meals);
            
            console.log('Nutrition data updated successfully');
        } else {
            console.error('API returned failure:', data.message);

            updateMealList([]);
            resetNutritionTotals();
        }
    } catch (error) {
        console.error('Error fetching meals:', error);
        updateMealList([]);
        resetNutritionTotals();
    }
}

function calculateDailyTotals(meals) {
    console.log('Calculating nutrition totals');
    
    dailyNutrition = {
        calories: 0,
        proteins: 0,
        carbs: 0,
        fats: 0
    };
    
    meals.forEach(meal => {
        dailyNutrition.calories += parseFloat(meal.calories) || 0;
        dailyNutrition.proteins += parseFloat(meal.proteins) || 0;
        dailyNutrition.carbs += parseFloat(meal.carbs) || 0;
        dailyNutrition.fats += parseFloat(meal.fats) || 0;
    });
    
    console.log('Daily nutrition totals:', dailyNutrition);
    
    updateNutritionUI();
}


function resetNutritionTotals() {
    dailyNutrition = {
        calories: 0,
        proteins: 0,
        carbs: 0,
        fats: 0
    };
    
    updateNutritionUI();
}

function updateNutritionUI() {
    console.log('Updating nutrition UI');
    
    const calorieGoalElement = document.getElementById('calorieGoalValue');
    const calorieGoalDisplayElement = document.getElementById('calorieGoalDisplay');
    
    let calorieGoal = 2000;
    
    if (calorieGoalElement && calorieGoalElement.textContent) {
        const parsedGoal = parseInt(calorieGoalElement.textContent);
        if (!isNaN(parsedGoal) && parsedGoal > 0) {
            calorieGoal = parsedGoal;
            console.log(`Using calorie goal from DOM: ${calorieGoal}`);
        }
    }
    
    if (calorieGoalDisplayElement) {
        calorieGoalDisplayElement.textContent = calorieGoal;
    }
    
    let percentage = 0;
    if (calorieGoal > 0) {
        percentage = Math.min(Math.max((dailyNutrition.calories / calorieGoal) * 100, 0), 100);
    }
    
    console.log(`Calories: ${dailyNutrition.calories}/${calorieGoal} (${percentage.toFixed(1)}%)`);
    
    const progressRing = document.querySelector('.progress-ring-circle');
    if (progressRing) {
        const radius = 90;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;
        progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
        progressRing.style.strokeDashoffset = offset;
        console.log(`Updated progress ring: offset=${offset.toFixed(1)}, percentage=${percentage.toFixed(1)}%`);
    } else {
        console.error('Progress ring element not found');
    }
    
    const caloriesElement = document.getElementById('currentCalories');
    if (caloriesElement) {
        caloriesElement.textContent = Math.round(dailyNutrition.calories);
    } else {
        console.error('Current calories element not found');
    }
    
    const proteinElement = document.getElementById('proteinTotal');
    const carbsElement = document.getElementById('carbsTotal');
    const fatsElement = document.getElementById('fatsTotal');
    
    if (proteinElement) {
        proteinElement.textContent = `${Math.round(dailyNutrition.proteins)}g`;
    } else {
        console.error('Protein element not found');
    }
    
    if (carbsElement) {
        carbsElement.textContent = `${Math.round(dailyNutrition.carbs)}g`;
    } else {
        console.error('Carbs element not found');
    }
    
    if (fatsElement) {
        fatsElement.textContent = `${Math.round(dailyNutrition.fats)}g`;
    } else {
        console.error('Fats element not found');
    }
}

function updateMealList(meals) {
    const mealList = document.getElementById('mealList');
    if (!mealList) {
        console.error('Meal list element not found during update');
        return;
    }
    
    console.log(`Updating meal list with ${meals.length} meals`);
    
    if (meals.length === 0) {
        mealList.innerHTML = '<div class="empty-meals">No meals logged today</div>';
        return;
    }
    
    mealList.innerHTML = meals.map(meal => `
        <div class="meal-item">
            <div class="meal-type ${meal.meal_type}">
                ${meal.meal_type}
            </div>
            <div class="meal-info">
                <div class="meal-name">${meal.food_name}</div>
                <div class="meal-macros">
                    ${meal.proteins ? `P: ${meal.proteins}g` : ''}
                    ${meal.carbs ? `C: ${meal.carbs}g` : ''}
                    ${meal.fats ? `F: ${meal.fats}g` : ''}
                </div>
            </div>
            <div class="meal-calories">
                ${Math.round(parseFloat(meal.calories) || 0)} cal
            </div>
        </div>
    `).join('');
}

function addMeal() {
    document.getElementById('addMealModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

async function saveMeal(event) {
    event.preventDefault();
    
    const mealData = {
        meal_type: document.getElementById('mealType').value,
        food_name: document.getElementById('foodName').value,
        calories: parseFloat(document.getElementById('calories').value) || 0,
        proteins: parseFloat(document.getElementById('proteins').value) || 0,
        carbs: parseFloat(document.getElementById('carbs').value) || 0,
        fats: parseFloat(document.getElementById('fats').value) || 0
    };

    console.log('Saving meal:', mealData);

    try {
        const response = await fetch('/api/meals/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(mealData)
        });

        const data = await response.json();
        console.log('Meal save response:', data);

        if (data.success) {
            document.getElementById('mealForm').reset();
            closeModal('addMealModal');
            
            setTimeout(async () => {
                try {
                    const mealResponse = await fetch('/api/meals/today');
                    const mealData = await mealResponse.json();
                    
                    console.log('Refreshed meal data:', mealData);
                    
                    if (mealData.success && Array.isArray(mealData.meals)) {
                        const mealList = document.getElementById('mealList');
                        if (!mealList) return;
                        
                        if (mealData.meals.length === 0) {
                            mealList.innerHTML = '<div class="empty-meals">No meals logged today</div>';
                        } else {
                            mealList.innerHTML = mealData.meals.map(meal => `
                                <div class="meal-item">
                                    <div class="meal-type ${meal.meal_type}">
                                        ${meal.meal_type}
                                    </div>
                                    <div class="meal-info">
                                        <div class="meal-name">${meal.food_name}</div>
                                        <div class="meal-macros">
                                            ${meal.proteins ? `P: ${meal.proteins}g` : ''}
                                            ${meal.carbs ? `C: ${meal.carbs}g` : ''}
                                            ${meal.fats ? `F: ${meal.fats}g` : ''}
                                        </div>
                                    </div>
                                    <div class="meal-calories">
                                        ${Math.round(parseFloat(meal.calories) || 0)} cal
                                    </div>
                                </div>
                            `).join('');
                        }
                        
                        const totals = {
                            calories: 0,
                            proteins: 0,
                            carbs: 0,
                            fats: 0
                        };
                        
                        mealData.meals.forEach(meal => {
                            totals.calories += parseFloat(meal.calories) || 0;
                            totals.proteins += parseFloat(meal.proteins) || 0;
                            totals.carbs += parseFloat(meal.carbs) || 0;
                            totals.fats += parseFloat(meal.fats) || 0;
                        });
                        
                        const caloriesElement = document.getElementById('currentCalories');
                        if (caloriesElement) {
                            caloriesElement.textContent = Math.round(totals.calories);
                        }
                        
                        const proteinElement = document.getElementById('proteinTotal');
                        if (proteinElement) {
                            proteinElement.textContent = `${Math.round(totals.proteins)}g`;
                        }
                        
                        const carbsElement = document.getElementById('carbsTotal');
                        if (carbsElement) {
                            carbsElement.textContent = `${Math.round(totals.carbs)}g`;
                        }
                        
                        const fatsElement = document.getElementById('fatsTotal');
                        if (fatsElement) {
                            fatsElement.textContent = `${Math.round(totals.fats)}g`;
                        }
                        
                        const progressRing = document.querySelector('.progress-ring-circle');
                        if (progressRing) {
                            const calorieGoalElement = document.getElementById('calorieGoalValue');
                            const calorieGoal = calorieGoalElement ? 
                                parseInt(calorieGoalElement.textContent) || 2000 : 2000;
                            
                            const percentage = Math.min((totals.calories / calorieGoal) * 100, 100);
                            const radius = 90;
                            const circumference = 2 * Math.PI * radius;
                            const offset = circumference - (percentage / 100) * circumference;
                            
                            progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
                            progressRing.style.strokeDashoffset = offset;
                        }
                    }
                } catch (error) {
                    console.error('Error refreshing meal display:', error);
                }
            }, 500);
        } else {
            alert(`Failed to save meal: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error saving meal:', error);
        alert(`Error saving meal: ${error.message}`);
    }
}

async function refreshMealDisplay() {
    try {
        const response = await fetch('/api/meals/today');
        const data = await response.json();
        
        if (!data.success || !Array.isArray(data.meals)) {
            return;
        }
        
        const mealList = document.getElementById('mealList');
        if (!mealList) return;
        
        if (data.meals.length === 0) {
            mealList.innerHTML = '<div class="empty-meals">No meals logged today</div>';
            return;
        }
        
        mealList.innerHTML = data.meals.map(meal => `
            <div class="meal-item">
                <div class="meal-type ${meal.meal_type}">
                    ${meal.meal_type}
                </div>
                <div class="meal-info">
                    <div class="meal-name">${meal.food_name}</div>
                    <div class="meal-macros">
                        ${meal.proteins ? `P: ${meal.proteins}g` : ''}
                        ${meal.carbs ? `C: ${meal.carbs}g` : ''}
                        ${meal.fats ? `F: ${meal.fats}g` : ''}
                    </div>
                </div>
                <div class="meal-calories">
                    ${Math.round(parseFloat(meal.calories) || 0)} cal
                </div>
            </div>
        `).join('');
        
        const totals = {
            calories: 0,
            proteins: 0,
            carbs: 0,
            fats: 0
        };
        
        data.meals.forEach(meal => {
            totals.calories += parseFloat(meal.calories) || 0;
            totals.proteins += parseFloat(meal.proteins) || 0;
            totals.carbs += parseFloat(meal.carbs) || 0;
            totals.fats += parseFloat(meal.fats) || 0;
        });
        
        document.getElementById('currentCalories').textContent = Math.round(totals.calories);
        document.getElementById('proteinTotal').textContent = `${Math.round(totals.proteins)}g`;
        document.getElementById('carbsTotal').textContent = `${Math.round(totals.carbs)}g`;
        document.getElementById('fatsTotal').textContent = `${Math.round(totals.fats)}g`;
        
        const progressRing = document.querySelector('.progress-ring-circle');
        if (progressRing) {
            const calorieGoal = parseInt(document.getElementById('calorieGoalValue').textContent) || 2000;
            const percentage = Math.min((totals.calories / calorieGoal) * 100, 100);
            const radius = 90;
            const circumference = 2 * Math.PI * radius;
            const offset = circumference - (percentage / 100) * circumference;
            progressRing.style.strokeDasharray = `${circumference} ${circumference}`;
            progressRing.style.strokeDashoffset = offset;
        }
    } catch (error) {
        console.error("Error refreshing meal display:", error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    refreshMealDisplay();
});

function initializeCalendar() {
    const calendarData = JSON.parse(document.getElementById('calendar-data').textContent);
    renderCalendar(calendarData);
}

function renderCalendar(calendarData) {
    const currentDate = new Date();
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    document.getElementById('currentMonth').textContent = new Date(year, month, 1).toLocaleString('default', { month: 'long' });
    document.getElementById('currentYear').textContent = year;
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDay = firstDay.getDay();
    
    const calendarGrid = document.getElementById('calendarDays');
    calendarGrid.innerHTML = '';

    for (let i = 0; i < startingDay; i++) {
        calendarGrid.appendChild(createEmptyDay());
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dateString = formatDate(date);
        const workout = calendarData[dateString];
        
        calendarGrid.appendChild(createDayCell(day, workout, dateString));
    }
}

function createEmptyDay() {
    const cell = document.createElement('div');
    cell.className = 'calendar-day empty';
    return cell;
}

function createDayCell(day, workout, dateString) {
    const cell = document.createElement('div');
    cell.className = `calendar-day${workout ? ' has-workout' : ''}`;
    
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day;
    
    if (workout) {
        const info = document.createElement('div');
        info.className = 'day-info';
        info.innerHTML = `
            <div class="workout-indicator">
                <i class='bx bx-flame'></i>
                ${Math.round(workout.calories_burned)} cal
            </div>
        `;
        cell.appendChild(info);
        
        cell.onclick = () => showWorkoutDetails(workout, dateString);
    }
    
    cell.appendChild(dayNumber);
    return cell;
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function refreshDashboardStats() {
    console.log('Refreshing dashboard stats...');
    fetch('/api/dashboard-stats-raw-sql')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            console.log('Received dashboard stats:', data);
            
            if (data.success) {
                const workoutsCount = document.getElementById('workouts-count');
                const totalCalories = document.getElementById('total-calories');
                const totalDuration = document.getElementById('total-duration');

                if (workoutsCount) {
                    workoutsCount.textContent = data.stats.workouts_count;
                    console.log('Updated workouts count to:', data.stats.workouts_count);
                } else {
                    console.error('workouts-count element not found');
                }
                
                if (totalCalories) {
                    totalCalories.textContent = data.stats.total_calories.toFixed(1);
                    console.log('Updated total calories to:', data.stats.total_calories);
                } else {
                    console.error('total-calories element not found');
                }
                
                if (totalDuration) {
                    totalDuration.textContent = data.stats.total_duration;
                    console.log('Updated total duration to:', data.stats.total_duration);
                } else {
                    console.error('total-duration element not found');
                }

                const streakElement = document.querySelector('.streak-counter span');
                if (streakElement && data.stats.streak_count !== undefined) {
                    streakElement.textContent = `${data.stats.streak_count} Day Streak`;
                }
            } else {
                console.error('Failed to get stats:', data.message);
            }
        })
        .catch(error => {
            console.error('Error refreshing dashboard stats:', error);
        });
}

function editCalorieGoal() {
    document.getElementById('calorieGoalModal').style.display = 'block';
}

async function checkUserProfile() {
    try {
        console.log('Checking user profile status...');
        const response = await fetch('/api/meals/today');
        const data = await response.json();
        
        if (data.success) {
            console.log('Profile check via meals API:', data);
            console.log('Calorie goal from API:', data.calorie_goal);
        } else {
            console.error('Error checking profile via meals API:', data.message);
        }
    } catch (error) {
        console.error('Error checking user profile:', error);
    }
}

async function updateCalorieGoal(event) {
    event.preventDefault();
    
    const newGoal = parseInt(document.getElementById('newCalorieGoal').value);
    console.log('Updating calorie goal to:', newGoal);
    
    const calorieGoalValue = document.getElementById('calorieGoalValue');
    const calorieGoalDisplay = document.getElementById('calorieGoalDisplay');
    
    if (calorieGoalValue) calorieGoalValue.textContent = newGoal;
    if (calorieGoalDisplay) calorieGoalDisplay.textContent = newGoal;
    
    closeModal('calorieGoalModal');
    updateNutritionUI();
    
    try {
        console.log('Sending request to update calorie goal...');
        const response = await fetch(`/api/simple-update-goal/${newGoal}`, {
            method: 'GET'
        });
        
        console.log('Response status:', response.status);
        const text = await response.text();
        console.log('Response text:', text);
        
    } catch (error) {
        console.error('Error updating calorie goal:', error);
    }
    
    setTimeout(() => {
        refreshMealDisplay();
    }, 500);
}

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
};

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.getElementsByClassName('modal');
        for (let modal of modals) {
            modal.style.display = 'none';
        }
    }
});

document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href && href !== '#' && href !== '') {
            window.location.href = href;
        }
    });
});

async function ensureUserProfile() {
    try {
        console.log('Checking if profile needs to be created...');
        const response = await fetch('/api/meals/today');
        const data = await response.json();
        
        if (!data.success) {
            console.error('Error checking profile status:', data.message);
            return false;
        }
        
        if (!data.calorie_goal) {
            console.log('No calorie goal found, attempting to create profile...');
            
            const createResponse = await fetch('/api/update-calorie-goal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    calorie_goal: 2000 
                })
            });
            
            const createData = await createResponse.json();
            console.log('Profile creation attempt response:', createData);
            
            return createData.success;
        }
        
        return true;
    } catch (error) {
        console.error('Error ensuring user profile exists:', error);
        return false;
    }
}