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
st.sidebar.title("Gestione Albero")

with st.sidebar.expander("Aggiungi Persona", expanded=False):
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

with st.sidebar.expander("Modifica Persona", expanded=True):
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
        st.sidebar.write("Nessun membro presente da modificare.")

with st.sidebar.expander("Rimuovi Persona", expanded=False):
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
        st.sidebar.write("Nessun membro presente.")

# --- VISUALIZZAZIONE E ESPORTAZIONE ---
st.title("Albero Genealogico Carli")

if st.session_state.membri:
    tab_interattiva, tab_pdf = st.tabs(["Vista Interattiva (Schermo)", "Vista per Stampa e Esportazione PDF"])
    
    # TAB 1: PYVIS INTERATTIVO
    with tab_interattiva:
        col_grafico, col_scheda = st.columns([3, 1])

        with col_grafico:
            net = Network(height="720px", width="100%", directed=True, notebook=False, cdn_resources='remote')
            
            net.set_options('{"physics": {"barnesHut": {"gravitationalConstant": -3500, "centralGravity": 0.3, "springLength": 110, "springConstant": 0.04, "damping": 0.09}, "minVelocity": 0.75}, "interaction": {"dragNodes": true, "zoomView": true}}')

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
                    font={"size": 16, "face": "Helvetica"},
                    margin=15
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
            st.subheader("Dettagli Persona")
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
                    st.markdown(f"**Nome e Cognome:** {membro.get('nome', '')} {membro.get('cognome', '')}")
                    st.markdown(f"**Data di Nascita:** {membro.get('nascita', 'Non inserita')}")
                    st.markdown(f"**Comune di Nascita:** {membro.get('comune', 'Non inserito')}")
                    st.markdown(f"**Codice Fiscale:** {membro.get('cf', 'Non inserito')}")
                    st.markdown(f"**Telefono:** {membro.get('telefono', 'Non inserito')}")
                    st.markdown(f"**Deceduto/a:** {membro.get('deceduto', 'NO')}")
                    st.markdown(f"**Genitore:** {membro.get('genitore', 'Nessuno / Capostipite')}")
                    st.markdown(f"**Coniuge:** {coniuge_testo}")
                    st.markdown(f"**Note:** {membro.get('note', 'Nessuna nota')}")
                    st.markdown("---")

    # TAB 2: STAMPA E CONVERSIONE IN PDF
    with tab_pdf:
        st.subheader("Generazione PDF e Immagine per Stampa e WhatsApp")
        st.write("Questa vista mostra l'albero con tutti i dati a vista all'interno di ogni nodo ingrandito, ideale per essere scaricato e condiviso.")
        
        dot = graphviz.Digraph(comment="Albero Genealogico Stampabile", format="pdf")
        dot.attr(
            rankdir="TB", 
            size="11.69,8.27",
            ratio="compress",
            nodesep="0.30",
            ranksep="0.50",
            splines="true"
        )
        
        dot.attr(
            "node", 
            shape="box", 
            style="rounded,filled", 
            fillcolor="#f8f9fa", 
            fontname="Helvetica", 
            fontsize="10", 
            margin="0.25,0.18",
            width="2.2"
        )

        for m in st.session_state.membri:
            if not m.get("id"):
                continue
            
            label = f"<font point-size='12'><b>{m.get('nome', '')} {m.get('cognome', '')}</b></font>"
            if m.get("ruolo_coniuge"):
                label += f"<br/><font point-size='9' color='#0275d8'><b>({m['ruolo_coniuge']})</b></font>"
            if m.get("nascita"):
                label += f"<br/><font point-size='9' color='#333333'>Nascita: {m['nascita']}</font>"
            if m.get("comune"):
                label += f"<br/><font point-size='9' color='#333333'>Comune: {m['comune']}</font>"
            if m.get("cf"):
                label += f"<br/><font point-size='8.5' color='#555555'>CF: {m['cf']}</font>"
            if m.get("telefono"):
                label += f"<br/><font point-size='9' color='#333333'>Tel: {m['telefono']}</font>"
            if m.get("deceduto") in ["SÌ", "Sì", "SI", True, "True"]:
                label += "<br/><font point-size='9' color='#d9534f'><b>DECEDUTO/A</b></font>"

            dot.node(str(m["id"]), label=f"<{label}>")

        # Raggruppamento specifico per Maurizio e Antonietta per affiancarli perfettamente
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node("Maurizio Vignoto")
            s.node("Antonietta Flocco")

        archi_agg = set()
        for m in st.session_state.membri:
            genitore_id = m.get("genitore")
            figlio_id = m.get("id")
            coniuge_id = m.get("coniuge")
            
            if genitore_id and figlio_id:
                coppia = (str(genitore_id), str(figlio_id))
                if coppia not in archi_aggiunti:
                    dot.edge(str(genitore_id), str(figlio_id), color="#555555", weight="1")
                    archi_agg.add(coppia)
                    
            if coniuge_id and figlio_id:
                coppia_c = tuple(sorted([str(figlio_id), str(coniuge_id)]))
                if coppia_c not in archi_agg:
                    # Se è la coppia Maurizio-Antonietta, usiamo un vincolo forte e diretto
                    if {"Maurizio Vignoto", "Antonietta Flocco"} == {str(figlio_id), str(coniuge_id)}:
                        dot.edge("Maurizio Vignoto", "Antonietta Flocco", dir="none", style="dashed", color="#d9534f", weight="1000", constraint="true")
                    else:
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
                    label="Scarica File PDF",
                    data=pdf_bytes,
                    file_name="Albero_Genealogico_Carli.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        with col_dl2:
            if png_bytes:
                st.download_button(
                    label="Scarica Immagine PNG (Consigliato per WhatsApp)",
                    data=png_bytes,
                    file_name="Albero_Genealogico_Carli.png",
                    mime="image/png",
                    use_container_width=True
                )

        st.graphviz_chart(dot, use_container_width=True)

else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")
