import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate, type Location } from "react-router-dom";

import { ApiError } from "@/api/http";
import { Button } from "@/components/ui/Button";
import { InputField } from "@/components/ui/Field";
import { errorMessage } from "@/lib/errors";

import { AuthLayout } from "./AuthLayout";
import { useAuth } from "./authContext";
import { loginSchema, type LoginValues } from "./schemas";

export const DEMO_ACCOUNTS = [
  { email: "alice@example.com", password: "Alice123!" },
  { email: "bob@example.com", password: "Bob123!" },
  { email: "carol@example.com", password: "Carol123!" },
] as const;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const from = (location.state as { from?: Location } | null)?.from?.pathname ?? "/tasks";

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login(values);
      navigate(from, { replace: true });
    } catch (error) {
      setFormError(
        error instanceof ApiError && error.status === 401
          ? "Invalid email or password"
          : errorMessage(error),
      );
    }
  });

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to manage your tasks"
      footer={
        <>
          New here?{" "}
          <Link to="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {formError && (
          <div
            role="alert"
            className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700 ring-1 ring-rose-200"
          >
            {formError}
          </div>
        )}
        <InputField
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register("email")}
        />
        <InputField
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Sign in
        </Button>
      </form>

      <section aria-labelledby="demo-accounts" className="mt-6 border-t border-slate-100 pt-5">
        <h2
          id="demo-accounts"
          className="text-xs font-semibold uppercase tracking-wide text-slate-500"
        >
          Demo accounts
        </h2>
        <ul className="mt-2 space-y-1">
          {DEMO_ACCOUNTS.map((account) => (
            <li key={account.email}>
              <button
                type="button"
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm text-slate-600 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-600"
                onClick={() => {
                  setValue("email", account.email, { shouldValidate: true });
                  setValue("password", account.password, { shouldValidate: true });
                }}
              >
                <span>{account.email}</span>
                <code className="text-xs text-slate-400">{account.password}</code>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </AuthLayout>
  );
}
