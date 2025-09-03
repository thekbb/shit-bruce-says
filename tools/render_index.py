#!/usr/bin/env python3

import argparse, pathlib

TEMPLATE = pathlib.Path("web/index.html.tpl").read_text()
CSS = '<link rel="stylesheet" href="styles.css">'
JS  = '<script src="app.js" defer></script>'

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--api", required=True)
    args = p.parse_args()

    html = TEMPLATE.replace("${api_base_url}", args.api.rstrip("/"))
    pathlib.Path("web/index.html").write_text(html)
    print(f"Wrote web/index.html with api_base={args.api}")

if __name__ == "__main__":
    main()
