import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from pyvis.network import Network
import graphviz

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

# --- VISUALIZZAZIONE E ESPORTAZIONE ---
st.title("🌳 Albero Genealogico Carli")

if st.session_state.membri:
    tab_interattiva, tab_pdf = st.tabs(["🌐 Vista Interattiva (Schermo)", "📄 Vista per Stampa / Esportazione PDF"])
    
    # TAB 1: PYVIS INTERATTIVO
    with tab_interattiva:
        col_grafico, col_scheda = st.columns([3, 1])

        with col_grafico:
            net = Network(height="720px", width="100%", directed=True, notebook=False, cdn_resources='remote')
            
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

            components.html(html_code, height=750, scrolling=True)

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

    # TAB 2: STAMPA E CONVERSIONE IN PDF PER WHATSAPP
    with tab_pdf:
        st.subheader("🖨️ Generazione PDF / Immagine Vettoriale per Stampa e WhatsApp")
        st.write("Questa vista genera l'albero tradizionale completo di **tutti i dati a vista all'interno di ogni nodo**, pronto per essere scaricato come immagine/PDF e inviato direttamente tramite WhatsApp.")
        
        dot = graphviz.Digraph(comment="Albero Genealogico Stampabile", format="pdf")
        dot.attr(
            rankdir="LR", 
            size="11.69,8.27", # Formato A4 Orizzontale
            ratio="compress",
            nodesep="0.15",
            ranksep="0.40",
            splines="true"
        )
        
        dot.attr(
            "node", 
            shape="box", 
            style="rounded,filled", 
            fillcolor="#f8f9fa", 
            fontname="Helvetica", 
            fontsize="9", 
            margin="0.15,0.10"
        )

        for m in st.session_state.membri:
            if not m.get("id"):
                continue
            
            # Etichetta HTML dettagliata con tutti i dati in chiaro
            label = f"<font point-size='10'><b>{m.get('nome', '')} {m.get('cognome', '')}</b></font>"
            if m.get("ruolo_coniuge"):
                label += f"<br/><font point-size='7.5' color='#0275d8'><b>({m['ruolo_coniuge']})</b></font>"
            if m.get("nascita"):
                label += f"<br/><font point-size='7.5' color='#333333'>🎂 {m['nascita']}</font>"
            if m.get("comune"):
                label += f"<br/><font point-size='7.5' color='#333333'>📍 {m['comune']}</font>"
            if m.get("cf"):
                label += f"<br/><font point-size='7' color='#555555'>CF: {m['cf']}</font>"
            if m.get("telefono"):
                label += f"<br/><font point-size='7.5' color='#333333'>📞 {m['telefono']}</font>"
            if m.get("deceduto") in ["SÌ", "Sì", "SI", True, "True"]:
                label += "<br/><font point-size='7.5' color='#d9534f'><b>🕊️ DECEDUTO/A</b></font>"

            dot.node(str(m["id"]), label=f"<{label}>")

        # Collegamenti
        archi_agg = set()
        for m in st.session_state.membri:
            genitore_id = m.get("genitore")
            figlio_id = m.get("id")
            coniuge_id = m.get("coniuge")
            
            if genitore_id and figlio_id:
                coppia = (str(genitore_id), str(figlio_id))
                if coppia not in archi_agg:
                    dot.edge(str(genitore_id), str(figlio_id), color="#555555", weight="1")
                    archi_agg.add(coppia)
                    
            if coniuge_id and figlio_id:
                coppia_c = tuple(sorted([str(figlio_id), str(coniuge_id)]))
                if coppia_c not in archi_agg:
                    dot.edge(str(figlio_id), str(coniuge_id), dir="none", style="dashed", color="#d9534f", weight="100", constraint="false")
                    archi_agg.add(coppia_c)

        try:
            pdf_bytes = dot.pipe(format="pdf")
            png_bytes = dot.pipe(format="png")
        except Exception as e:
            pdf_bytes = None
            png_bytes = None

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            if pdf_bytes:
                st.download_button(
                    label="📄 Scarica File PDF (Pronto da condividere/stampare)",
                    data=pdf_bytes,
                    file_name="Albero_Genealogico_Carli.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        with col_dl2:
            if png_bytes:
                st.download_button(
                    label="🖼️ Scarica Immagine PNG (Ottimo per WhatsApp)",
                    data=png_bytes,
                    file_name="Albero_Genealogico_Carli.png",
                    mime="image/png",
                    use_container_width=True
                )

        st.graphviz_chart(dot, use_container_width=True)

else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")
