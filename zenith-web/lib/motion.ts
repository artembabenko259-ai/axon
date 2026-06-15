/** Shared motion tokens — spring / ease-out physics (Linear-style). */
export const EASE_OUT = [0.2, 0.8, 0.2, 1] as const;

export const SPRING_SNAPPY = {
  type: "spring" as const,
  stiffness: 420,
  damping: 32,
  mass: 0.8,
};

export const HOVER_LIFT = {
  y: -2,
  transition: { duration: 0.2, ease: EASE_OUT },
};

export const TAP_PRESS = {
  scale: 0.97,
  transition: { duration: 0.08, ease: EASE_OUT },
};

export const STAGGER_CHILDREN = 0.05;
export const STAGGER_DELAY_CHILDREN = 0.04;

export const entranceItem = {
  hidden: { opacity: 0, y: 15 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: EASE_OUT },
  },
};

export const entranceContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER_CHILDREN,
      delayChildren: STAGGER_DELAY_CHILDREN,
    },
  },
};
