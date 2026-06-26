# Lynx URL Shortener

Lynx is a serverless URL shortener built on AWS. It serves a React portal from
S3 through CloudFront, creates short links through a protected Lambda Function
URL, and resolves short links through S3 website redirect objects.

The first version deliberately avoids API Gateway. Browser traffic enters
through CloudFront. API requests to `/api/*` are signed by Lambda@Edge before
they reach the create-link Lambda Function URL, and public short links use the
`/l/{code}` path.

## Architecture

- CloudFront is the public entrypoint for the portal, API, and redirects.
- The portal is a Vite, React, and TypeScript app in `portal/`.
- `POST /api/links` routes to a Lambda Function URL protected with `AWS_IAM`.
- Lambda@Edge signs API origin requests with SigV4.
- Short links are generated server-side and written as S3 objects at `l/{code}`.
- S3 website redirect metadata points each short link at its target URL.
- Redirect objects are tagged with `ttl=24h` or `ttl=7d`.
- S3 lifecycle rules expire redirect objects after 1 or 7 days.
- SNS alerts are published when links are created and when CloudWatch alarms fire.

See [notes/SPECIFICATION.md](notes/SPECIFICATION.md) for the detailed design.

## Portal Development

Install dependencies once:

```sh
cd portal
npm install
```

Run the local dev server:

```sh
npm run dev
```

Validate the portal:

```sh
npm run lint
npm run test
npm run build
npm audit
```

The production build is written to `portal/dist/` for upload to the portal S3
bucket.

## Lambda Development

Lambda functions live under `infrastructure/lambdas/`, with each function in
its own folder containing `src/` and `tests/`.

Run the shared checks:

```sh
cd infrastructure/lambdas
make test
make lint
make package
```

The Lambda tooling uses UV and Python. Terraform packages deployment artifacts
from each Lambda `src/` directory.

## Terraform

Terraform environment entrypoints live in:

```text
infrastructure/terraform/environments/dev/
infrastructure/terraform/environments/prod/
```

The shared implementation lives in:

```text
infrastructure/terraform/modules/lynx/
```

Common validation flow:

```sh
terraform fmt -recursive infrastructure/terraform

cd infrastructure/terraform/environments/dev
terraform init
terraform validate

cd ../prod
terraform init
terraform validate
```

Use `terraform plan` and `terraform apply` from the target environment directory
when deploying.

## API

Create a short link:

```http
POST /api/links
Content-Type: application/json

{
  "url": "https://example.com/some/long/path",
  "ttl": "24h"
}
```

Allowed TTL values are `24h` and `7d`. Missing `ttl` defaults to `24h`.
Targets must be absolute HTTPS URLs.

Successful responses include the generated code, short URL, target URL, TTL,
and nominal expiration timestamp.

## Deployment Notes

GitHub Actions deploys Lynx through `.github/workflows/deploy.yml`:

- Pull requests opened, reopened, or updated against `main` deploy `dev`.
- Pushes to `main`, including merged pull requests, deploy `prod`.
- Manual runs can deploy either environment through `workflow_dispatch`.

Create GitHub Environments named `dev` and `prod`, then add an environment
secret named `AWS_ROLE_ARN` to each one. The current role ARN is:

```text
arn:aws:iam::804221019544:role/github-actions-role
```

The permissions policy to attach to that role is in
[notes/GITHUB_ACTIONS_IAM_POLICY.json](notes/GITHUB_ACTIONS_IAM_POLICY.json).
It includes create, update, and delete permissions because Terraform applies
must be able to remove replaced resources as well as create them.

After applying the dev infrastructure:

1. Build the portal with `npm run build` in `portal/`.
2. Upload `portal/dist/` to the Terraform output portal bucket.
3. Open the CloudFront-backed domain.
4. Create a link through the portal.
5. Visit `/l/{code}` and confirm the S3 website redirect works.
6. Confirm the SNS alert contains the expected link creation details.

Example portal upload for dev:

```sh
cd portal
npm run build

PORTAL_BUCKET=$(cd ../infrastructure/terraform/environments/dev && terraform output -raw portal_bucket)
aws s3 sync dist/ "s3://${PORTAL_BUCKET}/" --delete
```

For prod, use the prod Terraform environment:

```sh
cd portal
npm run build

PORTAL_BUCKET=$(cd ../infrastructure/terraform/environments/prod && terraform output -raw portal_bucket)
aws s3 sync dist/ "s3://${PORTAL_BUCKET}/" --delete
```

If CloudFront has cached an older portal build, invalidate the distribution:

```sh
DISTRIBUTION_ID=$(cd ../infrastructure/terraform/environments/dev && terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths "/*"
```

## Current Tradeoffs

- S3 website redirects return HTTP `301`. Returning `307` would require a
  Lambda redirect resolver instead of the native S3 redirect engine.
- S3 lifecycle expiration is day-based and asynchronous, so displayed expiry
  timestamps are nominal.
- Link creation is public in the initial version. Future hardening may add
  authentication, WAF rate rules, custom aliases, analytics, or admin views.
