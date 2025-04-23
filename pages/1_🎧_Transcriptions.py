import streamlit as st
from urllib.parse import unquote
import os
from utils.utils_trad import get_total_audio_duration_by_user, list_audio_files_by_title, get_processed_audio_files_by_user_and_title, get_audio_url, save_annotation
from dotenv import load_dotenv

load_dotenv(".env")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL_S3")
ANNOTATIONS_PREFIX = "annotations"

if not all([S3_BUCKET, S3_PREFIX, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, ENDPOINT_URL]):
    st.error("Veuillez configurer correctement les variables d'environnement S3.")
    st.stop()

st.set_page_config(page_title="Travaux Audio", layout="wide")
st.title("🗣️ Travaux Audio - Transcription & Traduction")

st.markdown("""
Bienvenue sur la page des **Travaux Audio** du projet **MooreFrCollection**.

> 📝 Votre mission : écouter les audios mooré, écrire leur **transcription** (en mooré) et leur **traduction** (en français).
""")

if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False
if "current_username" not in st.session_state:
    st.session_state.current_username = ""
if "completed_titles" not in st.session_state:
    st.session_state.completed_titles = set()

if not st.session_state.user_logged_in:
    with st.form("login_form"):
        input_username = st.text_input("Entrez votre nom ou pseudo pour contribuer :", key="input_username")
        submit_button = st.form_submit_button("✅ Commencer à contribuer")

        if submit_button:
            if not input_username:
                st.error("Merci d'entrer un nom avant de continuer.")
            else:
                st.session_state.user_logged_in = True
                st.session_state.current_username = input_username
                st.rerun()
    st.stop()

username = st.session_state.current_username
st.success(f"👤 Connecté en tant que: **{username}**")

user_duration_minutes = get_total_audio_duration_by_user(username)
st.info(f"🎯 Vous avez déjà traité environ **{user_duration_minutes:.1f} minutes** d'audio.")

if st.button("👋 Changer d'utilisateur"):
    st.session_state.user_logged_in = False
    st.session_state.current_username = ""
    st.rerun()

# Charger les titres disponibles
audio_titles = list_audio_files_by_title()
if not audio_titles:
    st.warning("Aucun audio disponible pour l'instant.")
    st.stop()

available_titles = [title for title in audio_titles.keys() if title not in st.session_state.completed_titles]

if not available_titles:
    st.success("🎉 Félicitations ! Tous les groupes d'audio disponibles sont terminés.")
    st.stop()

# Sélection du titre audio
default_index = 0
if "selected_title" in st.session_state and st.session_state["selected_title"] in available_titles:
    default_index = available_titles.index(st.session_state["selected_title"])

selected_title = st.selectbox(
    "Choisissez un groupe audio :",
    available_titles,
    key="audio_group",
    index=default_index
)
st.session_state["selected_title"] = selected_title
audio_paths = audio_titles[selected_title]

# Récupérer les fichiers déjà traités pour ce titre et cet utilisateur
processed_files = get_processed_audio_files_by_user_and_title(username, selected_title)

# Filtrer la liste des audios pour ne garder que ceux non traités
unprocessed_audio_paths = [path for path in audio_paths if os.path.basename(path) not in processed_files]

if not unprocessed_audio_paths:
    st.success(f"🎉 Vous avez déjà terminé tous les audios du groupe '{selected_title}'!")
    st.session_state.completed_titles.add(selected_title)
    if st.button("Continuer avec un autre groupe (Terminé)"):
        st.rerun()
    st.stop()

# Initialiser l'index de l'audio pour le titre sélectionné (ou reprendre la progression)
index_key = f"index_{selected_title}"
if index_key not in st.session_state:
    st.session_state[index_key] = 0
else:
    st.session_state[index_key] = min(st.session_state[index_key], len(unprocessed_audio_paths) - 1)

current_index = st.session_state[index_key]

if unprocessed_audio_paths:
    current_audio = unprocessed_audio_paths[current_index]
    st.subheader(f"🎧 Audio {current_index + 1} sur {len(unprocessed_audio_paths)} : {current_audio.split('/')[-1]}")
    st.audio(get_audio_url(current_audio))

    with st.form(f"form_{current_audio}"):
        transcription = st.text_area("Transcription en mooré", key=f"tr_{current_audio}")
        traduction = st.text_area("Traduction en français", key=f"trad_{current_audio}")
        submitted = st.form_submit_button("💾 Soumettre")

        if submitted:
            save_annotation(
                audio_path=current_audio,
                user=username,
                transcription=transcription,
                traduction=traduction,
            )
            st.success("✅ Contribution enregistrée avec succès !")
            st.session_state[index_key] += 1

            # Vérifier si tous les audios non traités de ce groupe sont maintenant terminés
            if st.session_state[index_key] >= len(unprocessed_audio_paths):
                st.success(f"🎉 Vous avez terminé tous les audios du groupe '{selected_title}'!")
                st.session_state.completed_titles.add(selected_title)
                # Le bouton pour continuer est en dehors du formulaire principal
            else:
                st.rerun()
    # Bouton pour continuer après avoir potentiellement terminé un groupe (hors du formulaire)
    if st.session_state[index_key] >= len(unprocessed_audio_paths) and st.button("Continuer avec un autre groupe"):
        st.rerun()

else:
    st.info(f"Il ne reste plus d'audios à traiter pour le groupe '{selected_title}'.")
    if st.button("Choisir un autre groupe"):
        st.rerun()