document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    document.getElementById('to-date').valueAsDate = today;
    document.getElementById('from-date').valueAsDate = thirtyDaysAgo;
    document.getElementById('export-button').addEventListener('click', exportData);
    document.getElementById('generate-link-button').addEventListener('click', generateShareLink);
    document.getElementById('copy-link')?.addEventListener('click', copyShareLink);
});

function exportData() {
    const fromDate = document.getElementById('from-date').value;
    const toDate = document.getElementById('to-date').value;
    const format = document.querySelector('input[name="format"]:checked').value;
    const url = `/api/export-data?format=${format}&from=${fromDate}&to=${toDate}`;
    window.location.href = url;
}

async function generateShareLink() {
    try {
        const fromDate = document.getElementById('from-date').value;
        const toDate = document.getElementById('to-date').value;
        const response = await fetch('/api/generate-share-link', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                from: fromDate,
                to: toDate,
                expires: 7
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate shareable link');
        }
        
        const data = await response.json();
        const container = document.getElementById('share-link-container');
        container.style.display = 'block';
        document.getElementById('share-link').value = data.url || 
            `${window.location.origin}/shared-fitness-data?token=DEMO_TOKEN_${Date.now()}`;
        
        container.scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('Error generating link:', error);
        alert('Failed to generate shareable link. Please try again.');
    }
}

function copyShareLink() {
    const linkInput = document.getElementById('share-link');
    linkInput.select();
    document.execCommand('copy');
    const copyBtn = document.getElementById('copy-link');
    const originalHTML = copyBtn.innerHTML;
    copyBtn.innerHTML = '<i class="bx bx-check"></i>';

    setTimeout(() => {
        copyBtn.innerHTML = originalHTML;
    }, 2000);
}