<head-bottom>
  <link rel="stylesheet" href="{{baseUrl}}/stylesheets/main.css">
</head-bottom>

<header sticky>
  <navbar type="dark">
    <a slot="brand" href="{{baseUrl}}/index.html" title="Home" class="navbar-brand">DFIR Dataset</a>
    <li>
      <a highlight-on="sibling-or-child" href="{{baseUrl}}/index.html" class="nav-link">Home</a>
    </li>
    <li>
      <a highlight-on="sibling-or-child" href="{{baseUrl}}/user/index.html" class="nav-link">User Guide</a>
    </li>
    <li>
      <a highlight-on="sibling-or-child" href="{{baseUrl}}/developer/index.html" class="nav-link">Developer Guide</a>
    </li>
    <li>
      <a highlight-on="sibling-or-child" href="{{baseUrl}}/current-state/index.html" class="nav-link">Current State</a>
    </li>
    <li>
      <a href="https://github.com/darkrelicz/dfir-dataset" target="_blank" rel="noopener noreferrer" aria-label="GitHub repository" class="nav-link"><md>:fab-github:</md></a>
    </li>
    <li slot="right">
      <form class="navbar-form">
        <searchbar :data="searchData" placeholder="Search" :on-hit="searchCallback" menu-align-right></searchbar>
      </form>
    </li>
  </navbar>
</header>

<div id="flex-body">
  <nav id="site-nav">
    <div class="site-nav-top">
      <div class="fw-bold mb-2">Site Map</div>
    </div>
    <div class="nav-component slim-scroll">
      <site-nav>
* [Home]({{baseUrl}}/index.html)
* [Current State]({{baseUrl}}/current-state/index.html) :expanded:
  * [Revisions]({{baseUrl}}/current-state/revisions.html)
* [User Guide]({{baseUrl}}/user/index.html) :expanded:
  * [Command Overview]({{baseUrl}}/user/command-overview.html)
  * [Source Overview]({{baseUrl}}/user/source-overview.html)
* [Developer Guide]({{baseUrl}}/developer/index.html) :expanded:
  * [Pipeline Foundations]({{baseUrl}}/developer/pipeline-foundations.html)
  * [Collectors]({{baseUrl}}/developer/collectors.html)
  * [Synthesis]({{baseUrl}}/developer/synthesis.html)
  * [Quality Filtering]({{baseUrl}}/developer/quality-filtering.html)
  * [Packaging]({{baseUrl}}/developer/packaging.html)
  * [Fine-tuning]({{baseUrl}}/developer/finetuning.html)
  * [Evaluation]({{baseUrl}}/developer/evaluation.html)
* Reference :expanded:
  * [DFIR Artifact Taxonomy]({{baseUrl}}/reference/taxonomy.html)
      </site-nav>
    </div>
  </nav>

  <div id="content-wrapper">
    {{ content }}
  </div>

  <nav id="page-nav">
    <div class="nav-component slim-scroll">
      <page-nav />
    </div>
  </nav>

  <scroll-top-button></scroll-top-button>
</div>

<footer>
  <div class="text-center">
    <small>[<md>**Powered by**</md> <img src="https://markbind.org/favicon.ico" width="30"> {{MarkBind}}, generated on {{timestamp}}]</small>
  </div>
</footer>
