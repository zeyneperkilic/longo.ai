
(function() {
    'use strict';
    
    // Console.log listener'ı EN BAŞTA kur (asıl sitenin logları için)
    const originalConsoleLog = console.log;
    console.log = function(...args) {
        originalConsoleLog.apply(console, args);
        try {
            const logString = args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' ');
            // "UserID: 12" veya "Membership initialized - UserID: 12" formatını yakala
            const userIdMatch = logString.match(/UserID:\s*(\d+)/i);
            if (userIdMatch && userIdMatch[1]) {
                const newUserId = userIdMatch[1];
                if (window.longoRealUserId !== newUserId) {
                    window.longoRealUserId = newUserId;
                    try {
                        sessionStorage.setItem('longo_user_id', window.longoRealUserId);
                        localStorage.setItem('longo_user_id', window.longoRealUserId);
                    } catch(e) {}
                    originalConsoleLog('🔍 DEBUG: UserID captured from console.log:', newUserId);
                }
            }
        } catch(e) {}
    };
    
    // DOM hazır olunca widget'ı başlat
    function initWidget() {
        // Cache busting için version ekle
        console.log('🔍 DEBUG: Widget version 2.0 - Cart integration enabled');
        // Siteden userLevel gelip gelmediğini kontrol et
        // Ideasoft'ta gerçek değerler gelecek, yoksa guest (null) olarak ayarla
        console.log('🔍 DEBUG: window.longoUserLevel before:', window.longoUserLevel);
        
        // Basit çözüm: Direkt olarak user level'ı tespit et
        if (!window.longoUserLevel) {
            // Ideasoft'ta yaygın user level değişkenleri
            const possibleLevelVars = [
                'userLevel', 'user_level', 'level', 'userLevelValue',
                'membershipLevel', 'userType', 'accountLevel'
            ];
            
            for (const varName of possibleLevelVars) {
                if (window[varName] !== undefined) {
                    window.longoUserLevel = parseInt(window[varName]);
                    console.log('🔍 DEBUG: User level tespit edildi:', varName, '=', window.longoUserLevel);
                    break;
                }
            }
            
            // Hala bulunamadıysa null (guest)
            if (!window.longoUserLevel) {
                window.longoUserLevel = null;
                console.log('🔍 DEBUG: User level tespit edilemedi, guest olarak ayarlandı');
            }
        } else {
            console.log('🔍 DEBUG: window.longoUserLevel zaten set edilmiş:', window.longoUserLevel);
        }
        
        console.log('🔍 DEBUG: window.longoUserLevel after:', window.longoUserLevel);
        // Premium kullanıcılar için gerçek user ID auto-detect
        function readCookie(name) {
            const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)'));
            return match ? decodeURIComponent(match[1]) : null;
        }
        function resolveFromWindowKeys() {
            try {
                const propNames = Object.getOwnPropertyNames(window);
                const nameRegex = /(user.?id|member.?id|customer.?id|account.?id|current.?user.?id)/i;
                for (const name of propNames) {
                    if (!nameRegex.test(name)) continue;
                    const val = window[name];
                    if (val === undefined || val === null) continue;
                    if (typeof val === 'string' || typeof val === 'number') {
                        const str = String(val).trim();
                        if (str && str !== 'undefined' && str !== 'null') {
                            console.log('🔍 DEBUG: Real user id tespit edildi (window-scan):', name, '=', str);
                            return str;
                        }
                    }
                }
            } catch(e) {}
            return null;
        }
        if (!window.longoRealUserId) {
            // 1) Yaygın global değişkenler
            const possibleIdVars = [
                'longoRealUserId',
                'userId','user_id','userID','USER_ID',
                'customerId','customer_id','memberId','member_id',
                'accountId','account_id','currentUserId','current_user_id'
            ];
            for (const varName of possibleIdVars) {
                if (window[varName] !== undefined && window[varName] !== null && window[varName] !== '') {
                    window.longoRealUserId = String(window[varName]);
                    console.log('🔍 DEBUG: Real user id tespit edildi (global):', varName, '=', window.longoRealUserId);
                    break;
                }
            }
            if (!window.longoRealUserId) {
                const scanned = resolveFromWindowKeys();
                if (scanned) window.longoRealUserId = scanned;
            }
        }
        if (!window.longoRealUserId) {
            // 2) DOM data-* attribute'ları
            const elWithUserId = document.querySelector('[data-user-id], [data-userid], [data-customer-id], [data-member-id]');
            if (elWithUserId) {
                window.longoRealUserId = elWithUserId.getAttribute('data-user-id') || elWithUserId.getAttribute('data-userid') || elWithUserId.getAttribute('data-customer-id') || elWithUserId.getAttribute('data-member-id');
                if (window.longoRealUserId) {
                    console.log('🔍 DEBUG: Real user id tespit edildi (DOM):', window.longoRealUserId);
                }
            }
        }
        // Console.log listener zaten en başta kuruldu
        
        // LocalStorage/Cookie fallback (sadece console.log'da bulunamazsa)
        if (!window.longoRealUserId) {
            // 3) localStorage anahtar taraması
            try {
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i) || '';
                    if (/user.?id|customer.?id|member.?id|account.?id/i.test(key)) {
                        const val = localStorage.getItem(key);
                        if (val && val !== 'null' && val !== 'undefined') {
                            window.longoRealUserId = String(val).replace(/[^0-9a-zA-Z_-]/g, '');
                            console.log('🔍 DEBUG: Real user id tespit edildi (localStorage FALLBACK):', key, '=', window.longoRealUserId);
                            break;
                        }
                    }
                }
            } catch(e) { /* ignore */ }
        }
        if (!window.longoRealUserId) {
            // 4) Cookies (IdeaSoft vb.)
            const cookieCandidates = ['user_id','customer_id','member_id','USER_ID','CURRENT_USER_ID'];
            for (const c of cookieCandidates) {
                const v = readCookie(c);
                if (v) {
                    window.longoRealUserId = String(v);
                    console.log('🔍 DEBUG: Real user id tespit edildi (cookie FALLBACK):', c, '=', window.longoRealUserId);
                    break;
                }
            }
        }
        window.longoRealUserId = window.longoRealUserId || null;
        
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
            overflow: visible;
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
            z-index: 0;
            pointer-events: none;
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

        /* Header Butonları Container */
        .longo-header-buttons {
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
            z-index: 2;
        }

        /* Dropdown Menü Butonu */
        .longo-menu-btn {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 8px 12px;
            border-radius: 8px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
            position: relative;
            z-index: 2;
            pointer-events: auto;
        }

        .longo-menu-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
            border-color: rgba(255, 255, 255, 0.4);
        }

        /* Dropdown Menü */
        .longo-dropdown-menu {
            position: absolute;
            top: calc(100% + 8px);
            right: 0;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            min-width: 200px;
            z-index: 10005;
            overflow: hidden;
            display: none;
            border: 1px solid rgba(0, 0, 0, 0.1);
            pointer-events: auto;
        }

        .longo-dropdown-menu.show {
            display: block;
            animation: slideDown 0.2s ease;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .longo-dropdown-item {
            padding: 12px 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #1e293b;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s ease;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        }

        .longo-dropdown-item:last-child {
            border-bottom: none;
        }

        .longo-dropdown-item:hover {
            background: rgba(47, 93, 131, 0.1);
            color: #2F5D83;
        }

        .longo-dropdown-item-icon {
            font-size: 16px;
            width: 20px;
            text-align: center;
        }

        /* Chat History Modal - Chat window içinde */
        .longo-history-modal {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            z-index: 10010;
            display: none;
            flex-direction: column;
            animation: fadeIn 0.2s ease;
            border-radius: 25px;
        }

        .longo-history-modal.show {
            display: flex;
        }

        .longo-history-modal-content {
            background: transparent;
            width: 100%;
            height: 100%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .longo-history-modal-header {
            padding: 18px 25px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, rgba(47, 93, 131, 0.95) 0%, rgba(74, 124, 154, 0.95) 100%);
            color: white;
            flex-shrink: 0;
        }

        .longo-history-modal-header h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 700;
        }

        .longo-history-modal-close {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }

        .longo-history-modal-close:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.1) rotate(90deg);
        }

        .longo-history-modal-body {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
            min-height: 0;
        }

        .longo-history-item {
            padding: 15px;
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            background: rgba(255, 255, 255, 0.9);
        }

        .longo-history-item:hover {
            background: rgba(47, 93, 131, 0.1);
            border-color: rgba(47, 93, 131, 0.3);
            transform: translateX(5px);
        }

        .longo-history-item-title {
            font-size: 14px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 5px;
        }

        .longo-history-item-date {
            font-size: 12px;
            color: #64748b;
        }

        .longo-history-empty {
            text-align: center;
            padding: 40px 20px;
            color: #64748b;
            font-size: 14px;
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
            padding-bottom: 140px; /* Input alanı için daha fazla yer */
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
            margin-bottom: 15px;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(15px);
            border-radius: 15px;
            border: 1px solid rgba(59, 130, 246, 0.2);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        }

        .longo-welcome-message p {
            margin: 6px 0;
            font-size: 14px;
            line-height: 1.5;
            color: #334155;
            font-weight: 500;
        }

        /* Longo Karakteri Alanı */
        .longo-character-area {
            text-align: center;
            margin: 10px 0;
            padding: 10px;
        }

        .longo-character {
            width: 60px;
            height: 60px;
            margin: 0 auto 10px;
            background: linear-gradient(135deg, #4A7C9A 0%, #2F5D83 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 20px rgba(47, 93, 131, 0.3);
            animation: longoFloat 3s ease-in-out infinite;
            overflow: hidden;
            border: 2px solid rgba(255, 255, 255, 0.3);
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
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }

        /* Guest Kullanıcı Mesajı */
        .longo-guest-message {
            text-align: center;
            margin: 10px 0;
            padding: 10px 15px;
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid rgba(255, 193, 7, 0.3);
            border-radius: 12px;
            font-size: 12px;
            color: #856404;
            font-weight: 500;
        }

        /* Hazır Soru Butonları */
        .longo-quick-questions {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin: 20px 0;
            padding: 0 5px;
        }

        .longo-quick-questions-title {
            text-align: center;
            font-size: 13px;
            color: #64748b;
            font-weight: 500;
            margin-bottom: 8px;
            padding: 0 10px;
        }

        .longo-quick-question-btn {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 14px;
            color: #1e293b;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: left;
            font-weight: 500;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .longo-quick-question-btn:hover {
            background: rgba(47, 93, 131, 0.1);
            border-color: rgba(47, 93, 131, 0.4);
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(47, 93, 131, 0.15);
        }

        .longo-quick-question-btn:active {
            transform: translateX(3px) scale(0.98);
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
            background: rgba(255, 255, 255, 0.95);
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            align-items: center; /* Safari dikey hizalama */
            gap: 10px; /* Gap azaltıldı */
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 10;
            flex-shrink: 0;
            min-height: 120px; /* Minimum yükseklik eklendi */
            box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
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
            padding: 12px 16px; /* textarea icin daha uygun padding */
            min-height: 48px; /* 1 satır */
            max-height: 84px; /* ~2 satır görünür */
            overflow-y: auto; /* uzun metinde scroll */
            border: 2px solid rgba(59, 130, 246, 0.3);
            border-radius: 16px;
            font-size: 15px;
            line-height: 1.4;
            outline: none;
            transition: all 0.3s ease;
            background: white;
            color: #1e293b;
            font-weight: 500;
            box-sizing: border-box; /* Safari padding-border hesaplaması */
            resize: none; /* kullanici boyutlandirmasini engelle */
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
    
    // Widget'ı başlat
    createWidget();
    
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
                        <div class="longo-header-buttons">
                            <button onclick="longoToggleMenu()" class="longo-menu-btn" title="Menü">⋮</button>
                            <button onclick="longoCloseChat()" class="longo-close-btn">✕</button>
                        </div>
                        <div class="longo-dropdown-menu" id="longo-dropdown-menu">
                            <div class="longo-dropdown-item" onclick="longoStartNewChat()">
                                <span class="longo-dropdown-item-icon">🔄</span>
                                <span>Yeni Chat</span>
                            </div>
                            <div class="longo-dropdown-item" onclick="longoShowChatHistory()">
                                <span class="longo-dropdown-item-icon">📜</span>
                                <span>Chat Geçmişi</span>
                            </div>
                        </div>
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
                        
                        <!-- Guest Kullanıcı Mesajı -->
                        <div class="longo-guest-message" id="longo-guest-message" style="display: none;">
                            Kişiselleştirilmiş öneriler almak için üye olun
                        </div>
                        
                        <!-- Hazır Soru Butonları -->
                        <div class="longo-quick-questions" id="longo-quick-questions">
                            <div class="longo-quick-questions-title">
                                Sorulardan birini seçin veya mesajınızı yazın
                            </div>
                            <button class="longo-quick-question-btn" onclick="longoSendQuickQuestion('Hangi Longopass ürünleri bana uygun?')">
                                Hangi Longopass ürünleri bana uygun?
                            </button>
                            <button class="longo-quick-question-btn" onclick="longoSendQuickQuestion('Uyku kalitemi nasıl iyileştirebilirim?')">
                                Uyku kalitemi nasıl iyileştirebilirim?
                            </button>
                            <button class="longo-quick-question-btn" onclick="longoSendQuickQuestion('Sindirim ve bağırsak sağlığı için hangi alışkanlıklar önemli?')">
                                Sindirim ve bağırsak sağlığı için hangi alışkanlıklar önemli?
                            </button>
                        </div>
                    </div>
                    
                    <div id="longo-chat-input">
                        <div class="input-container">
                            <textarea id="longo-message-input" placeholder="Mesajınızı yazın..." rows="2" onkeydown="longoHandleKeyPress(event)"></textarea>
                            <button onclick="longoSendMessage()" class="longo-send-btn">
                                <span>Gönder</span>
                                <div class="btn-ripple"></div>
                            </button>
                        </div>
                        <div class="longo-disclaimer">
                            Longo yapay zeka desteklidir. Öneriler için doktorunuza danışınız.
                        </div>
                    </div>
                    
                    <!-- Chat History Modal - Chat window içinde -->
                    <div class="longo-history-modal" id="longo-history-modal">
                        <div class="longo-history-modal-content">
                            <div class="longo-history-modal-header">
                                <h3>Chat Geçmişi</h3>
                                <button onclick="longoCloseHistoryModal()" class="longo-history-modal-close">✕</button>
                            </div>
                            <div class="longo-history-modal-body" id="longo-history-modal-body">
                                <div class="longo-history-empty">Yükleniyor...</div>
                            </div>
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
    
    // Hazır soru butonuna tıklandığında
    window.longoSendQuickQuestion = function(question) {
        // Hazır soru butonlarını gizle
        const quickQuestions = document.getElementById('longo-quick-questions');
        if (quickQuestions) {
            quickQuestions.style.display = 'none';
        }
        
        // Longo karakterini kaldır
        removeLongoCharacter();
        
        // Mesajı input'a yaz ve gönder
        const input = document.getElementById('longo-message-input');
        input.value = question;
        longoSendMessage();
    };
    
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
        
        // Guest kullanıcı mesajını göster/gizle (sadece user level yokken)
        const guestMessage = document.getElementById('longo-guest-message');
        if (guestMessage) {
            // Guest kontrolü: sadece userLevel null/undefined ise guest (user level 1 = free üyelik, zaten üye)
            const isGuest = !window.longoUserLevel || window.longoUserLevel === null || window.longoUserLevel === undefined;
            guestMessage.style.display = isGuest ? 'block' : 'none';
        }
        
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
        
        // Dropdown menüyü kapat
        const dropdown = document.getElementById('longo-dropdown-menu');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
    };
    
    // Dropdown menüyü aç/kapat
    window.longoToggleMenu = function() {
        const dropdown = document.getElementById('longo-dropdown-menu');
        if (dropdown) {
            dropdown.classList.toggle('show');
        }
    };
    
    // Yeni chat başlat
    window.longoStartNewChat = async function() {
        // Dropdown menüyü kapat
        const dropdown = document.getElementById('longo-dropdown-menu');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
        
        // Yeni conversation başlat
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
            const newConversationId = data.conversation_id;
            
            // Conversation ID'yi kaydet
            setConversationId(newConversationId);
            
            // Chat mesajlarını temizle
            const messagesDiv = document.getElementById('longo-chat-messages');
            messagesDiv.innerHTML = '';
            
            // Welcome message ve karakteri tekrar ekle
            const welcomeHTML = `
                <div class="longo-welcome-message">
                    <p>Merhaba! Ben Longo, sağlık asistanın.</p>
                    <p>Nasıl yardımcı olabilirim?</p>
                </div>
                <div class="longo-character-area">
                    <div class="longo-character">
                        <img src="https://longo-ai.onrender.com/widget/longo.jpeg" alt="Longo AI Asistan" class="longo-image">
                    </div>
                    <div class="longo-character-text"></div>
                </div>
                <div class="longo-guest-message" id="longo-guest-message" style="display: none;">
                    Kişiselleştirilmiş öneriler almak için üye olun
                </div>
                <div class="longo-quick-questions" id="longo-quick-questions">
                    <div class="longo-quick-questions-title">
                        Sorulardan birini seç ve konuşmayı başlat
                    </div>
                    <button class="longo-quick-question-btn" onclick="longoSendQuickQuestion('Hangi Longopass ürünleri bana uygun?')">
                        Hangi Longopass ürünleri bana uygun?
                    </button>
                    <button class="longo-quick-question-btn" onclick="longoSendQuickQuestion('Uyku kalitemi nasıl iyileştirebilirim?')">
                        Uyku kalitemi nasıl iyileştirebilirim?
                    </button>
                    <button class="longo-quick-question-btn" onclick="longoSendQuickQuestion('Sindirim ve bağırsak sağlığı için hangi alışkanlıklar önemli?')">
                        Sindirim ve bağırsak sağlığı için hangi alışkanlıklar önemli?
                    </button>
                </div>
            `;
            messagesDiv.innerHTML = welcomeHTML;
            
            // Guest mesajını kontrol et (sadece user level yokken)
            const guestMessage = document.getElementById('longo-guest-message');
            if (guestMessage) {
                // Guest kontrolü: sadece userLevel null/undefined ise guest (user level 1 = free üyelik, zaten üye)
                const isGuest = !window.longoUserLevel || window.longoUserLevel === null || window.longoUserLevel === undefined;
                guestMessage.style.display = isGuest ? 'block' : 'none';
            }
            
            // Session history'yi temizle (free kullanıcılar için)
            if (window.longoUserPlan === 'free' || !window.longoUserPlan) {
                clearSessionChatHistory();
            }
            
        } catch (error) {
            console.error('Error starting new chat:', error);
            alert('Yeni chat başlatılırken bir hata oluştu. Lütfen tekrar deneyin.');
        }
    };
    
    // Chat geçmişini göster
    window.longoShowChatHistory = async function() {
        // Dropdown menüyü kapat
        const dropdown = document.getElementById('longo-dropdown-menu');
        if (dropdown) {
            dropdown.classList.remove('show');
        }
        
        // Modal'ı göster
        const modal = document.getElementById('longo-history-modal');
        const modalBody = document.getElementById('longo-history-modal-body');
        
        if (!modal || !modalBody) return;
        
        modal.classList.add('show');
        modalBody.innerHTML = '<div class="longo-history-empty">Yükleniyor...</div>';
        
        try {
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const apiUrl = isLocal ? 'http://localhost:8000' : 'https://longo-ai.onrender.com';
            
            const response = await fetch(`${apiUrl}/ai/chat/conversations`, {
                method: 'GET',
                headers: {
                    'username': 'longopass',
                    'password': '123456',
                    'x-user-id': getUserIdForChat(),
                    ...(window.longoUserLevel && { 'x-user-level': window.longoUserLevel }),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const conversations = await response.json();
            
            if (conversations.length === 0) {
                // Free kullanıcılar için özel mesaj
                const userPlan = window.longoUserPlan || (window.longoUserLevel === 3 ? 'premium_plus' : (window.longoUserLevel === 2 ? 'premium' : 'free'));
                const isFree = userPlan === 'free' || !userPlan || window.longoUserLevel === 1;
                
                if (isFree) {
                    modalBody.innerHTML = '<div class="longo-history-empty">Chat geçmişi Essential ve Ultimate üyelikler içindir.</div>';
                } else {
                    modalBody.innerHTML = '<div class="longo-history-empty">Henüz chat geçmişiniz yok.</div>';
                }
                return;
            }
            
            // Conversation'ları listele
            let historyHTML = '';
            conversations.forEach(conv => {
                // Backend UTC zamanı gönderiyor, Türkiye saatine çevir
                const date = new Date(conv.updated_at);
                
                // Sadece tarih göster (saat yok)
                const dateStr = date.toLocaleDateString('tr-TR', { 
                    day: 'numeric', 
                    month: 'long', 
                    year: 'numeric',
                    timeZone: 'Europe/Istanbul'
                });
                
                // Title'ı temizle (HTML escape)
                const cleanTitle = conv.title
                    .replace(/===.*?===/g, '')
                    .replace(/<[^>]*>/g, '')
                    .replace(/&nbsp;/g, ' ')
                    .trim();
                
                historyHTML += `
                    <div class="longo-history-item" onclick="longoLoadConversation(${conv.conversation_id})">
                        <div class="longo-history-item-title">${cleanTitle || 'Yeni Sohbet'}</div>
                        <div class="longo-history-item-date">${dateStr}</div>
                    </div>
                `;
            });
            
            modalBody.innerHTML = historyHTML;
            
        } catch (error) {
            console.error('Error loading chat history:', error);
            modalBody.innerHTML = '<div class="longo-history-empty">Chat geçmişi yüklenirken bir hata oluştu.</div>';
        }
    };
    
    // Conversation yükle
    window.longoLoadConversation = async function(conversationId) {
        // Modal'ı kapat
        longoCloseHistoryModal();
        
        // Conversation ID'yi kaydet
        setConversationId(conversationId);
        
        // Chat mesajlarını temizle
        const messagesDiv = document.getElementById('longo-chat-messages');
        messagesDiv.innerHTML = '<div class="longo-history-empty">Yükleniyor...</div>';
        
        try {
            const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            const apiUrl = isLocal ? 'http://localhost:8000' : 'https://longo-ai.onrender.com';
            
            const response = await fetch(`${apiUrl}/ai/chat/${conversationId}/history`, {
                method: 'GET',
                headers: {
                    'username': 'longopass',
                    'password': '123456',
                    'x-user-id': getUserIdForChat(),
                    ...(window.longoUserLevel && { 'x-user-level': window.longoUserLevel }),
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const history = await response.json();
            
            console.log('🔍 Conversation history loaded:', history);
            console.log('🔍 History length:', history ? history.length : 'null');
            
            // Mesajları göster
            messagesDiv.innerHTML = '';
            
            if (!history || history.length === 0) {
                messagesDiv.innerHTML = '<div class="longo-history-empty">Bu conversation için mesaj geçmişi bulunamadı.</div>';
                return;
            }
            
            history.forEach(item => {
                if (item.role && item.content) {
                    longoAddMessage(item.role, item.content, 'history'); // 'history' type = typing effect yok
                }
            });
            
            // Hazır soru butonlarını gizle (mesaj geçmişi varsa)
            const quickQuestions = document.getElementById('longo-quick-questions');
            if (quickQuestions) {
                quickQuestions.style.display = 'none';
            }
            
            // Longo karakterini kaldır (mesaj geçmişi varsa)
            removeLongoCharacter();
            
            // Scroll to bottom
            setTimeout(() => {
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }, 100);
            
        } catch (error) {
            console.error('❌ Error loading conversation:', error);
            messagesDiv.innerHTML = '<div class="longo-history-empty">Conversation yüklenirken bir hata oluştu: ' + error.message + '</div>';
        }
    };
    
    // History modal'ı kapat
    window.longoCloseHistoryModal = function() {
        const modal = document.getElementById('longo-history-modal');
        if (modal) {
            modal.classList.remove('show');
        }
    };
    
    // Enter ile gönder, Shift+Enter ile yeni satır (textarea)
    window.longoHandleKeyPress = function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
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
        
        // Hazır soru butonlarını gizle (mesaj geçmişi varsa)
        const quickQuestions = document.getElementById('longo-quick-questions');
        if (quickQuestions) {
            quickQuestions.style.display = 'none';
        }
        
        // Longo karakterini kaldır (mesaj geçmişi varsa)
        removeLongoCharacter();
        
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
        // Premium/Premium+ için userId zorunlu: gönderimden hemen önce tekrar tespit etmeyi dene
        function tryResolveUserId() {
            if (window.longoRealUserId) return window.longoRealUserId;
            
            // 1. SessionStorage'dan kontrol et (console.log listener kaydetmiş olabilir)
            try {
                const ssUserId = sessionStorage.getItem('longo_user_id');
                if (ssUserId && ssUserId !== 'null' && ssUserId !== 'undefined') {
                    window.longoRealUserId = String(ssUserId);
                    console.log('🔍 DEBUG: Real user id sessionStorage\'dan tespit:', window.longoRealUserId);
                    return window.longoRealUserId;
                }
            } catch(e) {}
            
            // 2. Global değişkenler
            const candidates = [
                window.longoRealUserId,
                window.userId, window.user_id, window.userID, window.USER_ID,
                window.customerId, window.customer_id, window.memberId, window.member_id,
                window.accountId, window.account_id, window.currentUserId, window.current_user_id
            ];
            for (const v of candidates) {
                if (v !== undefined && v !== null && v !== '') {
                    window.longoRealUserId = String(v);
                    console.log('🔍 DEBUG: Real user id send öncesi tespit:', window.longoRealUserId);
                    try { sessionStorage.setItem('longo_user_id', window.longoRealUserId); } catch(e) {}
                    break;
                }
            }
            // localStorage / sessionStorage
            if (!window.longoRealUserId) {
                try {
                    const lsKeys = ['user_id','USER_ID','customer_id','member_id','longo_user_id'];
                    for (const k of lsKeys) {
                        const val = localStorage.getItem(k) || sessionStorage.getItem(k);
                        if (val && val !== 'null' && val !== 'undefined') {
                            window.longoRealUserId = String(val).replace(/[^0-9a-zA-Z_-]/g, '');
                            console.log('🔍 DEBUG: Real user id storage ile tespit:', k, '=>', window.longoRealUserId);
                            try { sessionStorage.setItem('longo_user_id', window.longoRealUserId); } catch(e) {}
                            break;
                        }
                    }
                } catch(e) {}
            }
            // cookie
            if (!window.longoRealUserId) {
                try {
                    const cookieKeys = ['user_id','USER_ID','customer_id','member_id'];
                    for (const ck of cookieKeys) {
                        const v = (typeof readCookie === 'function') ? readCookie(ck) : null;
                        if (v) {
                            window.longoRealUserId = String(v);
                            console.log('🔍 DEBUG: Real user id cookie ile tespit:', ck, '=>', window.longoRealUserId);
                            try { sessionStorage.setItem('longo_user_id', window.longoRealUserId); } catch(e) {}
                            break;
                        }
                    }
                } catch(e) {}
            }
            return window.longoRealUserId;
        }
        // Eğer premium ise ve userId yoksa mesajı göndermeyi durdur
        const planNow = window.longoUserPlan || (window.longoUserLevel === 3 ? 'premium_plus' : (window.longoUserLevel === 2 ? 'premium' : 'free'));
        if ((planNow === 'premium' || planNow === 'premium_plus') && !tryResolveUserId()) {
            alert('Kullanıcı ID algılanamadı. Lütfen sayfayı yenileyin veya tekrar giriş yapın.');
            return;
        }
        console.log('🔍 DEBUG: Chat x-user-id =>', window.longoRealUserId);
        
        const input = document.getElementById('longo-message-input');
        const message = input.value.trim();
        if (!message) return;
        
        // Hazır soru butonlarını gizle (ilk mesajdan sonra)
        const quickQuestions = document.getElementById('longo-quick-questions');
        if (quickQuestions) {
            quickQuestions.style.display = 'none';
        }
        
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
            const products = result.products; // Sepete ekleme için ürünler
            
            console.log('🔍 DEBUG: AI Response:', result);
            console.log('🔍 DEBUG: Products:', products);
            console.log('🔍 DEBUG: Products length:', products ? products.length : 'null');
            console.log('🔍 DEBUG: Products type:', typeof products);
            
            // Limit popup kontrolü
            if (reply.startsWith('LIMIT_POPUP:')) {
                const cleanReply = reply.replace('LIMIT_POPUP:', '');
                longoAddMessage('assistant', cleanReply);
                showLimitPopup();
            } else {
                longoAddMessage('assistant', reply);
                
                // Eğer ürün önerileri varsa sepete ekle butonları göster
                console.log('🔍 DEBUG: Products kontrol ediliyor...');
                console.log('🔍 DEBUG: products var mı?', !!products);
                console.log('🔍 DEBUG: products length:', products ? products.length : 'null');
                console.log('🔍 DEBUG: products type:', typeof products);
                
                if (products && products.length > 0) {
                    console.log('🔍 DEBUG: Ürün butonları gösteriliyor:', products);
                    showProductButtons(products);
                } else {
                    console.log('🔍 DEBUG: Ürün bulunamadı, butonlar gösterilmiyor');
                    console.log('🔍 DEBUG: products değeri:', products);
                }
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
    
    // Typing effect fonksiyonu
    function typeText(element, text, delay = 30) {
        let index = 0;
        const timer = setInterval(() => {
            if (index < text.length) {
                // HTML tag'leri için özel kontrol
                if (text[index] === '<') {
                    // HTML tag'ini bul ve tamamını ekle
                    const tagEnd = text.indexOf('>', index);
                    if (tagEnd !== -1) {
                        const tag = text.substring(index, tagEnd + 1);
                        element.innerHTML += tag;
                        index = tagEnd + 1;
                    } else {
                        element.innerHTML += text[index];
                        index++;
                    }
                } else {
                    element.innerHTML += text[index];
                    index++;
                }
                
                // Scroll to bottom
                const messagesDiv = document.getElementById('longo-chat-messages');
                if (messagesDiv) {
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            } else {
                clearInterval(timer);
            }
        }, delay);
    }
    
    // Typing effect fonksiyonu - HTML'i doğru render etmek için (kelime kelime)
    function typeTextWithHTML(element, text, delay = 80) {
        // HTML tag'lerini koruyarak metni kelimelere ayır
        const words = [];
        let currentWord = '';
        let inTag = false;
        
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            
            if (char === '<') {
                inTag = true;
                // Eğer önceki kelime varsa ekle
                if (currentWord.trim()) {
                    words.push(currentWord);
                    currentWord = '';
                }
                currentWord += char;
            } else if (char === '>') {
                inTag = false;
                currentWord += char;
                // Tag'i bir kelime olarak ekle
                words.push(currentWord);
                currentWord = '';
            } else if (inTag) {
                // Tag içindeyken her şeyi ekle
                currentWord += char;
            } else if (char === ' ' || char === '\n') {
                // Boşluk veya yeni satır - kelimeyi bitir
                if (currentWord.trim()) {
                    words.push(currentWord);
                    currentWord = '';
                }
                // Boşluğu da ekle (ayrı bir "kelime" olarak)
                words.push(char);
            } else {
                currentWord += char;
            }
        }
        
        // Son kelimeyi ekle
        if (currentWord.trim()) {
            words.push(currentWord);
        }
        
        // Kelime kelime yaz
        element.innerHTML = '';
        let wordIndex = 0;
        
        const timer = setInterval(() => {
            if (wordIndex < words.length) {
                element.innerHTML += words[wordIndex];
                wordIndex++;
                
                // Scroll to bottom
                const messagesDiv = document.getElementById('longo-chat-messages');
                if (messagesDiv) {
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            } else {
                clearInterval(timer);
            }
        }, delay);
    }

    // Mesaj ekle
    function longoAddMessage(role, content, type = 'normal') {
        const messagesDiv = document.getElementById('longo-chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `longo-message ${role} ${type}`;
        
        const paragraph = document.createElement('p');
        
        // Backend'den gelen response'da zaten HTML var, sadece markdown formatındaki link'leri HTML'e çevir
        let convertedContent = content;
        
        // Bold: **text** -> <strong>text</strong>
        convertedContent = convertedContent.replace(
            /\*\*([^*]+)\*\*/g,
            '<strong style="font-weight: bold;">$1</strong>'
        );
        
        // Italic: *text* -> <em>text</em>
        convertedContent = convertedContent.replace(
            /\*([^*]+)\*/g,
            '<em style="font-style: italic;">$1</em>'
        );
        
        // Sadece markdown formatındaki link'leri HTML'e çevir, zaten HTML olanları dokunma
        if (!/<a\s/i.test(convertedContent)) {
            // Links (markdown): [text](url) -> <a href="url" target="_blank">text</a>
            convertedContent = convertedContent.replace(
                /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #007bff; text-decoration: underline;">$1</a>'
            );
        }
        
        // History yüklenirken typing effect yok
        if (type === 'history') {
            // Direkt render et, typing effect yok
            paragraph.innerHTML = convertedContent;
            messageDiv.appendChild(paragraph);
        } else if (role === 'assistant') {
            // Sadece assistant mesajları için typing effect
            // Link detection: <a tag'i, target="_blank" attribute'u veya markdown link formatı varsa
            const hasLink = /<a\s/i.test(convertedContent) || /target="_blank"/i.test(convertedContent) || /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g.test(convertedContent);
            // Link varsa typing effect'i kapatıp direkt render et (kliklenebilirlik için)
            if (hasLink) {
                paragraph.innerHTML = convertedContent;
                messageDiv.appendChild(paragraph);
            } else {
                // Typing effect için boş başlat
                paragraph.innerHTML = '';
                messageDiv.appendChild(paragraph);
                // Typing effect - HTML'i doğru render etmek için
                typeTextWithHTML(paragraph, convertedContent, 30); // 30ms delay
            }
        } else {
            // Kullanıcı mesajları normal göster
            paragraph.innerHTML = convertedContent;
            messageDiv.appendChild(paragraph);
        }
        
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
        
        // Session history'ye ekle (free kullanıcılar için)
        if (window.longoUserPlan === 'free' || !window.longoUserPlan) {
            addToSessionChatHistory(role, content);
        }
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
    
    // Ürün butonlarını göster
    function showProductButtons(products) {
        console.log('🔍 DEBUG: showProductButtons çağrıldı, products:', products);
        
        // Doğru selector'ı kullan
        const messagesDiv = document.getElementById('longo-chat-messages');
        
        console.log('🔍 DEBUG: messagesDiv bulundu mu?', !!messagesDiv);
        console.log('🔍 DEBUG: messagesDiv element:', messagesDiv);
        if (!messagesDiv) {
            console.log('🔍 DEBUG: messagesDiv bulunamadı! Tüm selector\'lar denendi.');
            return;
        }
        
        // Unique ID'ler oluştur
        const uniqueId = 'product-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const productListId = 'product-list-' + uniqueId;
        const toggleIconId = 'product-toggle-icon-' + uniqueId;
        
        const productDiv = document.createElement('div');
        productDiv.className = 'longo-message assistant';
        productDiv.style.marginTop = '10px';
        
        let productHTML = '<div class="longo-product-buttons">';
        productHTML += `
            <div class="longo-product-header" style="font-size: 12px; color: #666; margin-bottom: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; padding: 8px; background: #f0f0f0; border-radius: 6px; user-select: none;" onclick="toggleProductList('${productListId}', '${toggleIconId}')">
                <span>🛒 Önerilen Ürünler (${products.length})</span>
                <span id="${toggleIconId}" style="font-size: 14px; transition: transform 0.3s ease;">▼</span>
            </div>
            <div id="${productListId}" style="display: none; max-height: 300px; overflow-y: auto;">
        `;
        
        products.forEach(product => {
            productHTML += `
                <div class="longo-product-item" style="margin-bottom: 8px; padding: 8px; border: 1px solid #e0e0e0; border-radius: 6px; background: #f9f9f9;">
                    <div style="font-weight: 500; font-size: 13px; margin-bottom: 4px;">${product.name}</div>
                    <div style="font-size: 11px; color: #666; margin-bottom: 6px;">${product.category}</div>
                    <div style="font-size: 11px; color: #007bff; font-weight: 500;">${product.price}₺</div>
                </div>
            `;
        });
        
        productHTML += '</div></div>';
        productDiv.innerHTML = productHTML;
        
        console.log('🔍 DEBUG: Product HTML oluşturuldu:', productHTML);
        console.log('🔍 DEBUG: Product div DOM\'a ekleniyor...');
        
        messagesDiv.appendChild(productDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        console.log('🔍 DEBUG: Product div başarıyla eklendi!');
    }
    
    // Ürün listesini aç/kapat
    window.toggleProductList = function(productListId, toggleIconId) {
        const productList = document.getElementById(productListId);
        const toggleIcon = document.getElementById(toggleIconId);
        
        console.log('🔍 DEBUG: toggleProductList çağrıldı:', productListId, toggleIconId);
        console.log('🔍 DEBUG: productList bulundu mu?', !!productList);
        console.log('🔍 DEBUG: toggleIcon bulundu mu?', !!toggleIcon);
        
        if (productList && toggleIcon) {
            if (productList.style.display === 'none') {
                productList.style.display = 'block';
                toggleIcon.textContent = '▲';
                toggleIcon.style.transform = 'rotate(0deg)';
                console.log('🔍 DEBUG: Ürün listesi açıldı');
            } else {
                productList.style.display = 'none';
                toggleIcon.textContent = '▼';
                toggleIcon.style.transform = 'rotate(0deg)';
                console.log('🔍 DEBUG: Ürün listesi kapandı');
            }
        } else {
            console.log('🔍 DEBUG: Elementler bulunamadı!');
        }
    };
    
    // Sepete ekleme fonksiyonu kaldırıldı - Ideasoft entegrasyonu zor olduğu için
    
    // Dropdown menüyü dışarı tıklandığında kapat
    document.addEventListener('click', function(event) {
        const dropdown = document.getElementById('longo-dropdown-menu');
        const menuBtn = document.querySelector('.longo-menu-btn');
        
        if (dropdown && menuBtn && !dropdown.contains(event.target) && !menuBtn.contains(event.target)) {
            dropdown.classList.remove('show');
        }
    });
    }
    
    // DOM hazır olunca widget'ı başlat
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        // DOM zaten hazır
        initWidget();
    }
    
})();
