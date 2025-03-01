document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard page loaded, initializing stats...');
    
    const forceRefresh = sessionStorage.getItem('forceRefresh');
    if (forceRefresh === 'true') {
        console.log('Force refresh detected, clearing cache...');
        sessionStorage.removeItem('forceRefresh');
    }
    
    initializeWorkoutChart();
    initializeCalendar();
    refreshDashboardStats();
    
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
    const ctx = document.getElementById('workoutChart').getContext('2d');
    
    const workoutData = JSON.parse(document.getElementById('workout-data').textContent);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: workoutData.dates,
            datasets: [
                {
                    label: 'Calories Burned',
                    data: workoutData.calories,
                    borderColor: '#45ffca',
                    backgroundColor: 'rgba(69,255,202,0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Duration (mins)',
                    data: workoutData.durations,
                    borderColor: '#ff4d4d',
                    backgroundColor: 'rgba(255,77,77,0.1)',
                    tension: 0.4,
                    fill: true,
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
            },
            scales: {
                x: {
                    grid: {
                        color: '#333'
                    },
                    ticks: {
                        color: '#666'
                    }
                },
                y: {
                    grid: {
                        color: '#333'
                    },
                    ticks: {
                        color: '#666'
                    }
                }
            }
        }
    });
}

function initializeCalendar() {
    const calendarData = JSON.parse(document.getElementById('calendar-data').textContent);
    renderCalendar(calendarData);
}

function renderCalendar(calendarData) {
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

document.addEventListener('DOMContentLoaded', () => {
    initializeWorkoutChart();
    initializeCalendar();
});


function refreshDashboardStats() {
    console.log('Refreshing dashboard stats...');

    fetch('/api/dashboard-stats?t=' + Date.now())
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

function updateWorkoutChart(chartData) {
    if (window.workoutChart) {
        window.workoutChart.data.labels = chartData.dates;
        window.workoutChart.data.datasets[0].data = chartData.calories;
        window.workoutChart.data.datasets[1].data = chartData.durations;
        window.workoutChart.update();
    }
}

function fetchDashboardStats() {
    console.log('Fetching fresh dashboard stats...');
    
    document.getElementById('workouts-count').textContent = "...";
    document.getElementById('total-calories').textContent = "...";
    document.getElementById('total-duration').textContent = "...";
    
    fetch('/api/dashboard-stats?' + new URLSearchParams({
        timestamp: Date.now() 
    }))
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('Received fresh stats:', data);
            
            document.getElementById('workouts-count').textContent = data.stats.workouts_count;
            document.getElementById('total-calories').textContent = data.stats.total_calories.toFixed(1);
            document.getElementById('total-duration').textContent = data.stats.total_duration;
            document.querySelector('.streak-counter span').textContent = `${data.stats.streak_count} Day Streak`;

            if (data.workout_data && window.workoutChart) {
                window.workoutChart.data.labels = data.workout_data.dates;
                window.workoutChart.data.datasets[0].data = data.workout_data.calories;
                window.workoutChart.data.datasets[1].data = data.workout_data.durations;
                window.workoutChart.update();
            }
        } else {
            console.error('Failed to get stats:', data.message);
            alert('Failed to update dashboard stats. Please refresh the page.');
        }
    })
    .catch(error => {
        console.error('Error fetching dashboard stats:', error);
        alert('Error updating dashboard stats. Please refresh the page.');
    });
}

document.getElementById('refresh-stats-btn').addEventListener('click', function() {
    fetchDashboardStats();
});