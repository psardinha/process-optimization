
variable "aws_region" {
  description = "AWS region for the Lambda and EventBridge resources"
  type        = string
  default     = "eu-central-1"
}

variable "function_name" {
  description = "Name of the event handler Lambda"
  type        = string
  default     = "process-optimization-s3-handler"
}

variable "github_owner" {
  description = "Owner of Github repository where the ML pipeline is to run"
  type        = string
  default     = "psardinha"
}

variable "github_repo" {
  description = "Github repository where the ML pipeline is to run"
  type        = string
  default     = "process-optimization"
}

variable "github_event_type" {
  description = "Type of event to trigger ML pipeline execution from AWS"
  type        = string
  default     = "training_dataset_updated"
}

variable "data_bucket" {
  description = "AWS bucket where the creation of object orders_with_predicted_value.csv triggers the sending of a notification towards Github"
  type        = string
  default     = "test-bucket-psardinha"
}

variable "data_prefix" {
  description = "AWS folder where the creation of object orders_with_predicted_value.csv triggers the sending of a notification towards Github"
  type        = string
  default     = "decision-making/incoming/"
}

variable "secret_name" {
  description = "Handler of of the Github token stored in AWS Secrets used as authentication for triggering a Github workflow"
  type        = string
  default     = "process-optimization/github-dispatch-token"
}