import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pyvis.network import Network

st.set_page_config(page_title="Albero Genealogico Carli", layout="wide")

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
        
        header = [h.strip().lower() for h in rows[0]]
        data = []
        for row in rows[1:]:
            row_data = row + [""] * (len(header) - len(row))
            record = dict(zip(header, row_data))
            if not record.get("id") and record.get("nome") and record.get("cognome"):
                record["id"] = f"{record['nome']} {record['cognome']}"
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

if "membri" not in st.session_state:
    st.session_state.membri = carica_dati()

# --- SIDEBAR: GESTIONE ---
st.sidebar.title("📌 Gestione Albero")

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

# --- VISUALIZZAZIONE GRAFICA INTERATTIVA CON SCHEDA DETTAGLI ---
st.title("🌳 Albero Genealogico Interattivo")

if st.session_state.membri:
    col_grafico, col_scheda = st.columns([3, 1])

    with col_grafico:
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
            "zoomView": true,
            "selectConnectedEdges": false
          }
        }
        """)

        for m in st.session_state.membri:
            if not m.get("id"):
                continue
            
            label = f"{m.get('nome', '')} {m.get('cognome', '')}".strip()
            if not label:
                label = str(m['id'])
                
            if m.get("ruolo_coniuge"):
                label += f" ({m['ruolo_coniuge']})"

            colore_nodo = "#FFC0CB" if m.get("ruolo_coniuge") == "Moglie" else "#87CEFA"
            if not m.get("ruolo_coniuge") and (not m.get("genitore") or m.get("genitore") == ""):
                colore_nodo = "#ffcc00"

            net.add_node(
                str(m["id"]), 
                label=label, 
                color=colore_nodo,
                shape="box",
                font={"size": 14}
            )

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
            html_code = f.read()

        components.html(html_code, height=780, scrolling=True)

    with col_scheda:
        st.subheader("📋 Dettagli Persona")
        lista_nomi = [m["id"] for m in st.session_state.membri if m.get("id")]
        
        if lista_nomi:
            persona_selezionata = st.selectbox("Seleziona una persona:", lista_nomi, key="seleziona_dettaglio")
            
            membro = next((m for m in st.session_state.membri if m.get("id") == persona_selezionata), None)
            
            if membro:
                coniuge_testo = membro.get('coniuge', 'Nessuno')
                ruolo_c = membro.get('ruolo_coniuge', '')
                if coniuge_testo and coniuge_testo != 'Nessuno' and ruolo_c:
                    coniuge_testo += f" ({ruolo_c})"

                st.markdown("---")
                st.markdown(f"**👤 Nome e Cognome:** {membro.get('nome', '')} {membro.get('cognome', '')}")
                st.markdown(f"**🎂 Data di Nascita:** {membro.get('nascita', 'Non inserita')}")
                st.markdown(f"**📍 Comune di Nascita:** {membro.get('comune', 'Non inserito')}")
                st.markdown(f"**🆔 Codice Fiscale:** {membro.get('cf', 'Non inserito')}")
                st.markdown(f"**📞 Telefono:** {membro.get('telefono', 'Non inserito')}")
                st.markdown(f"**🕊️ Deceduto/a:** {membro.get('deceduto', 'NO')}")
                st.markdown(f"**👪 Genitore:** {membro.get('genitore', 'Nessuno / Capostipite')}")
                st.markdown(f"**💍 Coniuge:** {coniuge_testo}")
                st.markdown(f"**📝 Note:** {membro.get('note', 'Nessuna nota')}")
                st.markdown("---")
        else:
            st.info("Nessun membro disponibile.")

else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")
