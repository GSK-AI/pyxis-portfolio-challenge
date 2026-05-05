import React, { ReactNode } from "react";

type LayoutContainerProps = {
  children: ReactNode;
  className?: string;
  maxWidth?: string;
};
const LayoutContainer: React.FC<LayoutContainerProps> = ({
  children,
  className = "",
  maxWidth = "1260px",
}) => {
  return (
    <div className={`mx-auto px-4 ${className}`} style={{ maxWidth }}>
      {children}
    </div>
  );
};

export default LayoutContainer;
