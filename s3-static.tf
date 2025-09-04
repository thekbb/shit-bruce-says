resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "site" {
  bucket = "${local.name}-site-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_ownership_controls" "site" {
  bucket = aws_s3_bucket.site.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload rendered assets
resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.site.id
  key          = "index.html"
  content      = local.index_html
  content_type = "text/html; charset=utf-8"
  etag         = md5(local.index_html) # forces update when template changes
}

resource "aws_s3_object" "css" {
  bucket       = aws_s3_bucket.site.id
  key          = "styles.css"
  source       = "${path.module}/web/styles.css"
  content_type = "text/css; charset=utf-8"
  etag         = filemd5("${path.module}/web/styles.css")
}

resource "aws_s3_object" "js" {
  bucket       = aws_s3_bucket.site.id
  key          = "app.js"
  source       = "${path.module}/web/app.js"
  content_type = "application/javascript; charset=utf-8"
  etag         = filemd5("${path.module}/web/app.js")
}

resource "aws_s3_object" "favicon" {
  bucket       = aws_s3_bucket.site.id
  key          = "favicon.svg"
  source       = "${path.module}/web/favicon.svg"
  content_type = "image/svg+xml"
  etag         = filemd5("${path.module}/web/favicon.svg")
}
