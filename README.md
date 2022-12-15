# Deployment

For deployment with SSL, see: https://lcalcagni.medium.com/deploy-your-fastapi-to-aws-ec2-using-nginx-aa8aa0d85ec7
The above should apply to servers generally, not just EC2 machines.

# Hardware requirements

The minimum hardware requirements have not yet been determined. However, during testing 2GB of memory on a DigitalOcean droplet with Ubuntu 22.04 LTS resulted in the application silently failing when copying a large numpy array. Increasing the memory to 4GB resolved the problem.

Additional analysis is needed to determine exact hardware requirements.