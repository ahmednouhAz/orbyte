interface OrbyteLogoTypedProps {
  size?: number;
  className?: string;
}

// Real aspect ratio of logotype.svg's viewBox (806x197), so the image scales
// by height without being stretched or squished.
const ASPECT_RATIO = 806 / 197;

const SvgOrbyteLogoTyped = ({ size: height, className }: OrbyteLogoTypedProps) => (
  // eslint-disable-next-line @next/next/no-img-element
  <img
    src="/logotype.svg"
    height={height}
    width={height != null ? height * ASPECT_RATIO : undefined}
    className={className}
    alt=""
  />
);
export default SvgOrbyteLogoTyped;
