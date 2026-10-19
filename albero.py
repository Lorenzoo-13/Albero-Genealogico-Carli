import streamlit as st
import graphviz

st.set_page_config(page_title="Albero Genealogico Carli", layout="wide")

# Inizializzazione della lista dei membri nello stato di sessione
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

# Sidebar per la gestione
st.sidebar.title("📌 Gestione Albero")

# --- SEZIONE: AGGIUNGI PERSONA ---
with st.sidebar.expander("➕ Aggiungi Persona", expanded=True):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    data_nascita = st.text_input("Data di Nascita (gg/mm/aaaa)")
    comune = st.text_input("Comune di Nascita")
    cf = st.text_input("Codice Fiscale")
    deceduto = st.checkbox("Deceduto/a")
    
    # Selezione del genitore tra i membri esistenti
    opzioni_genitori = ["Nessuno (Capostipite)"] + [m["id"] for m in st.session_state.membri]
    genitore_scelto = st.selectbox("Genitore", opzioni_genitori)
    
    if st.button("Aggiungi alla Famiglia"):
        if nome and cognome:
            nuovo_id = f"{nome} {cognome}"
            
            # Controllo duplicati di base
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

# --- SEZIONE: ELIMINA PERSONA ---
with st.sidebar.expander("🗑️ Rimuovi Persona", expanded=False):
    if st.session_state.membri:
        persona_da_eliminare = st.selectbox(
            "Seleziona la persona da rimuovere",
            [m["id"] for m in st.session_state.membri]
        )
        if st.button("Elimina Persona", type="primary"):
            # Rimuove la persona selezionata
            st.session_state.membri = [m for m in st.session_state.membri if m["id"] != persona_da_eliminare]
            
            # Aggiorna eventuali riferimenti genitore per i figli rimanenti
            for m in st.session_state.membri:
                if m["genitore"] == persona_da_eliminare:
                    m["genitore"] = None
                    
            st.sidebar.success(f"{persona_da_eliminare} eliminato/a!")
            st.rerun()
    else:
        st.write("Nessun membro presente.")

# --- VISUALIZZAZIONE GRAFICA ---
st.title("🌳 Albero Genealogico Condiviso")

if st.session_state.membri:
    dot = graphviz.Digraph(comment="Albero Genealogico")
    dot.attr(rankdir="TB", size="12,8")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#e1e1e1", fontname="Helvetica")

    for m in st.session_state.membri:
        # Etichetta con i dettagli
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

        # Collegamento al genitore
        if m.get("genitore"):
            dot.edge(m["genitore"], m["id"])

    st.graphviz_chart(dot, use_container_width=True)
else:
    st.info("L'albero è vuoto. Aggiungi il primo membro dalla barra laterale.")