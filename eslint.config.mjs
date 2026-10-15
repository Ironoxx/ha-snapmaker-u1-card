// Lint for the card sources (frontend/src). The built bundle and tests are not linted.
import globals from "globals";

export default [
  {
    files: ["frontend/src/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser },
    },
    rules: {
      "no-undef": "error",
      "no-unused-vars": ["error", { args: "none", caughtErrors: "none" }],
      "no-dupe-class-members": "error",
      "no-redeclare": "error",
    },
  },
];
