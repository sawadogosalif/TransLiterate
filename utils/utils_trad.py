
import boto3
import json
import os
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
import soundfile as sf
from datetime import datetime


from dotenv import load_dotenv
load_dotenv(".env")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL_S3")
ANNOTATIONS_PREFIX = "annotations"


s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=ENDPOINT_URL
)

def list_audio_files_by_title():
    """Regroupe les fichiers audio par titre (préfixe de dossier)."""
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    if "Contents" not in response:
        return {}

    grouped = {}
    for obj in response["Contents"]:
        key = obj["Key"]
        if not key.endswith(".wav"):
            continue
        parts = key.split("/")
        if len(parts) >= 3:
            title = parts[1]
            grouped.setdefault(title, []).append(key)
    return grouped

def get_audio_url(audio_path):
    """Génère une URL temporaire pour écouter l'audio."""
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": S3_BUCKET, "Key": audio_path},
        ExpiresIn=3600,
    )

def get_audio_duration_from_s3(bucket, key):
    """Récupère la durée d'un fichier audio depuis S3."""
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        audio_bytes = obj['Body'].read()
        with BytesIO(audio_bytes) as audio_buffer:
            y, sr = sf.read(audio_buffer)
            duration = len(y) / sr
            return duration
    except Exception as e:
        print(f"Erreur lors de la lecture de la durée de {key}: {e}")
        return 0.0

def save_annotation(audio_path, user, transcription, traduction):
    """Sauvegarde l'annotation de l'utilisateur dans S3."""
    duration = get_audio_duration_from_s3(S3_BUCKET, audio_path)
    base_filename = os.path.basename(audio_path).replace(".wav", "")
    path_parts = audio_path.split('/')
    title = path_parts[-2]
    annotation_key = f"{ANNOTATIONS_PREFIX}/{title}/{base_filename}__{user}.json"

    payload = {
        "audio_path": audio_path,
        "user": user,
        "transcription": transcription,
        "traduction": traduction,
        "duration": duration,
        "created_at": datetime.utcnow().isoformat()  # Ajouter un timestamp UTC

    }

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=annotation_key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

def get_total_audio_duration_by_user(username: str) -> float:
    """Calcule la durée totale (en minutes) d'audios annotés par un utilisateur."""
    paginator = s3.get_paginator("list_objects_v2")
    total_seconds = 0.0

    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=ANNOTATIONS_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".json") or f"__{username}.json" not in key:
                continue
            try:
                file_obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
                content = file_obj["Body"].read().decode('utf-8')
                data = json.loads(content)
                duration = data.get("duration")
                if duration:
                    total_seconds += float(duration)
            except Exception as e:
                print(f"Erreur lors de la lecture de {key}: {e}")
                continue

    return total_seconds / 60.0

def get_processed_audio_files_by_user_and_title(username: str, title: str) -> set:
    """Récupère l'ensemble des noms de fichiers audio déjà traités par un utilisateur pour un titre donné."""
    processed_files = set()
    prefix = f"{ANNOTATIONS_PREFIX}/{title}/"
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(f"__{username}.json"):
                filename_with_ext = key.split("/")[-1].replace(f"__{username}.json", ".wav")
                processed_files.add(filename_with_ext)
    return processed_files
