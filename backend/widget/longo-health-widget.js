
(function() {
    'use strict';
    
    // DOM hazır olunca widget'ı başlat
    function initWidget() {
        // Siteden userLevel gelip gelmediğini kontrol et
        // Ideasoft'ta gerçek değerler gelecek, yoksa guest (null) olarak ayarla
        window.longoUserLevel = window.longoUserLevel || null; // Siteden gelmezse null (guest)
        window.longoRealUserId = window.longoRealUserId || null; // Premium kullanıcılar için gerçek user ID
        
        // User plan'ı user level'a göre otomatik belirle
        if (!window.longoUserLevel || window.longoUserLevel === 1) {
            window.longoUserPlan = 'free';
        } else if (window.longoUserLevel === 2) {
            window.longoUserPlan = 'premium';
        } else if (window.longoUserLevel === 3) {
            window.longoUserPlan = 'premium_plus';
        } else {
            window.longoUserPlan = 'free'; // Default fallback
        }
    
    // CSS Stillerini ekle
    const widgetStyles = `
        <style>
        
        

        #longo-health-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            -webkit-text-size-adjust: 100%;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* Widget kapsami: kutu modelini sabitle */
        #longo-health-widget, #longo-health-widget * {
            box-sizing: border-box !important;
        }

        /* Tema cakismalarini engelle: input & button reset */
        #longo-health-widget input, #longo-health-widget button {
            -webkit-appearance: none !important;
            appearance: none !important;
            line-height: 1 !important;
            font-size: 15px !important;
            border-radius: 30px !important;
        }

        
        #chat-button {
            width: 70px;
            height: 70px;
            background: transparent;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 8px 32px rgba(47, 93, 131, 0.4);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            color: white;
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 10002;
            overflow: hidden;
            border: none;
            backdrop-filter: blur(10px);
        }

        #chat-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.6s;
        }

        #chat-button:hover::before {
            left: 100%;
        }

        /* Tooltip baloncuk - HTML element olarak */
        .longo-tooltip {
            position: fixed !important;
            bottom: 60px !important;
            right: 100px !important;
            background: #2F5D83 !important;
            color: white !important;
            padding: 10px 15px !important;
            border-radius: 15px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
            opacity: 1 !important;
            visibility: visible !important;
            z-index: 99999 !important;
            box-shadow: 0 4px 15px rgba(47, 93, 131, 0.5) !important;
            border: 2px solid #4A7C9A !important;
            pointer-events: none !important;
            max-width: 180px !important;
            text-align: center !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            word-wrap: break-word !important;
        }

        /* Düşünce balonu ok işareti */
        .longo-tooltip::after {
            content: '' !important;
            position: absolute !important;
            right: -8px !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            width: 0 !important;
            height: 0 !important;
            border-left: 8px solid #2F5D83 !important;
            border-top: 8px solid transparent !important;
            border-bottom: 8px solid transparent !important;
        }

        #chat-button:hover {
            transform: scale(1.1) rotate(5deg);
            box-shadow: 0 15px 40px rgba(47, 93, 131, 0.6);
            border-color: rgba(255, 255, 255, 0.5);
        }

        #chat-button:active {
            transform: scale(0.95);
        }

        .chat-button-image {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            object-fit: cover;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
            z-index: 2;
            position: relative;
            border: none;
        }

        /* Chat Window - Kahve.com Glassmorphism */
        #longo-chat-window {
            position: fixed;
            bottom: 100px;
            right: 20px;
            width: 400px;
            height: min(600px, calc(100vh - 120px));
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(35px);
            border-radius: 25px;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.15);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: slideIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 10001;
        }

        /* Chat Header - Şeffaf ve Modern - SABİT */
        #longo-chat-header {
            background: linear-gradient(135deg, rgba(47, 93, 131, 0.95) 0%, rgba(74, 124, 154, 0.95) 100%);
            backdrop-filter: blur(20px);
            color: white;
            padding: 18px 25px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 10;
            overflow: hidden;
            border-bottom: 1px solid rgba(255, 255, 255, 0.3);
            flex-shrink: 0;
        }

        #longo-chat-header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
            animation: float 8s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-15px) rotate(180deg); }
        }

        #longo-chat-header h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 700;
            text-shadow: 0 2px 8px rgba(0,0,0,0.3);
            position: relative;
            z-index: 1;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-longo-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }

        .longo-close-btn {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 10px;
            border-radius: 50%;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            position: relative;
            z-index: 1;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .longo-close-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.1) rotate(90deg);
            border-color: rgba(255, 255, 255, 0.4);
        }
        
        /* Plan Badge Stilleri */
        .plan-badge {
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 10px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .plan-badge.free {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
            border-color: rgba(255, 193, 7, 0.5);
        }
        
        .plan-badge.premium {
            background: rgba(156, 39, 176, 0.2);
            color: #9c27b0;
            border-color: rgba(156, 39, 176, 0.5);
        }
        
        .plan-badge.premium-plus {
            background: rgba(255, 87, 34, 0.2);
            color: #ff5722;
            border-color: rgba(255, 87, 34, 0.5);
        }
        
        /* Mini Limit Popup Stilleri (Chatbot'un üstünde) */
        .limit-popup-mini {
            position: fixed;
            bottom: 200px;
            right: 20px;
            z-index: 10004;
            animation: slideInRight 0.3s ease;
        }
        
        .limit-popup-content-mini {
            background: linear-gradient(135deg, #2F5D83 0%, #4A7C9A 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(47, 93, 131, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(15px);
            display: flex;
            align-items: center;
            gap: 12px;
            max-width: 300px;
        }
        
        .limit-popup-icon {
            font-size: 24px;
            flex-shrink: 0;
        }
        
        .limit-popup-text {
            flex: 1;
        }
        
        .limit-popup-text h4 {
            margin: 0 0 5px 0;
            font-size: 14px;
            font-weight: 600;
        }
        
        .limit-popup-text p {
            margin: 0;
            font-size: 12px;
            opacity: 0.9;
            line-height: 1.3;
        }
        
        /* Premium'a geç butonu kaldırıldı */
        
        .limit-popup-close {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            font-size: 14px;
            cursor: pointer;
            padding: 6px;
            border-radius: 50%;
            transition: all 0.3s ease;
            flex-shrink: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .limit-popup-close:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.1);
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(100px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        /* Eski popup buton stilleri kaldırıldı */
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(50px) scale(0.9);
            }
            to { 
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        /* Chat Messages - Şeffaf Arka Plan - SCROLL EDİLEBİLİR */
        #longo-chat-messages {
            flex: 1;
            padding: 20px;
            padding-bottom: 130px; /* Disclaimer için daha fazla yer */
            overflow-y: auto;
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(25px);
            min-height: 0;
            height: calc(100% - 80px); /* Header yüksekliğini çıkar */
            scrollbar-width: thin;
            scrollbar-color: rgba(47, 93, 131, 0.5) transparent;
        }

        /* Webkit scrollbar stilleri */
        #longo-chat-messages::-webkit-scrollbar {
            width: 6px;
        }

        #longo-chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }

        #longo-chat-messages::-webkit-scrollbar-thumb {
            background: rgba(47, 93, 131, 0.5);
            border-radius: 3px;
        }

        #longo-chat-messages::-webkit-scrollbar-thumb:hover {
            background: rgba(47, 93, 131, 0.7);
        }

        .longo-welcome-message {
            text-align: center;
            color: #1e293b;
            margin-bottom: 20px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            border: 1px solid rgba(59, 130, 246, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .longo-welcome-message p {
            margin: 10px 0;
            font-size: 16px;
            line-height: 1.6;
            color: #334155;
            font-weight: 500;
        }

        /* Longo Karakteri Alanı */
        .longo-character-area {
            text-align: center;
            margin: 15px 0;
            padding: 15px;
        }

        .longo-character {
            width: 80px;
            height: 80px;
            margin: 0 auto 15px;
            background: linear-gradient(135deg, #4A7C9A 0%, #2F5D83 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 25px rgba(47, 93, 131, 0.4);
            animation: longoFloat 3s ease-in-out infinite;
            overflow: hidden;
            border: 3px solid rgba(255, 255, 255, 0.3);
        }

        .longo-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 50%;
            transition: transform 0.3s ease;
        }

        .longo-character:hover .longo-image {
            transform: scale(1.1);
        }

        @keyframes longoFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        .longo-character-text {
            font-size: 14px;
            color: #64748b;
            font-weight: 500;
        }

        /* Message Bubbles - Kahve.com Stilinde */
        .longo-message {
            margin: 20px 0;
            padding: 18px 24px;
            border-radius: 25px;
            max-width: 85%;
            word-wrap: break-word;
            position: relative;
            animation: messageSlide 0.4s ease;
            backdrop-filter: blur(10px);
        }

        @keyframes messageSlide {
            from {
                opacity: 0;
                transform: translateY(20px) scale(0.9);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        .longo-message.user {
            background: linear-gradient(135deg, rgba(47, 93, 131, 0.9) 0%, rgba(74, 124, 154, 0.9) 100%);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 10px;
            box-shadow: 0 8px 25px rgba(47, 93, 131, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .longo-message.assistant {
            background: rgba(255, 255, 255, 0.9);
            color: #1e293b;
            border: 1px solid rgba(59, 130, 246, 0.15);
            margin-right: auto;
            border-bottom-left-radius: 10px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }

        .longo-message.loading {
            background: rgba(255, 255, 255, 0.8);
            color: #64748b;
            font-style: italic;
            border: 1px solid rgba(59, 130, 246, 0.2);
            backdrop-filter: blur(15px);
        }

        .longo-message p {
            margin: 0;
            font-size: 15px;
            line-height: 1.6;
            font-weight: 500;
        }

        /* Chat Input - Şeffaf ve Modern - SABİT */
        #longo-chat-input {
            padding: 25px 30px 15px 30px; /* Alt padding azaltıldı */
            background: rgba(255, 255, 255, 0.05);
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            display: flex;
            flex-direction: column;
            align-items: center; /* Safari dikey hizalama */
            gap: 10px; /* Gap azaltıldı */
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 10;
            flex-shrink: 0;
            min-height: 120px; /* Minimum yükseklik eklendi */
        }
        
        /* Input ve button container */
        .input-container {
            display: flex;
            align-items: center;
            gap: 15px;
            width: 100%;
        }
        
        /* Disclaimer Stilleri */
        .longo-disclaimer {
            font-size: 9px; /* 10px'den 9px'e küçültüldü */
            color: #1e293b; /* Siyah renk */
            text-align: center;
            margin-top: 3px; /* 5px'den 3px'e küçültüldü */
            line-height: 1.2; /* 1.3'ten 1.2'ye küçültüldü */
            font-weight: 500; /* 600'den 500'e küçültüldü */
            opacity: 0.8; /* 1'den 0.8'e küçültüldü */
            max-width: 100%;
            word-wrap: break-word;
            padding: 0 5px; /* 0 10px'den 0 5px'e küçültüldü */
            z-index: 11;
            position: relative;
            background: transparent; /* Arka plan kaldırıldı */
            border-radius: 0; /* Border radius kaldırıldı */
            padding: 2px 4px; /* 4px 8px'den 2px 4px'e küçültüldü */
            backdrop-filter: none; /* Backdrop filter kaldırıldı */
            border: none; /* Border kaldırıldı */
        }

        #longo-message-input {
            flex: 1;
            padding: 0 24px;
            height: 48px; /* butonla hizalı sabit yükseklik */
            border: 2px solid rgba(59, 130, 246, 0.3);
            border-radius: 30px;
            font-size: 15px;
            outline: none;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            color: #1e293b;
            font-weight: 500;
            box-sizing: border-box; /* Safari padding-border hesaplaması */
        }

        #longo-message-input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
            background: white;
            transform: scale(1.02);
        }

        .longo-send-btn {
            background: linear-gradient(135deg, #2F5D83 0%, #4A7C9A 100%);
            color: white;
            border: none;
            padding: 0 26px;
            border-radius: 30px;
            cursor: pointer;
            font-weight: 600;
            font-size: 15px;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(47, 93, 131, 0.3);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
            /* Safari/iOS uyumluluğu */
            -webkit-appearance: none;
            appearance: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            height: 48px;
            line-height: 1;
            -webkit-font-smoothing: antialiased;
            box-sizing: border-box;
            min-width: 96px; /* label kesilmesini engelle */
        }

        .longo-send-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.6s;
        }

        .longo-send-btn:hover::before {
            left: 100%;
        }

        .longo-send-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(47, 93, 131, 0.5);
            border-color: rgba(255, 255, 255, 0.4);
        }

        .longo-send-btn:active {
            transform: translateY(-1px);
        }

        /* Typing Indicator - Kahve.com Stilinde */
        .typing-indicator {
            background: rgba(255, 255, 255, 0.9) !important;
            border: 1px solid rgba(59, 130, 246, 0.2) !important;
            backdrop-filter: blur(15px) !important;
        }

        .typing-dots {
            display: flex;
            gap: 6px;
            justify-content: center;
            align-items: center;
            height: 24px;
        }

        .typing-dots span {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            animation: typing 1.6s infinite ease-in-out;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
        }

        .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
        .typing-dots span:nth-child(3) { animation-delay: 0s; }

        @keyframes typing {
            0%, 80%, 100% {
                transform: scale(0.8);
                opacity: 0.5;
            }
            40% {
                transform: scale(1.2);
                opacity: 1;
            }
        }

        .typing-text {
            margin-top: 8px;
            font-size: 12px;
            color: #64748b;
            font-style: italic;
            text-align: center;
        }

        /* Pulse Ring Animation - Gelişmiş */
        .pulse-ring {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 100%;
            height: 100%;
            border: 3px solid rgba(59, 130, 246, 0.4);
            opacity: 0;
            animation: pulse 2.5s infinite;
        }

        @keyframes pulse {
            0% {
                transform: translate(-50%, -50%) scale(1);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.8);
                opacity: 0;
            }
        }

        /* Button Ripple Effect */
        .btn-ripple {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.4);
            transition: width 0.8s, height 0.8s;
        }

        .longo-send-btn:active .btn-ripple {
            width: 400px;
            height: 400px;
        }

        /* Enhanced Hover Effects */
        #chat-button:hover .pulse-ring {
            animation: none;
            opacity: 0;
        }

        .longo-message.user:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 12px 35px rgba(47, 93, 131, 0.4);
        }

        .longo-message.assistant:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15);
        }

        /* Focus Effects */
        #longo-message-input:focus {
            transform: scale(1.02);
        }

        /* Smooth Scrolling */
        #longo-chat-messages {
            scroll-behavior: smooth;
        }

        /* Loading State Enhancements */
        .longo-message.loading {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(59, 130, 246, 0.2);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(15px);
        }

        .longo-message.loading::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.15), transparent);
            animation: loadingShimmer 2s infinite;
        }

        @keyframes loadingShimmer {
            0% { left: -100%; }
            100% { left: 100%; }
        }

        /* Scrollbar Styling - Modern ve Belirgin */
        #longo-chat-messages::-webkit-scrollbar {
            width: 16px;
        }

        #longo-chat-messages::-webkit-scrollbar-track {
            background: rgba(47, 93, 131, 0.25);
            border-radius: 8px;
            margin: 5px;
        }

        #longo-chat-messages::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #2F5D83 0%, #4A7C9A 100%);
            border-radius: 8px;
            border: 3px solid rgba(255,255,255,0.9);
            box-shadow: 0 2px 8px rgba(47, 93, 131, 0.4);
        }

        #longo-chat-messages::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, #1e4a6b 0%, #2F5D83 100%);
            box-shadow: 0 4px 12px rgba(47, 93, 131, 0.6);
            transform: scale(1.1);
        }

        /* Firefox için scrollbar */
        #longo-chat-messages {
            scrollbar-width: thin;
            scrollbar-color: #2F5D83 rgba(47, 93, 131, 0.15);
        }

        /* Responsive Design */
        @media (max-width: 480px) {
            #longo-chat-window {
                width: 360px;
                height: min(600px, calc(100vh - 120px));
                right: 10px;
            }
            
            #longo-chat-window {
                bottom: 90px;
            }
            
            .longo-character {
                width: 60px;
                height: 60px;
            }
        }

        /* Smooth Transitions */
        * {
            transition: all 0.3s ease;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(30px) scale(0.9);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        </style>
    `;
    
    // CSS'i head'e ekle
    document.head.insertAdjacentHTML('beforeend', widgetStyles);
    
    // Session-based user ID yönetimi
    function getSessionUserId() {
        let userId = sessionStorage.getItem('longo_session_user_id');
        if (!userId) {
            userId = 'session-user-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('longo_session_user_id', userId);
        }
        return userId;
    }
    
    // Chat için user ID seçimi (Free: Session ID, Premium: Real ID)
    function getUserIdForChat() {
        const userPlan = window.longoUserPlan || 'free';
        
        if (userPlan === 'free') {
            return getSessionUserId(); // Session-based ID
        } else {
            return window.longoRealUserId; // Gerçek user ID
        }
    }
    
    // Widget HTML oluştur
    function createWidget() {
        const widgetHTML = `
            <div id="longo-health-widget">
                <div class="longo-tooltip">Nasıl yardımcı olabilirim?</div>
                <div id="chat-button" onclick="longoToggleChat()" title="Longo Sağlık Asistanı">
                    <img src="https://longo-ai.onrender.com/widget/longo.jpeg" alt="Longo" class="chat-button-image">
                    <div class="pulse-ring"></div>
                </div>
                
                <div id="longo-chat-window" style="display: none;">
                    <div id="longo-chat-header">
                        <h3>
                            <img src="https://longo-ai.onrender.com/widget/longo.jpeg" alt="Longo" class="header-longo-icon">
                            LONGO AI
                        </h3>
                        <button onclick="longoCloseChat()" class="longo-close-btn">✕</button>
                    </div>
                    
                    <div id="longo-chat-messages">
                        <div class="longo-welcome-message">
                            <p>Merhaba! Ben Longo, sağlık asistanın.</p>
                            <p>Nasıl yardımcı olabilirim?</p>
                            
                            
                        </div>
                        
                        <!-- Longo Karakteri -->
                        <div class="longo-character-area">
                            <div class="longo-character">
                                <img src="https://longo-ai.onrender.com/widget/longo.jpeg" alt="Longo AI Asistan" class="longo-image">
                            </div>
                            <div class="longo-character-text"></div>
                        </div>
                    </div>
                    
                    <div id="longo-chat-input">
                        <div class="input-container">
                            <input type="text" id="longo-message-input" placeholder="Mesajınızı yazın..." onkeypress="longoHandleKeyPress(event)">
                            <button onclick="longoSendMessage()" class="longo-send-btn">
                                <span>Gönder</span>
                                <div class="btn-ripple"></div>
                            </button>
                        </div>
                        <div class="longo-disclaimer">
                            Longo yapay zeka desteklidir. Öneriler için doktorunuza danışınız.
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        
        // Pulse animasyonu başlat
        startPulseAnimation();
        
        // Plan bilgisini güncelle
        updatePlanDisplay(window.longoUserPlan || 'free');
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
        // Kullanıcı planını kontrol et (Ideasoft'tan gelecek)
        const userPlan = window.longoUserPlan || 'free';
        const isPremium = userPlan === 'premium' || userPlan === 'premium_plus';
        
        const chatWindow = document.getElementById('longo-chat-window');
        const isVisible = chatWindow.style.display === 'block';
        
        if (isVisible) {
            longoCloseChat();
        } else {
            longoOpenChat();
        }
        
        // Plan bilgisini header'da göster
        updatePlanDisplay(userPlan);
    };
    
    // Plan bilgisini header'da güncelle
    function updatePlanDisplay(userPlan) {
        // Plan badge'leri gizli tutuluyor
        // Sadece popup'ta plan bilgisi gösteriliyor
    }
    
    // Free kullanıcılar için limit popup'ı göster (Chatbot'un üstünde küçük)
    window.showLimitPopup = function() {
        const existingPopup = document.getElementById('limit-popup');
        if (existingPopup) {
            existingPopup.remove();
        }
        
        const popupHTML = `
            <div id="limit-popup" class="limit-popup-mini">
                <div class="limit-popup-content-mini">
                    <div class="limit-popup-icon">🎯</div>
                    <div class="limit-popup-text">
                        <h4>Günlük limit doldu!</h4>
                        <p>Yarın tekrar konuşmaya devam edebilirsiniz</p>
                    </div>
                    <button onclick="closeLimitPopup()" class="limit-popup-close">✕</button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', popupHTML);
        
        // 5 saniye sonra otomatik kapat
        setTimeout(() => {
            closeLimitPopup();
        }, 5000);
    }
    
    // Limit popup'ını kapat
    window.closeLimitPopup = function() {
        const popup = document.getElementById('limit-popup');
        if (popup) {
            popup.remove();
        }
    };
    
    // Premium'a geç fonksiyonu kaldırıldı
    
    // Chat butonunu her zaman görünür tut
    function keepChatButtonVisible() {
        const chatButton = document.getElementById('chat-button');
        if (chatButton) {
            chatButton.style.display = 'flex';
            chatButton.style.visibility = 'visible';
        }
    }
    
    // Chat aç
    function longoOpenChat() {
        const chatWindow = document.getElementById('longo-chat-window');
        chatWindow.style.display = 'block';
        
        // Tooltip'i gizle
        const tooltip = document.querySelector('.longo-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
        
        // Animasyon için
        setTimeout(() => {
            chatWindow.style.opacity = '1';
            chatWindow.style.transform = 'translateY(0) scale(1)';
        }, 10);
        
        // Chat butonunu her zaman görünür tut
        keepChatButtonVisible();
        
        // Free kullanıcılar için session history'yi yükle
        if (window.longoUserPlan === 'free' || !window.longoUserPlan) {
            loadSessionChatHistory();
        }
        
        document.getElementById('longo-message-input').focus();
    };
    
    // Chat kapat
    window.longoCloseChat = function() {
        const chatWindow = document.getElementById('longo-chat-window');
        chatWindow.style.opacity = '0';
        chatWindow.style.transform = 'translateY(30px) scale(0.9)';
        
        setTimeout(() => {
            chatWindow.style.display = 'none';
            
            // Tooltip'i göster
            const tooltip = document.querySelector('.longo-tooltip');
            if (tooltip) {
                tooltip.style.display = 'block';
            }
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
    
    // Longo figürünü kaldır
    function removeLongoCharacter() {
        const longoCharacterArea = document.querySelector('.longo-character-area');
        if (longoCharacterArea) {
            longoCharacterArea.style.opacity = '0';
            longoCharacterArea.style.transform = 'scale(0.8)';
            setTimeout(() => {
                if (longoCharacterArea.parentNode) {
                    longoCharacterArea.remove();
                }
            }, 300);
        }
    }
    
    // Typing indicator'ı kaldır
    function longoRemoveTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Conversation ID state - sessionStorage'da sakla
    function getConversationId() {
        return sessionStorage.getItem('longo_conversation_id');
    }
    
    function setConversationId(id) {
        if (id) {
            sessionStorage.setItem('longo_conversation_id', id);
        } else {
            sessionStorage.removeItem('longo_conversation_id');
        }
    }
    
    // Session-based chat history (free kullanıcılar için)
    function getSessionChatHistory() {
        const history = sessionStorage.getItem('longo_session_chat_history');
        return history ? JSON.parse(history) : [];
    }
    
    function addToSessionChatHistory(role, content) {
        const history = getSessionChatHistory();
        history.push({
            role: role,
            content: content,
            timestamp: new Date().toISOString()
        });
        sessionStorage.setItem('longo_session_chat_history', JSON.stringify(history));
    }
    
    function clearSessionChatHistory() {
        sessionStorage.removeItem('longo_session_chat_history');
    }
    
    // Session history'yi UI'da göster
    function loadSessionChatHistory() {
        const history = getSessionChatHistory();
        if (history.length === 0) return;
        
        // Mevcut mesajları temizle (welcome message hariç)
        const messagesDiv = document.getElementById('longo-chat-messages');
        const welcomeMessage = messagesDiv.querySelector('.longo-welcome-message');
        const longoCharacterArea = messagesDiv.querySelector('.longo-character-area');
        
        // Tüm mesajları temizle
        messagesDiv.innerHTML = '';
        
        // Welcome message ve Longo character'ı geri ekle
        if (welcomeMessage) {
            messagesDiv.appendChild(welcomeMessage);
        }
        if (longoCharacterArea) {
            messagesDiv.appendChild(longoCharacterArea);
        }
        
        // Session history'den mesajları yükle
        history.forEach(item => {
            const messageDiv = document.createElement('div');
            messageDiv.className = `longo-message ${item.role}`;
            
            const paragraph = document.createElement('p');
            paragraph.textContent = item.content;
            messageDiv.appendChild(paragraph);
            
            messagesDiv.appendChild(messageDiv);
        });
        
        // En alta scroll
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    // Chat start endpoint
    async function startConversation() {
        try {
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const apiUrl = isLocal ? 'http://localhost:8000' : 'https://longo-ai.onrender.com';
            
            const response = await fetch(`${apiUrl}/ai/chat/start`, {
                method: 'POST',
                headers: {
                    'username': 'longopass',
                    'password': '123456',
                    'x-user-id': getUserIdForChat(),
                    ...(window.longoUserLevel && { 'x-user-level': window.longoUserLevel }),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.conversation_id;
        } catch (error) {
            console.error('Error starting conversation:', error);
            return null;
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
        
        // Longo figürünü kaldır (ilk mesajdan sonra)
        removeLongoCharacter();
        
        // Input'u devre dışı bırak
        input.disabled = true;
        
        // Typing effect göster
        showTypingIndicator();
        
        // API'ye gönder
        try {
            // Start conversation if needed
            let conversationId = getConversationId();
            if (!conversationId) {
                conversationId = await startConversation();
                if (!conversationId) {
                    throw new Error('Konuşma başlatılamadı');
                }
                setConversationId(conversationId);
            }
            
            // Local veya production için URL seç
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const apiUrl = isLocal ? 'http://localhost:8000' : 'https://longo-ai.onrender.com';
            
            const response = await fetch(`${apiUrl}/ai/chat`, {
                method: 'POST',
                headers: {
                    'username': 'longopass',
                    'password': '123456',
                    'x-user-id': getUserIdForChat(),
                    ...(window.longoUserLevel && { 'x-user-level': window.longoUserLevel }),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    text: message
                })
            });
            
            if (!response.ok) {
                // 429 Too Many Requests hatası için özel handling
                if (response.status === 429) {
                    const errorData = await response.json();
                    longoRemoveTypingIndicator();
                    longoAddMessage('assistant', 'Günlük soru limitiniz doldu. 24 saat sonra tekrar deneyin.');
                    showLimitPopup();
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Typing effect'i kaldır
            longoRemoveTypingIndicator();
            
            // AI yanıtını göster
            const reply = result.reply;
            
            // Limit popup kontrolü
            if (reply.startsWith('LIMIT_POPUP:')) {
                const cleanReply = reply.replace('LIMIT_POPUP:', '');
                longoAddMessage('assistant', cleanReply);
                showLimitPopup();
            } else {
                longoAddMessage('assistant', reply);
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            longoRemoveTypingIndicator();
            longoAddMessage('assistant', 'Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.');
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
        
        // XSS güvenliği için textContent kullan
        const paragraph = document.createElement('p');
        paragraph.textContent = content;
        messageDiv.appendChild(paragraph);
        
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
        
        // Sessio