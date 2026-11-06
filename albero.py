import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pyvis.network import Network

st.set_page_config(page_title="Albero Genealogico Carli", layout="wide")

# CSS di Stampa ottimizzato
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
        
        colonne = ["id", "nome", "cognome", "nascita", "comune", "cf", "telefono", "deceduto", "genitore", "coniuge", "ruolo_coniuge", "note"]
        
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
    
    opzioni_coniugi = ["Nessuno"] + [m["id"] for m in st.session_state.membri if m.get("id")]
    coniuge_scelto = st.selectbox("Coniuge (Moglie/Marito)", opzioni_coniugi, key="add_coniuge")
    ruolo_coniuge = st.radio("Ruolo del nuovo membro:", ["Moglie", "Marito"], key="add_ruolo_coniuge", horizontal=True)
    
    if st.button("Aggiungi alla Famiglia"):
        if nome and cognome:
            nuovo_id = f"{nome} {cognome}"
            if any(m.get("id") == nuovo_id for m in st.session_state.membri):
                st.sidebar.error("Una persona con questo nome e cognome esiste già!")
            else:
                coniuge_valore = "" if coniuge_scelto == "Nessuno" else coniuge_scelto
                ruolo_valore = ruolo_coniuge if coniuge_valore else ""
                
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
                    "coniuge": coniuge_valore,
                    "ruolo_coniuge": ruolo_valore,
                    "note": ""
                }
                st.session_state.membri.append(nuovo_membro)
                
                if coniuge_valore:
                    ruolo_reciproco = "Marito" if ruolo_coniuge == "Moglie" else "Moglie"
                    for m in st.session_state.membri:
                        if m.get("id") == coniuge_valore:
                            m["coniuge"] = nuovo_id
                            m["ruolo_coniuge"] = ruolo_reciproco
                            
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
            
            altri_coniugi = ["Nessuno"] + [m["id"] for m in st.session_state.membri if m.get("id") and m.get("id") != persona_da_modificare_id]
            coniuge_attuale = membro_target.get("coniuge", "")
            idx_coniuge = altri_coniugi.index(coniuge_attuale) if coniuge_attuale in altri_coniugi else 0
            mod_coniuge = st.selectbox("Coniuge", altri_coniugi, index=idx_coniuge, key="mod_coniuge")
            
            ruolo_attuale = membro_target.get("ruolo_coniuge", "Moglie")
            idx_ruolo = 0 if ruolo_attuale != "Marito" else 1
            mod_ruolo = st.radio("Ruolo di questa persona rispetto al coniuge:", ["Moglie", "Marito"], index=idx_ruolo, key="mod_ruolo", horizontal=True)
            
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
                            if m.get("coniuge") == old_id:
                                m["coniuge"] = nuovo_id
                    
                    membro_target["id"] = nuovo_id
                    membro_target["nome"] = mod_nome
                    membro_target["cognome"] = mod_cognome
                    membro_target["nascita"] = mod_nascita
                    membro_target["comune"] = mod_comune
                    membro_target["cf"] = mod_cf
                    membro_target["telefono"] = mod_telefono
                    membro_target["deceduto"] = "SÌ" if mod_deceduto else "NO"
                    membro_target["genitore"] = "" if mod_genitore == "Nessuno (Capostipite)" else mod_genitore
                    
                    nuovo_coniuge_valore = "" if mod_coniuge == "Nessuno" else mod_coniuge
                    membro_target["coniuge"] = nuovo_coniuge_valore
                    membro_target["ruolo_coniuge"] = mod_ruolo if nuovo_coniuge_valore else ""
                    
                    if nuovo_coniuge_valore:
                        ruolo_reciproco = "Marito" if mod_ruolo == "Moglie" else "Moglie"
                        for m in st.session_state.membri:
                            if m.get("id") == nuovo_coniuge_valore:
                                m["coniuge"] = nuovo_id
                                m["ruolo_coniuge"] = ruolo_reciproco
                    
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
                if m.get("coniuge") == persona_da_eliminare:
                    m["coniuge"] = ""
                    m["ruolo_coniuge"] = ""
            salva_dati(st.session_state.membri)
            st.sidebar.success(f"{persona_da_eliminare} eliminato/a!")
            st.rerun()
    else:
        st.write("Nessun membro presente.")

# --- VISUALIZZAZIONE GRAFICA INTERATTIVA CON PYVIS ---
st.title("🌳 Albero Genealogico Interattivo (PyVis)")

if st.session_state.membri:
    net = Network(height="750px", width="100%", directed=True, notebook=False, cdn_resources='remote')
    
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 90,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "minVelocity": 0.75
      },
      "interaction": {
        "dragNodes": true,
        "zoomView": true
      }
    }
    """)

    # 1. Aggiunta Nodi
    for m in st.session_state.membri:
        if not m.get("id"):
            continue
        
        label = f"{m['nome']} {m['cognome']}"
        if m.get("ruolo_coniuge"):
            label += f" ({m['ruolo_coniuge']})"
        
        title_info = f"<b>{m['nome']} {m['cognome']}</b>"
        if m.get("nascita"): title_info += f"<br>Nato/a: {m['nascita']}"
        if m.get("comune"): title_info += f"<br>Comune: {m['comune']}"
        if m.get("cf"): title_info += f"<br>CF: {m['cf']}"
        if m.get("telefono"): title_info += f"<br>Tel: {m['telefono']}"
        if m.get("deceduto") in ["SÌ", "Sì", "SI", True, "True"]:
            title_info += "<br><span style='color:red;'><b>DECEDUTO/A</b></span>"

        colore_nodo = "#FFC0CB" if m.get("ruolo_coniuge") == "Moglie" else "#87CEFA"
        if not m.get("ruolo_coniuge") and m.get("genitore") == "":
            colore_nodo = "#ffcc00"

        net.add_node(
            str(m["id"]), 
            label=label, 
            title=title_info, 
            color=colore_nodo,
            shape="box",
            font={"size": 14}
        )

    # 2. Aggiunta Collegamenti
    archi_aggiunti = set()
    for m in st.session_state.membri:
        genitore_id = m.get("genitore")
        figlio_id = m.get("id")
        coniuge_id = m.get("coniuge")
        
        if genitore_id and figlio_id:
            coppia = (str(genitore_id), str(figlio_id))
            if coppia not in archi_aggiunti:
                net.add_edge(str(genitore_id), str(figlio_id), color="#888888", width=2)
                archi_aggiunti.add(coppia)
                
        if coniuge_id and figlio_id:
            coppia_coniugi = tuple(sorted([str(figlio_id), str(coniuge_id)]))
            if coppia_coniugi not in archi_aggiunti:
                net.add_edge(
                    str(figlio_id), 
                    str(coniuge_id), 
                    color="#d9534f", 
                    width=3, 
                    dashes=True, 
                    arrows=""
                )
                archi_aggiunti.add(coppia_coniugi)

    html_path = "albero_interattivo.html"
    net.save_graph(html_path)

    with open(html_path, 'r', encoding='utf-8') as f:
        html_data = f.read()
    
    components.html(html_data, height=800, scrolling=True)

else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")
