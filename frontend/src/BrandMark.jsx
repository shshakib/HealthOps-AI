import React from "react";

// A simple H built from two record columns, shared by the workspace and sign-in.
export default function BrandMark() {
  return (
    <svg
      className="brand-mark"
      viewBox="0 0 30 32"
      fill="none"
      aria-hidden="true"
    >
      <path d="M2 2h6v28H2zM22 2h6v28h-6zM8 13h14v6H8z" fill="currentColor" />
      <path d="M12 3h6v6h-6zM12 23h6v6h-6z" fill="currentColor" opacity=".3" />
    </svg>
  );
}
