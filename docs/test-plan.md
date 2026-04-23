# V1 Verification Checklist

## Functional checks

- Portal homepage loads and renders banner, about, news, cases, quick links, and footer.
- News list supports keyword filtering and detail navigation.
- Case list supports keyword filtering and detail navigation.
- About page renders single-page content, leaders, and contact settings.
- Registering a user creates a pending account.
- Admin can approve pending users.
- Admin can create articles, cases, pages, banners, and upload files.
- Service page can submit a consultation request.

## Security checks

- Passwords are stored as hashes.
- Admin endpoints require bearer tokens.
- Non-admin users are blocked from admin APIs.

## Deployment checks

- API starts and seeds initial content on an empty database.
- Admin console and portal frontend can be started with environment-based API endpoints.
- Docker Compose contains API, frontend, admin, PostgreSQL, and Redis services.
