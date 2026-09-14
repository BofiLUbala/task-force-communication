# Déploiement production — Task Force Présidentielle (AWS)

Architecture cible :

```
Navigateur ──► Web App (S3 + CloudFront)
                   │
                   ▼
              API Django (App Runner)  ──► RDS PostgreSQL
                   │
                   ├──► S3 (médias : images, vidéos, PDF)
                   └──► YouTube / LinkedIn / SMTP / WhatsApp
```

L'app mobile Expo consomme **la même API**.

---

## 0. Ce qui est déjà prêt dans le dépôt

| Élément | État |
|---|---|
| `backend/Dockerfile` | Construit et **testé** : gunicorn, migrations au démarrage, healthcheck |
| `/healthz/` | Retourne `{"status":"ok","database":"ok"}`, 503 si la base est injoignable |
| `DATABASE_URL` | Supporté, avec `sslmode` (requis par RDS) |
| Fichiers statiques | WhiteNoise + `collectstatic` dans l'image |
| Médias S3 | `django-storages` activé dès que `AWS_STORAGE_BUCKET_NAME` est défini |
| CSRF / CORS / HTTPS | Pilotés par variables d'environnement, durcis quand `DEBUG=False` |
| Publications programmées | `python manage.py run_scheduled_publications` |
| Fallback SPA | `wrangler.jsonc` (`not_found_handling`) |

---

## 1. RDS PostgreSQL

1. RDS → Create database → PostgreSQL, classe `db.t4g.micro` pour démarrer.
2. Storage : 20 Go gp3, **autoscaling activé**.
3. **Public access : No.** L'API y accède par le VPC.
4. Noter l'endpoint. `DATABASE_URL` devient :
   `postgresql://USER:PASSWORD@ENDPOINT:5432/DBNAME?sslmode=require`

> Les migrations s'appliquent automatiquement au démarrage du conteneur. Aucune étape manuelle.

## 2. S3 — médias

Sans cela, **toute image/vidéo/PDF téléversé disparaît au prochain déploiement** : le système de fichiers d'App Runner est éphémère.

1. Créer un bucket, ex. `taskforce-media`.
2. Block Public Access : **activé**. Les objets sont servis via CloudFront, pas en accès direct.
3. Créer un utilisateur IAM limité à `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` sur ce seul bucket.
4. Distribution CloudFront devant le bucket (OAC), puis `AWS_S3_CUSTOM_DOMAIN=media.<domaine>`.

## 3. ECR + App Runner — API

```bash
aws ecr create-repository --repository-name taskforce-backend
aws ecr get-login-password --region <region> \
  | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

cd backend
docker build -t taskforce-backend .
docker tag taskforce-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/taskforce-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/taskforce-backend:latest
```

App Runner → Create service → Container registry → l'image ci-dessus.

- Port : `8000`
- Health check : **HTTP**, chemin `/healthz/`
- Variables d'environnement : voir `backend/.env.production.example`
- VPC connector vers le VPC du RDS

> `SECURE_SSL_REDIRECT=False` : App Runner termine déjà le TLS en amont. Laisser `True` provoque une boucle de redirection.

Générer la clé secrète :
```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

## 4. Web App — S3 + CloudFront

```bash
cd web-app
echo "VITE_API_URL=https://api.<domaine>/api" > .env.production
npm ci && npm run build
aws s3 sync dist/ s3://taskforce-web --delete
```

- CloudFront devant le bucket, **Default root object** `index.html`
- **Custom error response obligatoire** : 403 **et** 404 → `/index.html`, code 200.
  Sans cela, un rechargement sur `/espace/publications/...` renvoie une erreur.
- Invalider `/*` après chaque déploiement.

> `VITE_API_URL` est injecté **à la compilation**. Changer l'URL impose un rebuild, pas un simple redémarrage.

## 5. DNS et certificats (Route 53 + ACM)

| Nom | Cible |
|---|---|
| `<domaine>` | CloudFront (Web App) |
| `api.<domaine>` | App Runner |
| `media.<domaine>` | CloudFront (bucket médias) |

Certificats ACM **dans us-east-1** pour CloudFront. HTTPS obligatoire : les callbacks OAuth en HTTP sont refusés par Google.

## 6. Publications programmées

Rien ne les diffusait auparavant. Programmer `run_scheduled_publications` toutes les 5 minutes :

EventBridge Scheduler → ECS Fargate task (même image), commande :
```
python manage.py run_scheduled_publications
```

La commande est **idempotente** : deux exécutions simultanées ne publient jamais deux fois.

## 7. Après obtention des URLs réelles

Mettre à jour côté backend :
```env
ALLOWED_HOSTS=api.<domaine>
FRONTEND_URL=https://<domaine>
CORS_ALLOWED_ORIGINS=https://<domaine>
CSRF_TRUSTED_ORIGINS=https://<domaine>,https://api.<domaine>
SOCIAL_AUTH_REDIRECT_BASE=https://api.<domaine>
```

Puis, dans les consoles fournisseurs :

**Google Cloud** (projet `task-force-presidentielle`, n° `442441690167`) — ajouter le callback de production **sans supprimer celui de développement** :
```
https://api.<domaine>/api/social-accounts/oauth/youtube/callback/
```

**LinkedIn** — même opération pour `.../linkedin/callback/`.

## 8. Vérification — ne rien considérer comme déployé avant

- [ ] `https://api.<domaine>/healthz/` → `{"status":"ok","database":"ok"}`
- [ ] `https://api.<domaine>/admin/` → page de connexion **avec CSS**
- [ ] Connexion depuis le Web App réel (ni CORS ni CSRF en console)
- [ ] Téléversement d'une image → URL S3 → **toujours visible après un redéploiement**
- [ ] Reconnexion YouTube via le callback de production
- [ ] Publication test YouTube en `unlisted`, vidéo réellement présente
- [ ] Une publication programmée part toute seule
- [ ] App mobile pointée sur l'API de production

---

## Limitations connues (à traiter, non bloquantes pour le déploiement)

**Opérations longues et synchrones.** L'upload YouTube, l'envoi e-mail en masse et l'upload média LinkedIn s'exécutent **dans la requête HTTP**. L'upload YouTube de test a pris ~7 s pour 400 Ko ; une vidéo de 200 Mo dépassera le timeout d'App Runner (120 s configuré via `GUNICORN_TIMEOUT`). Aucune file de tâches n'existe dans le projet. À prévoir avant de publier des vidéos volumineuses ou d'envoyer une newsletter à une large audience.

**OAuth Google en mode `Testing`.** Les refresh tokens expirent au bout de 7 jours. Le passage en production exige une politique de confidentialité et des CGU publiques, un domaine vérifié, puis la validation Google (scope `youtube.upload` = sensible). C'est précisément ce que débloque ce déploiement.

**LinkedIn.** La publication échoue toujours sur `/author` (erreur pré-existante, non liée au déploiement).
