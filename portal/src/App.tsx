import {
  Check,
  Clipboard,
  ExternalLink,
  Link2,
  Loader2,
  ShieldCheck
} from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";
import { createLink, type CreateLinkResponse, type TtlOption } from "./api";

type SubmitState = "idle" | "submitting" | "success" | "error";

const TTL_OPTIONS: Array<{ value: TtlOption; label: string; detail: string }> = [
  { value: "24h", label: "24 hours", detail: "Default" },
  { value: "7d", label: "7 days", detail: "Extended" }
];

export function App() {
  const [targetUrl, setTargetUrl] = useState("");
  const [ttl, setTtl] = useState<TtlOption>("24h");
  const [status, setStatus] = useState<SubmitState>("idle");
  const [error, setError] = useState("");
  const [result, setResult] = useState<CreateLinkResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const trimmedUrl = targetUrl.trim();
  const normalizedUrl = useMemo(() => normalizeTargetUrl(trimmedUrl), [trimmedUrl]);
  const urlError = useMemo(() => validateHttpsUrl(normalizedUrl), [normalizedUrl]);
  const canSubmit = trimmedUrl.length > 0 && !urlError && status !== "submitting";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCopied(false);

    const normalizedTargetUrl = normalizeTargetUrl(trimmedUrl);
    const validationMessage = validateHttpsUrl(normalizedTargetUrl);
    if (validationMessage) {
      setStatus("error");
      setError(validationMessage);
      setResult(null);
      return;
    }

    setStatus("submitting");
    setError("");

    try {
      const response = await createLink({ url: normalizedTargetUrl, ttl });
      setResult(response);
      setStatus("success");
    } catch (caughtError) {
      setResult(null);
      setStatus("error");
      setError(caughtError instanceof Error ? caughtError.message : "Unable to create link.");
    }
  }

  async function handleCopy() {
    if (!result) {
      return;
    }

    await navigator.clipboard.writeText(result.short_url);
    setCopied(true);
  }

  return (
    <main className="app-shell">
      <section
        className={result ? "workspace workspace-has-result" : "workspace"}
        aria-labelledby="portal-title"
      >
        <div className="work-panel">
          <header className="brand-row">
            <div className="brand-mark" aria-hidden="true">
              <span>L</span>
              <Link2 size={19} strokeWidth={2.5} />
            </div>
            <div className="brand-copy">
              <p className="eyebrow">lynx.vaines.dev</p>
              <h1 id="portal-title">Link Shortener</h1>
            </div>
          </header>

          <form className="link-form" onSubmit={handleSubmit} noValidate>
            <label htmlFor="target-url">Destination URL</label>
            <div className="url-field">
              <ExternalLink aria-hidden="true" size={20} />
              <input
                id="target-url"
                name="url"
                type="url"
                inputMode="url"
                placeholder="https://example.com/launch-notes"
                value={targetUrl}
                onChange={(event) => {
                  setTargetUrl(event.target.value);
                  setError("");
                }}
                aria-invalid={Boolean(trimmedUrl && urlError)}
                aria-describedby="url-hint"
              />
            </div>
            <p id="url-hint" className={trimmedUrl && urlError ? "field-error" : "field-hint"}>
              {trimmedUrl && urlError
                ? urlError
                : "HTTPS only. Bare domains are normalised before they are sent."}
            </p>

            <fieldset>
              <legend>Lifetime</legend>
              <div className="ttl-options">
                {TTL_OPTIONS.map((option) => (
                  <label
                    className={ttl === option.value ? "ttl-card ttl-card-selected" : "ttl-card"}
                    key={option.value}
                  >
                    <input
                      type="radio"
                      name="ttl"
                      value={option.value}
                      checked={ttl === option.value}
                      onChange={() => setTtl(option.value)}
                    />
                    <span>{option.label}</span>
                    <small>{option.detail}</small>
                  </label>
                ))}
              </div>
            </fieldset>

            {error ? (
              <div className="alert" role="alert">
                {error}
              </div>
            ) : null}

            <button className="submit-button" type="submit" disabled={!canSubmit}>
              {status === "submitting" ? (
                <Loader2 className="spin" size={20} aria-hidden="true" />
              ) : (
                <Link2 size={20} aria-hidden="true" />
              )}
              <span>{status === "submitting" ? "Creating" : "Create short link"}</span>
            </button>
          </form>
        </div>

        {result ? (
          <aside className="result-panel" aria-live="polite">
            <div className="result-heading">
              <ShieldCheck size={22} aria-hidden="true" />
              <span>Ready</span>
            </div>
            <a href={result.short_url} className="short-url">
              {result.short_url}
            </a>
            <dl>
              <div>
                <dt>Code</dt>
                <dd>{result.code}</dd>
              </div>
              <div>
                <dt>Lifetime</dt>
                <dd>{result.ttl === "24h" ? "24 hours" : "7 days"}</dd>
              </div>
              <div>
                <dt>Target</dt>
                <dd>
                  <a href={result.target_url}>{result.target_url}</a>
                </dd>
              </div>
              <div>
                <dt>Nominal expiry</dt>
                <dd>{formatExpiry(result.nominal_expires_at)}</dd>
              </div>
            </dl>
            <button className="copy-button" type="button" onClick={handleCopy}>
              {copied ? (
                <Check size={18} aria-hidden="true" />
              ) : (
                <Clipboard size={18} aria-hidden="true" />
              )}
              <span>{copied ? "Copied" : "Copy link"}</span>
            </button>
          </aside>
        ) : null}
      </section>
    </main>
  );
}

function formatExpiry(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function normalizeTargetUrl(value: string): string {
  if (!value || /^[a-z][a-z\d+.-]*:\/\//i.test(value)) {
    return value;
  }

  return `https://${value}`;
}

function validateHttpsUrl(value: string): string {
  if (!value) {
    return "";
  }

  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:") {
      return "Enter a URL that starts with https://.";
    }
    if (!parsed.hostname) {
      return "Enter a URL with a valid hostname.";
    }
    return "";
  } catch {
    return "Enter a valid HTTPS URL.";
  }
}
