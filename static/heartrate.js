class PolarH10 {
    constructor() {
        this.device = null;
        this.server = null;
        this.service = null;
        this.characteristic = null;
    }

    async connect() {
        try {
            this.device = await navigator.bluetooth.requestDevice({
                filters: [{ services: ['heart_rate'] }],
                optionalServices: ['battery_service']
            });

            this.server = await this.device.gatt.connect();
            this.service = await this.server.getPrimaryService('heart_rate');
            this.characteristic = await this.service.getCharacteristic('heart_rate_measurement');
            
            await this.startNotifications();
        } catch (error) {
            console.error('Connection failed:', error);
        }
    }

    async startNotifications() {
        await this.characteristic.startNotifications();
        this.characteristic.addEventListener('characteristicvaluechanged', this.handleHeartRate);
    }

    handleHeartRate(event) {
        const value = event.target.value;
        const heartRate = value.getUint8(1);
        document.getElementById('heart-rate').textContent = heartRate;
    }

    disconnect() {
        if (this.device && this.device.gatt.connected) {
            this.device.gatt.disconnect();
        }
    }
}