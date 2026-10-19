import streamlit as st
import graphviz
import json
import os

# Configurazione della pagina
st.set_page_config(page_title="Albero Genealogico", layout="wide")
st.title("🌳 Albero Genealogico Condiviso")

# File per la persistenza dei dati (può essere sincronizzato o salvato)
DB_FILE = "albero_dati.json"

def carica_dati():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return [
        {
            "id": "1",
            "nome": "Mario",
            "cognome": "Carli",
            "data_nascita": "01/01/1950",
            "comune_nascita": "Roma",
            "cf": "CRLMRA50A01H501Z",
            "deceduto": True,
            "descrizione": "Capostipite della famiglia",
            "genitore_id": ""
        }
    ]

def salva_dati(dati):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)

persone = carica_dati()

# Barra laterale per aggiungere nuove persone
st.sidebar.header("➕ Aggiungi Persona")

with st.sidebar.form("form_persona"):
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    data_nascita = st.text_input("Data di Nascita (gg/mm/aaaa)")
    comune_nascita = st.text_input("Comune di Nascita")
    cf = st.text_input("Codice Fiscale")
    descrizione = st.text_area("Note / Descrizione")
    deceduto = st.checkbox("Deceduto/a")
    
    # Selezione del genitore a cui collegare il nodo
    opzioni_genitori = {"Nessuno (Radice Principale)": ""}
    for p in persone:
        label = f"{p['nome']} {p['cognome']}"
        opzioni_genitori[label] = p["id"]
        
    genitore_scelto = st.selectbox("Figlio/a di:", list(opzioni_genitori.keys()))
    
    submitted = st.form_submit_button("Salva Persona nell'Albero")

if submitted:
    if nome and cognome:
        nuovo_id = str(len(persone) + 1)
        nuova_persona = {
            "id": nuovo_id,
            "nome": nome,
            "cognome": cognome,
            "data_nascita": data_nascita,
            "comune_nascita": comune_nascita,
            "cf": cf,
            "deceduto": deceduto,
            "descrizione": descrizione,
            "genitore_id": opzioni_genitori[genitore_scelto]
        }
        persone.append(nuova_persona)
        salva_dati(persone)
        st.sidebar.success(f"Aggiunto/a {nome} {cognome} con successo!")
        st.rerun()
    else:
        st.sidebar.error("Compila almeno Nome e Cognome!")

# --- COSTRUZIONE DEL GRAFICO (Graphviz) ---
dot = graphviz.Digraph(comment='Albero Genealogico')
dot.attr(rankdir='TB', align='center', nodesep='0.5', ranksep='0.8')

for p in persone:
    # Costruzione delle righe per il rettangolo che adatta la dimensione alle informazioni
    righe = [f"<b>{p['nome']} {p['cognome']}</b>"]
    if p.get('data_nascita'): righe.append(f"Nato/a: {p['data_nascita']}")
    if p.get('comune_nascita'): righe.append(f"Comune: {p['comune_nascita']}")
    if p.get('cf'): righe.append(f"CF: {p['cf']}")
    if p.get('descrizione'): righe.append(f"Note: {p['descrizione']}")
    if p.get('deceduto'): righe.append("<b>[DECEDUTO/A]</b>")
    
    label_html = "<br/>".join(righe)
    
    # Grafica rettangoli: spessi e scuri per deceduti, chiari per viventi
    if p.get('deceduto'):
        color = "#000000"
        fillcolor = "#E0E0E0"
        penwidth = "3.0"
    else:
        color = "#2E5B88"
        fillcolor = "#F0F4F8"
        penwidth = "1.5"
        
    dot.node(
        p['id'],
        label=f"<{label_html}>",
        shape="box",
        style="filled,rounded",
        fillcolor=fillcolor,
        color=color,
        penwidth=penwidth,
        fontname="Arial"
    )
    
    # Collegamento al genitore tramite linea nera
    if p.get("genitore_id"):
        dot.edge(p["genitore_id"], p["id"], color="#000000", penwidth="1.5")

st.graphviz_chart(dot, use_container_width=True)