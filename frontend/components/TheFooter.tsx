import LayoutContainer from "./LayoutContainer";
import { WidgetBackendConnection } from "./WidgetBackendConnection";

export function TheFooter() {
  return (
    <footer>
      <LayoutContainer>
        <div className="flex items-center justify-between border-t border-gray-100 p-4 text-sm text-gray-400">
          <div>Developed by AIML, 2025</div>
          <WidgetBackendConnection />
        </div>
      </LayoutContainer>
    </footer>
  );
}
