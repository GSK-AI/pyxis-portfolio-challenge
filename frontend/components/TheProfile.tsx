import { useQuery } from "@tanstack/react-query";
import { ChevronDown, CircleUserRound, Power } from "lucide-react";
import { LoaderSingleData } from "./LoaderSingleData";
import { getUserName } from "@/lib/get-user-name";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { logout } from "@/lib/msal-auth";
import { Button } from "./ui/button";

export function TheProfile() {
  const { data, isLoading, isError, error } = useQuery<
    string | undefined,
    Error
  >({
    queryKey: ["getUserName"],
    queryFn: () => getUserName(),
  });

  async function handleLogout() {
    await logout();
  }

  if (isError) {
    console.error("Error fetching user name:", error);
  }
  return (
    <div className="flex items-center gap-2 text-sm font-thin">
      <CircleUserRound size={16} />
      {isLoading ? (
        <LoaderSingleData />
      ) : (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <div className="flex cursor-pointer items-center gap-2">
              {data} <ChevronDown size={12} />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="mr-4 mt-4 w-40" align="center">
            <div className="flex items-center px-2">
              <Power size={16} className="opacity-70" />{" "}
              <Button onClick={handleLogout} size="sm" variant="link">
                Log out
              </Button>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
