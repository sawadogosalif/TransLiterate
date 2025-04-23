import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.utils_stats import (
    load_all_annotations,
    calculate_total_duration,
    calculate_contributor_ranking,
    create_contributions_histogram,
    create_contributions_pie_chart,
    calculate_contributions_over_time,
    calculate_average_annotation_length
)

def display_most_recent_contributions(annotations, n=5):
    """Affiche les contributions les plus récentes."""
    if not annotations:
        st.info("Aucune contribution récente.")
        return

    st.subheader(f"⏱️ {n} Contributions les plus récentes (approximatif)")
    for ann in annotations[-n:]:
        st.markdown(f"- Utilisateur: **{ann.get('user', 'N/A')}**, Audio: `{(ann.get('audio_path', 'N/A'))}`")

st.set_page_config(page_title="Statistiques des Travaux Audio", layout="wide")
st.title("📊 Statistiques des Travaux Audio")

st.markdown("Voici un aperçu des statistiques de contribution pour le projet **MooreFrCollection**.")

# Charger toutes les annotations
all_annotations = load_all_annotations()

if all_annotations:
    # Première ligne : Métriques principales
    col1, col2, col3 = st.columns(3)
    with col1:
        total_duration_minutes = calculate_total_duration(all_annotations)
        st.metric("⏱️ Total d'audios traités", f"{total_duration_minutes:.2f} minutes")
    with col2:
        avg_annotation_length = calculate_average_annotation_length(all_annotations)
        st.metric("📏 Durée moyenne d'une annotation", f"{avg_annotation_length:.2f} minutes")
    with col3:
        st.empty()

    st.markdown("---")

    # Deuxième ligne : Classement et histogramme
    col_ranking, col_histogram = st.columns([1, 2])
    with col_ranking:
        st.subheader("🏆 Classement des contributeurs par durée totale")
        contributor_ranking = calculate_contributor_ranking(all_annotations)
        if contributor_ranking:
            ranking_df = pd.DataFrame(contributor_ranking, columns=['Contributeur', 'Durée totale (secondes)'])
            ranking_df['Durée totale (minutes)'] = ranking_df['Durée totale (secondes)'] / 60.0
            st.dataframe(ranking_df[['Contributeur', 'Durée totale (minutes)']].set_index('Contributeur'), height=300)
        else:
            st.info("Aucune contribution enregistrée pour le moment.")

    with col_histogram:
        histogram_fig = create_contributions_histogram(contributor_ranking)
        if histogram_fig:
            st.plotly_chart(histogram_fig, use_container_width=True)

    st.markdown("---")

    # Troisième ligne : Diagramme circulaire et contributions récentes
    col_pie, col_recent = st.columns(2)
    with col_pie:
        pie_chart_fig = create_contributions_pie_chart(all_annotations)
        if pie_chart_fig:
            st.plotly_chart(pie_chart_fig, use_container_width=True)

    with col_recent:
        display_most_recent_contributions(all_annotations)

    st.markdown("---")

    # Quatrième ligne : Évolution temporelle
    st.subheader("📈 Évolution temporelle des contributions")
    contributions_over_time_df = calculate_contributions_over_time(all_annotations)
    if contributions_over_time_df is not None and not contributions_over_time_df.empty:
        fig = go.Figure(data=[go.Scatter(x=contributions_over_time_df['Date'], y=contributions_over_time_df['Nombre de contributions'], mode='lines+markers')])
        st.plotly_chart(fig, use_container_width=True)
    elif all_annotations:
        st.info("Impossible de déterminer l'évolution temporelle des contributions (informations de date manquantes dans les clés S3).")
    else:
        st.info("Aucune contribution à afficher pour l'évolution temporelle.")

else:
    st.info("Aucune donnée d'annotation disponible pour générer les statistiques.")