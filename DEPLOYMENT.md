# Deployment Notes

## Render demo data

For a temporary public test stand, set this environment variable:

```text
SEED_DEMO_DATA=1
```

When enabled, the app creates demo users, demo students, and sample progress during startup. It does not delete existing data.

Useful test logins:

```text
teacher@test.ru
admin@test.ru
7@test.ru
8@test.ru
9@test.ru
```

Do not commit the SQLite database file. The demo data is generated from code.
