document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadPanel = document.getElementById('upload-panel');
    
    // Processing UI Elements
    const processingState = document.getElementById('processing-state');
    const progressFill = document.getElementById('progress-fill');
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const step3 = document.getElementById('step-3');
    
    // Results UI Elements
    const resultsPanel = document.getElementById('results-panel');
    const resetBtn = document.getElementById('reset-btn');
    const resReqId = document.getElementById('res-req-id');
    const resTime = document.getElementById('res-time');
    const resStatus = document.getElementById('res-status');
    
    // Code blocks
    const codeFinal = document.getElementById('code-final');
    const codeCleaned = document.getElementById('code-cleaned');
    const codeRaw = document.getElementById('code-raw');
    
    // Toast
    const errorToast = document.getElementById('error-toast');
    const toastMessage = document.getElementById('toast-message');

    // Drag and Drop Events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    // Handle File Drop
    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    }

    // Handle File Input Selection
    fileInput.addEventListener('change', function(e) {
        if (this.files && this.files.length > 0) {
            handleFile(this.files[0]);
        }
    });

    // Validate and process file
    function handleFile(file) {
        const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
        
        if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|png|jpe?g)$/i)) {
            showError("Please upload a supported format (.pdf, .png, .jpg)");
            return;
        }

        startProcessingUI();
        uploadFile(file);
    }

    // API Upload Function
    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Simulated steps visual only, since we wait for a single endpoint to return
            simulateSteps();

            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || data.error || 'Failed to process document');
            }

            // Finish up actual steps immediately 
            completeSteps();
            
            // Short delay to let user see "completed" state before switching
            setTimeout(() => {
                showResults(data);
            }, 800);

        } catch (error) {
            resetUI();
            showError(error.message);
        }
    }

    // UI State Functions
    let fakeStepInterval;
    
    function startProcessingUI() {
        dropZone.classList.add('hidden');
        processingState.classList.remove('hidden');
        
        // Reset steps
        document.querySelectorAll('.step').forEach(el => {
            el.className = 'step pending';
        });
        progressFill.style.width = '5%';
    }

    function simulateSteps() {
        let currentStep = 1;
        progressFill.style.width = '15%';
        
        fakeStepInterval = setInterval(() => {
            if (currentStep === 1) {
                step1.className = 'step active';
                progressFill.style.width = '30%';
                currentStep++;
            } else if (currentStep === 2) {
                step1.className = 'step completed';
                step2.className = 'step active';
                progressFill.style.width = '60%';
                currentStep++;
            } else if (currentStep === 3) {
                step2.className = 'step completed';
                step3.className = 'step active';
                progressFill.style.width = '85%';
                clearInterval(fakeStepInterval);
            }
        }, 3000); // Fake step roughly every 3s
    }

    function completeSteps() {
        clearInterval(fakeStepInterval);
        step1.className = 'step completed';
        step2.className = 'step completed';
        step3.className = 'step completed';
        progressFill.style.width = '100%';
    }

    function resetUI() {
        clearInterval(fakeStepInterval);
        uploadPanel.style.display = 'block';
        resultsPanel.classList.add('hidden');
        processingState.classList.add('hidden');
        dropZone.classList.remove('hidden');
        fileInput.value = '';
    }

    function showResults(data) {
        uploadPanel.style.display = 'none';
        resultsPanel.classList.remove('hidden');
        
        // Populate metrics
        resReqId.textContent = data.request_id || '-';
        
        if (data.processing_stages) {
            const totalMs = Object.values(data.processing_stages).reduce((a, b) => a + b, 0);
            resTime.textContent = (totalMs / 1000).toFixed(2) + 's';
        } else {
            resTime.textContent = 'N/A';
        }

        if (data.status === 'COMPLETED') {
            resStatus.textContent = 'SUCCESS';
            resStatus.className = 'metric-value status-badge success';
        } else {
            resStatus.textContent = data.status || 'ERROR';
            resStatus.className = 'metric-value status-badge error';
        }

        // Fill JSONs
        codeFinal.textContent = JSON.stringify(data.final_invoice, null, 2) || '{}';
        codeCleaned.textContent = JSON.stringify(data.cleaned_data, null, 2) || '{}';
        codeRaw.textContent = typeof data.raw_extraction === 'string' ? data.raw_extraction : JSON.stringify(data.raw_extraction, null, 2) || '{}';

        // Apply highlighting
        hljs.highlightElement(codeFinal);
        hljs.highlightElement(codeCleaned);
        hljs.highlightElement(codeRaw);
    }

    // Tabs functionality
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            // Add active to current
            btn.classList.add('active');
            const targetId = `tab-${btn.dataset.tab}`;
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Reset button
    resetBtn.addEventListener('click', resetUI);

    // Error Toast function
    function showError(msg) {
        toastMessage.textContent = msg;
        errorToast.classList.add('show');
        errorToast.classList.remove('hidden');
        
        setTimeout(() => {
            errorToast.classList.remove('show');
            setTimeout(() => {
                errorToast.classList.add('hidden');
            }, 400); // wait for transition
        }, 4000);
    }

});
