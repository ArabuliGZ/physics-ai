# Deployment Notes

## Render with a Timeweb domain

Keep the app hosted on Render and attach the domain bought on Timeweb as a
custom domain in Render.

In Render:

- Open the web service.
- Go to Settings -> Custom Domains.
- Add the domain or subdomain you want to use.
- Copy the DNS records Render gives you.

In Timeweb DNS:

- Add the records Render shows for your domain.
- For a subdomain like `app.example.ru`, this is usually a `CNAME`.
- For the root domain like `example.ru`, use the exact record Render provides.

OpenRouter stays external: the browser calls this app at `/check`, and only the
backend calls `https://openrouter.ai/api/v1/chat/completions`. Keep
`OPENROUTER_API_KEY` in Render environment variables, not in frontend JavaScript.

Recommended Render environment variables:

```text
MODEL_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-sonnet-4
SEED_DEMO_DATA=0
```

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
