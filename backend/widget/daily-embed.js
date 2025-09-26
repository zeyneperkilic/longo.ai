/**
 * Longopass Daily.co Video Call Widget
 * Longopass tasarımına uygun, sade ve temiz video call entegrasyonu
 */

(function() {
    'use strict';
    
    // Longopass renk paleti
    const COLORS = {
        primary: '#2F5D83',      // Koyu mavi
        secondary: '#E8F4FD',    // Açık mavi
        accent: '#1E3A5F',       // Daha koyu mavi
        text: '#2D3748',         // Koyu gri
        lightText: '#718096',    // Açık gri
        white: '#FFFFFF',
        success: '#38A169',
        warning: '#D69E2E',
        error: '#E53E3E'
    };
    
    let dailyFrame = null;
    let modalOverlay = null;
    let isDailyLoaded = false;
    
    // Daily.co JS'i dinamik yükle
    function loadDailyJS() {
        if (isDailyLoaded) return Promise.resolve();
        
        return new Promise((resolve, reject) => {
            if (window.DailyIframe) {
                isDailyLoaded = true;
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/@daily-co/daily-js@latest/dist/daily-iframe.js';
            script.onload = () => {
                isDailyLoaded = true;
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    // CSS stillerini enjekte et
    function injectStyles() {
        if (document.getElementById('longopass-daily-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'longopass-daily-styles';
        style.textContent = `
            .longopass-daily-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .longopass-daily-container {
                width: min(960px, 95vw);
                height: min(640px, 85vh);
                background: ${COLORS.white};
                border-radius: 16px;
                overflow: hidden;
                position: relative;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            }
            
            .longopass-daily-header {
                background: ${COLORS.primary};
                color: ${COLORS.white};
                padding: 16px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .longopass-daily-title {
                font-size: 18px;
                font-weight: 600;
                margin: 0;
            }
            
            .longopass-daily-close {
                background: none;
                border: none;
                color: ${COLORS.white};
                font-size: 24px;
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: background-color 0.2s;
            }
            
            .longopass-daily-close:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            
            .longopass-daily-iframe {
                width: 100%;
                height: calc(100% - 60px);
                border: none;
            }
            
            .longopass-daily-loading {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 200px;
                color: ${COLORS.lightText};
                font-size: 16px;
            }
            
            .longopass-daily-error {
                padding: 20px;
                text-align: center;
                color: ${COLORS.error};
            }
            
            .longopass-daily-button {
                background: ${COLORS.primary};
                color: ${COLORS.white};
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }
            
            .longopass-daily-button:hover {
                background: ${COLORS.accent};
                transform: translateY(-1px);
            }
            
            .longopass-daily-button:disabled {
                background: ${COLORS.lightText};
                cursor: not-allowed;
                transform: none;
            }
            
            .longopass-daily-button:disabled:hover {
                background: ${COLORS.lightText};
                transform: none;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Modal'ı kapat
    function closeModal() {
        if (dailyFrame) {
            try {
                dailyFrame.leave();
                dailyFrame.destroy();
            } catch (e) {
                console.warn('Daily frame kapatma hatası:', e);
            }
            dailyFrame = null;
        }
        
        if (modalOverlay) {
            modalOverlay.remove();
            modalOverlay = null;
        }
        
        document.body.style.overflow = '';
    }
    
    // Video call'ı başlat
    async function startVideoCall(meetingUrl, token = null) {
        try {
            await loadDailyJS();
            
            // Modal oluştur
            modalOverlay = document.createElement('div');
            modalOverlay.className = 'longopass-daily-modal';
            modalOverlay.innerHTML = `
                <div class="longopass-daily-container">
                    <div class="longopass-daily-header">
                        <h3 class="longopass-daily-title">Doktor Görüşmesi</h3>
                        <button class="longopass-daily-close" onclick="window.LongopassDaily.close()">×</button>
                    </div>
                    <div class="longopass-daily-loading">Görüşme başlatılıyor...</div>
                </div>
            `;
            
            document.body.appendChild(modalOverlay);
            document.body.style.overflow = 'hidden';
            
            // Daily iframe oluştur
            const iframeContainer = modalOverlay.querySelector('.longopass-daily-container');
            const loadingDiv = modalOverlay.querySelector('.longopass-daily-loading');
            
            const iframe = document.createElement('iframe');
            iframe.className = 'longopass-daily-iframe';
            iframe.style.display = 'none';
            
            iframeContainer.appendChild(iframe);
            
            // Daily frame oluştur
            dailyFrame = window.DailyIframe.createFrame(iframe, {
                showLeaveButton: true,
                showFullscreenButton: true,
                showLocalVideo: true,
                showParticipantsBar: true,
                showLocalVideo: true,
                showParticipantsBar: true
            });
            
            // Event listener'lar
            dailyFrame.on('joined-meeting', () => {
                console.log('Daily.co meeting joined');
                loadingDiv.style.display = 'none';
                iframe.style.display = 'block';
            });
            
            dailyFrame.on('left-meeting', () => {
                console.log('Daily.co meeting left');
                closeModal();
            });
            
            dailyFrame.on('error', (error) => {
                console.error('Daily.co hatası:', error);
                loadingDiv.innerHTML = `
                    <div class="longopass-daily-error">
                        Görüşme başlatılamadı: ${error.message || 'Bilinmeyen hata'}<br>
                        <button onclick="window.location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #2F5D83; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Tekrar Dene
                        </button>
                    </div>
                `;
            });
            
            // Timeout ekle
            setTimeout(() => {
                if (loadingDiv.style.display !== 'none') {
                    console.log('Daily.co timeout - modal kapanıyor');
                    closeModal();
                }
            }, 10000); // 10 saniye timeout
            
            // Meeting'e katıl
            const joinOptions = { url: meetingUrl };
            if (token) {
                joinOptions.token = token;
            }
            
            await dailyFrame.join(joinOptions);
            
        } catch (error) {
            console.error('Video call başlatma hatası:', error);
            if (modalOverlay) {
                const loadingDiv = modalOverlay.querySelector('.longopass-daily-loading');
                if (loadingDiv) {
                    loadingDiv.innerHTML = `
                        <div class="longopass-daily-error">
                            Görüşme başlatılamadı: ${error.message}
                        </div>
                    `;
                }
            }
        }
    }
    
    // Join endpoint'ine istek at
    async function joinMeeting(meetingId, extraPayload = {}) {
        const config = window.LongopassDailyConfig || {};
        const endpoint = config.joinEndpoint || '/ai/premium-plus/video-call/join';
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'username': 'longopass',
                    'password': '123456',
                    'x-user-id': config.userId || '',
                    'x-user-level': config.userLevel || 3
                },
                body: JSON.stringify({
                    meeting_id: meetingId,
                    ...extraPayload
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.message || 'Join başarısız');
            }
            
            return {
                meetingUrl: data.meetingUrl,
                token: data.token
            };
            
        } catch (error) {
            console.error('Join endpoint hatası:', error);
            throw new Error(`Görüşmeye katılım hatası: ${error.message}`);
        }
    }
    
    // Ana fonksiyon
    function init() {
        // CSS'leri enjekte et
        injectStyles();
        
        // Tüm .lp-join-call butonlarını dinle
        document.addEventListener('click', async (event) => {
            if (!event.target.classList.contains('lp-join-call')) return;
            
            const button = event.target;
            const meetingId = button.getAttribute('data-meeting-id');
            
            if (!meetingId) {
                alert('Meeting ID bulunamadı');
                return;
            }
            
            // Butonu disable et
            button.disabled = true;
            button.textContent = 'Bağlanıyor...';
            
            try {
                // Join endpoint'ine istek at
                const meetingData = await joinMeeting(meetingId);
                
                // Video call'ı başlat
                await startVideoCall(meetingData.meetingUrl, meetingData.token);
                
            } catch (error) {
                alert(error.message);
            } finally {
                // Butonu tekrar enable et
                button.disabled = false;
                button.textContent = 'Görüşmeye Katıl';
            }
        });
    }
    
    // Global API
    window.LongopassDaily = {
        init: init,
        start: startVideoCall,
        close: closeModal,
        join: joinMeeting
    };
    
    // Otomatik başlat
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();
