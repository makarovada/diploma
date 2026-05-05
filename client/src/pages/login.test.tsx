import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LoginPage } from "@/pages/login";

vi.mock("wouter", () => ({
  useLocation: () => ["/login", vi.fn()],
}));

vi.mock("@/app/auth-context", () => ({
  useAuth: () => ({
    login: vi.fn(),
    status: "unauthenticated",
    user: null,
  }),
}));

describe("LoginPage", () => {
  it("renders login form fields", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("page-login")).toBeInTheDocument();
    expect(screen.getByTestId("input-login-email")).toBeInTheDocument();
    expect(screen.getByTestId("input-login-password")).toBeInTheDocument();
    expect(screen.getByTestId("button-login-submit")).toBeInTheDocument();
  });
});
