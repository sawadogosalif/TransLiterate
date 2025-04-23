import boto3
import json
import os
from collections import defaultdict
from datetime import datetime
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

load_dotenv(".env")
S3_BUCKET = os.getenv("S3_BUCKET")
ANNOTATIONS_PREFIX = "annotations"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL_S3")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=ENDPOINT_URL
)

def load_all_annotations():
    """Charge toutes les annotations depuis S3."""
    annotations = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=ANNOTATIONS_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                try:
                    file_obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    content = file_obj["Body"].read().decode('utf-8')
                    data = json.loads(content)
                    annotations.append(data)
                except Exception as e:
                    print(f"Erreur lors de la lecture de {key}: {e}")
    return annotations

def calculate_total_duration(annotations):
    """Calcule la durée totale des audios annotés (en minutes)."""
    total_seconds = sum(float(ann.get("duration", 0)) for ann in annotations)
    return total_seconds / 60.0

def calculate_contributor_ranking(annotations):
    """Calcule la durée totale des contributions par utilisateur."""
    contributor_durations = defaultdict(float)
    for ann in annotations:
        user = ann.get("user")
        duration = float(ann.get("duration", 0))
        if user:
            contributor_durations[user] += duration
    return sorted(contributor_durations.items(), key=lambda item: item[1], reverse=True)

def create_contributions_histogram(contributor_ranking):
    """Crée un histogramme des contributions par utilisateur."""
    if not contributor_ranking:
        return None
    users = [item[0] for item in contributor_ranking]
    durations_minutes = [item[1] / 60.0 for item in contributor_ranking]
    fig = px.bar(x=users, y=durations_minutes, labels={'x': 'Contributeur', 'y': 'Durée totale (minutes)'},
                 title='Durée totale des contributions par utilisateur')
    return fig

def create_contributions_pie_chart(annotations):
    """Crée un diagramme circulaire des contributions par utilisateur (top 10)."""
    contributor_durations = defaultdict(float)
    for ann in annotations:
        user = ann.get("user")
        duration = float(ann.get("duration", 0))
        if user:
            contributor_durations[user] += duration

    if not contributor_durations:
        return None

    sorted_contributors = sorted(contributor_durations.items(), key=lambda item: item[1], reverse=True)
    top_n = sorted_contributors[:10]  # Afficher les 10 meilleurs contributeurs

    labels = [item[0] for item in top_n]
    values = [item[1] / 60.0 for item in top_n]

    fig = px.pie(names=labels, values=values, title='Répartition des contributions (Top 10 des contributeurs)',
                 hole=0.3)
    fig.update_traces(textinfo='percent+label')
    return fig

def extract_annotation_date(annotation_key):
    """Extrait une date approximative de l'annotation à partir de la clé S3."""
    parts = annotation_key.split('/')
    if len(parts) >= 3:
        for part in parts:
            try:
                return datetime.strptime(part, '%Y-%m-%d').date()
            except ValueError:
                pass
    return None

def calculate_contributions_over_time(annotations):
    """Calcule le nombre de contributions par jour en utilisant le champ 'created_at'."""
    daily_contributions_count = defaultdict(int)
    for ann in annotations:
        created_at_str = ann.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
                annotation_date = created_at.date()
                daily_contributions_count[annotation_date] += 1
            except ValueError:
                print(f"Erreur lors de la conversion de la date: {created_at_str}")

    if not daily_contributions_count:
        return None

    df = pd.DataFrame(daily_contributions_count.items(), columns=['Date', 'Nombre de contributions'])
    df = df.sort_values(by='Date')
    return df

def create_contributions_time_series(df_contributions):
    """Crée un graphique de l'évolution temporelle du nombre de contributions."""
    fig = px.line(df_contributions, x='Date', y='Nombre de contributions',
                  title='Nombre de contributions par jour')
    return fig

def calculate_average_annotation_length(annotations):
    """Calcule la durée moyenne des annotations."""
    total_duration = sum(float(ann.get("duration", 0)) for ann in annotations)
    num_annotations = len(annotations)
    if num_annotations > 0:
        return total_duration / num_annotations / 60.0  # en minutes
    return 0.0