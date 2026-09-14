# Déploiement automatique (GitHub Actions)

Trois workflows, un par cible. Chacun ne se déclenche que si le dossier
concerné a changé — modifier le web-app ne relance pas le build mobile.

| Workflow | Fichier | Déclencheur | Résultat |
|---|---|---|---|
| Web App | `.github/workflows/deploy-web.yml` | push `main` sur `web-app/**` | site en ligne (Cloudflare Workers) |
| API Django | `.github/workflows/deploy-backend.yml` | push `main` sur `backend/**` | image sur ECR + redéploiement App Runner |
| App mobile | `.github/workflows/build-mobile.yml` | manuel, ou tag `mobile-v*` | APK Android / IPA iOS via EAS |

## Pourquoi ce découpage

Le site et l'API se redéploient **à chaque push** : c'est du code serveur, la
mise à jour est immédiate et réversible. Les apps mobiles passent par une
**revue des stores** (quelques heures à 2 jours) et une version installée chez
l'utilisateur ne se remplace pas d'un push : elles se déclenchent donc à la
demande, sur un tag de version, jamais automatiquement.

## Secrets à créer

`Settings > Secrets and variables > Actions` dans le dépôt GitHub.

### Web App — onglet *Secrets*
| Nom | Où le trouver |
|---|---|
| `CLOUDFLARE_API_TOKEN` | dash.cloudflare.com > My Profile > API Tokens > Create Token > modèle **Edit Cloudflare Workers** |
| `CLOUDFLARE_ACCOUNT_ID` | `75a7ce7f558c33f20edfd67b0c041f92` |
| `VITE_API_URL` | l'URL publique de l'API, ex. `https://api.exemple.cd/api` |

Le projet Cloudflare existe déjà : **`taskforce`**, en ligne sur
<https://taskforce.bofigauthier3.workers.dev>. Sa configuration est
`wrangler.jsonc`, à la racine du dépôt.

> `wrangler.jsonc` → `assets.directory` doit rester sur **`web-app/dist`**.
> Tout ce que contient ce dossier est servi publiquement : le faire pointer sur
> `web-app/` publierait les sources, `node_modules` et les fichiers `.env`.

Le fallback SPA est assuré par `not_found_handling: single-page-application`.
L'ancien `web-app/public/_redirects` a été supprimé : les Workers refusent la
règle `/* /index.html 200` (boucle de redirection détectée au déploiement).

> `VITE_API_URL` est **inliné à la compilation**. Changer l'URL de l'API impose
> de relancer le workflow, pas seulement de redémarrer le serveur.

### API Django (AWS)

| Nom | Type | Rôle |
|---|---|---|
| `AWS_ROLE_ARN` | secret | rôle IAM assumé par GitHub via OIDC — aucune clé longue durée |
| `APPRUNNER_SERVICE_ARN` | secret, optionnel | déclenche le redéploiement et attend le retour en `RUNNING`. Absent → l'image est seulement poussée sur ECR |
| `AWS_REGION` | variable | défaut `eu-west-3` (Paris) |
| `ECR_REPOSITORY` | variable | défaut `taskforce-backend` |

Préparation AWS, une seule fois. Le dépôt d'images :

```bash
aws ecr create-repository --repository-name taskforce-backend --region eu-west-3
```

Le fournisseur OIDC, à ne créer que s'il n'existe pas déjà sur le compte :

```bash
aws iam create-open-id-connect-provider   --url https://token.actions.githubusercontent.com   --client-id-list sts.amazonaws.com
```

Puis le rôle assumable **uniquement** par la branche `main` de ce dépôt —
c'est cette condition `sub` qui empêche un autre dépôt d'utiliser le rôle :

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
cat > trust.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::${ACCOUNT}:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:BofiLUbala/task-force-communication:ref:refs/heads/main"
      }
    }
  }]
}
JSON
aws iam create-role --role-name github-actions-taskforce   --assume-role-policy-document file://trust.json
aws iam attach-role-policy --role-name github-actions-taskforce   --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

Si le workflow doit aussi redéployer App Runner, ajouter une politique en
ligne autorisant `apprunner:StartDeployment` et `apprunner:DescribeService`
sur l'ARN du service. L'ARN du rôle (`aws iam get-role --role-name
github-actions-taskforce --query Role.Arn --output text`) devient
`AWS_ROLE_ARN`.

Le reste de l'infrastructure — RDS, S3 médias, App Runner, Route 53, la tâche
planifiée `run_scheduled_publications` — est décrit pas à pas dans
[DEPLOYMENT.md](DEPLOYMENT.md). Ce workflow ne couvre que la livraison
continue de l'image.

### App mobile
| Nom | Où le trouver |
|---|---|
| `EXPO_TOKEN` | expo.dev > Account settings > Access tokens |

Préparation, une seule fois, depuis `mobile-app/` :

```bash
npm install -g eas-cli
eas login
eas init          # écrit extra.eas.projectId dans app.json → à commiter
eas secret:create --name EXPO_PUBLIC_API_URL --value https://api.<domaine>/api
eas credentials   # Android : laisser EAS générer le keystore
```

Pour iOS, il faut un compte **Apple Developer (99 $/an)** ; sans lui, seul le
profil `preview` (build simulateur) fonctionne. Aucun Mac n'est nécessaire :
le build tourne sur les serveurs Expo.

## Utilisation

**Site et API** — rien à faire : `git push` sur `main`.

**APK Android de test** — Actions > *Build mobile* > Run workflow >
plateforme `android`, profil `preview`. Le lien de téléchargement de l'APK
s'affiche à la fin du job (il reste aussi sur expo.dev).

**Version pour les stores** :

```bash
git tag mobile-v1.0.0
git push origin mobile-v1.0.0
```

Build `production` sur Android **et** iOS. L'envoi aux stores se fait ensuite
avec `eas submit --platform android --latest` (idem `ios`).

## Vérifier qu'un déploiement est bien parti

- Onglet **Actions** : le job doit être vert.
- Web : rechargement forcé du site, la modification doit être visible.
- API : `https://api.<domaine>/healthz/` → `{"status":"ok","database":"ok"}`.
