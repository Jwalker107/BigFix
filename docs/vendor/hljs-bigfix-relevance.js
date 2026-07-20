/*!
 * highlight.js language definition for the BigFix Relevance language.
 *
 * Vendored from https://github.com/bigfix/hljs-bigfix-relevance (v1.0.1),
 * licensed under the Apache License, Version 2.0 - see LICENSE-hljs-bigfix-relevance.txt
 * in this directory for the full license text.
 *
 * The grammar below is unmodified from the upstream index.js; only the
 * module wrapper was changed (from a CommonJS `module.exports` for
 * `require("highlight.js")` to a plain `hljs.registerLanguage` call), so
 * this can be loaded with a plain <script> tag after highlight.js's own
 * browser build instead of through a bundler.
 */
(function () {
  "use strict";

  if (typeof window === "undefined" || !window.hljs) return;

  function longestFirst(a, b) {
    return b.length - a.length;
  }

  window.hljs.registerLanguage("bigfix-relevance", function (hljs) {
    var keywords = [
      "and",
      "as",
      "contains",
      "does not contain",
      "does not end with",
      "does not equal",
      "does not start with",
      "else",
      "ends with",
      "equals",
      "exist",
      "exist no",
      "exists",
      "exists no",
      "false",
      "if",
      "is",
      "is contained by",
      "is equal to",
      "is greater than",
      "is greater than or equal to",
      "is less than",
      "is less than or equal to",
      "is not",
      "is not contained by",
      "is not equal to",
      "is not greater than",
      "is not greater than or equal to",
      "is not less than",
      "is not less than or equal to",
      "it",
      "mod",
      "nil",
      "not",
      "nothing",
      "nothings",
      "null",
      "of",
      "or",
      "starts with",
      "then",
      "there do not exist",
      "there does not exist",
      "there exist",
      "there exist no",
      "there exists",
      "there exists no",
      "true",
      "whose",
    ];

    var keywordsRe = keywords
      .sort(longestFirst)
      .join("|")
      .replace(/\s+/g, "\\s+((a|an|the)\\s+)*");

    return {
      case_insensitive: true,
      contains: [
        hljs.C_BLOCK_COMMENT_MODE,
        {
          className: "number",
          begin: "\\b[0-9]+",
          relevance: 0,
        },
        {
          className: "string",
          begin: '"',
          end: '"',
          relevance: 0,
        },
        {
          className: "keyword",
          begin: "\\b(" + keywordsRe + ")\\b",
          relevance: 2,
        },
      ],
    };
  });
})();
