# Plan de déploiement — Backend TileForge sur NVIDIA Brev

Prérequis déjà en place : crédits hackathon disponibles, instance GPU déjà créée sur Brev.

## 1. Se connecter à l'instance

Depuis le dashboard Brev, récupère la commande SSH de ton instance (bouton "Connect" / "Shell") et connecte-toi :

```bash
ssh <ton-instance-brev>
# ou : brev shell <nom-instance>
```

Vérifie que le GPU est bien visible :

```bash
nvidia-smi
```

## 2. Récupérer le code

Première fois :

```bash
git clone https://github.com/yahya-dev-e/TileForge.git
cd TileForge
```

Si déjà cloné, juste mettre à jour :

```bash
cd TileForge
git pull origin main
```

`main` contient déjà : la protection par clé API sur `/api/v1/generate-tile`, le format `collider_polygons` corrigé côté Unity, les dépendances pinnées, et le script de mock payloads.

## 3. Définir la clé API avant de lancer le serveur

Le serveur n'exige une clé que si `TILEFORGE_API_KEY` est définie dans l'environnement — **il faut l'exporter avant** de lancer `setup_cloud.sh`, sinon le endpoint reste ouvert à tout le monde une fois l'IP publique exposée :

```bash
export TILEFORGE_API_KEY="choisis-un-secret-ici"
```

Note ce secret quelque part — il faudra le recopier dans Unity à l'étape 6.

## 4. Lancer le provisioning

```bash
chmod +x backend/setup_cloud.sh
./backend/setup_cloud.sh --start
```

Ce script (dans l'ordre) :
- installe les paquets système et crée un virtualenv (`~/tileforge-venv`),
- installe PyTorch avec support CUDA 12.1,
- installe `backend/requirements.txt`,
- précharge les poids SD-Turbo depuis Hugging Face (peut prendre plusieurs minutes selon la connexion),
- lance `uvicorn` sur le port 8000 avec `--start`.

Si tu préfères lancer en deux temps (pour vérifier avant de démarrer le serveur), enlève `--start` puis lance manuellement :

```bash
source ~/tileforge-venv/bin/activate
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 5. Exposer le port 8000 publiquement

Dans le dashboard Brev, section "Ports" / "Networking" de ton instance, expose le port **8000** (souvent en HTTPS, via un tunnel Brev). Brev te donnera une URL publique du type `https://<id>-8000.brev.dev` — c'est cette URL qu'on utilisera, pas nécessairement l'IP brute affichée par le script.

## 6. Configurer Unity

Dans `Window > TileForge > Level Generator` :

1. **Server URL** : colle l'URL publique Brev (ou l'IP:8000 si tu utilises un tunnel SSH direct).
2. **API Key** : colle exactement le secret défini à l'étape 3.
3. Clique **Test Connection** → le statut doit passer au vert.

## 7. Vérifier que c'est bien SD-Turbo et pas le fallback

Génère une tile, puis vérifie dans la réponse (`metadata.engine` dans les logs Unity, ou via `/health` et `/docs` côté serveur) que `engine` vaut `"SD-Turbo"` et `device` vaut `"cuda"` — pas `"Procedural Fallback"` / `"cpu"`. Si c'est le fallback, le chargement du modèle a échoué (vérifier les logs `uvicorn` côté Brev pour la vraie erreur : VRAM insuffisante, échec de téléchargement, etc.).

## 8. Filet de sécurité si Brev pose problème

Si l'instance Brev a un souci de dernière minute (crédits épuisés, port non exposable, etc.), `backend/colab_fallback.ipynb` + ngrok reste un plan B gratuit et rapide (GPU T4), documenté dans le README, section "Option C".
