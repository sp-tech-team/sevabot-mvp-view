# ui_styles.py - All UI styling and design elements

def get_favicon_link():
    """Get favicon link HTML"""
    return '<link rel="icon" href="https://isha.sadhguru.org/favicon.ico" type="image/x-icon">'

def get_isha_logo_svg():
    """Get enhanced Isha logo SVG for header"""
    return """
    <div style="display: flex; align-items: center;">
        <div style="display: flex; align-items: center; margin-right: 1rem;">
            <img src="/images/isha-logo.png" alt="Isha Logo" width="48" height="48" style="margin-right: 0.75rem; border-radius: 50%;" />
            <span style="font-family: 'Google Sans', 'Product Sans', 'Roboto', system-ui, sans-serif; font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: 1.2px;">Sevabot</span>
        </div>
        <div style="display: flex; gap: 0.5rem;">
            <div style="width: 6px; height: 6px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); opacity: 0.8;"></div>
            <div style="width: 5px; height: 5px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); opacity: 0.6;"></div>
            <div style="width: 4px; height: 4px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); opacity: 0.7;"></div>
        </div>
    </div>
    """

def get_landing_page_html():
    """Get complete landing page HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome to Isha Sevabot</title>
        {get_favicon_link()}
        <style>
            {get_landing_page_css()}
        </style>
    </head>
    <body>
        <div class="login-container">
            
            <!-- Welcome text -->
            <!-- <div class="welcome-text">🙏 Namaskaram, Welcome to</div> -->
            
            <!-- Isha Logo (bigger, with spacing) -->
            <div class="isha-logo">
                <img src="/images/isha-logo-2.svg" alt="Isha Logo" width="100" height="100" />
            </div>
            
            <!-- Sevabot title (closer to logo) -->
            <h1 class="title">SEVABOT</h1>
            
            <!-- Google Sign-in -->
            <div class="signin-section">
                <a href="/login" class="login-button-link">
                    <button class="gsi-material-button">
                        <div class="gsi-material-button-state"></div>
                        <div class="gsi-material-button-content-wrapper">
                            <div class="gsi-material-button-icon">
                                <!-- Correct Google “G” logo -->
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                                    <path fill="none" d="M0 0h48v48H0z"/>
                                </svg>
                            </div>
                            <span class="gsi-material-button-contents">Sign in with Google</span>
                        </div>
                    </button>
                </a>
            </div>
            
            <!-- Access restriction text -->
            <div class="domain-info">
                <strong>Access Restricted:</strong> Only whitelisted @sadhguru.org email addresses are permitted
            </div>
        </div>
    </body>
    </html>
    """

def get_landing_page_css():
    """Landing page CSS styles"""
    return """
        html, body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif;
            text-align: center;
            padding: 0;
            margin: 0;
            background: white;
            color: #333;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        .welcome-text {
            font-size: 1.1rem;
            margin-bottom: 1.2rem;
        }

        .isha-logo {
            margin-bottom: 0.8rem;
        }

        .title {
            font-size: 3.125rem;
            margin-top: 0.2rem;
            margin-bottom: 2rem;
            background: linear-gradient(135deg, #b8860b 0%, #cd853f 50%, #8b4513 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
            letter-spacing: 2px;
        }

        .login-container {
            background: white;
            border: 1px solid #ddd;    
            border-radius: 16px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
            padding: 3rem 2.5rem;
            text-align: center;
            max-width: 400px;
            width: 90%;
        }

        .isha-logo img {
            filter: drop-shadow(0 2px 8px rgba(0,0,0,0.1));
            max-width: 100%;
            height: auto;
        }

        /* Google Sign-in Button Styles */
        .signin-section {
            margin: 2.5rem 0;
            display: flex;
            justify-content: center;
        }
        
        .login-button-link {
            text-decoration: none;
            display: inline-block;
        }
        
        .gsi-material-button {
            -moz-user-select: none;
            -webkit-user-select: none;
            -ms-user-select: none;
            -webkit-appearance: none;
            background-color: #f2f2f2;
            border: none;
            border-radius: 20px;
            box-sizing: border-box;
            color: #1f1f1f;
            cursor: pointer;
            font-family: 'Roboto', arial, sans-serif;
            font-size: 14px;
            height: 40px;
            letter-spacing: 0.25px;
            outline: none;
            overflow: hidden;
            padding: 0 12px;
            position: relative;
            text-align: center;
            transition: background-color .218s, border-color .218s, box-shadow .218s;
            vertical-align: middle;
            white-space: nowrap;
            width: auto;
            max-width: 400px;
            min-width: min-content;
        }
        
        .gsi-material-button .gsi-material-button-icon {
            height: 20px;
            margin-right: 12px;
            min-width: 20px;
            width: 20px;
        }
        
        .gsi-material-button .gsi-material-button-content-wrapper {
            align-items: center;
            display: flex;
            flex-direction: row;
            flex-wrap: nowrap;
            height: 100%;
            justify-content: space-between;
            position: relative;
            width: 100%;
        }
        
        .gsi-material-button .gsi-material-button-contents {
            flex-grow: 1;
            font-family: 'Roboto', arial, sans-serif;
            font-weight: 500;
            overflow: hidden;
            text-overflow: ellipsis;
            vertical-align: top;
        }
        
        .gsi-material-button .gsi-material-button-state {
            transition: opacity .218s;
            bottom: 0;
            left: 0;
            opacity: 0;
            position: absolute;
            right: 0;
            top: 0;
        }
        
        .gsi-material-button:not(:disabled):hover {
            box-shadow: 0 1px 2px 0 rgba(60, 64, 67, .30), 0 1px 3px 1px rgba(60, 64, 67, .15);
        }
        
        .gsi-material-button:not(:disabled):hover .gsi-material-button-state {
            background-color: #001d35;
            opacity: 8%;
        }
        
        .domain-info {
            margin-top: 2rem;
            padding: 1rem;
            background: #fdf6ef;              /* very light brown instead of grey */
            border-radius: 12px;
            font-size: 0.9rem;
            color: #6c757d;
            border-left: 4px solid #cd853f;  /* lighter brown (Peru) instead of dark */
        }
        
        /* Mobile responsiveness */
        @media (max-width: 480px) {
            .login-container {
                padding: 2rem 1.5rem;
                margin: 1rem;
            }
            .title {
                font-size: 2rem;
            }
            .isha-logo img {
                width: 100px;
                height: 100px;
            }
        }
    """

def get_main_app_css():
    """Main application CSS styles - cleaned and optimized"""
    return """
        /* Hide Gradio footer */
        .gradio-container .footer, .gradio-container footer, footer[data-testid="footer"], .gradio-container > div:last-child { 
            display: none !important; 
        }
        
        /* Global font family */
        * { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Open Sans', 'Helvetica Neue', sans-serif !important;
            box-sizing: border-box !important;
        }

        /* Force specific row to be horizontal */
        .gradio-container .gradio-column .gradio-row:has(button) {
            display: flex !important;
            flex-direction: row !important;
            width: 100% !important;
            gap: 0.25rem !important;
        }

        .gradio-container .gradio-column .gradio-row:has(button) > * {
            flex: 1 !important;
            min-width: 0 !important;
        }
                
        /* Layout reset */
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            overflow-x: hidden !important;
        }
        
        /* Container */
        .gradio-container {
            width: 100vw !important;
            height: 100vh !important;
            margin: 0 !important;
            padding: 0.5rem !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            display: flex !important;
            flex-direction: column !important;
        }
        
        /* Text spacing */
        .gradio-container p, .gradio-container h1, .gradio-container h2, .gradio-container h3, 
        .gradio-container .markdown {
            margin: 0.5rem 0 !important;
            padding: 0.25rem !important;
        }

        /* ========== THEMED ACTION BUTTONS ========== */
 
        /* General reset */
        .new-chat-btn,
        .delete-chat-btn,
        .refresh-chat-btn {
            position: relative !important;
            font-size: 1.3rem !important;   /* make emoji bigger */
            color: black !important;        /* emoji/text color */
            border: none !important;
            border-radius: 12px !important;
            transition: all 0.2s ease !important;
        }

        /* New Chat: Indigo */
        .new-chat-btn {
            background-color: #667eea !important;
        }
        .new-chat-btn:hover {
            background-color: #5a67d8 !important;
        }

        /* Delete Chat: Plum */
        .delete-chat-btn {
            background-color: #a855f7 !important;
        }
        .delete-chat-btn:hover {
            background-color: #9333ea !important;
        }

        /* Refresh Chat: Deep Violet */
        .refresh-chat-btn {
            background-color: #6d28d9 !important;
        }
        .refresh-chat-btn:hover {
            background-color: #5b21b6 !important;
        }

        /* === Tooltips above instead of below === */
        .new-chat-btn::after,
        .delete-chat-btn::after,
        .refresh-chat-btn::after {
            position: absolute;
            bottom: 100%;                  /* place above button */
            left: 50%;
            transform: translateX(-50%) translateY(-6px);
            background: rgba(0,0,0,0.85);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s;
            z-index: 10000;
        }

        .new-chat-btn::after { content: "New Chat"; }
        .delete-chat-btn::after { content: "Delete Chat"; }
        .refresh-chat-btn::after { content: "Refresh"; }

        .new-chat-btn:hover::after,
        .delete-chat-btn:hover::after,
        .refresh-chat-btn:hover::after {
            opacity: 1;
        }


        
        /* Chat messages spacing */
        .chatbot .message, .chatbot .message-wrap {
            margin: 0.1rem 0 !important;
            padding: 0.3rem 0.5rem !important;
            line-height: 1.3 !important;
        }
        
        /* Header and main areas */
        .gradio-container > div:first-child {
            padding: 0.5rem !important;
            flex-shrink: 0 !important;
        }
        
        .gradio-container > div:nth-child(2) {
            flex: 1 !important;
            padding: 0 0.5rem !important;
        }
        
        /* Chat layout spacing */
        .gradio-tabs .tabitem .gradio-row {
            gap: 1rem !important;
        }
        
        /* Logo styling */
        .sevabot-logo { 
            height: 4rem !important;
            display: flex !important;
            align-items: center !important;
            overflow: hidden !important;
        }
        
        .sevabot-logo svg {
            width: 16rem !important;
            height: 4rem !important;
            flex-shrink: 0 !important;
        }
        
        /* Button styles */
        .send-btn-compact, .send-btn {
            background-color: #dc2626 !important;
            color: white !important;
            font-weight: 500 !important;
            min-width: 60px !important;
            max-width: 80px !important;
            padding: 0.5rem !important;
            font-size: 0.875rem !important;
        }
        
        .logout-btn { 
            background-color: #dc2626 !important; 
            color: white !important;
            min-width: 5rem !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.875rem !important;
        }
        
        /* Notifications */
        .notification {
            position: fixed !important;
            top: 1rem !important;
            right: 1rem !important;
            background: #10b981 !important;
            color: white !important;
            padding: 0.75rem 1.25rem !important;
            border-radius: 0.5rem !important;
            box-shadow: 0 0.25rem 0.75rem rgba(0,0,0,0.15) !important;
            z-index: 1000 !important;
            font-weight: 600 !important;
            animation: fadeInOut 5s ease-in-out forwards !important;
        }

        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateX(100%); }
            10% { opacity: 1; transform: translateX(0); }
            90% { opacity: 1; transform: translateX(0); }
            100% { opacity: 0; transform: translateX(100%); }
        }
        
        /* Unified Feedback Container */
        .feedback-container {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(147, 51, 234, 0.05) 100%) !important;
            border: 1px solid rgba(59, 130, 246, 0.2) !important;
            border-radius: 12px !important;
            padding: 1.25rem !important;
            margin: 1rem 0 !important;
        }

        .feedback-container .markdown {
            margin-bottom: 0.75rem !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            color: #1f2937 !important;
        }

        /* Radio Buttons - Hide all Gradio fieldset styling */
        .feedback-radio-inline > div > div {
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
        }

        .feedback-radio-inline fieldset {
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        .feedback-radio-inline legend {
            display: none !important;
        }

        /* Remove any colored circles/dots from Gradio's radio wrapper */
        .feedback-radio-inline .wrap::before,
        .feedback-radio-inline > div::before {
            display: none !important;
        }

        .feedback-radio-inline .wrap {
            display: flex !important;
            flex-direction: row !important;
            gap: 1.5rem !important;
            align-items: center !important;
            margin-bottom: 1rem !important;
            background: transparent !important;
        }

        .feedback-radio-inline input[type="radio"] {
            appearance: auto !important;
            -webkit-appearance: radio !important;
            width: 1.25rem !important;
            height: 1.25rem !important;
            cursor: pointer !important;
            margin-right: 0.5rem !important;
        }

        .feedback-radio-inline input[type="radio"][value="✅ Fully"] {
            accent-color: #16a34a !important;
        }
        .feedback-radio-inline input[type="radio"][value="⚠️ Partially"] {
            accent-color: #eab308 !important;
        }
        .feedback-radio-inline input[type="radio"][value="❌ Nopes"] {
            accent-color: #dc2626 !important;
        }

        .feedback-radio-inline label {
            font-weight: 500 !important;
            font-size: 1rem !important;
            color: #1f2937 !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
        }

        /* Textbox - Light background matching container */
        .feedback-remarks {
            background: transparent !important;
        }

        .feedback-remarks textarea {
            background: rgba(255, 255, 255, 0.8) !important;
            border: 1px solid #d1d5db !important;
            border-radius: 8px !important;
            font-size: 0.95rem !important;
            padding: 0.75rem !important;
            resize: vertical !important;
            color: #1f2937 !important;
            min-height: 80px !important;
        }

        .feedback-remarks textarea:focus {
            background: white !important;
            border-color: #3b82f6 !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        }

        /* Submit Button - Force two lines */
        .feedback-submit-btn {
            display: flex !important;
            align-items: stretch !important;
        }

        .feedback-submit-btn button {
            width: 100% !important;
            min-width: 110px !important;
            max-width: 110px !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            padding: 0.6rem 0.5rem !important;
            border-radius: 8px !important;
            white-space: normal !important;
            background-color: #3b82f6 !important;
            color: white !important;
            border: none !important;
            cursor: pointer !important;
            line-height: 1.3 !important;
            text-align: center !important;
            word-wrap: break-word !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        .feedback-submit-btn button:hover {
            background-color: #2563eb !important;
        }

        /* Section backgrounds */
        .admin-section, .files-section {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            border-radius: 0.75rem !important;
            padding: 1rem !important;
            margin: 0.5rem 0 !important;
        }
        
        .spoc-section {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(251, 191, 36, 0.1) 100%) !important;
            border: 1px solid rgba(245, 158, 11, 0.2) !important;
            border-radius: 0.75rem !important;
            padding: 1rem !important;
            margin: 0.5rem 0 !important;
        }
        
        /* Copyright footer */
        .copyright-footer {
            text-align: center !important;
            color: #9ca3af !important;
            font-size: 0.875rem !important;
            padding: 1rem 0.5rem !important;
            margin-top: auto !important;
            flex-shrink: 0 !important;
            background: white !important;
        }
        
        /* Scrollbar */
        html { scrollbar-gutter: stable; }
        
        /* Mobile */
        @media (max-width: 48rem) {
            .gradio-container { padding: 0.25rem !important; }
            .sevabot-logo svg { width: 12rem !important; height: 3rem !important; }
        }
        
        /* Enhanced styling for in-place clarification editing */
        .clarification-text {
            border: 2px solid #e5e7eb !important;
            transition: border-color 0.3s ease !important;
        }

        .clarification-text:focus {
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        }

        /* Edit buttons styling */
        .clarification-edit-buttons {
            margin-top: 0.5rem !important;
            padding: 0.5rem !important;
            background: #f8fafc !important;
            border-radius: 0.5rem !important;
            border: 1px solid #e2e8f0 !important;
        }

        /* Enhanced notification styles */
        .notification {
            padding: 12px 16px !important;
            border-radius: 8px !important;
            margin: 8px 0 !important;
            background: #10b981 !important;
            color: white !important;
            font-weight: 500 !important;
            border: none !important;
            animation: fadeIn 0.3s ease-in !important;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Table row hover effects for better selection */
        .dataframe tbody tr:hover {
            background-color: #f1f5f9 !important;
            cursor: pointer !important;
        }

        .dataframe tbody tr.selected {
            background-color: #dbeafe !important;
            border-left: 4px solid #3b82f6 !important;
        }
    """