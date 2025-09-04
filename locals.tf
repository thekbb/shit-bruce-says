locals {
  # Render web/index.html.tpl with the API custom domain base URL
  index_html = templatefile("${path.module}/web/index.html.tpl", {
    api_base_url = "https://${aws_apigatewayv2_domain_name.api.domain_name}"
  })

  name = "bruce-quotes"
}
