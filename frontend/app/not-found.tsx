import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { SplashCardV2 } from "@/components/v2/SplashScreenV2";

export default function NotFound() {
  return (
    <SplashCardV2>
      <div className="flex items-center gap-4">
        <Image
          src="/images/pyxis-app-icon-2.svg"
          alt="Pyxis"
          width={50}
          height={50}
        />
        <div>
          <h1 className="text-lg font-bold tracking-wide">
            404 | Pyxis Portfolio Challenge
          </h1>
          <p className="font-thin text-muted-foreground">
            This page could not be found.
          </p>
        </div>
      </div>
      <div className="mt-6">
        <Button asChild variant="ghost">
          <Link href="/">Back to home</Link>
        </Button>
      </div>
    </SplashCardV2>
  );
}
