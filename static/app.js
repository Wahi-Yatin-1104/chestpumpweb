function startWorkout() {
    fetch("/start_workout", { method: "POST" })
        .then(response => response.json())
        .then(data => alert(data.message));
}

function stopWorkout() {
    fetch("/stop_workout", { method: "POST" })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            console.log(data.data);
        });
}

function updateTracker() {
    fetch("/process_frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
    })
        .then(response => response.json())
        .then(data => {
            document.getElementById("reps").innerText = data.reps;
            document.getElementById("calories").innerText = data.calories.toFixed(2);
            document.getElementById("warnings").innerText = data.warnings;
            document.getElementById("mode").innerText = data.mode;
        });
}

setInterval(updateTracker, 2000);
