# Portal P1 User Lifecycle

## 1. Scope

P1-D closes the Portal V1 user-management lifecycle by extending the existing Portal auth/RBAC model. It does not implement SMS verification login, real SMS provider integration, password-reset changes, V2 business modules, or deployment changes.

## 2. User States

| State | Meaning | Login Result | Admin Operation |
|---|---|---|---|
| `pending` | Personal registration is waiting for review | rejected | approve or reject |
| `active` | User can authenticate and use role-based permissions | accepted | disable or assign role |
| `rejected` | Registration was rejected | rejected | no direct enable in P1-D |
| `disabled` | Existing account is administratively suspended | rejected | enable |

The password login route already requires `User.status == "active"`. P1-D also makes authenticated dependency resolution reject non-active accounts so a disabled account cannot continue using an existing token.

## 3. Admin API

| Method | Path | Purpose | Permission |
|---|---|---|---|
| `GET` | `/api/v1/admin/users` | List users with optional status filter | admin |
| `GET` | `/api/v1/admin/users/pending` | List pending registrations | admin |
| `GET` | `/api/v1/admin/roles` | List assignable role metadata | admin |
| `POST` | `/api/v1/admin/users` | Create an active institution user | admin |
| `POST` | `/api/v1/admin/users/{user_id}/approve` | Approve a pending personal registration | admin |
| `POST` | `/api/v1/admin/users/{user_id}/reject` | Reject a pending personal registration | admin |
| `POST` | `/api/v1/admin/users/{user_id}/disable` | Disable an active user | admin |
| `POST` | `/api/v1/admin/users/{user_id}/enable` | Re-enable a disabled user | admin |
| `PUT` | `/api/v1/admin/users/{user_id}/role` | Assign a role | super admin |

Institution user creation is limited to the current seed roles `registered_user` and `institute_editor`. P1-D reuses `institute_editor` as the current institution-user role code instead of renaming the seed role.

## 4. Safety Rules

- User creation hashes the initial password and never returns it.
- Role assignment requires `super_admin`.
- A user cannot disable their own account.
- A super admin cannot remove their own super-admin role.
- The last active super admin cannot be disabled or demoted.
- Rejected users are not directly enabled in P1-D.
- Password-reset token, expiry, hashing, and consumed-state behavior remain unchanged.

## 5. Audit Events

P1-D writes `audit_logs` records for:

- `users/create`
- `users/approve`
- `users/reject`
- `users/disable`
- `users/enable`
- `users/assign_role`

Audit details include status and role codes where useful. They do not include raw passwords, password-reset tokens, SMS codes, secrets, or full reset links.

## 6. Admin Console

The admin user page now supports:

- filtering by status;
- approving and rejecting pending users;
- disabling active users;
- enabling disabled users;
- creating institution users;
- assigning roles for active users.

The UI maps available actions to the backend state machine. It does not add SMS login, password-reset pages, or public portal content changes.

## 7. Smoke Coverage

`scripts/smoke_user_lifecycle_backend.sh` runs against an isolated runtime SQLite database and verifies:

- admin login;
- personal registration creates a pending user;
- pending login is rejected;
- approval enables login;
- disable blocks login;
- enable restores login;
- self-disable protection;
- admin-created institution user can log in;
- role assignment updates role code;
- self-demotion protection;
- rejection blocks login;
- audit events exist and do not contain raw smoke passwords.

## 8. Remaining Work

- Broader permission-matrix tests remain for P1-F.
- Formal migration support remains a later hardening item because the current Portal backend uses `Base.metadata.create_all`.
- Real SMTP password-reset full-link UAT remains separate from P1-D.
- SMS verification login remains excluded from Portal V1.
