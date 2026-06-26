data "archive_file" "edge_signer" {
  type        = "zip"
  source_dir  = "${local.lambdas_path}/edge_signer/src"
  output_path = local.edge_signer_archive_path

  excludes = [
    "**/__pycache__/**",
    "**/*.pyc",
  ]
}
