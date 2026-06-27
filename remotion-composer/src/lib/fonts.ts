import { loadFont as loadNotoSansSC } from "@remotion/google-fonts/NotoSansSC";
import { loadFont as loadNotoSerifSC } from "@remotion/google-fonts/NotoSerifSC";
import { loadFont as loadZCOOLXiaoWei } from "@remotion/google-fonts/ZCOOLXiaoWei";
import { loadFont as loadZCOOLQingKeHuangYou } from "@remotion/google-fonts/ZCOOLQingKeHuangYou";
import { loadFont as loadZCOOLKuaiLe } from "@remotion/google-fonts/ZCOOLKuaiLe";

// Chinese font faces loaded from @remotion/google-fonts (Google Fonts CDN).
// These are lazy-loaded at runtime by Remotion.

export type ChineseFontName =
  | "NotoSansSC"
  | "NotoSerifSC"
  | "ZCOOLXiaoWei"
  | "ZCOOLQingKeHuangYou"
  | "ZCOOLKuaiLe";

type FontLoaderResult = {
  fontFamily: string;
  fonts: Record<string, Record<string, Record<string, string>>>;
  unicodeRanges: Record<string, string>;
  waitUntilDone: () => Promise<undefined>;
};

const CHINESE_FONT_LOADERS: Record<ChineseFontName, () => FontLoaderResult> = {
  NotoSansSC: () =>
    loadNotoSansSC("normal", {
      weights: ["400", "500", "700"],
      subsets: ["latin"],
    }),
  NotoSerifSC: () =>
    loadNotoSerifSC("normal", {
      weights: ["400", "700"],
      subsets: ["latin"],
    }),
  ZCOOLXiaoWei: () =>
    loadZCOOLXiaoWei("normal", {
      weights: ["400"],
      subsets: ["latin"],
    }),
  ZCOOLQingKeHuangYou: () =>
    loadZCOOLQingKeHuangYou("normal", {
      weights: ["400"],
      subsets: ["latin"],
    }),
  ZCOOLKuaiLe: () =>
    loadZCOOLKuaiLe("normal", {
      weights: ["400"],
      subsets: ["latin"],
    }),
};

const loadedFonts: Partial<Record<ChineseFontName, FontLoaderResult>> = {};

export function loadChineseFont(name: ChineseFontName): FontLoaderResult {
  if (!loadedFonts[name]) {
    loadedFonts[name] = CHINESE_FONT_LOADERS[name]();
  }
  return loadedFonts[name]!;
}

export const CHINESE_FONT_FAMILIES: Record<ChineseFontName, string> = {
  NotoSansSC: "'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif",
  NotoSerifSC: "'Noto Serif SC', 'Songti SC', 'SimSun', serif",
  ZCOOLXiaoWei: "'ZCOOL XiaoWei', 'Noto Sans SC', cursive",
  ZCOOLQingKeHuangYou: "'ZCOOL QingKe HuangYou', 'Noto Sans SC', sans-serif",
  ZCOOLKuaiLe: "'ZCOOL KuaiLe', 'Noto Sans SC', cursive",
};

/**
 * Build a font-family CSS string that includes a primary (usually Latin)
 * font and a Chinese fallback. Use this in components when rendering text
 * that may contain mixed Latin and CJK content.
 */
export function withChineseFallback(
  primaryFont: string,
  chineseFont: ChineseFontName = "NotoSansSC"
): string {
  const chinese = CHINESE_FONT_FAMILIES[chineseFont];
  // Strip generic fallback from primary so we can insert Chinese before it.
  const primaryWithoutFallback = primaryFont
    .replace(/,\s*sans-serif$/i, "")
    .replace(/,\s*serif$/i, "")
    .replace(/,\s*monospace$/i, "")
    .replace(/,\s*cursive$/i, "");
  return `${primaryWithoutFallback}, ${chinese}, sans-serif`;
}

export function getFontStack(
  primaryFont?: string,
  chineseFont: ChineseFontName = "NotoSansSC"
): string {
  if (primaryFont) {
    return withChineseFallback(primaryFont, chineseFont);
  }
  return CHINESE_FONT_FAMILIES[chineseFont];
}
