FROM python:3.11-slim

# Éviter les prompts durant l'installation
ENV DEBIAN_FRONTEND=noninteractive

# Créer un utilisateur non-root
RUN useradd -m -u 1000 user
USER user
ENV HOME="/home/user"
ENV PATH="${HOME}/.local/bin:$PATH"


RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Dossier de travail
WORKDIR $HOME/app

# Cloner ton dépôt GitHub
RUN git clone --depth 1 https://github.com/sawadogosalif/TransLiterate.git .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Exposer le port utilisé par Streamlit
EXPOSE 7860

# Lancer l'application Streamlit
CMD streamlit run Home.py --server.port 7860 --server.address 0.0.0.0
