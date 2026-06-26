data "archive_file" "create_link" {
  type        = "zip"
  source_dir  = "${local.lambdas_path}/create_link/src"
  output_path = local.create_link_archive_path

  excludes = [
    "**/__pycache__/**",
    "**/*.pyc",
  ]
}
