terraform {
  required_providers {
    okta = {
      source  = "okta/okta"
      version = "4.13.1"
    }
  }
}

provider "okta" {
  org_name  = "raftai"
  base_url  = "okta.com"
  api_token = "00txziuMesu9jwRGGB41gkrotJztwePJ01hPMRb_ci"
}
