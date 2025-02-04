const videoElement = document.getElementById('video');
const canvasElement = document.getElementById('pose-canvas');
const canvasCtx = canvasElement.getContext('2d');

const pose = new Pose({
    locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
    }
});

pose.setOptions({
    modelComplexity: 1,
    smoothLandmarks: true,
    enableSegmentation: false,
    smoothSegmentation: true,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoElement.srcObject = stream;
        videoElement.addEventListener('loadeddata', predictPose);
    } catch (error) {
        console.error("Error accessing webcam:", error);
        alert("Unable to access webcam. Please check permissions.");
    }
}

async function predictPose() {
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    
    async function detect() {
        await pose.send({image: videoElement});
        requestAnimationFrame(detect);
    }
    detect();
}

pose.onResults((results) => {
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    if (results.poseLandmarks) {
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
            { color: '#00FF00', lineWidth: 2 });
        drawLandmarks(canvasCtx, results.poseLandmarks,
            { color: '#FF0000', lineWidth: 1 });
    }
});

window.onload = startCamera;