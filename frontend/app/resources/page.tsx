import {
  customRenderers,
  MarkdownRenderer,
} from "@/components/MarkdownRenderer";
import { promises as fs } from "fs";
import path from "path";
import { StartOnboardingTour } from "@/components/InvestmentGame/StartOnboardingTour";
async function ResourcesPage() {
  const markdownFileName = "investment-game-resources.md";
  const filePath = path.join(
    process.cwd(),
    "public",
    "resources",
    markdownFileName,
  );
  try {
    await fs.access(filePath);
  } catch (error) {
    return (
      <div className="container mx-auto">
        <MarkdownRenderer content={`File not found`} />
      </div>
    );
  }
  const content = await fs.readFile(filePath, "utf-8");
  return (
    <div className="container mx-auto">
      <MarkdownRenderer
        content={content}
        customRenderersOverrides={{
          a: (props) => {
            const { href } = props;
            if (href === "start-tour") {
              return <StartOnboardingTour />;
            }
            return <customRenderers.a {...props} />;
          },
        }}
      />
    </div>
  );
}

export default ResourcesPage;
