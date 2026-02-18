"""
Script to fetch proof_format_overview.md from VeriPB gitlab repository and create
overview.html.

Author:
    Matthew McIlree: 18-02-2026
"""

import requests
import markdown

URL = "https://gitlab.com/MIAOresearch/software/veripb/-/raw/main/proof_format_overview.md"

md_text = requests.get(URL).text

html = markdown.markdown(md_text, extensions=["fenced_code", "tables"])

with open("overview.html", "w") as f:
    f.write(
        """<!doctype html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" type="text/css" href="bootstrap.min.css">
  <link rel="stylesheet" type="text/css" href="style.css">
  <title>VeriPB Overview</title>
  <link rel="shortcut icon" href="veripb-icon.png">
</head>

<body class="container">
  <p>Navigation:
    <a href="index.html" class="menu">Front Page</a>
    <a href="overview.html" class="menu">Proof Format Overview</a>
    <a href="publications.html" class="menu">Publications</a>
  </p>
  <i>Note this page is automatically generated from the corresponding markdown file <a
  href="https://gitlab.com/MIAOresearch/software/veripb/-/raw/main/proof_format_overview.md">on GitLab.</a></i>
"""
    )
    f.write(html)
    f.write("</body>")

print("Generated overview.html")
