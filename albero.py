import streamlit as st
import graphviz
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Albero Genealogico Carli", layout="wide")

# CSS per la stampa
st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"], 
        header, 
        footer, 
        .stButton, 
        .stDownloadButton {
            display: none !important;
        }
        .main .block-container {
            max-width: 100% !important;
            padding: 0 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Connessione a Google Sheets tramite gspread e secrets di Streamlit
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
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return []
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Errore nella lettura da Google Sheets: {e}")
        return []

def salva_dati(membri):
    try:
        client = get_gspread_client()
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(sheet_url).sheet1
        sheet.clear()
        df = pd.DataFrame(membri)
        # Inserisce intestazioni e dati nel foglio
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Errore nel salvataggio su Google Sheets: {e}")

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
        
        # Recupera i dati attuali della persona selezionata
        membro_target = next((m for m in st.session_state.membri if m.get("id") == persona_da_modificare_id), None)
        
        if membro_target:
            mod_nome = st.text_input("Nome", value=str(membro_target.get("nome", "")), key="mod_nome")
            mod_cognome = st.text_input("Cognome", value=str(membro_target.get("cognome", "")), key="mod_cognome")
            mod_nascita = st.text_input("Data di Nascita", value=str(membro_target.get("nascita", "")), key="mod_nascita")
            mod_comune = st.text_input("Comune di Nascita", value=str(membro_target.get("comune", "")), key="mod_comune")
            mod_cf = st.text_input("Codice Fiscale", value=str(membro_target.get("cf", "")), key="mod_cf")
            mod_telefono = st.text_input("Numero di Telefono", value=str(membro_target.get("telefono", "")), key="mod_telefono")
            
            is_deceduto = True if membro_target.get("deceduto") in ["SÌ", True, "True"] else False
            mod_deceduto = st.checkbox("Deceduto/a", value=is_deceduto, key="mod_deceduto")
            
            # Lista genitori escludendo se stessi
            altri_membri = ["Nessuno (Capostipite)"] + [m["id"] for m in st.session_state.membri if m.get("id") and m.get("id") != persona_da_modificare_id]
            genitore_attuale = membro_target.get("genitore", "")
            idx_genitore = altri_membri.index(genitore_attuale) if genitore_attuale in altri_membri else 0
            mod_genitore = st.selectbox("Genitore", altri_membri, index=idx_genitore, key="mod_genitore")
            
            if st.button("Salva Modifiche", type="primary"):
                nuovo_id = f"{mod_nome} {mod_cognome}"
                old_id = membro_target["id"]
                
                # Se il nome/cognome è cambiato, verifica che il nuovo ID non sia già occupato
                if nuovo_id != old_id and any(m.get("id") == nuovo_id for m in st.session_state.membri):
                    st.sidebar.error("Esiste già un'altra persona con questo Nome e Cognome!")
                else:
                    # Aggiorna i riferimenti ai figli se l'ID (nome/cognome) è cambiato
                    if nuovo_id != old_id:
                        for m in st.session_state.membri:
                            if m.get("genitore") == old_id:
                                m["genitore"] = nuovo_id
                    
                    # Aggiorna i dati del membro
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
    
    dot = graphviz.Digraph(comment="Albero Genealogico", format="png")
    dot.attr(rankdir="TB", size="12,8")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#f0f2f6", fontname="Helvetica")

    for m in st.session_state.membri:
        if not m.get("id"):
            continue
        label = f"<b>{m['nome']} {m['cognome']}</b>"
        if m.get("nascita"):
            label += f"<br/>Nato/a: {m['nascita']}"
        if m.get("comune"):
            label += f"<br/>Comune: {m['comune']}"
        if m.get("cf"):
            label += f"<br/>CF: {m['cf']}"
        if m.get("telefono"):
            label += f"<br/>Tel: {m['telefono']}"
        if m.get("note"):
            label += f"<br/>Note: {m['note']}"
        if m.get("deceduto") == "SÌ" or m.get("deceduto") is True:
            label += "<br/><b>[DECEDUTO/A]</b>"

        dot.node(str(m["id"]), label=f"<{label}>")

        if m.get("genitore"):
            dot.edge(str(m["genitore"]), str(m["id"]))

    png_bytes = dot.pipe(format="png")
    with col1:
        st.download_button(
            label="🖼️ Scarica Immagine (PNG)",
            data=png_bytes,
            file_name="albero_genealogico_carli.png",
            mime="image/png",
            use_container_width=True
        )
    
    with col2:
        if st.button("🖨️ Stampa Pagina / Salva in PDF", use_container_width=True):
            components.html("<script>window.parent.print();</script>", height=0, width=0)

    st.graphviz_chart(dot, use_container_width=True)
else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")