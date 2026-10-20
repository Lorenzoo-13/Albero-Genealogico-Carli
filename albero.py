import streamlit as st
import graphviz
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Albero Genealogico Carli", layout="wide")

# CSS di Stampa ottimizzato per A4 verticale in pagina unica senza tagli
st.markdown("""
    <style>
    @media print {
        @page {
            size: A4 portrait;
            margin: 4mm;
        }
        
        html, body, [data-testid="stAppViewContainer"], .main, .block-container {
            background-color: #ffffff !important;
            color: #000000 !important;
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
        }
        
        [data-testid="stSidebar"], 
        header, 
        footer, 
        .stButton, 
        .stDownloadButton,
        h1,
        [data-testid="stHeader"] {
            display: none !important;
        }
        
        /* Contenitore grafico centrato e scalato per rientrare interamente nel foglio */
        [data-testid="stGraphvizChart"] {
            width: 100% !important;
            height: 100% !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 0 auto !important;
        }
        
        /* Ridimensiona l'SVG per farlo stare comodamente in un solo foglio verticale */
        [data-testid="stGraphvizChart"] svg {
            max-width: 100% !important;
            max-height: 94vh !important;
            width: auto !important;
            height: auto !important;
            transform: scale(0.78);
            transform-origin: top center;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Connessione sicura a Google Sheets tramite Secrets
@st.cache_resource
def get_gspread_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

def carica_dati():
    try:
        client = get_gspread_client()
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        rows = sheet.get_all_values()
        if not rows or len(rows) <= 1:
            return []
        
        header = rows[0]
        data = []
        for row in rows[1:]:
            row_data = row + [""] * (len(header) - len(row))
            record = dict(zip(header, row_data))
            if record.get("id"):
                data.append(record)
        return data
    except Exception as e:
        st.error(f"Errore nella lettura da Google Sheets: {e}")
        return []

def salva_dati(membri):
    try:
        client = get_gspread_client()
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(sheet_url).sheet1
        sheet.clear()
        
        colonne = ["id", "nome", "cognome", "nascita", "comune", "cf", "telefono", "deceduto", "genitore", "note"]
        
        rows = [colonne]
        if membri:
            for m in membri:
                row = [str(m.get(col, "")) for col in colonne]
                rows.append(row)
            
        sheet.update(rows)
    except Exception as e:
        st.error(f"Errore nel salvataggio su Google Sheets: {e}")

# Inizializzazione sessione
if "membri" not in st.session_state:
    st.session_state.membri = carica_dati()

# --- SIDEBAR: GESTIONE ---
st.sidebar.title("📌 Gestione Albero")

# 1. Aggiungi Persona
with st.sidebar.expander("➕ Aggiungi Persona", expanded=False):
    nome = st.text_input("Nome", key="add_nome")
    cognome = st.text_input("Cognome", key="add_cognome")
    data_nascita = st.text_input("Data di Nascita (gg/mm/aaaa)", key="add_nascita")
    comune = st.text_input("Comune di Nascita", key="add_comune")
    cf = st.text_input("Codice Fiscale", key="add_cf")
    telefono = st.text_input("Numero di Telefono", key="add_telefono")
    deceduto = st.checkbox("Deceduto/a", key="add_deceduto")
    
    opzioni_genitori = ["Nessuno (Capostipite)"] + [m["id"] for m in st.session_state.membri if m.get("id")]
    genitore_scelto = st.selectbox("Genitore", opzioni_genitori, key="add_genitore")
    
    if st.button("Aggiungi alla Famiglia"):
        if nome and cognome:
            nuovo_id = f"{nome} {cognome}"
            if any(m.get("id") == nuovo_id for m in st.session_state.membri):
                st.sidebar.error("Una persona con questo nome e cognome esiste già!")
            else:
                nuovo_membro = {
                    "id": nuovo_id,
                    "nome": nome,
                    "cognome": cognome,
                    "nascita": data_nascita,
                    "comune": comune,
                    "cf": cf,
                    "telefono": telefono,
                    "deceduto": "SÌ" if deceduto else "NO",
                    "genitore": "" if genitore_scelto == "Nessuno (Capostipite)" else genitore_scelto,
                    "note": ""
                }
                st.session_state.membri.append(nuovo_membro)
                salva_dati(st.session_state.membri)
                st.sidebar.success(f"{nuovo_id} aggiunto/a con successo!")
                st.rerun()
        else:
            st.sidebar.error("Nome e Cognome sono obbligatori!")

# 2. Modifica Persona
with st.sidebar.expander("✏️ Modifica Persona", expanded=True):
    if st.session_state.membri:
        lista_ids = [m["id"] for m in st.session_state.membri if m.get("id")]
        persona_da_modificare_id = st.selectbox("Seleziona Persona da Modificare", lista_ids, key="mod_select")
        
        membro_target = next((m for m in st.session_state.membri if m.get("id") == persona_da_modificare_id), None)
        
        if membro_target:
            mod_nome = st.text_input("Nome", value=str(membro_target.get("nome", "")), key="mod_nome")
            mod_cognome = st.text_input("Cognome", value=str(membro_target.get("cognome", "")), key="mod_cognome")
            mod_nascita = st.text_input("Data di Nascita", value=str(membro_target.get("nascita", "")), key="mod_nascita")
            mod_comune = st.text_input("Comune di Nascita", value=str(membro_target.get("comune", "")), key="mod_comune")
            mod_cf = st.text_input("Codice Fiscale", value=str(membro_target.get("cf", "")), key="mod_cf")
            mod_telefono = st.text_input("Numero di Telefono", value=str(membro_target.get("telefono", "")), key="mod_telefono")
            
            is_deceduto = True if membro_target.get("deceduto") in ["SÌ", True, "True", "Sì", "si"] else False
            mod_deceduto = st.checkbox("Deceduto/a", value=is_deceduto, key="mod_deceduto")
            
            altri_membri = ["Nessuno (Capostipite)"] + [m["id"] for m in st.session_state.membri if m.get("id") and m.get("id") != persona_da_modificare_id]
            genitore_attuale = membro_target.get("genitore", "")
            idx_genitore = altri_membri.index(genitore_attuale) if genitore_attuale in altri_membri else 0
            mod_genitore = st.selectbox("Genitore", altri_membri, index=idx_genitore, key="mod_genitore")
            
            if st.button("Salva Modifiche", type="primary"):
                nuovo_id = f"{mod_nome} {mod_cognome}"
                old_id = membro_target["id"]
                
                if nuovo_id != old_id and any(m.get("id") == nuovo_id for m in st.session_state.membri):
                    st.sidebar.error("Esiste già un'altra persona con questo Nome e Cognome!")
                else:
                    if nuovo_id != old_id:
                        for m in st.session_state.membri:
                            if m.get("genitore") == old_id:
                                m["genitore"] = nuovo_id
                    
                    membro_target["id"] = nuovo_id
                    membro_target["nome"] = mod_nome
                    membro_target["cognome"] = mod_cognome
                    membro_target["nascita"] = mod_nascita
                    membro_target["comune"] = mod_comune
                    membro_target["cf"] = mod_cf
                    membro_target["telefono"] = mod_telefono
                    membro_target["deceduto"] = "SÌ" if mod_deceduto else "NO"
                    membro_target["genitore"] = "" if mod_genitore == "Nessuno (Capostipite)" else mod_genitore
                    
                    salva_dati(st.session_state.membri)
                    st.sidebar.success("Modifiche salvate con successo!")
                    st.rerun()
    else:
        st.write("Nessun membro presente da modificare.")

# 3. Rimuovi Persona
with st.sidebar.expander("🗑️ Rimuovi Persona", expanded=False):
    if st.session_state.membri:
        persona_da_eliminare = st.selectbox(
            "Seleziona la persona da rimuovere",
            [m["id"] for m in st.session_state.membri if m.get("id")],
            key="del_select"
        )
        if st.button("Elimina Persona"):
            st.session_state.membri = [m for m in st.session_state.membri if m.get("id") != persona_da_eliminare]
            for m in st.session_state.membri:
                if m.get("genitore") == persona_da_eliminare:
                    m["genitore"] = ""
            salva_dati(st.session_state.membri)
            st.sidebar.success(f"{persona_da_eliminare} eliminato/a!")
            st.rerun()
    else:
        st.write("Nessun membro presente.")

# --- VISUALIZZAZIONE GRAFICA E STAMPA ---
st.title("🌳 Albero Genealogico Condiviso")

if st.session_state.membri:
    col1, col2 = st.columns([1, 1])
    
    # Configurazione Graphviz pulita: una sola freccia e dimensioni A4 verticale
    dot = graphviz.Digraph(comment="Albero Genealogico", format="png")
    dot.attr(
        rankdir="LR", 
        size="7.0,9.2!",       # Mantiene l'albero dentro i margini A4 verticali
        ratio="compress",
        nodesep="0.08",        # Spaziatura verticale compatta per far entrare Lidia Toniolo in fondo
        ranksep="0.30",        # Spaziatura tra generazioni
        concentrate="true"     # FONDE le frecce duplicate in un'unica freccia!
    )
    
    # Stile nodi pulito
    dot.attr(
        "node", 
        shape="box", 
        style="rounded,filled", 
        fillcolor="#f8f9fa", 
        fontname="Helvetica", 
        fontsize="7.5", 
        margin="0.1,0.06"
    )
    
    # Stile frecce: forza 1 sola freccia singola
    dot.attr(
        "edge",
        dir="forward",
        arrowsize="0.7",
        penwidth="1.0"
    )

    # Creazione dei nodi
    for m in st.session_state.membri:
        if not m.get("id"):
            continue
        
        # Etichetta formattata per stare dentro i rettangoli
        label = f"<font point-size='8.5'><b>{m['nome']} {m['cognome']}</b></font>"
        if m.get("nascita"):
            label += f"<br/><font point-size='7' color='#444444'>Nato/a: {m['nascita']}</font>"
        if m.get("comune"):
            label += f"<br/><font point-size='7' color='#444444'>Comune: {m['comune']}</font>"
        if m.get("cf"):
            label += f"<br/><font point-size='6.5' color='#444444'>CF: {m['cf']}</font>"
        if m.get("telefono"):
            label += f"<br/><font point-size='7' color='#444444'>Tel: {m['telefono']}</font>"
        if m.get("note"):
            label += f"<br/><font point-size='6.5' color='#444444'>Note: {m['note']}</font>"
        if m.get("deceduto") in ["SÌ", "Sì", "SI", True, "True"]:
            label += "<br/><font point-size='7' color='#d9534f'><b>[DECEDUTO/A]</b></font>"

        dot.node(str(m["id"]), label=f"<{label}>")

    # Creazione dei collegamenti senza duplicati (risolve le 3 frecce)
    archi_aggiunti = set()
    for m in st.session_state.membri:
        genitore_id = m.get("genitore")
        figlio_id = m.get("id")
        
        if genitore_id and figlio_id:
            coppia = (str(genitore_id), str(figlio_id))
            if coppia not in archi_aggiunti:
                dot.edge(str(genitore_id), str(figlio_id))
                archi_aggiunti.add(coppia)

    try:
        png_bytes = dot.pipe(format="png")
    except Exception as e:
        png_bytes = None

    with col1:
        if png_bytes:
            st.download_button(
                label="🖼️ Scarica Immagine (PNG)",
                data=png_bytes,
                file_name="albero_genealogico_carli.png",
                mime="image/png",
                use_container_width=True
            )
        else:
            st.button("🖼️ Scarica Immagine (PNG)", disabled=True, use_container_width=True)
    
    with col2:
        if st.button("🖨️ Stampa Pagina / Salva in PDF", use_container_width=True):
            components.html("<script>window.parent.print();</script>", height=0, width=0)

    st.graphviz_chart(dot, use_container_width=True)
else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")
