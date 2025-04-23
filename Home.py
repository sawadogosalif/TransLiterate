import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="MooreFrCollection",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

with open("assets/css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🚀 Outil de Traduction et Transcription pour MooreFrCollection")
st.markdown("""
    ### Bienvenue sur MooreFrCollection
    Aidez-nous à casser la barrière de la langue et à améliorer l'accès aux ressources en mooré. 
            
    Cette plateforme permet de collecter des audios, de les transcrire et de les traduire.
    
    MooreFrCollection a pour but de collecter des ressources en mooré pour la mise en place de plusieurs IA locaux. 
            
    Votre participation est essentielle pour enrichir la base de données et faciliter la traduction de la langue mooré.

    ### L'Alphabet Mooré
    Voici l'alphabet mooré attendu :
""")

alphabet = ["a", "ã", "b", "d", "e", "ẽ", "ɛ", "f", "g", "h", "i", "ĩ", "ɩ", "k", "l", "m", "n", "o", "õ", "p", "r", "s", "t", "u", "ũ", "ʋ", "v", "w", "y", "z"]
st.write(", ".join(alphabet))

