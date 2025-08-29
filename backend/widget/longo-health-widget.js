// Longo Sağlık Asistanı - Güzel Chat Bot
(function() {
    'use strict';
    
    // Widget HTML oluştur
    function createWidget() {
        const widgetHTML = `
            <div id="longo-health-widget">
                <div id="chat-button" onclick="longoToggleChat()" title="Longo Sağlık Asistanı">
                    <img src="longo.jpeg" alt="Longo" class="chat-button-image">
                    <div class="pulse-ring"></div>
                </div>
                
                <div id="longo-chat-window" style="display: none;">
                    <div id="longo-chat-header">
                        <h3>
                            <img src="longo.jpeg" alt="Longo" class="header-longo-icon">
                            Longo Sağlık Asistanı
                        </h3>
                        <button onclick="longoCloseChat()" class="longo-close-btn">✕</button>
                    </div>
                    
                    <div id="longo-chat-messages">
                        <div class="longo-welcome-message">
                            <p>👋 Merhaba! Ben Longo, senin sağlık asistanın</p>
                            <p>💊 Nasıl yardımcı olabilirim?</p>
                            
                        </div>
                        
                        <!-- Longo Karakteri -->
                        <div class="longo-character-area">
                            <div class="longo-character">
                                <img src="longo.jpeg" alt="Longo AI Asistan" class="longo-image">
                            </div>
                            <div class="longo-character-text">Longo AI Asistan</div>
                        </div>
                    </div>
                    
                    <div id="longo-chat-input">
                        <input type="text" id="longo-message-input" placeholder="Mesajınızı yazın..." onkeypress="longoHandleKeyPress(event)">
                        <button onclick="longoSendMessage()" class="longo-send-btn">
                            <span>Gönder</span>
                            <div class="btn-ripple"></div>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        
        // Pulse animasyonu başlat
        startPulseAnimation();
    }
    
    // Pulse animasyonu
    function startPulseAnimation() {
        const pulseRing = document.querySelector('.pulse-ring');
        if (pulseRing) {
            setInterval(() => {
                pulseRing.style.animation = 'pulse 2s infinite';
            }, 3000);
        }
    }
    
    // Chat toggle
    window.longoToggleChat = function() {
        const chatWindow = document.getElementById('longo-chat-window');
        const isVisible = chatWindow.style.display === 'block';
        
        if (isVisible) {
            longoCloseChat();
        } else {
            longoOpenChat();
        }
    };
    
    // Chat aç
    function longoOpenChat() {
        const chatWindow = document.getElementById('longo-chat-window');
        chatWindow.style.display = 'block';
        
        // Animasyon için
        setTimeout(() => {
            chatWindow.style.opacity = '1';
            chatWindow.style.transform = 'translateY(0) scale(1)';
        }, 10);
        
        document.getElementById('longo-message-input').focus();
    };
    
    // Chat kapat
    window.longoCloseChat = function() {
        const chatWindow = document.getElementById('longo-chat-window');
        chatWindow.style.opacity = '0';
        chatWindow.style.transform = 'translateY(30px) scale(0.9)';
        
        setTimeout(() => {
            chatWindow.style.display = 'none';
        }, 300);
    };
    
    // Enter tuşu ile mesaj gönder
    window.longoHandleKeyPress = function(event) {
        if (event.key === 'Enter') {
            longoSendMessage();
        }
    };
    
    // Typing indicator göster
    function showTypingIndicator() {
        const messagesDiv = document.getElementById('longo-chat-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'longo-message assistant typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <div class="typing-text">Longo yazıyor...</div>
        `;
        messagesDiv.appendChild(typingDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    // Typing indicator'ı kaldır
    function longoRemoveTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Mesaj gönder
    window.longoSendMessage = async function() {
        const input = document.getElementById('longo-message-input');
        const message = input.value.trim();
        if (!message) return;
        
        // Mesajı göster
        longoAddMessage('user', message);
        input.value = '';
        
        // Input'u devre dışı bırak
        input.disabled = true;
        
        // Typing effect göster
        showTypingIndicator();
        
        // API'ye gönder
        try {
            const response = await fetch('https://longo-ai.onrender.com/ai/chat', {
                method: 'POST',
                headers: {
                    'username': 'longopass',
                    'password': '123456',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conv_id: 1
                })
            });
            
            const result = await response.json();
            
            // Typing effect'i kaldır
            longoRemoveTypingIndicator();
            
            // AI yanıtını göster
            longoAddMessage('assistant', result.reply);
            
        } catch (error) {
            longoRemoveTypingIndicator();
            longoAddMessage('assistant', '❌ Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.');
        } finally {
            // Input'u tekrar aktif et
            input.disabled = false;
            input.focus();
        }
    };
    
    // Mesaj ekle
    function longoAddMessage(role, content, type = 'normal') {
        const messagesDiv = document.getElementById('longo-chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `longo-message ${role} ${type}`;
        messageDiv.innerHTML = `<p>${content}</p>`;
        
        // Başlangıçta görünmez yap
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        
        messagesDiv.appendChild(messageDiv);
        
        // Animasyon ile göster
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 100);
        
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    // Loading mesajını kaldır
    function longoRemoveLoadingMessage() {
        const loadingMessage = document.querySelector('.longo-message.loading');
        if (loadingMessage) {
            loadingMessage.style.opacity = '0';
            loadingMessage.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                if (loadingMessage.parentNode) {
                    loadingMessage.remove();
                }
            }, 300);
        }
    }
    
    // Widget'ı başlat
    createWidget();
    
})();
