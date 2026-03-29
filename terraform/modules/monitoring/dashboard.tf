resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = templatefile("${path.module}/cloudwatch-dashboard.json", {
    aws_region              = var.aws_region
    alb_arn_suffix          = var.alb_arn_suffix
    asg_name                = var.asg_name
    target_group_arn_suffix = var.target_group_arn_suffix
    db_identifier           = var.db_instance_identifier
  })
}