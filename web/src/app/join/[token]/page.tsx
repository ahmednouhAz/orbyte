import { redirect } from "next/navigation";
import { User } from "@/lib/types";
import { getCurrentUserSS } from "@/lib/users/svcSS";
import AuthFlowContainer from "@/components/auth/AuthFlowContainer";
import JoinLinkForm from "./JoinLinkForm";

interface PageProps {
  params: Promise<{ token: string }>;
}

const Page = async ({ params }: PageProps) => {
  const { token } = await params;

  let currentUser: User | null = null;
  try {
    currentUser = await getCurrentUserSS();
  } catch (e) {
    console.log(`Some fetch failed for the join page - ${e}`);
  }

  // Someone already logged in shouldn't redeem a link meant for a new
  // teammate — send them back into the app instead.
  if (currentUser && currentUser.is_active && !currentUser.is_anonymous_user) {
    return redirect("/app");
  }

  return (
    <AuthFlowContainer authState="signup">
      <JoinLinkForm token={token} />
    </AuthFlowContainer>
  );
};

export default Page;
