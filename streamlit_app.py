"""
app.py — Generador de Agenda Semanal
=====================================
Ejecutar:
    streamlit run app.py

Requiere en la misma carpeta:
    data_loader.py
    agenda_flyer.py
    Nishi.png, Cueva.png, Victory.png  (y demás logos de eventos)
"""

import streamlit as st
import tempfile
from datetime import date, timedelta
from pathlib import Path

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Agenda Semanal · Nishi",
    page_icon="🗓️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Estilos ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,400;0,700;1,700&family=Barlow:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0a0a10 0%, #0d1520 50%, #0a0a16 100%);
        min-height: 100vh;
    }
    .block-container { padding-top: 1rem !important; max-width: 760px !important; }

    .app-header { text-align: center; padding: 2rem 0 1.5rem; }
    .app-header h1 {
        font-family: 'Barlow Condensed', sans-serif;
        font-style: italic; font-weight: 700;
        font-size: clamp(2rem, 6vw, 3.5rem);
        color: #f2ede1; margin: 0; letter-spacing: 0.02em;
        text-shadow: 0 2px 20px rgba(91,157,213,0.3);
    }
    .app-header .accent-line {
        width: 80px; height: 3px; background: #5b9dd5;
        margin: 0.75rem auto 0; border-radius: 2px;
    }

    .login-card {
        background: rgba(22,22,34,0.9);
        border: 1px solid rgba(91,157,213,0.25);
        border-radius: 16px; padding: 2.5rem 2rem;
        max-width: 420px; margin: 2rem auto;
        box-shadow: 0 8px 40px rgba(0,0,0,0.4);
    }
    .login-card h2 {
        font-family: 'Barlow Condensed', sans-serif;
        font-style: italic; color: #5b9dd5;
        font-size: 1.6rem; margin-bottom: 1.5rem; text-align: center;
    }

    .stTextInput > label, .stDateInput > label,
    .stSelectbox > label, .stMultiSelect > label {
        color: #b9b2a5 !important; font-size: 0.85rem !important;
        font-weight: 500 !important; letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
    }
    .stTextInput input {
        background: rgba(10,10,16,0.8) !important;
        border: 1px solid rgba(91,157,213,0.3) !important;
        border-radius: 8px !important; color: #f2ede1 !important;
    }
    .stTextInput input:focus {
        border-color: #5b9dd5 !important;
        box-shadow: 0 0 0 2px rgba(91,157,213,0.15) !important;
    }

    .stButton > button {
        width: 100%;
        background: #5b9dd5 !important; color: #0a0a10 !important;
        border: none !important; border-radius: 8px !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-style: italic !important; font-weight: 700 !important;
        font-size: 1.1rem !important; letter-spacing: 0.08em !important;
        padding: 0.6rem 1rem !important; text-transform: uppercase !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: #7ab3e0 !important; transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(91,157,213,0.4) !important;
    }

    .stDownloadButton > button {
        width: 100%; background: transparent !important;
        color: #5b9dd5 !important; border: 2px solid #5b9dd5 !important;
        border-radius: 8px !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-style: italic !important; font-weight: 700 !important;
        font-size: 1.1rem !important; letter-spacing: 0.08em !important;
        text-transform: uppercase !important; transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(91,157,213,0.1) !important;
        transform: translateY(-1px) !important;
    }

    .stImage img {
        border-radius: 12px;
        box-shadow: 0 8px 40px rgba(0,0,0,0.5);
        width: 100% !important;
    }
    hr { border-color: rgba(91,157,213,0.2) !important; margin: 1.5rem 0 !important; }
    .stSpinner > div { border-top-color: #5b9dd5 !important; }
</style>
""", unsafe_allow_html=True)

# ── Credenciales desde variables de entorno (st.secrets) ─────────────────────
# Definir en .streamlit/secrets.toml o en Streamlit Cloud → Settings → Secrets
USUARIOS = {
    st.secrets["APP_USER"]: st.secrets["APP_PASSWORD"]
}

SHEET_URL_DEFAULT = st.secrets["SHEET_URL"]

LOGOS_DEFAULT = ["Nishi.png", "Cueva.png", "Victory.png"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def proximo_lunes() -> date:
    hoy = date.today()
    dias = (7 - hoy.weekday()) % 7
    return hoy + timedelta(days=dias if dias else 7)


def lunes_de(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ── Estado ────────────────────────────────────────────────────────────────────
for k, v in [("flyer_bytes", None), ("flyer_nombre", "agenda.png")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>Agenda Semanal</h1>
    <div class="accent-line"></div>
</div>
""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
# APP PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("---")

# ── Controles ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    fecha_sel = st.date_input(
        "Semana a generar",
        value=proximo_lunes(),
        help="Selecciona cualquier día — se ajustará al lunes de esa semana",
    )
    fecha_lunes = lunes_de(fecha_sel)
    st.caption(f"Semana del **{fecha_lunes.strftime('%d/%m/%Y')}** "
               f"al **{(fecha_lunes + timedelta(days=6)).strftime('%d/%m/%Y')}**")

with col2:
    sheet_url = st.text_input(
        "URL del Google Sheet",
        value=SHEET_URL_DEFAULT,
        help="Debe estar publicado como CSV",
    )

st.markdown("---")

# ── Botón generar ─────────────────────────────────────────────────────────────
if st.button("🗓  Generar Agenda"):
    lunes_str = fecha_lunes.strftime("%Y-%m-%d")
    error = None

    try:
        from data_loader import cargar_semana
        from agenda_flyer import generar_agenda

        with st.spinner("Leyendo eventos del sheet..."):
            semana, week_start, semana_label = cargar_semana(
                fuente=sheet_url.strip(),
                lunes=lunes_str,
            )

        with st.spinner("Generando imagen..."):
            logos = [p for p in LOGOS_DEFAULT if Path(p).exists()]
            tmp   = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()

            generar_agenda(
                semana       = semana,
                week_start   = week_start,
                semana_label = semana_label,
                logos        = logos,
                output       = tmp.name,
                direccion    = "Av. 12E # 2-100 Quinta Oriental",
                subtitulo    = "Cueva del Búho · Victory Road · Nishi",
            )

        with open(tmp.name, "rb") as f:
            st.session_state.flyer_bytes  = f.read()
            st.session_state.flyer_nombre = f"agenda_{lunes_str}.png"

        st.success(f"✅ Agenda generada — {semana_label}")

    except ConnectionError as e:
        error = ("⚠️ No se pudo leer el Sheet",
                 "Asegúrate de publicarlo como CSV:\n"
                 "Archivo → Compartir → Publicar en la web → CSV")
    except FileNotFoundError as e:
        error = ("⚠️ Archivo no encontrado", str(e))
    except Exception as e:
        error = ("⚠️ Error inesperado", str(e))

    if error:
        st.error(f"**{error[0]}**\n\n{error[1]}")

# ── Resultado ─────────────────────────────────────────────────────────────────
if st.session_state.flyer_bytes:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image(st.session_state.flyer_bytes, use_column_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label            = "⬇  Descargar PNG",
        data             = st.session_state.flyer_bytes,
        file_name        = st.session_state.flyer_nombre,
        mime             = "image/png",
        use_container_width = True,
    )
