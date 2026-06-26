terraform {
  backend "s3" {
    bucket       = "terraform-804221019544-state"
    key          = "lynx-url-shortener/prod/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}
