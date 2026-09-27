# Plan de déploiement — Backend TileForge sur NVIDIA Brev

Instance déjà créée : `tileforge`, NVIDIA A10G 24GB, 1 GPU / 32 CPUs, 256GiB stockage,
IP publique `54.159.8.64`, région Ashburn VA (AWS), **$2.98/hr en cours d'exécution**.
→ Pense à cliquer **Stop** sur le dashboard dès que vous avez fini de tester, pour ne pas
cramer les crédits hackathon entre deux sessions de travail.

24GB de VRAM est largement suffisant pour SD-Turbo en fp16 (le modèle tient dans ~2-3GB),
donc pas de risque d'OOM à ce niveau.

## 1. Ouvrir un terminal sur l'instance

Depuis ton terminal **WSL** (celui où tu as fait `brev login`) :

```bash
brev shell tileforge
```

> Sous WSL, `brev open tileforge cursor` ne fonctionne pas : la commande enregistre l'alias
> SSH `tileforge` dans le `~/.ssh/config` de WSL, mais Cursor est une appli Windows native
> qui lit le `.ssh/config` de Windows — qui ne connaît pas cet alias (`Could not resolve
> hostname tileforge`). `brev shell` gère le SSH entièrement à l'intérieur de WSL et évite
> ce conflit ; utilise `nano`/`vim` en ligne de commande pour éditer les fichiers (pas
> d'éditeur graphique dans ce chemin).

Toutes les commandes ci-dessous s'exécutent dans ce terminal (sur l'instance, pas sur ta
machine locale).

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

Édite `backend/.env` (ex. `nano .env`) pour qu'il ressemble à :

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

Contrairement au port SSH (proxié via `global.prd.ga.run.brev.nvidia.com:38300`), le port
8000 exposé s'ouvre directement sur l'IP publique de l'instance — confirmé en visitant
`http://54.159.8.64:8000/health` dans un navigateur, qui répond `{"status":"ok",
"device":"cuda","gpu_name":"NVIDIA A10G","model_loaded":true}`. Pas besoin de chercher un
endpoint séparé, `54.159.8.64:8000` est la bonne adresse.

## 6. Configurer Unity

Dans `Window > TileForge > Level Generator` :

1. **Server URL** : `http://54.159.8.64:8000`
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
