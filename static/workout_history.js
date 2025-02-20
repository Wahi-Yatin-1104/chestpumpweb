const today = new Date();
let currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
let workoutData = {};

document.addEventListener('DOMContentLoaded', () => {
    fetchWorkoutData();
    renderCalendar();
});

async function fetchWorkoutData() {
    try {
        const response = await fetch('/api/workout-history');
        workoutData = await response.json();
        renderCalendar();
    } catch (error) {
        console.error('Error fetching workout data:', error);
    }
}

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
	const monthName = new Date(year, month, 1).toLocaleString('default', { month: 'long' });
    document.getElementById('calendarTitle').textContent = `${monthName} ${year}`;
	const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startingDayIndex = firstDay.getDay();
    const totalDays = lastDay.getDate();
	const calendarGrid = document.getElementById('calendarDays');
    calendarGrid.innerHTML = '';

    for (let i = 0; i < startingDayIndex; i++) {
        calendarGrid.appendChild(createEmptyDay());
    }
    for (let day = 1; day <= totalDays; day++) {
        const date = new Date(year, month, day);
        const dateString = formatDate(date);
        const workouts = workoutData[dateString] || [];
        
        const dayCell = createDayCell(day, workouts, dateString);
        
        if (date.toDateString() === today.toDateString()) {
            dayCell.classList.add('current-day');
        }
        
        calendarGrid.appendChild(dayCell);
    }
}

function createEmptyDay() {
    const cell = document.createElement('div');
    cell.className = 'calendar-day empty';
    return cell;
}

function createDayCell(day, workouts, dateString) {
    const cell = document.createElement('div');
    cell.className = `calendar-day ${workouts?.length > 0 ? 'has-workout' : ''}`;
    
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day;
    
    const dayInfo = document.createElement('div');
    dayInfo.className = 'day-info';
    
    if (workouts?.length > 0) {
        const totalCalories = workouts.reduce((sum, w) => sum + w.calories_burned, 0);
        const totalDuration = workouts.reduce((sum, w) => sum + w.duration, 0);
        
        dayInfo.innerHTML = `
            <div class="workout-summary">
                <span class="workout-count">${workouts.length} workout${workouts.length > 1 ? 's' : ''}</span>
                <span class="calorie-count">${Math.round(totalCalories)} cal</span>
                <span class="duration">${totalDuration} min</span>
            </div>
        `;
        
        cell.onclick = () => showWorkoutDetails(workouts, dateString);
    }
    
    cell.appendChild(dayNumber);
    cell.appendChild(dayInfo);
    return cell;
}

function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
}

function goToToday() {
    currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    renderCalendar();
}

function showWorkoutDetails(workouts, dateString) {
    const modal = document.getElementById('workoutModal');
    const details = document.getElementById('workoutDetails');
    
    const date = new Date(dateString);
    const formattedDate = date.toLocaleDateString('default', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    let html = `<h4>${formattedDate}</h4>`;
    
    workouts.forEach(workout => {
        html += `
            <div class="workout-entry">
                <div class="workout-time">
                    ${new Date(workout.date).toLocaleTimeString()}
                </div>
                <div class="workout-stats">
                    <div class="stat">
                        <i class='bx bx-time'></i>
                        ${workout.duration} mins
                    </div>
                    <div class="stat">
                        <i class='bx bx-flame'></i>
                        ${workout.calories_burned} cal
                    </div>
                </div>
                <div class="exercise-breakdown">
                    ${Object.entries(workout.exercise_data)
                        .map(([exercise, reps]) => `
                            <div class="exercise">
                                <span class="exercise-name">${exercise.toUpperCase()}</span>
                                <span class="exercise-reps">${reps} reps</span>
                            </div>
                        `).join('')}
                </div>
            </div>
        `;
    });
    
    details.innerHTML = html;
    modal.style.display = 'block';
}

function closeModal() {
    document.getElementById('workoutModal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('workoutModal');
    if (event.target === modal) {
        closeModal();
    }
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeModal();
    }
});