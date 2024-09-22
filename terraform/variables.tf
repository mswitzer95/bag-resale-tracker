variable "csv_file_name" {
  description = "The name of the output CSV file to be stored in S3."
  type        = string
  default     = "bag-resale-tracker.csv"
}