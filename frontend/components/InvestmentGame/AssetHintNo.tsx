import { MoveLeft } from "lucide-react";

export default function AssetHintNo() {
  return (
    <div className="flex items-center gap-1 rounded-full p-1 text-blue-700 ring-1 ring-blue-700">
      <div className="h-4 w-4 rounded-full bg-blue-700"></div>
      <MoveLeft size={16} />
    </div>
  );
}
