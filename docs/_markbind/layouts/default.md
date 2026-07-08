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
* [Current State]({{baseUrl}}/current-state/index.html)
* [User Guide]({{baseUrl}}/user/index.html) :expanded:
  * [Quick Start]({{baseUrl}}/user/quickstart.html)
  * [Running The Pipeline]({{baseUrl}}/user/running-the-pipeline.html)
  * [Source Guide]({{baseUrl}}/user/source-guide.html)
  * [Quality And Packaging]({{baseUrl}}/user/quality-and-packaging.html)
* [Developer Guide]({{baseUrl}}/developer/index.html) :expanded:
  * [Architecture]({{baseUrl}}/developer/architecture.html)
  * [Data Contracts]({{baseUrl}}/developer/data-contracts.html)
  * [Collectors]({{baseUrl}}/developer/collectors.html)
  * [Synthesis]({{baseUrl}}/developer/synthesis.html)
  * [Validation And Quality]({{baseUrl}}/developer/validation-quality.html)
  * [Packaging]({{baseUrl}}/developer/packaging.html)
  * [Configuration]({{baseUrl}}/developer/configuration.html)
  * [Extension Points]({{baseUrl}}/developer/extension-points.html)
  * [Diagrams]({{baseUrl}}/developer/diagrams.html)
  * [Project State Memory]({{baseUrl}}/developer/project-state-memory.html)
  * [Suggested Improvements]({{baseUrl}}/developer/suggested-improvements.html)
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
