import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const fetchMock = vi.fn();
const writeTextMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  writeTextMock.mockReset();
  writeTextMock.mockResolvedValue(undefined);
  vi.stubGlobal("fetch", fetchMock);
});

describe("App", () => {
  it("blocks invalid URLs before submitting", async () => {
    const user = setupUser();
    render(<App />);

    await user.type(screen.getByLabelText(/destination url/i), "http://example.com");
    await user.click(screen.getByRole("button", { name: /create short link/i }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByText("Enter a URL that starts with https://.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create short link/i })).toBeDisabled();
  });

  it("sends the expected request body for a valid submission", async () => {
    const user = setupUser();
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        code: "aB3kP9xQ",
        short_url: "https://lynx.example.com/l/aB3kP9xQ",
        target_url: "https://example.com/launch",
        ttl: "7d",
        nominal_expires_at: "2026-07-03T12:00:00Z"
      })
    );
    render(<App />);

    await user.type(screen.getByLabelText(/destination url/i), "https://example.com/launch");
    await user.click(screen.getByLabelText(/7 days/i));
    await user.click(screen.getByRole("button", { name: /create short link/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith("/api/links", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        url: "https://example.com/launch",
        ttl: "7d"
      })
    });
  });

  it("adds https to bare domains before submitting", async () => {
    const user = setupUser();
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        code: "bareHost",
        short_url: "https://lynx.example.com/l/bareHost",
        target_url: "https://example.com/launch",
        ttl: "24h",
        nominal_expires_at: "2026-06-27T12:00:00Z"
      })
    );
    render(<App />);

    await user.type(screen.getByLabelText(/destination url/i), "example.com/launch");
    await user.click(screen.getByRole("button", { name: /create short link/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/links",
      expect.objectContaining({
        body: JSON.stringify({
          url: "https://example.com/launch",
          ttl: "24h"
        })
      })
    );
  });

  it("renders a successful short URL and copies it", async () => {
    const user = setupUser();
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        code: "copyCode",
        short_url: "https://lynx.example.com/l/copyCode",
        target_url: "https://example.com/copy",
        ttl: "24h",
        nominal_expires_at: "2026-06-27T12:00:00Z"
      })
    );
    render(<App />);

    await user.type(screen.getByLabelText(/destination url/i), "https://example.com/copy");
    await user.click(screen.getByRole("button", { name: /create short link/i }));

    expect(
      await screen.findByRole("link", { name: "https://lynx.example.com/l/copyCode" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /copy link/i }));

    await waitFor(() =>
      expect(writeTextMock).toHaveBeenCalledWith("https://lynx.example.com/l/copyCode")
    );
    expect(screen.getByRole("button", { name: /copied/i })).toBeInTheDocument();
  });

  it("renders API error responses", async () => {
    const user = setupUser();
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "url must use the https scheme"
        },
        false
      )
    );
    render(<App />);

    await user.type(screen.getByLabelText(/destination url/i), "https://example.com/error");
    await user.click(screen.getByRole("button", { name: /create short link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("url must use the https scheme");
  });

  it("renders Lambda Function URL error messages", async () => {
    const user = setupUser();
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          Message: "Forbidden. For troubleshooting Function URL authorization issues."
        },
        false
      )
    );
    render(<App />);

    await user.type(screen.getByLabelText(/destination url/i), "https://example.com/error");
    await user.click(screen.getByRole("button", { name: /create short link/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Forbidden. For troubleshooting Function URL authorization issues."
    );
  });
});

function setupUser() {
  const user = userEvent.setup();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: writeTextMock
    }
  });
  return user;
}

function jsonResponse(body: unknown, ok = true) {
  return {
    ok,
    json: async () => body
  };
}
