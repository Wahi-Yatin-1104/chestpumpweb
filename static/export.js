document.addEventListener('DOMContentLoaded', function() {
    const formatDate = (date) => date.toISOString().split('T')[0];
    const isPremiumUser = !document.getElementById('premium-export-card')?.classList.contains('locked');

    const fromDateBasic = document.getElementById('from-date-basic');
    const toDateBasic = document.getElementById('to-date-basic');
    if (fromDateBasic && toDateBasic) {
        const todayBasic = new Date();
        const thirtyDaysAgoBasic = new Date();
        thirtyDaysAgoBasic.setDate(todayBasic.getDate() - 30);
        fromDateBasic.value = formatDate(thirtyDaysAgoBasic);
        toDateBasic.value = formatDate(todayBasic);
    }

    const exportBasicButton = document.getElementById('export-basic-button');
    if (exportBasicButton) {
        exportBasicButton.addEventListener('click', exportBasicData);
    }

    const fromDatePdf = document.getElementById('from-date-pdf');
    const toDatePdf = document.getElementById('to-date-pdf');
    if (fromDatePdf && toDatePdf) {
        const todayPdf = new Date();
        const thirtyDaysAgoPdf = new Date();
        thirtyDaysAgoPdf.setDate(todayPdf.getDate() - 30);
        fromDatePdf.value = formatDate(thirtyDaysAgoPdf);
        toDatePdf.value = formatDate(todayPdf);
    }

    const generatePdfButton = document.getElementById('generate-pdf-button');
    const pdfLoadingIndicator = document.getElementById('pdf-loading-indicator');
    const pdfErrorMessage = document.getElementById('pdf-error-message');

    if (generatePdfButton && isPremiumUser) {
        generatePdfButton.addEventListener('click', generatePdfReport);
    }

    const toggleBasicButton = document.getElementById('toggle-basic-export');
    const basicExportSection = document.getElementById('basic-export-collapsible');
    const closeBasicButton = document.getElementById('close-basic-export'); 

    if (toggleBasicButton && basicExportSection && isPremiumUser) {
        basicExportSection.classList.add('hidden');
        basicExportSection.style.display = 'none';

        toggleBasicButton.addEventListener('click', () => {
            const isHidden = basicExportSection.classList.contains('hidden');
            if (isHidden) {
                basicExportSection.style.display = 'block'; 
                setTimeout(() => {
                    basicExportSection.classList.remove('hidden');
                    toggleBasicButton.innerHTML = "<i class='bx bx-x'></i> Hide Raw Data Options";
                 }, 10);
            } else {
                basicExportSection.classList.add('hidden');
                basicExportSection.addEventListener('transitionend', () => {
                    if(basicExportSection.classList.contains('hidden')) {
                         basicExportSection.style.display = 'none';
                    }
                }, { once: true });
                toggleBasicButton.innerHTML = "<i class='bx bx-download'></i> Show Raw Data Options";
            }
        });

         if (closeBasicButton) {
             closeBasicButton.addEventListener('click', () => {
                 if (!basicExportSection.classList.contains('hidden')) {
                     toggleBasicButton.click();
                 }
             });
         }

    } else if (basicExportSection && !isPremiumUser) {
        basicExportSection.classList.remove('hidden');
        basicExportSection.style.display = 'block';
    }

    function exportBasicData() {
        const fromDate = document.getElementById('from-date-basic')?.value;
        const toDate = document.getElementById('to-date-basic')?.value;
        const format = document.querySelector('input[name="basic-format"]:checked')?.value || 'json';
        if (!validateDates(fromDate, toDate)) return;
        const url = `/export-data/download?format=${format}&from=${fromDate}&to=${toDate}`;
        console.log("Exporting basic data with URL:", url);
        window.location.href = url;
    }

    async function generatePdfReport() {
        const fromDate = document.getElementById('from-date-pdf')?.value;
        const toDate = document.getElementById('to-date-pdf')?.value;
        const selectedSections = Array.from(document.querySelectorAll('input[name="sections"]:checked')).map(el => el.value);

        if (!validateDates(fromDate, toDate)) return;
        if (selectedSections.length === 0) {
            displayPdfError("Please select at least one section.");
            return;
        }

        if (generatePdfButton) generatePdfButton.disabled = true;
        if (pdfLoadingIndicator) pdfLoadingIndicator.style.display = 'flex';
        displayPdfError(null);

        try {
            const response = await fetch('/export-data/generate-pdf-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from_date: fromDate,
                    to_date: toDate,
                    sections: selectedSections
                })
            });

            if (!response.ok) {
                let errorMsg = `Failed. Status: ${response.status}`;
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { /* ignore */ }
                throw new Error(errorMsg);
            }

            const contentType = response.headers.get("content-type");
            if (contentType && contentType.includes("application/pdf")) {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = downloadUrl;
                const reportDate = new Date().toISOString().split('T')[0];
                link.setAttribute('download', `Pump_Chest_Report_${reportDate}.pdf`);
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(downloadUrl);
            } else {
                let errorMsg = "Server returned unexpected response.";
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { /* ignore */ }
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('Error generating PDF:', error);
            displayPdfError(error.message || 'An error occurred.');
        } finally {
            if (generatePdfButton) generatePdfButton.disabled = false;
            if (pdfLoadingIndicator) pdfLoadingIndicator.style.display = 'none';
        }
    }

    function validateDates(fromDate, toDate) {
        if (!fromDate || !toDate) { alert("Please select both dates."); return false; }
        if (new Date(fromDate) > new Date(toDate)) { alert("'From' date cannot be after 'To' date."); return false; }
        return true;
    }

    function displayPdfError(message) {
        if (pdfErrorMessage) {
            pdfErrorMessage.textContent = message || '';
            pdfErrorMessage.style.display = message ? 'block' : 'none';
        }
    }
});