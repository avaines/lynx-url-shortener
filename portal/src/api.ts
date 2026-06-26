export type TtlOption = "24h" | "7d";

export type CreateLinkRequest = {
  url: string;
  ttl: TtlOption;
};

export type CreateLinkResponse = {
  code: string;
  short_url: string;
  target_url: string;
  ttl: TtlOption;
  nominal_expires_at: string;
};

type ErrorResponse = {
  error?: string;
  message?: string;
  Message?: string;
};

export async function createLink(request: CreateLinkRequest): Promise<CreateLinkResponse> {
  const response = await fetch("/api/links", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request)
  });

  const body = (await response.json().catch(() => ({}))) as ErrorResponse | CreateLinkResponse;

  if (!response.ok) {
    const message =
      ("error" in body && body.error) ||
      ("message" in body && body.message) ||
      ("Message" in body && body.Message) ||
      "Unable to create link.";
    throw new Error(message);
  }

  return body as CreateLinkResponse;
}
