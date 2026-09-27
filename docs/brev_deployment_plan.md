# Plan de déploiement — Backend TileForge sur NVIDIA Brev

Instance déjà créée : `tileforge`, NVIDIA A10G 24GB, 1 GPU / 32 CPUs, 256GiB stockage,
IP publique `54.159.8.64`, région Ashburn VA (AWS), **$2.98/hr en cours d'exécution**.
→ Pense à cliquer **Stop** sur le dashboard dès que vous avez fini de tester, pour ne pas
cramer les crédits hackathon entre deux sessions de travail.

24GB de VRAM est largement suffisant pour SD-Turbo en fp16 (le modèle tient dans ~2-3GB),
donc pas de risque d'OOM à ce niveau.

## 1. Ouvrir un terminal sur l'instance

Pas besoin de configurer SSH à la main. Depuis ta machine, avec le Brev CLI déjà installé et connecté (`brev login`) :

```bash
brev open tileforge cursor
```

Ça ouvre Cursor connecté directement à l'instance `tileforge`, avec un terminal intégré déjà
sur la bonne machine. Toutes les commandes ci-dessous s'exécutent dans ce terminal (sur
l'instance, pas sur ta machine locale).

## 2. Récupérer le code

Première fois :

```bash
git clone https://github.com/yahya-dev-e/TileForge.git
cd TileForge
```

Si déjà cloné :

```bash
cd TileForge
git pull origin main
```

`main` contient déjà : la protection par clé API sur `/api/v1/generate-tile`, le support
`.env`, le format `collider_polygons` corrigé côté Unity, les dépendances pinnées, et le
script de mock payloads.

## 3. Créer la clé API dans un fichier `.env`

Un `.env` est déjà lu automatiquement au démarrage du serveur (`backend/app/main.py` appelle
`load_dotenv()` sur `backend/.env`). Il n'y a rien à `export` à la main, et rien à recopier
à chaque nouvelle session SSH — le fichier reste sur disque.

```bash
cd backend
cp .env.example .env
```

Génère un vrai secret et colle-le dans `.env` :

```bash
openssl rand -hex 32
```

Édite `backend/.env` (déjà ouvert dans Cursor) pour qu'il ressemble à :

```
TILEFORGE_API_KEY=<le-secret-généré-ci-dessus>
```

`.env` est déjà dans `.gitignore` — il ne sera jamais commité. Garde ce secret de côté,
il faudra le recopier dans Unity à l'étape 6.

## 4. Lancer le provisioning

Depuis la racine du repo :

```bash
chmod +x backend/setup_cloud.sh
./backend/setup_cloud.sh --start
```

Ce script, dans l'ordre :
- vérifie `nvidia-smi` (doit détecter le A10G),
- installe les paquets système et crée un virtualenv (`~/tileforge-venv`),
- installe PyTorch avec support CUDA 12.1,
- installe `backend/requirements.txt` (inclut maintenant `python-dotenv`),
- précharge les poids SD-Turbo depuis Hugging Face (plusieurs minutes selon la connexion),
- lance `uvicorn` sur le port 8000.

Le `.env` créé à l'étape 3 est chargé automatiquement au démarrage d'`uvicorn` — aucune
variable d'environnement à exporter manuellement.

## 5. Exposer le port 8000 publiquement

Sur le dashboard Brev de l'instance `tileforge`, section **Cloud Firewall Ports** (là où
seul le port 22 apparaît actuellement) :

1. Dans le champ "Expose Port(s)", tape `8000`.
2. Laisse "Allow All IPs" — la clé API créée à l'étape 3 protège déjà l'accès, pas besoin
   de restreindre par IP en plus (ça compliquerait l'accès pour l'équipe depuis différents
   réseaux pendant le hackathon).
3. Clique **Expose Port**.

Une nouvelle ligne apparaît dans le tableau **TCP/UDP Ports**, sur le même modèle que la
ligne SSH existante (`global.prd.ga.run.brev.nvidia.com:38300` → port 22) mais pour le port
8000. Note l'**Endpoint** et le **Public Port** que Brev t'attribue à ce moment-là — c'est
cette adresse (pas l'IP `54.159.8.64` brute) qu'on utilise dans Unity.

## 6. Configurer Unity

Dans `Window > TileForge > Level Generator` :

1. **Server URL** : `http://<endpoint-noté-à-l-étape-5>:<public-port>`
2. **API Key** : colle exactement le secret généré à l'étape 3.
3. Clique **Test Connection** → le statut doit passer au vert.

## 7. Vérifier que c'est bien SD-Turbo et pas le fallback

Génère une tile, puis vérifie que `metadata.engine` vaut `"SD-Turbo"` et `device` vaut
`"cuda"` (visible dans les logs `uvicorn` côté instance, ou en inspectant la réponse) — pas
`"Procedural Fallback"` / `"cpu"`. Si c'est le fallback, le chargement du modèle a échoué :
regarde les logs `uvicorn` sur l'instance pour la vraie erreur (VRAM, échec de téléchargement
HuggingFace, etc.) — avec un A10G 24GB ça ne devrait pas être un problème de mémoire.

## 8. Filet de sécurité si Brev pose problème

Si l'instance a un souci de dernière minute (crédits épuisés, port non exposable, etc.),
`backend/colab_fallback.ipynb` + ngrok reste un plan B gratuit et rapide (GPU T4), documenté
dans le README, section "Option C".
