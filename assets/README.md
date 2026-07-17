# assets/

Branding images shown in the header of the **Management HTML report**
(`reports/ManagementReport_*.html`).

Replace these placeholder files with your own (keep the same names, or update the
paths in `config/settings.yaml` -> `reporting.branding`):

| File | Where it appears | Suggested size |
|------|------------------|----------------|
| `company_logo.png` | top-left, next to the report title | ~160 x 52 px (any ratio; max-width 160px, height 52px) |
| `author.png` | top-right, shown as a circle | square, e.g. 96 x 96 px or larger |

PNG or JPG both work. Images are embedded into the HTML as base64, so the report
stays a single self-contained file (no external links). If a file is missing or
its config value is blank, that element is simply omitted.

Configure the text (company name, your name, role) in
`config/settings.yaml`:

```yaml
reporting:
  branding:
    company_name: "Your Company Name"
    company_logo: "assets/company_logo.png"
    author_name: "Yogesh Tyagi"
    author_role: "QA / ETL Automation"
    author_image: "assets/author.png"
```
