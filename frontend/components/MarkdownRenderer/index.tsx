import { Button } from "@/components/ui/button";
import Link from "next/link";
import Image from "next/image";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight } from "lucide-react";

type MarkdownComponents = Parameters<typeof Markdown>[0]["components"];
export const customRenderers = {
  a: ({ children, href }) => {
    return (
      <Link
        href={href ?? ""}
        passHref
        target="_blank"
        rel="noopener noreferrer"
      >
        <Button
          disabled={!href}
          variant="link"
          className="text-md h-0 px-0 py-0 pr-1 text-blue-500 dark:text-blue-300"
        >
          {children}
        </Button>
      </Link>
    );
  },
  details: ({ children, ...rest }) => {
    const initialOpen =
      "initial-open" in rest && rest["initial-open"] === "true";
    if (!children) {
      return null;
    }
    if (!Array.isArray(children)) {
      return <>{children}</>;
    }
    const summaryNodes = children.find((node) => {
      return typeof node === "object" && node?.type === "summary";
    });
    const summary = summaryNodes?.props?.children;
    const contentNodes = children.filter((node) => {
      return typeof node === "object" && node?.type !== "summary";
    });
    const content = contentNodes.map((node) => {
      if (typeof node === "object") {
        return node.props.children;
      }
      return node;
    });
    return (
      <Collapsible className="group" defaultOpen={initialOpen}>
        <CollapsibleTrigger className="flex w-full items-center text-muted-foreground">
          <ChevronRight className="mr-2 h-10 transition-transform group-data-[state=open]:rotate-90" />
          <div className="mr-2 h-[1px] w-8 bg-muted-foreground" />
          <span className="text-md font-normal">{summary}</span>
          <div className="ml-2 h-[1px] flex-1 bg-muted-foreground" />
        </CollapsibleTrigger>
        <CollapsibleContent className="overflow-hidden py-4 pl-12 text-muted-foreground data-[state=closed]:animate-slide-up data-[state=open]:animate-slide-down">
          <div className="">
            {content.map((node, index) => {
              if (typeof node === "string") {
                return <p key={index}>{node}</p>;
              }
              return (
                <p key={index} className="my-4">
                  {node}
                </p>
              );
            })}
          </div>
        </CollapsibleContent>
      </Collapsible>
    );
  },
  link: ({ children, href }) => {
    return (
      <Link
        href={href ?? ""}
        passHref
        target="_blank"
        rel="noopener noreferrer"
      >
        <Button disabled={!href} variant="link" className="py-0text-md">
          {children}
        </Button>
      </Link>
    );
  },
  h1: ({ children }) => {
    return <h1 className="mdown-h1 mb-4 mt-8">{children}</h1>;
  },
  h2: ({ children }) => {
    return <h2 className="mdown-h2 mb-4 mt-8">{children}</h2>;
  },
  h3: ({ children }) => {
    return <h3 className="mdown-h3 mb-4 mt-8">{children}</h3>;
  },
  h4: ({ children }) => {
    return <h4 className="mdown-h4 mb-4 mt-8">{children}</h4>;
  },
  h5: ({ children }) => {
    return <h5 className="mdown-h5 mb-4 mt-8">{children}</h5>;
  },
  h6: ({ children }) => {
    return <h6 className="mdown-h6">{children}</h6>;
  },
  blockquote: ({ children }) => {
    return (
      <blockquote className="mdown-blockquote border-l p-2 italic">
        {children}
      </blockquote>
    );
  },
  pre: ({ children }) => {
    return <pre>{children}</pre>;
  },
  em: ({ children }) => {
    return <em>{children}</em>;
  },
  strong: ({ children }) => {
    return <strong className="mt-4 text-gray-600">{children}</strong>;
  },
  del: ({ children }) => {
    return <del>{children}</del>;
  },
  ul: ({ children }) => {
    return (
      <ul
        style={{
          listStyleType: "disc",
        }}
        className="ml-6"
      >
        {children}
      </ul>
    );
  },
  ol: ({ children }) => {
    return (
      <ol
        style={{
          listStyleType: "decimal",
        }}
        className="ml-6"
      >
        {children}
      </ol>
    );
  },
  li: ({ children }) => {
    if (typeof children === "string") {
      return <li className="mb-2 mt-2 list-disc pl-3">{children}</li>;
    } else {
      return <li className="mb-2 mt-2 pl-3">{children}</li>;
    }
  },
  p: ({ children }) => {
    if (typeof children === "string") {
      return <p className="mdown-p mb-2 mt-2">{children}</p>;
    }
    return <div>{children}</div>;
  },
  table: ({ children }) => <Table className="my-10">{children}</Table>,
  thead: ({ children }) => <TableHeader>{children}</TableHeader>,
  tbody: ({ children }) => <TableBody>{children}</TableBody>,
  tr: ({ children }) => <TableRow>{children}</TableRow>,
  th: ({ children }) => <TableHead>{children}</TableHead>,
  td: ({ children }) => <TableCell>{children}</TableCell>,
  caption: ({ children }) => <TableCaption>{children}</TableCaption>,
  img: ({ src, alt }) => {
    return (
      <div>
        <div className="relative mb-4 mt-4 w-full">
          <Image src={src ?? ""} alt={alt ?? ""} width={800} height={400} />
        </div>
      </div>
    );
  },
} satisfies MarkdownComponents;

type MarkdownRendererProps = {
  content: string;
  customRenderersOverrides?: MarkdownComponents;
};

export const MarkdownRenderer = ({
  content,
  customRenderersOverrides,
}: MarkdownRendererProps) => {
  return (
    <Markdown
      components={{
        ...customRenderers,
        ...(customRenderersOverrides ?? {}),
      }}
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
    >
      {content}
    </Markdown>
  );
};
