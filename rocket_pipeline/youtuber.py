import os
from loguru import logger
import boto3
from tqdm import tqdm
from pydub import AudioSegment
from yt_dlp import YoutubeDL
from dotenv import load_dotenv



def filter_videos_by_keywords(candidates, keywords):

    if not candidates:
        return []
        
    filtered_videos = []
    
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
            
        title = str(candidate.get("title", "")).lower()
        description = str(candidate.get("description", "")).lower()
        
        if any(keyword.lower() in title or keyword.lower() in description for keyword in keywords):
            filtered_videos.append(candidate)
    
    logger.info(f"Filtrage terminé: {len(filtered_videos)}/{len(candidates)} vidéos correspondent aux mots-clés {keywords}")
    return filtered_videos

def get_videos_from_channel(channel_url=None):

    if channel_url is None:
        channel_url = CHANNEL_URL
        
    logger.info(f"Extraction des vidéos depuis la chaîne: {channel_url}")
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        if 'entries' in info:
            videos = info['entries']
            videos_urls = [video for video in videos  if not "Shorts" in  video["title"]]
            videos_urls = sum([videos_url["entries"] for videos_url in videos_urls], [])
            logger.info(f"Nombre total  de videos trouvées: {len(videos_urls)}")
            return videos_urls
        else:
            logger.warning("Aucune vidéo trouvée sur cette chaîne")
            return []

def download_youtube_audios(videos, output_dir=None):
    """
    Télécharge les fichiers audio des vidéos YouTube.
    
    Args:
        videos: Liste des vidéos à télécharger
        output_dir: Répertoire de sortie (utilise INPUT_DIR par défaut)
    """
    if output_dir is None:
        output_dir = INPUT_DIR
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
        'quiet': False,
    }
    
    logger.info(f"Début du téléchargement de {len(videos)} vidéos")
    with YoutubeDL(ydl_opts) as ydl:
        for video in tqdm(videos, desc="Téléchargement des vidéos"):
            try:
                url = f"https://www.youtube.com/watch?v={video['id']}"
                logger.info(f"Téléchargement de l'audio (WAV) : {video['title']}")
                ydl.download([url])
            except Exception as e:
                logger.error(f"Erreur lors du téléchargement de {video.get('title', video.get('id', 'inconnu'))}: {str(e)}")

def segment_audio_files(input_dir=None, output_dir=None, segment_length=None):
    """
    Découpe les fichiers audio en segments.
    
    Args:
        input_dir: Répertoire des fichiers audio source (utilise INPUT_DIR par défaut)
        output_dir: Répertoire des segments audio (utilise OUTPUT_DIR par défaut)
        segment_length: Durée de chaque segment en ms (utilise SEGMENT_LENGTH_MS par défaut)
    
    Returns:
        Nombre total de segments créés
    """
    if input_dir is None:
        input_dir = INPUT_DIR
    if output_dir is None:
        output_dir = OUTPUT_DIR
    if segment_length is None:
        segment_length = SEGMENT_LENGTH_MS
    
    wav_files = [f for f in os.listdir(input_dir) if f.endswith(".wav")]
    logger.info(f"Nombre de fichiers WAV à traiter: {len(wav_files)}")
    
    total_segments = 0
    processed_segments = []
    
    for filename in tqdm(wav_files, desc="Traitement des fichiers audio"):
        try:
            filepath = os.path.join(input_dir, filename)
            audio = AudioSegment.from_wav(filepath)
            duration = len(audio)
            
            base_name = os.path.splitext(filename)[0]
            
            video_folder = os.path.join(output_dir, base_name)
            os.makedirs(video_folder, exist_ok=True)
            
            logger.info(f"Découpage de : {filename} → dossier [{video_folder}]")
            
            num_segments = (duration + segment_length - 1) // segment_length
            segments_created = 0
            
            for i in tqdm(range(0, duration, segment_length), 
                          desc=f"Segments de {base_name}", 
                          total=num_segments):
                segment = audio[i:i + segment_length]
                segment_name = f"part{i // segment_length + 1}.wav"
                segment_path = os.path.join(video_folder, segment_name)
                segment.export(segment_path, format="wav")
                segments_created += 1
                processed_segments.append(segment_path)
            
            logger.info(f"Fichier {filename}: {segments_created} segments créés")
            total_segments += segments_created
        except Exception as e:
            logger.error(f"Erreur lors du traitement de {filename}: {str(e)}")
    
    logger.info(f"Traitement terminé. Total des segments créés: {total_segments}")
    return total_segments, processed_segments

def setup_s3_client():

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL_S3")
    
    if not all([access_key, secret_key]):
        logger.warning("Variables d'environnement AWS manquantes (AWS_ACCESS_KEY_ID ou AWS_SECRET_ACCESS_KEY)")
        return None
    
    client_params = {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    
    if endpoint_url:
        client_params["endpoint_url"] = endpoint_url
    
    try:
        return boto3.client("s3", **client_params)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du client S3: {str(e)}")
        return None


def upload_file_to_s3(s3_client, local_path, bucket_name, s3_key):

    try:
        s3_client.upload_file(local_path, bucket_name, s3_key)
        logger.info(f"Uploadé {local_path} vers s3://{bucket_name}/{s3_key}")
    except Exception as e:
        logger.error(f"Erreur lors de l'upload de {local_path}: {str(e)}")

def upload_segments_to_s3(segments, bucket_name=None, prefix=None):

    if bucket_name is None:
        bucket_name = BUCKET_NAME
    if prefix is None:
        prefix = S3_PREFIX
    
    s3_client = setup_s3_client()
    if not s3_client:
        logger.error("Client S3 non disponible. Upload annulé.")
        return 0
    
    uploaded_count = 0
    logger.info(f"Début de l'upload des segments vers S3 (bucket: {bucket_name}, préfixe: {prefix})")
    
    for segment_path in tqdm(segments, desc="Upload des segments vers S3"):
        try:
            relative_path = os.path.relpath(segment_path, start=OUTPUT_DIR)
            s3_key = os.path.join(prefix, relative_path)
            
            upload_file_to_s3(s3_client, segment_path, bucket_name, s3_key)
            uploaded_count += 1
        except Exception as e:
            logger.error(f"Erreur lors de l'upload de {segment_path}: {str(e)}")
    
    logger.info(f"Upload terminé. {uploaded_count}/{len(segments)} fichiers envoyés vers S3.")
    return uploaded_count

def main():

    # ====================== CHANGE ME - CONFIGURATION ======================
    # Mots-clés pour le filtrage des vidéos
    FILTER_KEYWORDS = ["sid pa"]  # 


    CHANNEL_URL = "https://www.youtube.com/@livenewsafrica/" 

    # Configuration des répertoires
    INPUT_DIR = "audios_sidpa"  # Répertoire pour les fichiers audio téléchargés
    OUTPUT_DIR = "audios_segments"  # Répertoire pour les segments audio

    # Durée des segments en millisecondes
    SEGMENT_LENGTH_MS = 30 * 1000  # 30 secondes par défaut

    # Configuration S3
    BUCKET_NAME = "moore-collection"  # Nom de votre bucket S3
    S3_PREFIX = "audios_to_tests"  # Préfixe pour les fichiers dans S3
    USE_S3 = False  # Mettre à True pour activer les opérations S3
    # ====================== FIN CHANGE ME ======================

    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info("Démarrage du traitement des fichiers audio")
    
    videos = get_videos_from_channel()
    filtered_videos = filter_videos_by_keywords(videos, keywords=["sid pa"])
    download_youtube_audios(filtered_videos)
    
    total_segments, processed_segments = segment_audio_files()
    
    if USE_S3:
        upload_segments_to_s3(processed_segments)
    
    logger.info("Traitement terminé avec succès")

if __name__ == "__main__":
    main()
