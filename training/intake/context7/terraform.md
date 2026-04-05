# Terraform
> Source: Context7 MCP | Category: infra
> Fetched: 2026-04-04

### The Core Terraform Workflow

Source: https://developer.hashicorp.com/terraform/intro/v1.8.x/core-workflow

The core Terraform workflow consists of three fundamental steps:
1. **Write** — author your infrastructure as code
2. **Plan** — preview the changes Terraform will make before they are applied
3. **Apply** — provision the actual infrastructure

This workflow is designed to be iterative and provides a feedback loop similar to developing application code. By following these steps, you ensure that your infrastructure is defined, reviewed, and provisioned in a consistent and reproducible manner.

---

### Apply Terraform Configuration

Source: https://developer.hashicorp.com/terraform/tutorials/configuration-language/variables

Applies the current Terraform configuration to provision or update infrastructure. If the configuration matches the existing infrastructure, no changes will be made.

```bash
$ terraform apply
##...
No changes. Your infrastructure matches the configuration.

Terraform has compared your real infrastructure against your configuration
and found no differences, so no changes are needed.
```

---

### Destroy Terraform Provisioned Infrastructure

Source: https://developer.hashicorp.com/terraform/tutorials/applications/blue-green-canary-tests-deployments

Destroys all provisioned infrastructure using Terraform. Requires confirmation with 'yes'.

```bash
$ terraform destroy -var 'traffic_distribution=blue'
##...
Plan: 0 to add, 0 to change, 41 to destroy.

Changes to Outputs:
  - lb_dns_name = "main-app-infinite-toucan-lb-937939527.us-west-2.elb.amazonaws.com" -> null

    Do you really want to destroy all resources?
      Terraform will destroy all your managed infrastructure, as shown above.
          There is no undo. Only 'yes' will be accepted to confirm.

              Enter a value: yes
##...
Destroy complete! Resources: 41 destroyed.
```

---

### Define and Synthesize Single Stack in C# (CDK for Terraform)

Source: https://developer.hashicorp.com/terraform/cdktf/v0.15.x/concepts/stacks

This C# code defines a single Terraform stack named 'a-single-stack' using the Terraform CDK. It configures the AWS provider for the 'eu-central-1' region and provisions a t2.micro EC2 instance with a specific AMI.

```csharp
using Amazon.CDK;
using Constructs;
using HashiCorp.Terraform.Cdktf;
using HashiCorp.Terraform.Cdktf.Providers.Aws;
using HashiCorp.Terraform.Cdktf.Providers.Aws.Instance;

namespace MyProject
{
    public class MySingleStack : TerraformStack
    {
        public MySingleStack(Construct scope, string name) : base(scope, name)
        {
            new AwsProvider(this, "aws", new AwsProviderConfig
            {
                Region = "eu-central-1"
            });

            new Instance(this, "instance", new InstanceConfig
            {
                Ami = "ami-2757f631",
                InstanceType = "t2.micro",
            });
        }
        public static void Main(string[] args)
        {
            App app = new App();
            new MySingleStack(app, "a-single-stack");
            app.Synth();
        }
    }
}
```

---

### CDK for Terraform — How it Works

Source: https://developer.hashicorp.com/terraform/cdktf/v0.16

CDK for Terraform leverages concepts and libraries from the AWS Cloud Development Kit to translate your code into infrastructure configuration files for Terraform. At a high level:
1. **Create an Application** using a built-in or custom template
2. **Define Infrastructure** using your chosen language to define the infrastructure you want to provision on one or more providers
3. **Deploy** using `cdktf` CLI commands to provision infrastructure with Terraform or synthesize your code into a JSON configuration file
