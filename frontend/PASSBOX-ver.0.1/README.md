# Secure AI Console

## Development mock login

Mock login is available only when Vite runs in development mode and `VITE_API_BASE_URL` is unset. It is not included in the production bundle.

| Role | User ID | Password | Institution |
| --- | --- | --- | --- |
| USER | `test-user` | `Test1234!` | 테스트 기관 |
| OPERATOR | `test-operator` | `Test1234!` | 테스트 기관 |
| APPROVER | `test-approver` | `Test1234!` | 테스트 기관 |
| ADMIN | `test-admin` | `Test1234!` | 테스트 기관 |

Run `npm run dev`, open `/login`, and use one of the accounts above. Do not use these credentials outside local development.

## Vite template reference

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.

## PASSBOX backend integration

The frontend and backend are separate local projects. The frontend repository shares source code, but it does not share the PostgreSQL database, uploaded files, backend `.env`, or API keys.

For a real backend connection:

1. Copy `.env.example` to `.env.local`.
2. Set `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1` for local development.
3. Start PostgreSQL and the FastAPI backend separately.
4. Run the backend table setup and seed a local user before logging in.
5. Use an `APPROVER` or `SECURITY_ADMIN` account to open `/approvals`.

Never commit `.env.local`, backend `.env`, uploaded documents, database dumps, or API keys. Each teammate needs their own local environment and database. Source-code changes become visible to teammates only after they are committed and pushed to the shared Git repository.
