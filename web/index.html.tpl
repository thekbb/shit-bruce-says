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

  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://shitbrucesays.co.uk/">
  <meta property="og:title" content="Shit Bruce Says>
  <meta property="og:description" content="A collection of memorable quotes and sayings from Bruce. Share your favorite Bruce quotes and discover what others remember him saying.">
  <meta property="og:site_name" content="Shit Bruce Says">

  <!-- Twitter (Because nobody calls it X. Ever.)-->
  <meta property="twitter:card" content="summary">
  <meta property="twitter:url" content="https://shitbrucesays.co.uk/">
  <meta property="twitter:title" content="Shit Bruce Says">
  <meta property="twitter:description" content="A collection of memorable quotes and sayings from Bruce. Share your favorite Bruce quotes and discover what others remember him saying.">

  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="styles.css">
  <script src="app.js" defer></script>
  <title>Shit Bruce Says</title>
</head>
<body>
  <div id="wrapper">
    <h1>Shit Bruce Says</h1>
    <div class="form">
      <form id="quote-form">
        <input type="text" id="quote" minlength="5" maxlength="300" name="quote" required />
        <input type="submit" value="Submit"/>
      </form>
    </div>
    <div class="quotes" id="quotes"></div>
  </div>
</body>
</html>
