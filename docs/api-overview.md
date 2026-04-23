# API Overview

## Public endpoints

- `GET /api/v1/public/home`
- `GET /api/v1/public/news`
- `GET /api/v1/public/news/{slug}`
- `GET /api/v1/public/cases`
- `GET /api/v1/public/cases/{slug}`
- `GET /api/v1/public/pages/{page_key}`
- `GET /api/v1/public/leaders`
- `GET /api/v1/public/institutes`
- `GET /api/v1/public/institutes/{slug}`
- `GET /api/v1/public/settings`
- `POST /api/v1/public/inquiries`

## Auth endpoints

- `POST /api/v1/auth/login/password`
- `POST /api/v1/auth/login/sms`
- `POST /api/v1/auth/register`
- `GET /api/v1/auth/me`

## Admin endpoints

- `GET /api/v1/admin/dashboard`
- `GET|POST|PUT /api/v1/admin/articles`
- `GET|POST|PUT /api/v1/admin/cases`
- `GET|POST|PUT /api/v1/admin/pages`
- `GET|POST|PUT /api/v1/admin/banners`
- `GET|POST /api/v1/admin/categories`
- `GET|POST /api/v1/admin/tags`
- `GET /api/v1/admin/leaders`
- `GET /api/v1/admin/institutes`
- `GET|POST /api/v1/admin/files`
- `GET|PUT /api/v1/admin/settings`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/pending`
- `POST /api/v1/admin/users/{id}/approve`
- `GET /api/v1/admin/audit-logs`
- `GET /api/v1/admin/login-logs`

## Response envelope

All endpoints return:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```
