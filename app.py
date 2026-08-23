import { useEffect } from "react";
import {
  ArrowRight,
  Building2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function App() {
  return (
    <div>
      <div className="min-h-[956px] bg-white text-neutral-950 flex flex-col w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <header className="bg-white border-neutral-200 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-12 justify-between items-center h-20">
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-xl bg-neutral-950 text-white flex justify-center items-center">
              <Sparkles className="size-5" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-base leading-6 tracking-tight">
                Generative<span className="text-neutral-900">Insight</span>
              </span>
              <span className="text-neutral-500 text-xs leading-4">
                AI Operations Copilot
              </span>
            </div>
          </div>
          <div className="text-neutral-500 text-sm leading-5 flex items-center gap-2">
            <span>Need an account?</span>
            <Button variant="ghost" className="text-neutral-950 px-3 h-9">
              Create account
            </Button>
          </div>
        </header>
        <main className="bg-neutral-100/30 flex px-8 py-12 justify-center items-center flex-1">
          <div className="max-w-[430px] flex flex-col gap-8 w-full">
            <div className="text-center flex flex-col items-center gap-3">
              <div className="size-14 shadow-sm rounded-2xl bg-neutral-950 text-white flex justify-center items-center">
                <Sparkles className="size-7" />
              </div>
              <div className="flex flex-col gap-2">
                <h1 className="font-semibold text-3xl leading-9 tracking-tight">
                  Welcome back
                </h1>
                <p className="text-neutral-500 text-sm leading-5">
                  Sign in to continue to your operational intelligence
                  workspace.
                </p>
              </div>
            </div>
            <Card className="shadow-sm rounded-2xl p-8 gap-6">
              <CardHeader className="p-0 gap-2">
                <CardTitle className="text-xl leading-7">
                  Sign in to your account
                </CardTitle>
                <CardDescription>
                  Enter your work credentials below.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex p-0 flex-col gap-5">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="email">Work email</Label>
                  <div className="relative">
                    <Mail className="top-1/2 -translate-y-1/2 size-4 text-neutral-500 absolute left-3" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@company.com"
                      className="pl-10 h-11"
                      defaultValue=""
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <Label htmlFor="password">Password</Label>
                    <Button
                      variant="link"
                      className="text-neutral-500 text-xs leading-4 p-0 h-auto"
                    >
                      Forgot password?
                    </Button>
                  </div>
                  <div className="relative">
                    <LockKeyhole className="top-1/2 -translate-y-1/2 size-4 text-neutral-500 absolute left-3" />
                    <Input
                      id="password"
                      placeholder="Enter your password"
                      className="pl-10 pr-11 h-11"
                      defaultValue=""
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      className="top-1/2 size-9 -translate-y-1/2 absolute right-1"
                      aria-label="Toggle password visibility"
                    >
                      <EyeOff className="size-4 text-neutral-500 hidden" />
                      <Eye className="size-4 text-neutral-500" />
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox id="remember" defaultChecked={false} />
                  <Label
                    htmlFor="remember"
                    className="font-normal text-neutral-500 text-sm leading-5"
                  >
                    Keep me signed in for 30 days
                  </Label>
                </div>
                <div className="rounded-lg bg-[#e7000b]/5 text-[#e7000b] text-sm leading-5 border-[#e7000b]/30 border-1 border-solid hidden p-3">
                  Please enter your email and password to continue.
                </div>
                <Button className="gap-2 w-full h-11">
                  Sign in
                  <ArrowRight className="size-4" />
                </Button>
              </CardContent>
              <CardFooter className="p-0 flex-col gap-3">
                <div className="flex items-center gap-3 w-full">
                  <div className="bg-neutral-200 flex-1 h-px" />
                  <span className="text-neutral-500 text-xs leading-4">
                    or continue with
                  </span>
                  <div className="bg-neutral-200 flex-1 h-px" />
                </div>
                <Button variant="outline" className="gap-2 w-full h-11">
                  <Building2 className="size-4" />
                  Continue with company SSO
                </Button>
              </CardFooter>
            </Card>
            <p className="text-center text-neutral-500 text-xs leading-5">
              By continuing, you agree to our
              <span className="underline-offset-4 underline text-neutral-950">
                Terms of Service
              </span>
              and
              <span className="underline-offset-4 underline text-neutral-950">
                Privacy Policy
              </span>
              .
            </p>
          </div>
        </main>
        <footer className="bg-white border-neutral-200 border-t-1 border-r-0 border-b-0 border-l-0 border-solid flex justify-center items-center h-16">
          <div className="text-neutral-500 text-xs leading-4 flex items-center gap-2">
            <ShieldCheck className="size-4" />
            Enterprise-grade security for your operational data
          </div>
        </footer>
      </div>
    </div>
  );
}
