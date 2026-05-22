# VeriPB.org Website

This is the source repository for the `veripb.org` website.

It mostly a plain html static site, using the [bootstrap
v5.3.8](https://blog.getbootstrap.com/2025/08/25/bootstrap-5-3-8/) theme for
styles.

## Generated Pages
The files `publications.html`and `overview.html` are generated using the corresponding python scripts. 
Do not edit these directly: instead edit the scripts or the source data.

To regenerate the html for these, the python packages listed in `requirements.txt` are needed.
This can be installed in a virtual environment using 
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```
Then run:
```
python3 make_overview.py
python3 make_publications.py
```

