# Watch List (Django)

Application Django avec:
- authentification complète (inscription, connexion, déconnexion),
- reset password (forgot + reset token expiré et stocké hashé),
- watchlist privée par utilisateur,
- import de séries TMDB (Netflix / Amazon Prime / Apple TV).

## Prérequis

- Python 3.13+
- pipenv (ou pip + virtualenv)

## Variables d'environnement

Fichier partagé lu automatiquement:
- `api/tmdb-streaming/environments/.env`

- `DEBUG` (default: `true`)
- `ALLOWED_HOSTS` (default: `localhost,127.0.0.1`)
- `TMDB_READ_ACCESS_TOKEN`
- `TMDB_LANGUAGE` (default: `fr-FR`)
- `TMDB_WATCH_REGION` (default: `US`)
- `FRANCECONNECT_ENABLED` (default: `true`, actif seulement si client id/secret présents)
- `FRANCECONNECT_CLIENT_ID`
- `FRANCECONNECT_CLIENT_SECRET`
- `FRANCECONNECT_AUTHORIZE_URL` (default: `https://fcp-low.integ01.dev-franceconnect.fr/api/v1/authorize`)
- `FRANCECONNECT_TOKEN_URL` (default: `https://fcp-low.integ01.dev-franceconnect.fr/api/v1/token`)
- `FRANCECONNECT_USERINFO_URL` (default: `https://fcp-low.integ01.dev-franceconnect.fr/api/v1/userinfo`)
- `FRANCECONNECT_SCOPE` (default: `openid profile email`)
- `FRANCECONNECT_REDIRECT_URI` (optionnel, sinon auto-construit)
- `EMAIL_BACKEND` (default: `django.core.mail.backends.console.EmailBackend`)
- `DEFAULT_FROM_EMAIL` (default: `no-reply@watch-list.local`)
- `SESSION_COOKIE_SECURE` (default: `false`)
- `CSRF_COOKIE_SECURE` (default: `false`)
- `SECURE_HSTS_SECONDS` (default: `0`)
- `CORS_ALLOWED_ORIGINS` (comma-separated, example: `https://app.example.com`)

## Démarrage local

```bash
cd watch-list/watch-list
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py seed_data
pipenv run python manage.py runserver
```

Utilisateurs:
- seed: `seed@example.com` / `SeedPass123!`

## Endpoints principaux

- `GET/POST /register/`
- `GET/POST /login/`
- `GET /login/franceconnect/` (démarrage OAuth2/OIDC FranceConnect)
- `GET /login/franceconnect/callback/` (callback OAuth2/OIDC FranceConnect)
- `POST /logout/`
- `GET/POST /forgot-password/`
- `GET/POST /reset-password/<token>/`
- `GET /me/` (JSON utilisateur connecté)
- `GET /` (watchlist privée, login requis)

## Sécurité implémentée

- Hash des mots de passe Django (`set_password` / auth backend Django)
- Validation serveur des formulaires
- Protection CSRF (sessions/cookies)
- Rate limiting:
  - `/login/`
  - `/forgot-password/`
- Messages neutres sur forgot-password (pas d'énumération d'email)
- Cookies session/CSRF durcis (`httpOnly`, `sameSite`, options `secure`)
- Headers sécurité + CORS restreint aux origines autorisées
- Pas de logs de mots de passe/tokens
- Tokens de reset stockés hashés + expiration + invalidation après usage

## Tests

```bash
cd watch-list/watch-list
python3 manage.py test
```

Les tests couvrent:
- validation formulaires auth,
- workflows register/login/logout/me,
- workflow login FranceConnect + création auto si utilisateur inconnu,
- forgot/reset password,
- isolation des watchlists par utilisateur,
- import TMDB et anti-doublons par utilisateur.
