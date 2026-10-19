import streamlit as st
import graphviz
import streamlit.components.v1 as components

st.set_page_config(page_title="Albero Genealogico Carli", layout="wide")

# CSS personalizzato per nascondere la sidebar e le intestazioni durante la stampa
st.markdown("""
    <style>
    @media print {
        /* Nasconde la barra laterale, la barra di Streamlit e i pulsanti durante la stampa */
        [data-testid="stSidebar"], 
        header, 
        footer, 
        .stButton, 
        .stDownloadButton {
            display: none !important;
        }
        /* Garantisce che l'albero occupi tutto il foglio */
        .main .block-container {
            max-width: 100% !important;
            padding: 0 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Inizializzazione temporanea dei membri (in attesa di Google Sheets)
if "membri" not in st.session_state:
    st.session_state.membri = [
        {
            "id": "Mario Carli",
            "nome": "Mario",
            "cognome": "Carli",
            "nascita": "01/01/1950",
            "comune": "Roma",
            "cf": "CRLMRA50A01H501Z",
            "deceduto": True,
            "genitore": None,
            "note": "Capostipite della famiglia"
        }
    ]

# --- SIDEBAR: GESTIONE ---
st.sidebar.title("📌 Gestione Albero")

# Aggiungi Persona
with st.sidebar.expander("➕ Aggiungi Persona", expanded=True):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    data_nascita = st.text_input("Data di Nascita (gg/mm/aaaa)")
    comune = st.text_input("Comune di Nascita")
    cf = st.text_input("Codice Fiscale")
    deceduto = st.checkbox("Deceduto/a")
    
    opzioni_genitori = ["Nessuno (Capostipite)"] + [m["id"] for m in st.session_state.membri]
    genitore_scelto = st.selectbox("Genitore", opzioni_genitori)
    
    if st.button("Aggiungi alla Famiglia"):
        if nome and cognome:
            nuovo_id = f"{nome} {cognome}"
            if any(m["id"] == nuovo_id for m in st.session_state.membri):
                st.sidebar.error("Una persona con questo nome e cognome esiste già!")
            else:
                nuovo_membro = {
                    "id": nuovo_id,
                    "nome": nome,
                    "cognome": cognome,
                    "nascita": data_nascita,
                    "comune": comune,
                    "cf": cf,
                    "deceduto": deceduto,
                    "genitore": None if genitore_scelto == "Nessuno (Capostipite)" else genitore_scelto
                }
                st.session_state.membri.append(nuovo_membro)
                st.sidebar.success(f"{nuovo_id} aggiunto/a con successo!")
                st.rerun()
        else:
            st.sidebar.error("Nome e Cognome sono obbligatori!")

# Rimuovi Persona
with st.sidebar.expander("🗑️ Rimuovi Persona", expanded=False):
    if st.session_state.membri:
        persona_da_eliminare = st.selectbox(
            "Seleziona la persona da rimuovere",
            [m["id"] for m in st.session_state.membri]
        )
        if st.button("Elimina Persona", type="primary"):
            st.session_state.membri = [m for m in st.session_state.membri if m["id"] != persona_da_eliminare]
            for m in st.session_state.membri:
                if m["genitore"] == persona_da_eliminare:
                    m["genitore"] = None
            st.sidebar.success(f"{persona_da_eliminare} eliminato/a!")
            st.rerun()
    else:
        st.write("Nessun membro presente.")

# --- VISUALIZZAZIONE GRAFICA E STAMPA ---
st.title("🌳 Albero Genealogico Condiviso")

if st.session_state.membri:
    col1, col2 = st.columns([1, 1])
    
    # Costruzione grafico
    dot = graphviz.Digraph(comment="Albero Genealogico", format="png")
    dot.attr(rankdir="TB", size="12,8")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#f0f2f6", fontname="Helvetica")

    for m in st.session_state.membri:
        label = f"<b>{m['nome']} {m['cognome']}</b>"
        if m.get("nascita"):
            label += f"<br/>Nato/a: {m['nascita']}"
        if m.get("comune"):
            label += f"<br/>Comune: {m['comune']}"
        if m.get("cf"):
            label += f"<br/>CF: {m['cf']}"
        if m.get("note"):
            label += f"<br/>Note: {m['note']}"
        if m.get("deceduto"):
            label += "<br/><b>[DECEDUTO/A]</b>"

        dot.node(m["id"], label=f"<{label}>")

        if m.get("genitore"):
            dot.edge(m["genitore"], m["id"])

    # Pulsante per scaricare l'immagine dell'albero
    png_bytes = dot.pipe(format="png")
    with col1:
        st.download_button(
            label="🖼️ Scarica Immagine (PNG)",
            data=png_bytes,
            file_name="albero_genealogico_carli.png",
            mime="image/png",
            use_container_width=True
        )
    
    # Pulsante per attivare la Stampa di sistema del Browser
    with col2:
        if st.button("🖨️ Stampa Pagina / Salva in PDF", use_container_width=True):
            components.html("<script>window.parent.print();</script>", height=0, width=0)

    st.graphviz_chart(dot, use_container_width=True)
else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")