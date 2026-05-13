"""Premium CSS styles for the AI Travel Planner UI."""

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --primary: #6C63FF;
        --primary-light: #8B85FF;
        --primary-dark: #4F46E5;
        --accent: #00D4AA;
        --accent-light: #34EDCA;
        --warning: #F59E0B;
        --bg-dark: #0A0E17;
        --bg-card: rgba(18, 24, 38, 0.88);
        --bg-card-hover: rgba(28, 36, 54, 0.95);
        --bg-glass: rgba(255, 255, 255, 0.03);
        --bg-selected: rgba(108, 99, 255, 0.12);
        --text-primary: #E6EDF3;
        --text-secondary: #8B949E;
        --text-dim: #484F58;
        --border: rgba(108, 99, 255, 0.15);
        --border-active: rgba(108, 99, 255, 0.5);
        --glow: 0 0 20px rgba(108, 99, 255, 0.15);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif !important;
        color: var(--text-primary);
    }

    .stApp {
        background: linear-gradient(160deg, #0A0E17 0%, #111827 50%, #0A0E17 100%);
    }

    #MainMenu, footer, header { visibility: hidden; }

    .block-container {
        max-width: 1100px;
        padding: 1.5rem 1rem 4rem;
    }

    /* ── Text inputs ── */
    .stTextInput > div > div > input {
        background: var(--bg-card) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        font-size: 15px !important;
        color: var(--text-primary) !important;
        transition: all 0.3s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.12), var(--glow) !important;
    }
    .stTextInput label {
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        letter-spacing: 0.3px !important;
    }

    /* ── Buttons ── */
    div.stButton > button {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.65em 2em !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        letter-spacing: 0.3px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(108, 99, 255, 0.35) !important;
    }
    div.stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── Hero ── */
    .hero-wrap {
        text-align: center;
        padding: 30px 0 10px;
        position: relative;
    }
    .hero-icon { font-size: 48px; margin-bottom: 8px; }
    .hero-title {
        font-size: 44px;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF 0%, #00D4AA 50%, #6C63FF 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shimmer 4s ease-in-out infinite;
        line-height: 1.15;
        margin-bottom: 6px;
    }
    @keyframes shimmer {
        0%, 100% { background-position: 0% center; }
        50% { background-position: 100% center; }
    }
    .hero-sub {
        font-size: 15px;
        color: var(--text-secondary);
        max-width: 600px;
        margin: 0 auto 20px;
        line-height: 1.6;
    }

    /* ── Step indicator ── */
    .step-bar {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 20px 0 28px;
    }
    .step-pill {
        padding: 8px 22px;
        border-radius: 30px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.5px;
        border: 1.5px solid var(--border);
        color: var(--text-dim);
        background: var(--bg-glass);
        transition: all 0.3s;
    }
    .step-active {
        border-color: var(--primary);
        color: var(--primary-light);
        background: var(--bg-selected);
        box-shadow: var(--glow);
    }
    .step-done {
        border-color: var(--accent);
        color: var(--accent);
        background: rgba(0,212,170,0.08);
    }

    /* ── Glass cards ── */
    .glass-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 22px;
        margin: 10px 0;
        backdrop-filter: blur(16px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .glass-card:hover {
        background: var(--bg-card-hover);
        border-color: var(--border-active);
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.3);
    }
    .glass-card-selected {
        border-color: var(--primary) !important;
        background: var(--bg-selected) !important;
        box-shadow: 0 0 0 2px rgba(108,99,255,0.2), var(--glow) !important;
    }

    /* ── Section headers ── */
    .section-hdr {
        font-size: 20px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 32px 0 6px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-hdr .icon { font-size: 22px; }
    .section-sub {
        font-size: 13px;
        color: var(--text-secondary);
        margin: 0 0 16px;
    }

    /* ── Flight / hotel cards ── */
    .opt-card {
        background: var(--bg-card);
        border: 1.5px solid var(--border);
        border-radius: 14px;
        padding: 18px 20px;
        margin: 8px 0;
        cursor: pointer;
        transition: all 0.25s;
        position: relative;
    }
    .opt-card:hover {
        border-color: var(--primary-light);
        background: var(--bg-card-hover);
    }
    .opt-selected {
        border-color: var(--primary) !important;
        background: var(--bg-selected) !important;
        box-shadow: inset 0 0 0 1px var(--primary), var(--glow);
    }
    .opt-badge {
        position: absolute;
        top: -8px;
        right: 14px;
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: white;
        font-size: 10px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 6px;
        letter-spacing: 0.5px;
    }
    .opt-price {
        font-size: 22px;
        font-weight: 800;
        color: var(--accent);
    }
    .opt-name {
        font-size: 16px;
        font-weight: 700;
        color: var(--text-primary);
    }
    .opt-detail {
        font-size: 13px;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    .opt-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* ── Cost badge ── */
    .cost-strip {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        margin: 12px 0 20px;
    }
    .cost-chip {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px 22px;
        text-align: center;
        flex: 1;
        min-width: 160px;
    }
    .cost-chip .val {
        font-size: 24px;
        font-weight: 800;
        color: var(--accent);
    }
    .cost-chip .lbl {
        font-size: 11px;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 2px;
    }

    /* ── Star rating ── */
    .stars { color: var(--warning); letter-spacing: 1px; }

    /* ── Starter prompt buttons ── */
    .starter-btn button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        font-size: 13px !important;
        text-align: left !important;
        transition: all 0.25s !important;
    }
    .starter-btn button:hover {
        border-color: var(--primary) !important;
        color: var(--primary-light) !important;
        background: var(--bg-selected) !important;
        transform: none !important;
        box-shadow: none !important;
    }

    /* ── Download buttons ── */
    .stDownloadButton > button {
        background: var(--bg-card) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--primary-light) !important;
    }

    /* ── Misc ── */
    hr { border-color: var(--border) !important; opacity: 0.3; }
    .stRadio label { color: var(--text-secondary) !important; }
    .stRadio [role="radiogroup"] { gap: 0 !important; }

    /* ── Confirmation button ── */
    .confirm-btn button {
        background: linear-gradient(135deg, var(--accent), #00B894) !important;
        font-weight: 700 !important;
    }
    .confirm-btn button:hover {
        box-shadow: 0 8px 30px rgba(0,212,170,0.35) !important;
    }

    /* ── Sidebar polish ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A0E17 0%, #0F1623 100%) !important;
        border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 10px 14px !important;
        border-radius: 10px !important;
        transition: all 0.25s !important;
        margin: 2px 0 !important;
        cursor: pointer !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: var(--bg-glass) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
        background: var(--bg-selected) !important;
        border: 1px solid var(--border-active) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] {
        gap: 0 !important;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 14px 18px !important;
    }
</style>
"""
