resource "aws_s3_bucket" "design_files" {
  bucket = "design-file-manager-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "design-file-manager-${var.environment}" }
}

resource "aws_s3_bucket_versioning" "design_files" {
  bucket = aws_s3_bucket.design_files.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "design_files" {
  bucket = aws_s3_bucket.design_files.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "design_files" {
  bucket = aws_s3_bucket.design_files.id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_policy" "design_files" {
  bucket = aws_s3_bucket.design_files.id
  policy = data.aws_iam_policy_document.bucket_policy.json
}

data "aws_iam_policy_document" "bucket_policy" {
  statement {
    sid       = "DenyNonSSL"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [
      aws_s3_bucket.design_files.arn,
      "${aws_s3_bucket.design_files.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "ecs_s3_access" {
  statement {
    sid    = "ECSS3ReadWrite"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      aws_s3_bucket.design_files.arn,
      "${aws_s3_bucket.design_files.arn}/*",
    ]
  }
}
