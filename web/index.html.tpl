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
