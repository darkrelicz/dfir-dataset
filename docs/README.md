# DFIR Dataset Guides

This directory is a self-contained MarkBind site for successor-facing user and
developer documentation.

## Local setup

```bash
cd guides
npm install
npm run serve
```

For a static build:

```bash
cd guides
npm run build
```

The generated site is written to `guides/_site/`.

## GitHub Pages

The deployment workflow lives at `.github/workflows/deploy-guides.yml`.

The current `site.json` uses:

```json
"baseUrl": "/dfir-dataset"
```

Change this if the GitHub repository name or hosting shape changes.

PlantUML rendering requires Java. Non-sequence UML diagrams also need Graphviz;
the workflow installs both.
