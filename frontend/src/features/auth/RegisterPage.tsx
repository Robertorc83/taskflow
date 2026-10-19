import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "@/api/http";
import { Button } from "@/components/ui/Button";
import { InputField } from "@/components/ui/Field";
import { errorMessage, fieldErrors } from "@/lib/errors";

import { AuthLayout } from "./AuthLayout";
import { useAuth } from "./authContext";
import { registerSchema, type RegisterValues } from "./schemas";

export function RegisterPage() {
  const { register: registerAccount } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: "", email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await registerAccount(values);
      navigate("/tasks", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setError("email", { message: "An account with this email already exists" });
        return;
      }
      const mapped = fieldErrors(error).filter(
        (e): e is { field: keyof RegisterValues; message: string } =>
          ["full_name", "email", "password"].includes(e.field),
      );
      if (mapped.length > 0) {
        mapped.forEach(({ field, message }) => setError(field, { message }));
        return;
      }
      setFormError(errorMessage(error));
    }
  });

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start organising your work in seconds"
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
            Sign in
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
          label="Full name"
          autoComplete="name"
          error={errors.full_name?.message}
          {...register("full_name")}
        />
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
          autoComplete="new-password"
          hint="At least 8 characters"
          error={errors.password?.message}
          {...register("password")}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
