import type { IconProps } from "@opal/types";
const SvgOnyxLogo = ({ size, className }: IconProps) => (
  // eslint-disable-next-line @next/next/no-img-element
  <img src="/logo.svg" width={size} height={size} className={className} alt="" />
);
export default SvgOnyxLogo;
