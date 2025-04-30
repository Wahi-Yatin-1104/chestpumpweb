let efficiencyChart = null;
let exerciseChart = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    
    setupEventListeners();
    
    setInterval(checkPageGrowth, 1000);
});

function parseDate(dateString) {
    const [year, month, day] = dateString.split('-').map(num => parseInt(num, 10));
    return new Date(year, month - 1, day);
}

function checkPageGrowth() {
    const body = document.body;
    const html = document.documentElement;
    
    const height = Math.max(
        body.scrollHeight, body.offsetHeight,
        html.clientHeight, html.scrollHeight, html.offsetHeight
    );
    
    if (height > 5000) {
        console.log("Detected excessive page height, applying fix");
        document.body.style.height = '100%';
        document.body.style.overflow = 'auto';
        
        const chartContainers = document.querySelectorAll('.chart-card');
        chartContainers.forEach(container => {
            container.style.height = '400px';
            container.style.maxHeight = '400px';
            container.style.overflow = 'hidden';
        });
        
        initializeCharts();
    }
}

function setupEventListeners() {
    const showTrendlineEl = document.getElementById('showTrendline');
    if (showTrendlineEl) {
        showTrendlineEl.addEventListener('change', function() {
            if (efficiencyChart && efficiencyChart.data.datasets.length >= 2) {
                efficiencyChart.data.datasets[1].hidden = !this.checked;
                efficiencyChart.update('none');
            }
        });
    }
    
    const showMovingAverageEl = document.getElementById('showMovingAverage');
    if (showMovingAverageEl) {
        showMovingAverageEl.addEventListener('change', function() {
            if (efficiencyChart && efficiencyChart.data.datasets.length >= 3) {
                efficiencyChart.data.datasets[2].hidden = !this.checked;
                efficiencyChart.update('none');
            }
        });
    }

    const chartMetricEl = document.getElementById('chartMetric');
    if (chartMetricEl) {
        chartMetricEl.addEventListener('change', function() {
            updateExerciseChart(this.value);
        });
    }
    
    const timeRangeFilter = document.getElementById('timeRangeFilter');
    if (timeRangeFilter) {
        timeRangeFilter.addEventListener('change', function() {
            loadAnalyticsData(this.value);
        });
    }
}

function initializeCharts() {
    if (efficiencyChart) {
        efficiencyChart.destroy();
        efficiencyChart = null;
    }
    
    if (exerciseChart) {
        exerciseChart.destroy();
        exerciseChart = null;
    }
    
    const efficiencyCtx = document.getElementById('efficiencyChart');
    if (!efficiencyCtx) return;
    
    efficiencyCtx.height = 300;
    efficiencyCtx.style.height = '300px';
    efficiencyCtx.style.maxHeight = '300px';
    
    const dates = efficiencyData ? efficiencyData.map(workout => workout.date) : [];
    const scores = efficiencyData ? efficiencyData.map(workout => workout.score) : [];
    
    const trendlineData = calculateTrendline(dates.map((_, i) => i), scores);
    
    const movingAvgData = calculateMovingAverage(scores, 3);
    
    efficiencyChart = new Chart(efficiencyCtx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Efficiency Score',
                    data: scores,
                    borderColor: '#45ffca',
                    backgroundColor: 'rgba(69, 255, 202, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Trend Line',
                    data: trendlineData,
                    borderColor: 'rgba(255, 255, 255, 0.5)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                    tension: 0
                },
                {
                    label: 'Moving Average',
                    data: movingAvgData,
                    borderColor: 'rgba(255, 99, 132, 0.7)',
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.2,
                    hidden: false
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
                        color: '#777',
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 17, 17, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#333',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            if (context.dataset.label === 'Efficiency Score') {
                                return `Score: ${context.raw.toFixed(1)}`;
                            }
                            return `${context.dataset.label}: ${context.raw.toFixed(1)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#222'
                    },
                    ticks: {
                        color: '#777'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 10,
                    grid: {
                        color: '#222'
                    },
                    ticks: {
                        color: '#777'
                    }
                }
            },
            animation: false
        }
    });
    
    const exerciseCtx = document.getElementById('exerciseChart');
    if (!exerciseCtx) return;
    
    exerciseCtx.height = 300;
    exerciseCtx.style.height = '300px';
    exerciseCtx.style.maxHeight = '300px';
    
    const exerciseLabels = exerciseComparison ? Object.keys(exerciseComparison) : [];
    const exerciseScores = exerciseLabels.map(exercise => 
        exerciseComparison[exercise].avg_score
    );
    
    exerciseChart = new Chart(exerciseCtx, {
        type: 'bar',
        data: {
            labels: exerciseLabels,
            datasets: [{
                label: 'Average Score',
                data: exerciseScores,
                backgroundColor: '#45ffca',
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#777'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 17, 17, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#333',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#222'
                    },
                    ticks: {
                        color: '#777'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 10,
                    grid: {
                        color: '#222'
                    },
                    ticks: {
                        color: '#777'
                    }
                }
            },
            animation: false
        }
    });
    
    loadAnalyticsData();
}


function loadAnalyticsData(timeRange = 'all') {
    if (isFetching) return;
    isFetching = true;
    
    let url = '/api/workout-efficiency-data';
    if (timeRange && timeRange !== 'all') {
        url += `?days=${timeRange}`;
    }
    
    const loadingIndicator = document.querySelector('.loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }
    
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load analytics data');
            }
            return response.json();
        })
        .then(data => {
            window.efficiencyData = data.detailed_scores || [];
            window.exerciseComparison = data.exercise_comparison || {};
            window.overallStats = data.overall_stats || {};
            
            updateEfficiencyChart(data.detailed_scores);
            
            const metricSelector = document.getElementById('chartMetric');
            const selectedMetric = metricSelector ? metricSelector.value : 'avg_score';
            updateExerciseChart(selectedMetric, data.exercise_comparison);
            
            updateDashboard(data);
            
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            isFetching = false;
        })
        .catch(error => {
            console.error('Error loading analytics data:', error);
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            isFetching = false;
        });
}

let isFetching = false;


function updateDashboard(data) {
    if (!data || !data.overall_stats) return;

    requestAnimationFrame(() => {
        updateTextContent('overall-score', data.overall_stats.avg_score);
        updateTextContent('trend', data.overall_stats.trend);
        updateTextContent('improvement', data.overall_stats.improvement + '%');
        updateTextContent('workouts-count', data.overall_stats.num_workouts);
        const trendElement = document.getElementById('trend');
        const improvementElement = document.getElementById('improvement');
        
        if (trendElement) {
            trendElement.classList.remove('negative', 'positive', 'neutral');
            
            if (data.overall_stats.trend.includes('Declining')) {
                trendElement.classList.add('negative');
                updateTrendIcon('down', 'negative');
            } else if (data.overall_stats.trend.includes('Improving')) {
                trendElement.classList.add('positive');
                updateTrendIcon('up', 'positive');
            } else {
                trendElement.classList.add('neutral');
                updateTrendIcon('right', 'neutral');
            }
        }
        
        if (improvementElement) {
            improvementElement.classList.remove('negative', 'positive', 'neutral');
            
            if (data.overall_stats.improvement < 0) {
                improvementElement.classList.add('negative');
            } else if (data.overall_stats.improvement > 0) {
                improvementElement.classList.add('positive');
                improvementElement.textContent = '+' + data.overall_stats.improvement + '%';
            } else {
                improvementElement.classList.add('neutral');
            }
        }
        
        if (data.overall_stats.r_squared !== undefined) {
            const rSquaredEl = document.getElementById('r-squared');
            if (rSquaredEl) {
                rSquaredEl.textContent = data.overall_stats.r_squared.toFixed(2);
            }
        }
        
        if (data.overall_stats.volatility !== undefined) {
            const volatilityEl = document.getElementById('volatility');
            if (volatilityEl) {
                volatilityEl.textContent = data.overall_stats.volatility.toFixed(1);
            }
        }
        
        if (data.overall_stats.has_plateau !== undefined) {
            const plateauEl = document.getElementById('has-plateau');
            if (plateauEl) {
                plateauEl.textContent = data.overall_stats.has_plateau ? 'Yes' : 'No';
                plateauEl.classList.toggle('alert', data.overall_stats.has_plateau);
            }
        }
        
        safelyUpdateExerciseBreakdown(data);
        
        safelyUpdateRecommendations(data);
        
        safelyUpdateWorkoutDetails(data);
    });
}

window.addEventListener('resize', () => {
    if (window.resizeTimeout) clearTimeout(window.resizeTimeout);
    window.resizeTimeout = setTimeout(() => {
        if (efficiencyChart) efficiencyChart.resize();
        if (exerciseChart) exerciseChart.resize();
    }, 250);
});

function updateTrendIcon(direction, className) {
    const iconElement = document.querySelector('.stat-icon.bx-trending-up, .stat-icon.bx-trending-down, .stat-icon.bx-trending-right');
    if (iconElement) {
        iconElement.className = `bx bx-trending-${direction} stat-icon ${className}`;
    }
}

function updateTextContent(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined) {
        element.textContent = value;
    }
}

function updateEfficiencyChart(detailedScores) {
    if (!efficiencyChart || !detailedScores || !detailedScores.length) return;

    const sortedScores = [...detailedScores].sort((a, b) => {
        return new Date(a.date) - new Date(b.date);
    });
    
    const dates = sortedScores.map(score => score.date);
    const scores = sortedScores.map(score => score.score);
    
    const trendlineData = calculateTrendline(dates.map((_, i) => i), scores);

    const movingAvgData = calculateMovingAverage(scores, 3);

    efficiencyChart.data.labels = dates;
    efficiencyChart.data.datasets[0].data = scores;

    if (efficiencyChart.data.datasets.length > 1) {
        efficiencyChart.data.datasets[1].data = trendlineData;
    }

    if (efficiencyChart.data.datasets.length > 2) {
        efficiencyChart.data.datasets[2].data = movingAvgData;
    }

    efficiencyChart.update('none');
}