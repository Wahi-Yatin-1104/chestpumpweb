document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    const formatDate = (date) => date.toISOString().split('T')[0];
    document.getElementById('to-date').value = formatDate(today);
    document.getElementById('from-date').value = formatDate(thirtyDaysAgo);

    const exportButton = document.getElementById('export-button');
    if (exportButton) {
        exportButton.addEventListener('click', exportData);
    } else {
        console.error("Export button not found.");
    }
});

function exportData() {
    const fromDate = document.getElementById('from-date').value;
    const toDate = document.getElementById('to-date').value;
    const format = document.querySelector('input[name="format"]:checked')?.value || 'json';

    if (!fromDate || !toDate) {
        alert("Please select both a start and end date.");
        return;
    }
    if (new Date(fromDate) > new Date(toDate)) {
        alert("The 'From' date cannot be after the 'To' date.");
        return;
    }

    const url = `/export-data/download?format=${format}&from=${fromDate}&to=${toDate}`;
    console.log("Exporting data with URL:", url);
    window.location.href = url;
}
