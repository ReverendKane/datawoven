"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import UserMenu from "@/components/UserMenu";

type Sections = Record<string, string[]>;

const MOBILE_BREAKPOINT = 640;

const slug = (category: string, item: string) =>
  "/" +
  category.toLowerCase() +
  "/" +
  item
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

export default function Header() {
  const [headerMode, setHeaderMode] = useState<
    "default" | "mobile"
  >("default");
  const [scrolled, setScrolled] = useState(false);
  const [openMenu, setOpenMenu] = useState<
    keyof Sections | null
  >(null);
  const [isHoveringNav, setIsHoveringNav] = useState(false);
  const [instantTransition, setInstantTransition] =
    useState(false);
  const skipAnimationRef = useRef(false);
  const { user, loading } = useAuth();

  const baseSections: Sections = {
    Services: ["Discovery", "AI Solutions", "Support"],
    Solutions: ["Browse All", "Case Studies"],
    Resources: [
      "Documentation",
      "Technical Overview",
      "Security & Privacy",
      "FAQ",
    ],
  };

  // Add Dashboard section for authenticated users
  const sections: Sections = user
    ? {
        ...baseSections,
        Dashboard: ["Overview"],
        ...(user.groups.includes("DiscoveryAdmin") ||
        user.groups.includes("DataWovenAdmin")
          ? { "Discovery Tools": ["Sessions", "Reports"] }
          : {}),
        ...(user.groups.includes("ImplementationUser") ||
        user.groups.includes("DataWovenAdmin")
          ? {
              Implementation: [
                "Chat",
                "Documents",
                "Analytics",
              ],
            }
          : {}),
      }
    : baseSections;

  useEffect(() => {
    const handleResize = () => {
      setHeaderMode(
        window.innerWidth < MOBILE_BREAKPOINT
          ? "mobile"
          : "default"
      );
    };
    const handleScroll = () => {
      setScrolled(window.scrollY > 0);
    };

    handleResize();
    handleScroll();
    window.addEventListener("resize", handleResize);
    window.addEventListener("scroll", handleScroll, {
      passive: true,
    });
    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  const headerHeight = headerMode === "default" ? 75 : 35;
  const showBlackBg = scrolled || isHoveringNav;

  // Calculate dropdown height
  const dropdownHeight = openMenu
    ? sections[openMenu].length * 40
    : 0;

  return (
    <header
      id="main-header"
      className="fixed top-0 w-full flex justify-center"
      style={{
        height: openMenu
          ? headerHeight + dropdownHeight
          : headerHeight,
        zIndex: 50,
      }}
      onMouseLeave={() => {
        setOpenMenu(null);
        setIsHoveringNav(false);
      }}
      aria-label="Site header"
    >
      {/* Full-width black background - animated */}
      <motion.div
        id="header-black-background"
        className="absolute top-0 left-0 right-0 w-full"
        initial={false}
        animate={{
          opacity: showBlackBg ? 0.95 : 0,
        }}
        transition={{
          duration: instantTransition ? 0 : 0.3,
          ease: "easeInOut",
        }}
        style={{
          height: "100%",
          pointerEvents: "none",
          backgroundColor: "#000000",
        }}
      />

      <div
        id="header-content-container"
        className="w-full max-w-[1280px] px-4 flex items-center justify-between transition-colors duration-200 relative z-10"
        style={{ height: headerHeight }}
      >
        {/* Logo */}
        <div id="leftNav" className="flex items-center">
          <Link
            href="/"
            aria-label="Go to homepage"
            className="block"
          >
            <motion.div
              animate={{
                filter: showBlackBg
                  ? "invert(1)"
                  : "invert(0)",
              }}
              transition={{
                duration: instantTransition ? 0 : 0.3,
              }}
            >
              <Image
                id="logo"
                src="/svg/headerLogo.svg"
                width={headerMode === "default" ? 252 : 200}
                height={50}
                alt="DataWoven Logo"
                priority
              />
            </motion.div>
          </Link>
        </div>

        {/* Center Navigation */}
        <nav
          id="centerNav"
          className={`relative ${headerMode === "mobile" ? "hidden" : "flex"} items-center`}
          style={{ gap: "50px" }}
          aria-label="Primary"
          onMouseEnter={() => setIsHoveringNav(true)}
        >
          {Object.keys(sections).map((key) => {
            const k = key as keyof Sections;
            const isOpen = openMenu === k;
            return (
              <div
                key={key}
                className="relative"
                onMouseEnter={() => setOpenMenu(k)}
              >
                <motion.button
                  className="font-semibold bg-transparent border-0 outline-none cursor-pointer p-0"
                  style={{
                    fontSize: "14px",
                  }}
                  aria-haspopup="menu"
                  aria-expanded={isOpen}
                  animate={{
                    color: showBlackBg
                      ? "#ffffff"
                      : "#000000",
                  }}
                  transition={{
                    duration: instantTransition ? 0 : 0.3,
                  }}
                >
                  {key}
                </motion.button>

                {/* Dropdown - conditional rendering based on scroll */}
                {scrolled ? (
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        key={k}
                        role="menu"
                        className="absolute top-full"
                        style={{
                          left: "5px",
                          paddingTop: "24px",
                          minWidth: "200px",
                        }}
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{
                          duration: 0.3,
                          ease: "easeInOut",
                        }}
                      >
                        <ul
                          style={{
                            listStyle: "none",
                            padding: 0,
                            margin: 0,
                            display: "flex",
                            flexDirection: "column",
                            gap: "12px",
                          }}
                        >
                          {sections[k].map((item) => (
                            <li
                              key={item}
                              style={{
                                margin: 0,
                                padding: 0,
                              }}
                            >
                              <Link
                                href={slug(key, item)}
                                role="menuitem"
                                onClick={() => {
                                  setInstantTransition(
                                    true
                                  );
                                  setTimeout(
                                    () =>
                                      setInstantTransition(
                                        false
                                      ),
                                    50
                                  );
                                  setOpenMenu(null);
                                  setIsHoveringNav(false);
                                }}
                                style={{
                                  textDecoration: "none",
                                  display: "block",
                                }}
                              >
                                <motion.span
                                  style={{
                                    display: "block",
                                    fontSize: "12px",
                                    fontWeight: 500,
                                    whiteSpace: "nowrap",
                                    paddingRight: "8px",
                                  }}
                                  initial={{
                                    color: "#999999",
                                  }}
                                  animate={{
                                    color: "#999999",
                                  }}
                                  whileHover={{
                                    color: "#ffffff",
                                  }}
                                  transition={{
                                    duration: 0.2,
                                  }}
                                >
                                  {item}
                                </motion.span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </motion.div>
                    )}
                  </AnimatePresence>
                ) : (
                  isOpen && (
                    <div
                      role="menu"
                      className="absolute top-full"
                      style={{
                        left: "5px",
                        paddingTop: "24px",
                        minWidth: "200px",
                      }}
                    >
                      <ul
                        style={{
                          listStyle: "none",
                          padding: 0,
                          margin: 0,
                          display: "flex",
                          flexDirection: "column",
                          gap: "12px",
                        }}
                      >
                        {sections[k].map((item) => (
                          <li
                            key={item}
                            style={{
                              margin: 0,
                              padding: 0,
                            }}
                          >
                            <Link
                              href={slug(key, item)}
                              role="menuitem"
                              onClick={() => {
                                setInstantTransition(true);
                                setTimeout(
                                  () =>
                                    setInstantTransition(
                                      false
                                    ),
                                  50
                                );
                                setOpenMenu(null);
                                setIsHoveringNav(false);
                              }}
                              style={{
                                textDecoration: "none",
                                display: "block",
                              }}
                            >
                              <motion.span
                                style={{
                                  display: "block",
                                  fontSize: "12px",
                                  fontWeight: 500,
                                  whiteSpace: "nowrap",
                                  paddingRight: "8px",
                                }}
                                initial={{
                                  color: "#999999",
                                }}
                                animate={{
                                  color: "#999999",
                                }}
                                whileHover={{
                                  color: "#ffffff",
                                }}
                                transition={{
                                  duration: 0.2,
                                }}
                              >
                                {item}
                              </motion.span>
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )
                )}
              </div>
            );
          })}
        </nav>

        {/* Auth Section */}
        <div id="rightNav" className="flex items-center">
          {loading ? (
            <div
              style={{ width: "80px", height: "40px" }}
            />
          ) : user ? (
            <UserMenu />
          ) : (
            <Link
              href="/login"
              style={{ textDecoration: "none" }}
            >
              <motion.span
                className="text-[10pt] font-semibold block"
                style={{
                  fontFamily: "inherit",
                  padding: "8px 16px",
                  borderRadius: "6px",
                }}
                animate={{
                  color: showBlackBg
                    ? "#ffffff"
                    : "#000000",
                  borderWidth: "2px",
                  borderStyle: "solid",
                  borderColor: showBlackBg
                    ? "#ffffff"
                    : "#000000",
                  backgroundColor: "transparent",
                }}
                whileHover={{
                  color: showBlackBg
                    ? "#000000"
                    : "#ffffff",
                  backgroundColor: showBlackBg
                    ? "#ffffff"
                    : "#000000",
                  borderColor: showBlackBg
                    ? "#ffffff"
                    : "#000000",
                }}
                transition={{
                  duration: instantTransition ? 0 : 0.3,
                }}
              >
                Log In
              </motion.span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
