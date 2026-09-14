"""
Create AgentCore Gateway with Lambda target using AgentCore SDK
"""

import json
import logging
import argparse
import boto3
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

PROVIDER_NAME = "outbound-identity-for-cost-estimator-agent"
IDENTITY_FILE = Path("../agent/inbound_authorizer.json")
CONFIG_FILE = Path("outbound_gateway.json")


def setup_gateway(provider_name: str = PROVIDER_NAME, force: bool = False) -> dict:
    """
    Setup Gateway with GitHub OAuth2 credential provider.
    
    This function:
    1. Creates Gateway with Inbound Authorizer from 06_identity
    2. Attach AWS Lambda to Gateway as Outbound target
    3. Saves configuration to outbound_gateway.json

    Args:
        provider_name: Name for the credential provider
        force: Whether to force recreation of resources

    Returns:
        dict: Configuration
    """

    config = load_config()
    region = boto3.Session().region_name

    has_provider = config and 'provider' in config
    has_gateway = config and 'gateway' in config

    control_client = boto3.client('bedrock-agentcore-control', region_name=region)
    gateway_client = GatewayClient(region_name=region)
    
    # Check if gateway exists but target creation was incomplete
    has_target = has_gateway and 'target_id' in config.get('gateway', {})

    # If everything is complete and not forcing, show summary and exit
    if config and has_provider and has_target and not force:
        logger.info("All components already configured (use --force to recreate)")
        return config
    elif config:
        if has_gateway and force:
            logger.info("Delete existing Gateway...")
            delete_gateway(gateway_client, config['gateway'])
            has_gateway = False
            has_target = False
    
    if not has_gateway:
        logger.info("Creating Gateway with credential provider...")

        logger.info("Loading identity configuration from file...")
        if IDENTITY_FILE.exists():
            with open(IDENTITY_FILE) as f:
                identity_config = json.load(f)
        else:
            raise FileNotFoundError("Identity configuration file not found")

        gateway_name = "AWSCostEstimatorGateway"
        authorizer_config = {
            "customJWTAuthorizer": {
                "discoveryUrl": identity_config["cognito"]["discovery_url"],
                "allowedClients": [identity_config["cognito"]["client_id"]]
            }
        }
        gateway = gateway_client.create_mcp_gateway(
            name=gateway_name,
            role_arn=None,
            authorizer_config=authorizer_config,
            enable_semantic_search=False
        )
            
        gateway_id = gateway["gatewayId"]
        gateway_url = gateway["gatewayUrl"]
        gateway_role_arn = gateway["roleArn"]

        logger.info("Gateway is created!")

        # Gateway 실행 역할(execution role)에 Lambda 호출 권한 부여
        # - role_arn=None으로 SDK가 자동 생성한 역할에는 특정 Lambda 호출 권한이
        #   없으므로, CreateGatewayTarget이 ValidationException으로 거부됩니다.
        # - 여기서 lambda:InvokeFunction 권한을 인라인 정책으로 추가합니다.
        grant_lambda_invoke_permission(gateway_role_arn, config["lambda_arn"], region)

        # Wait for IAM role propagation — the SDK auto-creates
        # AgentCoreGatewayExecutionRole when role_arn=None, and IAM roles
        # are eventually consistent (~10-15s to propagate across AWS).
        import time
        logger.info("Waiting 15s for IAM role propagation...")
        time.sleep(15)

        logger.info("Adding Lambda target to Gateway...")
        tool_schema = [
            {
                "name": "markdown_to_email",
                "description": "Convert Markdown content to email format",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "markdown_text": {
                            "type": "string",
                            "description": "Markdown content to convertre to email format"
                        },
                        "email_address": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Title of email"
                        }
                    },
                    "required": ["markdown_text", "email_address"]
                }
            }
        ]

        # Create lambda target with required credentialProviderConfigurations
        # Note: toolkit's create_mcp_gateway_target doesn't handle custom target_payload + credentials
        # Reference: https://github.com/aws/bedrock-agentcore-starter-toolkit/pull/57 
        target_name = gateway_name + "Target"
            
        create_request = {
            "gatewayIdentifier": gateway_id,
            "name": target_name,
            "targetConfiguration": {
                "mcp": {
                    "lambda": {
                        "lambdaArn": config["lambda_arn"],
                        "toolSchema": {
                            "inlinePayload": tool_schema
                        }
                    }
                }
            },
            "credentialProviderConfigurations": [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
        }

        # Save gateway config before target creation (enables resume on partial failure)
        save_config({
            "gateway": {
                "id": gateway_id,
                "url": gateway_url,
            }
        })

        target_response = control_client.create_gateway_target(**create_request)
        target_id = target_response["targetId"]
        # Update config with target info
        save_config({
            "gateway": {
                "id": gateway_id,
                "url": gateway_url,
                "target_id": target_id
            }
        })
        logger.info("✅ Gateway configuration saved")            
        logger.info("✅ Gateway setup complete!")
        logger.info("Next step: Run 'uv run python test_gateway.py' to test the Gateway")
    
    config = load_config()
    return config


def grant_lambda_invoke_permission(role_arn: str, lambda_arn: str, region: str):
    """Gateway 실행 역할에 특정 Lambda 함수 호출 권한을 인라인 정책으로 추가.

    Gateway가 role_arn=None으로 생성되면 SDK가 실행 역할을 자동 생성하지만
    특정 Lambda를 호출할 lambda:InvokeFunction 권한은 포함되지 않는다.
    이 함수가 없으면 CreateGatewayTarget이 ValidationException으로 실패한다.

    Args:
        role_arn: Gateway 실행 역할 ARN (예: .../role/AgentCoreGatewayExecutionRole)
        lambda_arn: 호출을 허용할 Lambda 함수 ARN
        region: AWS 리전
    """
    # ARN에서 역할 이름 추출 (arn:aws:iam::<acct>:role/<name>)
    role_name = role_arn.split("/")[-1]
    iam_client = boto3.client("iam", region_name=region)

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_arn,
            }
        ],
    }

    logger.info(f"Granting lambda:InvokeFunction to role '{role_name}'...")
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="AllowInvokeGatewayLambdaTarget",
        PolicyDocument=json.dumps(policy_document),
    )
    logger.info("✅ Lambda invoke permission granted to Gateway execution role")


def delete_gateway(client, config):
    """Clean up existing Gateway resources.

    GatewayClient.delete_gateway는 skip_resource_in_use=True를 주면
    연결된 target을 먼저 모두 삭제한 뒤 Gateway를 삭제한다.
    (SDK 메서드명은 delete_mcp_gateway가 아니라 delete_gateway)
    """
    if 'id' in config:
        result = client.delete_gateway(
            gateway_identifier=config['id'],
            skip_resource_in_use=True,
        )
        if result.get("status") == "success":
            logger.info("Deleted Gateway: %s", config['id'])
        else:
            # 이미 삭제되었거나 존재하지 않아도 계속 진행 (best-effort)
            logger.warning("Gateway delete returned: %s", result.get("message"))


def load_config():
    """Load configuration from file"""
    if not CONFIG_FILE.exists():
        return {}
    with CONFIG_FILE.open('r') as f:
        config = json.load(f)
    return config


def save_config(updates: Optional[dict]=None, delete_key: str=""):
    """Update configuration file with new data"""
    config = load_config()
    
    if updates is not None:
        config.update(updates)
    elif delete_key:
        del config[delete_key]
    
    with CONFIG_FILE.open('w') as f:
        json.dump(config, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Create AgentCore Gateway')
    parser.add_argument('--force', action='store_true', help='Force recreation of resources')
    args = parser.parse_args()
    console = Console()
    
    try:
        config = setup_gateway(force=args.force)
    except Exception as e:
        logger.warning("❌ Setup Gateway failed:")
        logger.exception(e)
        return

    console.print_json(json.dumps(config))
    console.print(Panel("uv run python test_gateway.py", title="Let's test agent with gateway!"))


if __name__ == "__main__":
    main()
