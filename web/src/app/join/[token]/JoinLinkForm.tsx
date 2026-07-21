"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { Formik } from "formik";
import * as Yup from "yup";
import { AuthLayouts, InputVertical, toast } from "@opal/layouts";
import { Button } from "@opal/components";
import InputTypeInField from "@/refresh-components/form/InputTypeInField";
import PasswordInputTypeInField from "@/refresh-components/form/PasswordInputTypeInField";
import Text from "@/refresh-components/texts/Text";
import { PageLoader } from "@/refresh-components/PageLoader";
import { PasswordRequirements } from "@/lib/auth/components";
import {
  passwordHasUppercase,
  passwordHasLowercase,
  passwordHasDigit,
  passwordHasSpecialChar,
  passwordMeetsLengthRequirements,
} from "@/lib/auth/utils";
import { useCaptcha } from "@/lib/hooks/useCaptcha";
import { basicLogin } from "@/lib/users/svc";
import { useUser } from "@/providers/UserProvider";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { SWR_KEYS } from "@/lib/swr-keys";

interface FormValues {
  email: string;
  password: string;
}

interface JoinLinkLookupResponse {
  valid: boolean;
  group_name: string | null;
}

interface JoinLinkFormProps {
  token: string;
}

function JoinLinkForm({ token }: JoinLinkFormProps) {
  const { authTypeMetadata } = useUser();
  const { getCaptchaToken } = useCaptcha();

  const { data: lookup, isLoading } = useSWR<JoinLinkLookupResponse>(
    SWR_KEYS.joinLinkLookup(token),
    errorHandlingFetcher
  );

  const validationSchema = useMemo(() => {
    const minLength = authTypeMetadata?.passwordMinLength ?? 0;
    const maxLength = authTypeMetadata?.passwordMaxLength ?? Infinity;

    let passwordSchema = Yup.string().test(
      "length",
      `Password must be between ${minLength}–${maxLength} characters`,
      (v) => passwordMeetsLengthRequirements(v ?? "", minLength, maxLength)
    );
    if (authTypeMetadata?.passwordRequireUppercase)
      passwordSchema = passwordSchema.test(
        "uppercase",
        "Password must contain at least one uppercase letter",
        (v) => passwordHasUppercase(v ?? "")
      );
    if (authTypeMetadata?.passwordRequireLowercase)
      passwordSchema = passwordSchema.test(
        "lowercase",
        "Password must contain at least one lowercase letter",
        (v) => passwordHasLowercase(v ?? "")
      );
    if (authTypeMetadata?.passwordRequireDigit)
      passwordSchema = passwordSchema.test(
        "digit",
        "Password must contain at least one number",
        (v) => passwordHasDigit(v ?? "")
      );
    if (authTypeMetadata?.passwordRequireSpecialChar)
      passwordSchema = passwordSchema.test(
        "special-char",
        "Password must contain at least one special character",
        (v) => passwordHasSpecialChar(v ?? "")
      );

    return Yup.object().shape({
      email: Yup.string()
        .email()
        .required()
        .transform((value: string) => value.toLowerCase()),
      password: passwordSchema.required(),
    });
  }, [authTypeMetadata]);

  async function handleSubmit(values: FormValues) {
    const email = values.email.toLowerCase();

    const captchaToken = await getCaptchaToken("signup");
    const res = await fetch(`/api/join-link/${token}/redeem`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(captchaToken ? { "X-Captcha-Token": captchaToken } : {}),
      },
      body: JSON.stringify({ email, password: values.password }),
    });

    if (!res.ok) {
      const errorBody: any = await res.json().catch(() => ({}));
      const errorDetail = errorBody.detail;
      let errorMsg = "Failed to create your account.";
      if (res.status === 410) {
        errorMsg = "This join link is invalid or has expired.";
      } else if (res.status === 429) {
        errorMsg = "Too many requests. Please try again later.";
      } else if (errorDetail === "REGISTER_USER_ALREADY_EXISTS") {
        errorMsg = "An account already exists with this email.";
      } else if (typeof errorDetail === "string" && errorDetail) {
        errorMsg = errorDetail;
      }
      toast.error(errorMsg);
      return;
    }

    const loginCaptchaToken = await getCaptchaToken("login");
    const loginResponse = await basicLogin(
      email,
      values.password,
      loginCaptchaToken
    );
    if (loginResponse.ok) {
      window.location.href = "/app";
    } else {
      toast.error(
        "Account created — please log in with your new credentials."
      );
      window.location.href = "/auth/login";
    }
  }

  if (isLoading) {
    return <PageLoader />;
  }

  if (!lookup?.valid) {
    return (
      <div className="w-full">
        <Text as="p" headingH2 text05>
          Invalid link
        </Text>
        <Text as="p" text03>
          This join link is invalid, expired, or has already been used.
          Please ask your admin for a new one.
        </Text>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-6">
      <div className="w-full">
        <Text as="p" headingH2 text05>
          Join {lookup.group_name}
        </Text>
        <Text as="p" text03>
          Create your account to get started with Orbyte.
        </Text>
      </div>

      <Formik
        initialValues={{ email: "", password: "" }}
        validateOnChange
        validateOnBlur
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
      >
        {({ isSubmitting, isValid, dirty, values }) => (
          <AuthLayouts.FormBody>
            <AuthLayouts.Fields>
              <InputVertical title="Email Address" withLabel="email">
                <InputTypeInField
                  name="email"
                  placeholder="email@yourcompany.com"
                  autoComplete="username"
                />
              </InputVertical>

              <div className="flex flex-col gap-1">
                <InputVertical
                  title="Password"
                  withLabel="password"
                  subDescription="Password requirements:"
                >
                  <PasswordInputTypeInField
                    name="password"
                    placeholder="Password"
                    autoComplete="new-password"
                  />
                </InputVertical>
                <PasswordRequirements password={values.password} />
              </div>
            </AuthLayouts.Fields>

            <Button
              type="submit"
              prominence="primary"
              disabled={isSubmitting || !isValid || !dirty}
            >
              {isSubmitting ? "Creating account..." : "Create account"}
            </Button>
          </AuthLayouts.FormBody>
        )}
      </Formik>
    </div>
  );
}

export default JoinLinkForm;
