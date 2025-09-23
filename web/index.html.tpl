<!DOCTYPE html>
<html lang="en">
<head>
  <!-- GA -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-RR8X5VGSWX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-RR8X5VGSWX');
  </script>

  <!-- Terraform (and local render_index.py) inject API base here -->
  <meta name="api-base" content="${api_base_url}" />

  <!-- SEO Meta Tags -->
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="A collection of memorable quotes and sayings from Bruce. Share your favorite Bruce quotes and discover what others remember him saying.">
  <meta name="keywords" content="Bruce quotes, sayings, memorable quotes, funny quotes, Bruce sayings">
  <meta name="author" content="Shit Bruce Says">

  <!-- Open Graph / Facebook / LinkedIn -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://shitbrucesays.co.uk/">
  <meta property="og:title" content="Shit Bruce Says">
  <meta property="og:description" content="A collection of memorable quotes and sayings from Bruce. Share your favorite Bruce quotes and discover what others remember him saying.">
  <meta property="og:site_name" content="Shit Bruce Says">
  <meta property="og:image" content="https://shitbrucesays.co.uk/favicon.svg">
  <meta property="og:image:width" content="512">
  <meta property="og:image:height" content="512">
  <meta property="og:image:type" content="image/svg+xml">
  <meta property="og:locale" content="en_US">

  <!-- Twitter Card (legacy support) -->
  <meta property="twitter:card" content="summary">
  <meta property="twitter:url" content="https://shitbrucesays.co.uk/">
  <meta property="twitter:title" content="Shit Bruce Says">
  <meta property="twitter:description" content="A collection of memorable quotes and sayings from Bruce. Share your favorite Bruce quotes and discover what others remember him saying.">
  <meta property="twitter:image" content="https://shitbrucesays.co.uk/favicon.svg">

  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script src="https://unpkg.com/infinite-scroll@4/dist/infinite-scroll.pkgd.min.js"></script>
  <script src="app.js" defer></script>
  <title>Shit Bruce Says</title>
</head>
<body>
  <div id="wrapper">
    <header>
      <h1>Shit Bruce Says</h1>
      <p class="tagline">A collection of memorable quotes and sayings from Bruce</p>
    </header>

    <main>
      <section class="form" aria-label="Add a new quote">
        <h2 class="visually-hidden">Add a New Quote</h2>
        <form id="quote-form" role="form">
          <label for="quote" class="visually-hidden">Enter a Bruce quote</label>
          <input type="text" id="quote" minlength="5" maxlength="300" name="quote"
                 placeholder="What did Bruce say?" required
                 aria-describedby="quote-help" />
          <small id="quote-help" class="visually-hidden">Enter a memorable quote from Bruce (5-300 characters)</small>
          <input type="submit" value="Submit Quote"/>
        </form>
      </section>

      <section class="quotes" id="quotes" aria-label="Bruce quotes" role="feed">
        <h2 class="visually-hidden">All Quotes</h2>
        <!-- Quotes will be loaded here -->
      </section>
    </main>
  </div>
</body>
</html>
