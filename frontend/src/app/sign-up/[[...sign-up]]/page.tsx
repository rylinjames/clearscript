import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#fafafa]">
      <SignUp
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "shadow-[var(--shadow-modal)] border border-gray-200/60 rounded-2xl",
            headerTitle: "text-xl font-bold text-gray-900",
            headerSubtitle: "text-gray-500",
            formButtonPrimary: "bg-primary-600 hover:bg-primary-700",
          },
        }}
      />
    </div>
  );
}
