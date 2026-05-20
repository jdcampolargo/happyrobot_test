# HappyRobot Inbound Carrier Sales PoC

This is the build for the HappyRobot FDE technical challenge.

What's the idea? A carrier calls in looking for freight, the HappyRobot agent gets their MC number, checks if they are eligible, searches loads, negotiates the rate, and then logs what happened so the broker can actually see useful metrics after the call.

I built the HappyRobot side as the voice workflow and this repo is the custom backend/dashboard that supports it.

## What this does

- Verifies carriers by MC number through FMCSA, with fallback demo records if the external lookup is unavailable.
- Searches a structured load file with the fields from the prompt.
- Evaluates counteroffers with deterministic pricing rules instead of letting the model guess.
- Handles up to three negotiation rounds.
- Logs post-call outcomes, sentiment, offers, lane data, and transcript details.
- Shows a custom metrics dashboard instead of relying on HappyRobot platform analytics.
- Runs as a Dockerized FastAPI app.

## Main endpoints

- `POST /api/carriers/verify`
- `POST /api/loads/search`
- `POST /api/offers/evaluate`
- `POST /api/calls/log`
- `GET /api/metrics`
- `GET /dashboard`

All API routes use an API key. The dashboard can use a query-param key for demo purposes.

## Dashboard

I tried to make the dashboard show things a broker would actually care about:

- total calls
- mocked transfer rate
- qualified carrier rate
- rate vs loadboard
- average final offer
- negotiation rounds
- outcome mix
- sentiment mix
- lane conversion
- recent call records

## Demo values

For the web-call demo:

- Eligible MC: `123456` - B MARRON LOGISTICS LLC
- Ineligible MC: `100008` - BC ECOCHIPS LTD
- Main load: `ACME-1001`, Chicago, IL to Dallas, TX, dry van, listed at `$2,450`


## Running it locally

If needed:

```bash
cp .env.example .env
docker compose up --build
```

Then open:

```text
http://localhost:8000/dashboard?api_key=local-dev-key
```

## Notes

The live version is deployed separately from this repo. Secrets are not committed here, so `.env` needs to be created locally or configured in the deployment environment.
