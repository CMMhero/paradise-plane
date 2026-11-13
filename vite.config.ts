// vp migrate: merged .oxlintrc.json (4aff08b0d419e51dd95a3e67817224b4).
import { defineConfig } from "vite-plus";

export default defineConfig({
  fmt: {
    printWidth: 120,
    tabWidth: 2,
    trailingComma: "es5",
    sortTailwindcss: {
      stylesheet: "packages/tailwind-config/index.css",
      functions: ["cn", "clsx", "cva"],
    },
    overrides: [
      {
        files: ["packages/codemods/**/*"],
        options: {
          printWidth: 80,
        },
      },
    ],
  },
  lint: {
    plugins: ["react", "typescript", "jsx-a11y", "import", "promise", "unicorn", "oxc"],
    jsPlugins: [
      "@shadcn/lint",
      {
        name: "vite-plus",
        specifier: "vite-plus/oxlint-plugin",
      },
    ],
    categories: {
      correctness: "warn",
      suspicious: "warn",
      perf: "warn",
    },
    env: {
      browser: true,
      node: true,
      es2024: true,
    },
    settings: {
      react: {
        version: "18.3",
      },
      "jsx-a11y": {
        polymorphicPropName: "as",
      },
      shadcn: {
        componentImports: ["^@plane/propel(/|$)", "^@plane/ui(/|$)"],
      },
    },
    ignorePatterns: [
      ".cache/**",
      ".next/**",
      ".react-router/**",
      ".storybook/**",
      ".turbo/**",
      ".vite/**",
      "*.config.{js,mjs,cjs,ts}",
      "build/**",
      "coverage/**",
      "dist/**",
      "**/public/**",
      "storybook-static/**",
    ],
    rules: {
      "react/react-in-jsx-scope": "off",
      "unicorn/filename-case": "off",
      "unicorn/no-null": "off",
      "no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
      "vite-plus/prefer-vite-plus-imports": "error",
    },
    options: {
      // Type-aware lint stays off for now: tsgolint would add a second type
      // checker next to `check:types` (tsc). Turn it on in a separate pass.
      typeAware: false,
      typeCheck: false,
    },
  },
});
