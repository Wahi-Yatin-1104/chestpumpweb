window.currentCalendarDate = new Date();

function previousMonth() {
    window.currentCalendarDate = new Date(
        window.currentCalendarDate.getFullYear(),
        window.currentCalendarDate.getMonth() - 1, 
        1
    );
    updateCalendarDisplay();
}

function nextMonth() {
    window.currentCalendarDate = new Date(
        window.currentCalendarDate.getFullYear(),
        window.currentCalendarDate.getMonth() + 1, 
        1
    );
    updateCalendarDisplay();
}

function currentMonth() {
    window.currentCalendarDate = new Date();
    updateCalendarDisplay();
}

function updateCalendarDisplay() {
    const current = window.currentCalendarDate;
    document.getElementById('currentMonth').textContent = current.toLocaleString('default', { month: 'long' });
    document.getElementById('currentYear').textContent = current.getFullYear();
    
    try {
        const calendarData = JSON.parse(document.getElementById('calendar-data').textContent);
        renderCalendar(calendarData);
    } catch (e) {
        console.error("Error updating calendar:", e);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    updateCalendarDisplay();
}); 