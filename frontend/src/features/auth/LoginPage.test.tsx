import { screen, waitFor } from "@testing-library/react";
import { http } from "msw";

import { tokenStorage } from "@/api/tokenStorage";
import { problem } from "@/test/handlers";
import { renderApp } from "@/test/render";
import { server } from "@/test/server";

describe("Given I am on the login page", () => {
  it("when I submit an empty form, then I see inline validation errors (F1)", async () => {
    const { user } = renderApp("/login", { authenticated: false });

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });

  it("when I type a malformed email, then I am told to fix it (F1)", async () => {
    const { user } = renderApp("/login", { authenticated: false });

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.type(screen.getByLabelText("Password"), "whatever");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
  });

  it("when I sign in with valid credentials, then I land on my tasks (F2)", async () => {
    const { user, router } = renderApp("/login", { authenticated: false });

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "Alice123!");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Tasks" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/tasks");
    expect(tokenStorage.hasSession()).toBe(true);
  });

  it("when I use the wrong password, then I see a non-field error (F3)", async () => {
    const { user } = renderApp("/login", { authenticated: false });

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
    expect(tokenStorage.hasSession()).toBe(false);
  });

  it("when I am rate limited, then I am told how long to wait (F3)", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () => {
        const response = problem(429, "Too Many Requests");
        response.headers.set("Retry-After", "30");
        return response;
      }),
    );
    const { user } = renderApp("/login", { authenticated: false });

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "Alice123!");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Too many attempts, try again in 30 s",
    );
  });

  it("when I pick a demo account, then the form is filled in for me (F4)", async () => {
    const { user } = renderApp("/login", { authenticated: false });

    await user.click(screen.getByRole("button", { name: /bob@example\.com/ }));

    expect(screen.getByLabelText("Email")).toHaveValue("bob@example.com");
    expect(screen.getByLabelText("Password")).toHaveValue("Bob123!");
  });
});

describe("Given I am signed out", () => {
  it("when I open a protected page, then I am sent to login and returned there afterwards (F2)", async () => {
    const { user, router } = renderApp("/tasks/new", { authenticated: false });

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "Alice123!");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/tasks/new"));
  });
});

describe("Given I am signed in", () => {
  it("when I visit the login page, then I am redirected to my tasks", async () => {
    const { router } = renderApp("/login");

    await waitFor(() => expect(router.state.location.pathname).toBe("/tasks"));
  });

  it("when I sign out, then my session is cleared and I see the login page", async () => {
    const { user } = renderApp("/tasks");

    await screen.findByText("Alice Smith");
    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(tokenStorage.hasSession()).toBe(false);
  });
});

describe("Given I am on the register page", () => {
  it("when I create an account, then I am signed in and see my (empty) task list", async () => {
    const { user } = renderApp("/register", { authenticated: false });

    await user.type(screen.getByLabelText("Full name"), "Carol Diaz");
    await user.type(screen.getByLabelText("Email"), "carol@example.com");
    await user.type(screen.getByLabelText("Password"), "Secret123!");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("No tasks yet")).toBeInTheDocument();
  });

  it("when the email is taken, then the email field shows the conflict", async () => {
    const { user } = renderApp("/register", { authenticated: false });

    await user.type(screen.getByLabelText("Full name"), "Alice Again");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "Secret123!");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByText("An account with this email already exists"),
    ).toBeInTheDocument();
  });

  it("when the server rejects a field, then the message appears under that field", async () => {
    server.use(
      http.post("*/api/v1/auth/register", () =>
        problem(422, "Validation failed", {
          errors: [{ field: "body.password", message: "Too common" }],
        }),
      ),
    );
    const { user } = renderApp("/register", { authenticated: false });

    await user.type(screen.getByLabelText("Full name"), "Carol");
    await user.type(screen.getByLabelText("Email"), "carol@example.com");
    await user.type(screen.getByLabelText("Password"), "Password1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Too common")).toBeInTheDocument();
  });

  it("when the password is too short, then I am told before submitting", async () => {
    const { user } = renderApp("/register", { authenticated: false });

    await user.type(screen.getByLabelText("Full name"), "Carol");
    await user.type(screen.getByLabelText("Email"), "carol@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Use at least 8 characters")).toBeInTheDocument();
  });
});
