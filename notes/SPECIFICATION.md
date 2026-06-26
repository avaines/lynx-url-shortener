# Lynx URL Shortener Specification

## Purpose

Lynx is a small serverless URL shortener deployed on AWS. It provides a public web portal for creating short links and a CloudFront-backed redirect path for resolving them.

The service combines two AWS patterns:

- A CloudFront distribution in front of a static React portal and protected Lambda Function URLs.
- An S3 website redirection engine where zero-byte S3 objects contain website redirect metadata pointing at the long URL.

The first implementation must avoid API Gateway. Browser traffic enters through CloudFront, API requests are routed to Lambda Function URLs, and link redirects are served by S3 website redirect objects.

## Source References

- AWS Compute Blog, "Protecting an AWS Lambda function URL with Amazon CloudFront and Lambda@Edge": https://aws.amazon.com/blogs/compute/protecting-an-aws-lambda-function-url-with-amazon-cloudfront-and-lambdaedge/
- AWS Compute Blog, "Build a Serverless, Private URL Shortener": https://aws.amazon.com/blogs/compute/build-a-serverless-private-url-shortener/
- Amazon S3 webpage redirect documentation: https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-to-page-redirect.html
- CloudFront origin access control documentation: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html

## Core Decisions

- Public short links use the path format `/l/{code}`.
- Link creation is public for the initial version.
- Users can create generated short codes only. Custom aliases are out of scope.
- Long URLs must use `https://`.
- The default link lifetime is 24 hours.
- Users can optionally choose a 7-day lifetime.
- Link expiry is enforced by S3 lifecycle rules.
- A redirect creation event publishes a full SNS notification.
- API creation traffic uses Lambda Function URLs protected with `AWS_IAM`.
- CloudFront uses Lambda@Edge on API origin requests to add SigV4 authentication headers before forwarding requests to the Lambda Function URL.
- API Gateway is not used.
- The portal is built with Vite and React under `portal/`.

## Important Tradeoffs

### Redirect Status Code

S3 object website redirects are interpreted by the S3 website endpoint as HTTP `301` redirects. Lynx will use this S3-native redirect behavior for the first implementation.

A true HTTP `307` redirect would require putting Lambda in the redirect path, for example by routing `/l/*` to a resolver Lambda that reads redirect metadata and returns `307`. That is not part of the initial implementation because the chosen requirement is to use the S3 webpage redirect mechanism from the AWS blog post.

### Expiry Precision

S3 lifecycle expiration is day-based and asynchronous. A 24-hour link should be treated as "eligible for expiry after 1 day", and a 7-day link should be treated as "eligible for expiry after 7 days". The portal and SNS messages may show a nominal expiration timestamp, but the storage cleanup is not guaranteed to happen at the exact timestamp.

### Bucket Layout

The preferred implementation uses separate buckets:

- A private portal bucket served by CloudFront using origin access control.
- A redirect bucket configured for S3 static website hosting and S3 object redirects.

This is less tidy than a single bucket, but it keeps the portal on the normal private-S3-plus-OAC pattern. CloudFront OAC does not support S3 website endpoints, and S3 object redirects only execute when requests hit the website endpoint rather than the REST endpoint.

## User Flows

### Create a Short Link

1. A user opens the CloudFront-backed portal.
2. The portal displays a URL input and a lifetime selector.
3. The user enters an `https://` URL.
4. If the user does not choose a lifetime, the portal submits `24h`.
5. The portal sends `POST /api/links` to the same CloudFront domain.
6. CloudFront routes `/api/*` to the create-link Lambda Function URL origin.
7. Lambda@Edge signs the origin request using SigV4 and the Lambda service.
8. The create-link Lambda validates the request.
9. The create-link Lambda generates a short code.
10. The Lambda creates a zero-byte redirect object in S3 at `l/{code}` with `x-amz-website-redirect-location` set to the long URL.
11. The Lambda tags the redirect object with the selected TTL class.
12. The Lambda publishes a message to the SNS alerts topic.
13. The Lambda returns the short URL to the portal.
14. The portal displays the short URL and a copy action.

### Follow a Short Link

1. A visitor opens `https://{domain}/l/{code}`.
2. CloudFront routes `/l/*` to the redirect bucket website endpoint.
3. S3 website hosting reads the object metadata for `l/{code}`.
4. S3 returns an HTTP `301` redirect to the stored long URL.
5. The visitor's browser follows the redirect.

### Expire a Short Link

1. Each redirect object has an object tag identifying its TTL class.
2. The redirect bucket lifecycle policy expires objects tagged `ttl=24h` after 1 day.
3. The redirect bucket lifecycle policy expires objects tagged `ttl=7d` after 7 days.
4. After S3 deletes the redirect object, `/l/{code}` returns not found.

## Public API

### `POST /api/links`

Creates a short link.

Request body:

```json
{
  "url": "https://example.com/some/long/path",
  "ttl": "24h"
}
```

Fields:

- `url` is required and must be an absolute `https://` URL.
- `ttl` is optional. Allowed values are `24h` and `7d`. The default is `24h`.

Successful response:

```json
{
  "code": "aB3kP9xQ",
  "short_url": "https://lynx.example.com/l/aB3kP9xQ",
  "target_url": "https://example.com/some/long/path",
  "ttl": "24h",
  "nominal_expires_at": "2026-06-27T12:00:00Z"
}
```

Status codes:

- `201` when the link is created.
- `400` when the request body is invalid.
- `405` when the method is unsupported.
- `409` if generated-code collision retries are exhausted.
- `500` for unexpected failures.

### API Security

The Lambda Function URL uses `authorization_type = "AWS_IAM"`.

CloudFront attaches a Lambda@Edge function to the `/api/*` origin request behavior. The edge function signs the request with SigV4 and adds the standard AWS authentication headers required by Lambda Function URLs, including `Authorization`, `X-Amz-Date`, and, when applicable, `X-Amz-Security-Token`.

`X-Lynx-Origin-Authorization` is not used for the initial Lambda Function URL protection model. A custom header would be suitable for a future `AuthType = NONE` plus shared-secret design, but the AWS_IAM Function URL model requires standard SigV4 headers.

Because `POST /api/links` has a body, the CloudFront Lambda@Edge association must include the request body for the API behavior. Link creation payloads are intentionally small.

## Redirect Object Format

Each short link is represented by a zero-byte S3 object in the redirect bucket.

Object key:

```text
l/{code}
```

Object metadata:

```text
x-amz-website-redirect-location: https://example.com/some/long/path
```

Object tags:

```text
ttl=24h
```

or:

```text
ttl=7d
```

The public URL path remains `/l/{code}` for both TTL classes. Lifecycle rules filter by object tag rather than by folder prefix so the URL namespace stays stable.

## Code Generation

- Codes are generated server-side only.
- Codes use a URL-safe alphabet.
- The first implementation should use 8 characters.
- The alphabet should avoid path separators and whitespace.
- The Lambda must check for object existence before writing.
- On collision, the Lambda retries with a new code.
- If retries are exhausted, the Lambda returns `409`.

Recommended alphabet:

```text
0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
```

## URL Validation

The create-link Lambda must reject:

- Missing URLs.
- Non-string URLs.
- URLs that are not absolute.
- URLs whose scheme is not `https`.
- URLs with no hostname.
- URLs longer than the configured maximum.
- Non-public or malformed hostnames if validation for those is introduced.

Initial maximum URL length: 2048 characters.

Future hardening may add blocklists, private IP detection after DNS resolution, phishing checks, or authenticated creation.

## SNS Alerts

Every successful redirect creation publishes to an SNS topic.

The alert payload should include:

- Event type, for example `link_created`.
- Environment.
- Short code.
- Short URL.
- Target URL.
- TTL class.
- Nominal expiration timestamp.
- Redirect bucket name.
- Redirect object key.
- Requester IP, using `X-Forwarded-For` when present.
- User agent.
- Referer, when present.
- CloudFront request ID, when available.
- Lambda request ID.
- Creation timestamp.

The SNS topic contains sensitive data because it includes target URLs and requester information. Topic policies and subscriptions must be kept narrow.

## CloudFront Design

One CloudFront distribution fronts the entire service.

Behaviors:

- Default behavior serves the portal from the private portal S3 bucket.
- `/api/*` routes to the create-link Lambda Function URL origin.
- `/l/*` routes to the redirect bucket S3 website endpoint.

Viewer policy:

- Redirect HTTP to HTTPS or require HTTPS-only viewer requests.

API behavior:

- Allowed methods include `GET`, `HEAD`, `OPTIONS`, `POST`.
- Cached methods are `GET` and `HEAD`.
- Caching is disabled for `/api/*`.
- The origin request Lambda@Edge function signs requests for the Lambda Function URL.
- Request body forwarding is enabled for signing `POST` requests.

Redirect behavior:

- Allowed methods are `GET` and `HEAD`.
- Caching should be disabled or use a very low TTL to avoid stale short-link behavior after lifecycle expiry.
- The origin is configured as a custom origin because S3 website endpoints are not S3 REST origins.
- Origin protocol to the S3 website endpoint is HTTP.

Portal behavior:

- The portal bucket remains private and is accessed through CloudFront OAC.
- The portal is initially a simple single-screen application, so CloudFront SPA fallback is not required for `/l/*`.

## Lambda Design

### `create_link`

Location:

```text
infrastructure/lambdas/create_link/
```

Structure:

```text
infrastructure/lambdas/create_link/src/
infrastructure/lambdas/create_link/tests/
```

Runtime:

- Python.
- Managed with UV through the shared `infrastructure/lambdas/` tooling.

Responsibilities:

- Parse Function URL event payloads.
- Validate method and body.
- Validate HTTPS target URL.
- Normalize TTL selection.
- Generate a short code.
- Check redirect object collisions.
- Write a zero-byte redirect object with website redirect metadata.
- Tag the object with the TTL class.
- Publish the SNS alert.
- Return JSON responses with appropriate status codes.

Environment variables:

- `REDIRECT_BUCKET_NAME`
- `PUBLIC_BASE_URL`
- `ALERTS_TOPIC_ARN`
- `DEFAULT_TTL`
- `MAX_URL_LENGTH`
- `CODE_LENGTH`

### `edge_signer`

Location:

```text
infrastructure/lambdas/edge_signer/
```

Structure:

```text
infrastructure/lambdas/edge_signer/src/
infrastructure/lambdas/edge_signer/tests/
```

Runtime:

- Python, unless implementation proves materially simpler or safer in Node.js.
- If Node.js is selected only for Lambda@Edge SigV4 signing, document the exception clearly in the lambda README or module comments.

Responsibilities:

- Run as Lambda@Edge on origin requests for `/api/*`.
- Derive the target Lambda Function URL host and region.
- Sign the outgoing request for the Lambda service using SigV4.
- Add the required authentication headers.
- Preserve request method, path, query string, and body.
- Avoid logging secrets or signed authorization values.

Lambda@Edge constraints:

- The function must be created in `us-east-1`.
- CloudFront must associate a published function version, not `$LATEST`.
- The execution role must trust both Lambda and Lambda@Edge service principals as required.
- The role must allow `lambda:InvokeFunctionUrl` for the protected create-link Lambda Function URL with the `lambda:FunctionUrlAuthType = AWS_IAM` condition.
- The role must also allow `lambda:InvokeFunction` with `lambda:InvokedViaFunctionUrl = true`, which is required for new Lambda Function URLs.

## Portal Design

Location:

```text
portal/
```

Technology:

- Vite.
- React.
- TypeScript preferred.

Initial user interface:

- A modern, professional single-screen form.
- URL input.
- TTL selector with `24 hours` and `7 days`.
- Submit button with loading state.
- Result view showing the generated short URL.
- Copy-to-clipboard control.
- Validation and error states.
- Responsive layout for mobile and desktop.

The portal should be the application itself, not a marketing landing page.

## Terraform Design

Terraform lives under:

```text
infrastructure/terraform/
```

Environment entrypoints:

```text
infrastructure/terraform/environments/dev/
infrastructure/terraform/environments/prod/
```

Primary module:

```text
infrastructure/terraform/modules/lynx/
```

Shared S3 module:

```text
infrastructure/terraform/modules/s3_bucket/
```

Naming convention:

- Each Terraform resource should live in a hierarchical file named after the resource type without the `aws_` prefix, then the resource name, then `.tf`.
- Example: `sns_topic.alerts.tf` for `resource "aws_sns_topic" "alerts"`.
- Data resources for resource-local policies may live beside the resource that uses them.
- Shared or reused data resources should be split into their own hierarchical file.

Expected Lynx resources include:

- `cloudfront_distribution.main`
- `cloudfront_origin_access_control.portal`
- `lambda_function.create_link`
- `lambda_function_url.create_link`
- `lambda_function.edge_signer`
- `iam_role.create_link`
- `iam_role.edge_signer`
- `iam_role_policy.create_link`
- `iam_role_policy.edge_signer`
- `s3_bucket_website_configuration.redirects`
- `s3_bucket_lifecycle_configuration.redirects`
- `s3_bucket_policy.redirects`
- `sns_topic.alerts`
- `sns_topic_subscription.alert_email`
- `route53_record.main`
- `acm_certificate.main`
- `acm_certificate_validation.main`

Module variables should include:

- `environment`
- `domain_root`
- `alert_email`
- `default_ttl`
- `extended_ttl`
- `code_length`
- `max_url_length`

Environment-specific `domain_root` values should represent the actual public app domain for that environment. The module should not add an extra environment subdomain unless that is explicitly desired by the environment configuration.

## S3 Module Implications

The existing `s3_bucket` module is a useful starting point for private buckets. The redirect bucket needs additional behavior:

- Website hosting configuration.
- Public read access for website endpoint redirect objects, unless a different website-origin access strategy is chosen.
- Lifecycle rules filtered by object tag.
- Public access block settings compatible with the redirect bucket policy.

This may be implemented by extending the shared S3 module with explicit opt-in variables, or by creating redirect-specific resources in the `lynx` module when that keeps the shared module cleaner.

## Observability

Required logs and metrics:

- CloudWatch Logs for `create_link`, with explicit retention configured by Terraform.
- CloudWatch Logs for the Lambda@Edge signer source function in `us-east-1`, with explicit retention configured by Terraform.
- Lambda@Edge invocation logs are emitted in the AWS Region where each edge replica executes, not only in `us-east-1`. During operations, check CloudWatch Logs in Regions near viewers for Lambda@Edge replica log groups.
- Lambda errors and duration metrics.
- SNS publish failures from `create_link`.
- CloudFront standard metrics.

Recommended alarms:

- Create-link Lambda errors.
- Create-link Lambda throttles.
- Elevated CloudFront `5xx` rate.

SNS publish failures are not treated as a separate v1 alarm. The create-link Lambda currently converts unexpected failures into HTTP `500` responses, so SNS publish failures are expected to surface through the CloudFront `5xx` alarm and Lambda logs rather than the Lambda `Errors` metric. A future version can add a custom application metric if single failed SNS publishes need dedicated alerting.

## Abuse Controls

Because link creation is public in the initial version, the implementation should include basic abuse resistance:

- HTTPS-only target URLs.
- Maximum URL length.
- Generated-only codes.
- No arbitrary user-supplied object keys.
- No open CORS requirement because the portal and API share the same CloudFront domain and the portal uses same-origin `POST /api/links`.
- Consider AWS WAF rate-based rules on the CloudFront distribution.
- Keep SNS subscriptions restricted because alert messages include full target URLs and requester data. The v1 Terraform module manages a single email subscription from `var.alert_email`, and the SNS topic policy grants publishing to the create-link role and CloudWatch alarms.

## Testing Requirements

Lambda unit tests:

- Valid `POST /api/links` creates a redirect object.
- Missing URL returns `400`.
- Non-HTTPS URL returns `400`.
- Invalid TTL returns `400`.
- Missing TTL defaults to `24h`.
- `7d` TTL is accepted.
- Collision retry works.
- Collision retry exhaustion returns `409`.
- SNS publish payload includes required fields.
- Unsupported method returns `405`.

Edge signer tests:

- Signs requests with standard SigV4 headers.
- Preserves method, path, query string, and body.
- Does not log authorization header values.

Portal tests:

- Build succeeds.
- Form validation blocks invalid URLs.
- Successful API response renders copyable short URL.
- API error response renders a useful error state.

Terraform validation:

- `terraform fmt`.
- `terraform validate` per environment.
- Provider aliases or us-east-1 handling are correct for CloudFront, ACM, and Lambda@Edge.

## Acceptance Criteria

- Opening the CloudFront domain displays the Lynx portal.
- Submitting a valid HTTPS URL creates a short URL under `/l/{code}`.
- The direct Lambda Function URL is not invokable without IAM authentication.
- The CloudFront `/api/links` path successfully invokes the Lambda through Lambda@Edge signing.
- A redirect object is created at `l/{code}`.
- Visiting `/l/{code}` redirects to the original HTTPS URL.
- Default links are tagged for 24-hour lifecycle expiry.
- Extended links are tagged for 7-day lifecycle expiry.
- Every successful link creation publishes an SNS alert with full creation information.
- Terraform follows the repository's hierarchical file naming convention.
- Lambda source and tests live under `infrastructure/lambdas/{lambda_name}/src` and `infrastructure/lambdas/{lambda_name}/tests`.
- The portal source lives under `portal/` and uses Vite with React.

## Out of Scope for Initial Version

- User authentication.
- Custom aliases.
- API Gateway.
- DynamoDB link storage.
- Exact-to-the-second expiration.
- HTTP `307` redirects.
- Link editing or deletion from the portal.
- Link analytics.
- Preview/interstitial pages.
- Bulk link creation.

## Future Options

- Add user authentication for link creation.
- Add custom aliases with collision and reservation handling.
- Move redirect resolution to Lambda to support `307`, exact expiry checks, and analytics.
- Store link metadata in DynamoDB while continuing to use S3 redirects for simple resolution.
- Add WAF managed rule groups and stronger rate limits.
- Add domain allowlists or denylists.
- Add an admin view for recent links.
- Add audit/event storage beyond SNS notifications.
