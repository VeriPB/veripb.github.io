"""
Running this script should turn the BibTeX file in publications.bib into an HTML
document publications.html

Author:
    Matthew McIlree: 18-02-2026
    (somewhat adapted from https://github.com/JianCheng/bibtex2html.py)
"""

import bibtexparser

BIB_FILE = "publications.bib"
BIBTYPE_PRIORITY = [
    "phdthesis",
    "book",
    "inbook",
    "article",
    "inproceedings",
    "conferences",
]


def sort_key(bib_entry):
    """Sort by year in then bib type"""
    year_val = int(bib_entry["year"]) if bib_entry["year"].isdigit() else float("inf")
    type_val = float("inf")
    if bib_entry["ENTRYTYPE"] in BIBTYPE_PRIORITY:
        type_val = BIBTYPE_PRIORITY.index(bib_entry["ENTRYTYPE"])
    return (year_val, type_val)


def clean_entry(entry):
    """Clean up an entry"""

    for k, v in entry.items():
        v = v.strip()

        # replace special characters - I'm sure there's a better way to do this...
        v = v.replace("\\AE", "Æ")
        v = v.replace("\\$\\$", " ")
        v = v.replace("~", " ")
        v = v.replace("\\O", "Ø")
        v = v.replace("\\AA", "Å")
        v = v.replace("\\ae", "æ")
        v = v.replace("\\o", "ø")
        v = v.replace('\\"o', "ö")
        v = v.replace('\\"a', "ä")
        v = v.replace("\\aa", "å")
        v = v.replace("\\'a", "&aacute;")
        v = v.replace("\\'c", "&cacute;")
        v = v.replace("\\'o", "&oacute;")
        v = v.replace("\\'e", "&eacute;")
        v = v.replace("\\c{c}", "&ccedil;")

        v = v.replace("{", "")
        v = v.replace("}", "")
        v = v.replace('"', "")

        # remove trailing comma and dot
        if len(v) > 0:
            if v[-1] == ",":
                v = v[:-1]

        # fix author
        if k == "author" or k == "author_first" or k == "author_corresponding":

            # split into list of authors
            authors = v.split(" and ")
            authors = [a.strip() for a in authors]

            # make blanks non-breakable
            authors = [a.replace(" ", "&nbsp;") for a in authors]

            # reverse first and surname
            for i, a in enumerate(authors):
                # print a + "\n"
                # surname =
                namearray = a.split("&nbsp;")
                surname = namearray[0]
                if surname.find(",") >= 0:
                    surname = surname.replace(",", "")
                    firstname = " ".join(namearray[1:])
                    authors[i] = firstname + " " + surname
                else:
                    authors[i] = " ".join(namearray)

            v = ", ".join(authors[:])

        # fix pages
        if k == "pages":
            v = v.replace("--", "&ndash;")
            v = v.replace("-", "&ndash;")

        entry[k] = v


def get_bib_entry_as_html(entry):
    """Get HTML output for a bib entry"""

    def span(cls, text):
        return f'<span class="{cls}">{text}</span>'

    def format_title_or_chapter():
        if "chapter" in entry:
            chapter_html = f'<span class="title">"{entry["chapter"]}"</span>'
            book_info = f'in: {entry["title"]}, {entry["publisher"]}'
            return chapter_html + book_info
        return f'<span class="title"><i>"{entry["title"]}"</i></span>'

    def format_publisher():
        if "journal" in entry:
            return span("publisher", entry["journal"])
        if "booktitle" in entry:
            return span("publisher", entry["booktitle"])
        if "eprint" in entry:
            return span("publisher", entry["eprint"])
        if entry["ENTRYTYPE"] == "phdthesis":
            return f"PhD thesis, {entry['school']}"
        if entry["ENTRYTYPE"] == "techreport":
            return f"Tech. Report, {entry['number']}"
        if entry["ENTRYTYPE"] == "book":
            return entry["publisher"]
        return ""

    def format_volume_pages_notes():
        parts = []
        if "volume" in entry:
            parts.append(f"vol. {entry['volume']}")
        if "number" in entry and entry["ENTRYTYPE"] != "techreport":
            parts.append(f"no. {entry['number']}")
        if "pages" in entry:
            parts.append(f"pp. {entry['pages']}")
        if "month" in entry:
            parts.append(entry["month"])
        return ", ".join(parts)

    def get_link():
        # URL / DOI / WWW
        if "url" in entry and entry["url"] != "":
            return entry["url"]
        elif "www" in entry:
            return entry["www"]
        elif "doi" in entry:
            return "https://dx.doi.org/%s" % entry["doi"]
        elif "hal_id" in entry:
            return "https://hal.archives-ouvertes.fr/%s" % entry["hal_id"]

        return None

    # --- Start building HTML ---
    out = ["\n<li>\n"]

    if "author" in entry:
        out.append(span("author", entry["author"] + ","))
        out.append("\n")

    out.append(format_title_or_chapter() + ",\n")
    publisher_html = format_publisher()
    if publisher_html:
        out.append(publisher_html)

    vp = format_volume_pages_notes()
    if vp:
        out.append(", " + vp)

    out.append(", " + span("year", entry["year"]) + ".\n")

    link = get_link()
    if link:
        out.insert(1, f'<a href="{link}">')
        out.append("</a>")
    # Terminate list
    out.append("\n</li>\n")
    out.append("<br>\n")

    return "".join(out)


if __name__ == "__main__":
    with open(BIB_FILE, "r", encoding="utf8") as bibtex_file:
        bibtex_str = bibtex_file.read()

    bib_database = bibtexparser.loads(bibtex_str)
    bib_entries = sorted(bib_database.entries, key=sort_key)

    with open("publications.html", "w") as f1:
        html_prelude = r"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="bootstrap.min.css">
        <link rel="stylesheet" type="text/css" href="style.css">
        <title>VeriPB Publications</title>
        <link rel="shortcut icon" href="img/favicon.svg">
    </head>

    <body class="container">
        <p>Navigation:
            <a href="index.html" class="menu">Front Page</a>
            <a href="overview.html" class="menu">Proof Format Overview</a>
            <a href="publications.html" class="menu">Publications</a>
        </p>

        <div class="row">
        <h1> Publications </h1>

        <h3>How to cite VeriPB</h3>
        <p>Please cite up to three of the following references in this order of priority. You can click on the references to get their BibTeX entry:</p>
        <p>
        <details>
        <summary>
        Bart Bogaerts, Stephan Gocht, Ciaran McCreesh, and Jakob Nordström.
        Certified Dominance and Symmetry Breaking for Combinatorial Optimisation.
        Journal of Artificial Intelligence Research, 2023.
        </summary>

        <pre><code>
        @article{BGMN23Dominance,
        author    = {Bart Bogaerts and Stephan Gocht and Ciaran McCreesh
                    and Jakob Nordström},
        title     = {Certified Dominance and Symmetry Breaking for
                    Combinatorial Optimisation},
        year      = {2023},
        month     = aug,
        journal   = {Journal of Artificial Intelligence Research},
        volume    = {77},
        pages     = {1539\nobreakdash--1589},
        note      = {Preliminary version in \emph{AAAI~'22}},
        }
        </code></pre>

        </details>
        </p>

        <P>
        <details>
        <summary>
        Stephan Gocht, and Jakob Nordström.
        Certifying Parity Reasoning Efficiently Using Pseudo-Boolean Proofs.
        Proceedings of the 35th AAAI Conference on Artificial Intelligence (AAAI '21), 2021.
        </summary>

        <pre><code>
        @inproceedings{GN21CertifyingParity,
        author    = {Stephan Gocht and Jakob Nordström},
        title     = {Certifying Parity Reasoning Efficiently Using
                    Pseudo-{B}oolean Proofs},
        year      = {2021},
        month     = feb,
        booktitle = {Proceedings of the 35th {AAAI} Conference on
                    Artificial Intelligence ({AAAI}~'21)},
        pages     = {3768\nobreakdash--3777}
        }
        </code></pre>

        </details>
        </p>

        <p>
        <details>
        <summary>
        Stephan Gocht.
        Certifying Correctness for Combinatorial Algorithms by Using Pseudo-Boolean Reasoning.
        Lund University, Lund, Sweden, 2022.
        </summary>

        <pre><code>
        @phdthesis{Gocht22Thesis,
        author  = {Stephan Gocht},
        title   = {Certifying Correctness for Combinatorial Algorithms
                    by Using Pseudo-{B}oolean Reasoning},
        school  = {Lund University},
        address = {Lund, Sweden},
        year    = {2022},
        month   = jun,
        note    = {Available at
                    \url{https://portal.research.lu.se/en/publications/certifying-correctness-for-combinatorial-algorithms-by-using-pseu}},
        }
        </code></pre>

        </details>
        </p>

        <h3>VeriPB in the Literature</h3>
        <p>The following is a list of scientific publications that make use of (some version of) VeriPB.</p>
        <ul class="list-unstyled">
    """
        f1.write(html_prelude)
        for bib_entry in bib_entries:
            bib = clean_entry(bib_entry)
            f1.write(get_bib_entry_as_html(bib_entry))
        f1.write("</ul></div></div></body></html>")
