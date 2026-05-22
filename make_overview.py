"""
Script to fetch proof_format_overview.md from VeriPB gitlab repository and create
overview.html.

Author:
    Matthew McIlree: 18-02-2026
"""

import requests
import markdown

from common import STAT_COUNTER_HTML

URL = "https://gitlab.com/MIAOresearch/software/veripb/-/raw/main/proof_format_overview.md"

md_text = requests.get(URL).text

# Gitlab uses a different TOC marker than the toc extension for python markdown
# and I can't figure out an obvious way to change this
md_text = md_text.replace("[[_TOC_]]", "[TOC]")

html = markdown.markdown(
    md_text,
    extensions=["fenced_code", "toc", "tables", "pymdownx.arithmatex"],
    extension_configs={"pymdownx.arithmatex": {"preview": False}},
)

with open("overview.html", "w") as f:
    _ = f.write("""<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" type="text/css" href="bootstrap.min.css">
    <link rel="stylesheet" type="text/css" href="style.css">
    <title>VeriPB Overview</title>
    <link rel="shortcut icon" href="veripb-icon.png">
    <script>
window.MathJax = {
  options: {
    ignoreHtmlClass: 'tex2jax_ignore',
    processHtmlClass: 'tex2jax_process',
    renderActions: {
      find: [10, function (doc) {
        for (const node of document.querySelectorAll('script[type^="math/tex"]')) {
          const display = !!node.type.match(/; *mode=display/);
          const math = new doc.options.MathItem(node.textContent, doc.inputJax[0], display);
          const text = document.createTextNode('');
          const sibling = node.previousElementSibling;
          node.parentNode.replaceChild(text, node);
          math.start = {node: text, delim: '', n: 0};
          math.end = {node: text, delim: '', n: 0};
          doc.math.push(math);
          if (sibling && sibling.matches('.MathJax_Preview')) {
            sibling.parentNode.removeChild(sibling);
          }
        }
      }, '']
    }
  }
};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>

<body class="container">
  <p>Navigation:
    <a href="index.html" class="menu">Front Page</a>
    <a href="overview.html" class="menu">Proof Format Overview</a>
    <a href="publications.html" class="menu">Publications</a>
  </p>
  <i>Note this page is automatically generated from the corresponding markdown file <a
  href="https://gitlab.com/MIAOresearch/software/veripb/-/raw/main/proof_format_overview.md">on GitLab.</a></i>
""")
    f.write(html)
    f.write(STAT_COUNTER_HTML)
    f.write("</body></html>")

print("Generated overview.html")
