# Logistics Load Tracker API

This is a small backend + dashboard for inbound carrier sales.

The basic flow is: a carrier comes in looking for freight, the system checks their MC number, searches available loads, evaluates any counteroffer, and logs the result so the broker can see what is actually happening across calls.

I built it to show the parts that matter in this kind of workflow: API design, carrier verification, load matching, pricing rules, call logging, and metrics.

## What this does

- Verifies carriers by MC number through FMCSA, with fallback demo records if the external lookup is unavailable.
- Searches a structured load file with pickup, delivery, rate, equipment, commodity, dimensions, and lane data.
- Evaluates counteroffers with deterministic pricing rules instead of letting the model guess.
- Handles up to three negotiation rounds.
- Logs post-call outcomes, sentiment, offers, lane data, and transcript details.
- Shows a custom metrics dashboard for call outcomes, carrier quality, rate discipline, and lane conversion.
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

The dashboard is meant to be more useful than a generic analytics page. It shows things a broker would actually care about:

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

Useful local values:

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

Secrets are not committed here, so `.env` needs to be created locally or configured in the deployment environment.
