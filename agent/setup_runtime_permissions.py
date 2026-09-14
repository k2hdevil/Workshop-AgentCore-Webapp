"""
AgentCore Runtime 실행 역할에 AWS Pricing API 권한 부여

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
목적:
  에이전트가 AWS Pricing MCP Server를 통해 실시간 가격을 조회하려면
  런타임 실행 역할(execution role)에 pricing:GetProducts 등의 권한이 필요하다.
  이 권한이 없으면 AccessDeniedException이 발생하고, LLM은 추정치로 대체한다.

왜 별도 스크립트인가:
  - 런타임 실행 역할 자신은 iam:PutRolePolicy 권한이 없다 (권한 상승 방지).
    따라서 에이전트 코드 안에서 스스로 권한을 부여할 수 없다.
  - 이 스크립트는 배포 전/후 로컬에서, IAM 수정 권한이 있는 자격증명으로
    한 번만 실행하면 된다.

사용법:
  cd agent
  uv run python setup_runtime_permissions.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import logging
import os

import boto3
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bedrock_agentcore.yaml")
POLICY_NAME = "AllowAWSPricingAPI"

# AWS Pricing API는 리소스 단위 제한을 지원하지 않으므로 Resource는 "*"
PRICING_POLICY_DOCUMENT = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "pricing:GetProducts",
                "pricing:DescribeServices",
                "pricing:GetAttributeValues",
                "pricing:GetPriceListFileUrl",
                "pricing:ListPriceLists",
            ],
            "Resource": "*",
        }
    ],
}


def _load_execution_role_arn() -> str:
    """.bedrock_agentcore.yaml에서 실행 역할 ARN을 읽는다."""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f".bedrock_agentcore.yaml not found at {CONFIG_FILE}. "
            "Run 'agentcore configure --entrypoint invoke.py' first."
        )

    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f)

    agent_name = cfg.get("default_agent", "")
    role_arn = (
        cfg.get("agents", {})
        .get(agent_name, {})
        .get("aws", {})
        .get("execution_role")
    )
    if not role_arn:
        raise ValueError(
            "execution_role not found in .bedrock_agentcore.yaml. "
            "Deploy the agent first so the runtime role is assigned."
        )
    return role_arn


def grant_pricing_permissions() -> None:
    """실행 역할에 Pricing API 인라인 정책을 추가한다 (멱등적)."""
    role_arn = _load_execution_role_arn()
    role_name = role_arn.split("/")[-1]
    logger.info("Target runtime execution role: %s", role_name)

    iam_client = boto3.client("iam")

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(PRICING_POLICY_DOCUMENT),
    )
    logger.info("✅ Granted AWS Pricing API permissions to '%s'", role_name)
    logger.info(
        "   Actions: pricing:GetProducts, DescribeServices, GetAttributeValues, "
        "GetPriceListFileUrl, ListPriceLists"
    )
    logger.info("   No redeploy needed — IAM changes apply to the running runtime immediately.")


def main() -> None:
    try:
        grant_pricing_permissions()
    except Exception as e:
        logger.error("❌ Failed to grant Pricing permissions: %s", e)
        raise


if __name__ == "__main__":
    main()
