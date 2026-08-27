# Amazon Bedrock AgentCore 워크샵 — 빈칸 채우기 실습

## 워크샵 개요

실시간 AWS 가격 데이터를 기반으로 아키텍처 비용을 견적하는 AI 에이전트를 구축하며,
Amazon Bedrock AgentCore의 핵심 기능(Runtime, Memory, Gateway, Identity, Code Interpreter)을 학습합니다.

코드의 빈칸(`"_____"` 또는 `____`)을 채워 AgentCore 에이전트를 완성하는 **Hands-on 워크샵**입니다.
각 빈칸 위에 `# HINT:` 주석과 공식 문서 링크가 제공되므로, 문서를 참고하며 스스로 정답을 찾아가는 학습 방식입니다.

## 워크샵 목표

- Amazon Bedrock AgentCore의 5대 핵심 서비스(Runtime, Memory, Gateway, Identity, Code Interpreter)를 이해하고 실제 코드로 통합하기
- Strands Agents 프레임워크를 활용한 AI 에이전트 오케스트레이션 구현
- MCP(Model Context Protocol)를 통해 외부 도구(AWS Pricing API, Lambda)를 에이전트에 연결하기
- OAuth2 M2M(Machine-to-Machine) 인증 플로우를 이해하고 Gateway 보안 연동 구현
- 완성된 에이전트를 웹 애플리케이션으로 배포하여 End-to-End 동작 검증

## 대상 참가자

- AWS 서비스에 관심이 있는 백엔드/풀스택 개발자
- AI/ML 에이전트 개발에 입문하려는 소프트웨어 엔지니어
- Amazon Bedrock AgentCore를 실무에 적용하고자 하는 클라우드 아키텍트
- 생성형 AI 기반 도구 통합 패턴을 학습하고자 하는 DevOps 엔지니어

## 사전 지식

| 영역 | 필수 수준 |
|------|-----------|
| Python | 중급 — 데코레이터, 컨텍스트 매니저, async/await 이해 |
| AWS 기초 | 초중급 — IAM, Lambda, boto3 기본 사용 경험 |
| REST API | 초중급 — HTTP 요청/응답, OAuth2 개념 이해 |
| CLI 환경 | 초급 — 터미널에서 명령어 실행, 환경변수 설정 가능 |
| LLM/AI 에이전트 | 초급 — 프롬프트, 도구 호출(Tool Use) 개념 인지 |

## 워크샵 완료시 습득 역량

- **AgentCore Runtime** — `@app.entrypoint` 데코레이터로 에이전트를 서버리스 런타임에 배포하고 `invoke_agent_runtime` API로 호출하는 패턴
- **AgentCore Memory** — `list_events` / `create_event`를 활용한 단기 대화 메모리(STM) 관리 및 세션 연속성 확보
- **AgentCore Code Interpreter** — 보안 샌드박스에서 동적 Python 코드를 실행하여 LLM이 생성한 계산 로직을 안전하게 처리
- **AgentCore Identity** — Cognito User Pool + OAuth2 Credential Provider를 생성하고, `client_credentials` 플로우로 M2M 토큰 발급
- **AgentCore Gateway** — Lambda를 MCP Target으로 등록하고, `streamablehttp_client` + Bearer 토큰으로 외부 도구에 접근
- **Strands Agents + MCP** — `MCPClient`로 도구를 로드하고, `Agent(tools=[...])` 패턴으로 LLM에게 다중 도구를 오케스트레이션 위임
- **End-to-End 웹 통합** — FastAPI + SSE 스트리밍으로 에이전트 응답을 실시간 렌더링하는 풀스택 구현

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser (web/static/index.html)                                    │
│    - 채팅 UI, 마크다운 렌더링, 세션 관리                              │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ POST /api/chat
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Web Backend (web/app.py)                        [TODO 9~11, 14]    │
│    - FastAPI 서버                                                    │
│    - boto3 invoke_agent_runtime() 호출                               │
│    - SSE 스트리밍 응답 처리                                           │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ invoke_agent_runtime API
                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AgentCore Runtime (agent/invoke.py)             [TODO 1~5]         │
│                                                                     │
│  ┌─── Memory ────────────────────────────────────────────────────┐  │
│  │  list_events() → 이전 대화 조회            [TODO 2]            │  │
│  │  create_event() → 현재 대화 저장           [TODO 3]            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─── Agent (Strands + Claude Sonnet) ───────────────────────────┐  │
│  │                                                               │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐  │  │
│  │  │ Code Interpreter│  │ AWS Pricing MCP  │  │ Gateway MCP │  │  │
│  │  │ [TODO 6, 15]    │  │ [TODO 7]         │  │ [TODO 5]    │  │  │
│  │  └────────┬────────┘  └────────┬─────────┘  └──────┬──────┘  │  │
│  │           │                    │                    │         │  │
│  └───────────┼────────────────────┼────────────────────┼─────────┘  │
│              ▼                    ▼                    ▼             │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────────┐   │
│  │ AgentCore      │  │ AWS Pricing API │  │ AgentCore Gateway  │   │
│  │ Code Interpreter│  │ (us-east-1)    │  │  → Lambda → SES   │   │
│  └────────────────┘  └─────────────────┘  └────────────────────┘   │
│                                                                     │
│  ┌─── Identity ──────────────────────────────────────────────────┐  │
│  │  Cognito OAuth M2M → Bearer Token → Gateway 인증 [TODO 4]    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 빈칸 목록 (총 17개 TODO)

### 파일 1: `agent/invoke.py` — Runtime 엔트리포인트

| TODO | 난이도 | 설명 | 관련 서비스 |
|------|--------|------|-------------|
| **TODO 1** | ★★☆ | Runtime 엔트리포인트 데코레이터 | AgentCore Runtime |
| **TODO 2** | ★★★ | Memory에서 이전 대화 조회 API + max_results 값 | AgentCore Memory |
| **TODO 3** | ★★★ | Memory에 대화 저장 API + 메시지 역할(role) 지정 | AgentCore Memory |
| **TODO 4** | ★★☆ | OAuth2 client_credentials 플로우의 grant_type | AgentCore Identity |
| **TODO 5** | ★★★ | Gateway MCP 연결 시 URL과 인증 헤더 | AgentCore Gateway |

### 파일 2: `agent/cost_estimator_agent/cost_estimator_agent.py` — 에이전트 핵심 로직

| TODO | 난이도 | 설명 | 관련 서비스 |
|------|--------|------|-------------|
| **TODO 6** | ★★☆ | Code Interpreter invoke 액션명 + 언어 지정 | Code Interpreter |
| **TODO 7** | ★★☆ | AWS Pricing MCP Server 패키지명 | MCP (Pricing) |
| **TODO 8** | ★☆☆ | Strands Agent 생성 시 도구 목록 파라미터 | Strands Agents |
| **TODO 15** | ★☆☆ | Code Interpreter 세션 시작 메서드 | Code Interpreter |

### 파일 3: `web/app.py` — FastAPI 백엔드

| TODO | 난이도 | 설명 | 관련 서비스 |
|------|--------|------|-------------|
| **TODO 9** | ★★★ | 에이전트 런타임 호출 메서드명 | AgentCore Runtime |
| **TODO 10** | ★★☆ | 에이전트 ARN 파라미터명 | AgentCore Runtime |
| **TODO 11** | ★★★ | 세션 ID 파라미터명 (최소 33자 제약) | AgentCore Runtime |
| **TODO 14** | ★★☆ | AgentCore 데이터 플레인 boto3 서비스명 + read_timeout 값 | AgentCore Runtime |

### 파일 4: `identity/setup_identity.py` — Identity 설정

| TODO | 난이도 | 설명 | 관련 서비스 |
|------|--------|------|-------------|
| **TODO 12** | ★★★ | OAuth2 credential provider 생성 API + vendor 값 | AgentCore Identity |
| **TODO 13** | ★★☆ | AgentCore 제어 플레인 boto3 서비스명 | AgentCore Identity |

### 파일 5: `gateway/setup_outbound_gateway.py` — Gateway 설정

| TODO | 난이도 | 설명 | 관련 서비스 |
|------|--------|------|-------------|
| **TODO 16** | ★★★ | Gateway Target 설정의 Lambda 키 이름 | AgentCore Gateway |
| **TODO 17** | ★★☆ | credentialProviderType 값 (IAM 역할 방식) | AgentCore Gateway |

## 워크샵 실습 목차

### Step 1: Identity 설정 (`identity/setup_identity.py`)

Cognito User Pool과 AgentCore Identity Provider를 생성합니다.

```bash
cd identity
uv run python setup_identity.py
```

**학습 포인트:**
- `bedrock-agentcore-control` 클라이언트로 Identity 리소스 관리
- OAuth2 credential provider 개념 이해

**관련 TODO:** TODO 12, TODO 13

---

### Step 2: 에이전트 핵심 로직 (`agent/cost_estimator_agent/cost_estimator_agent.py`)

Code Interpreter와 MCP 도구를 연결하는 에이전트를 구현합니다.

**학습 포인트:**
- Code Interpreter 세션 시작/실행/정리 라이프사이클
- MCP(Model Context Protocol)로 외부 도구 연결
- Strands Agent에 도구 리스트 전달

**관련 TODO:** TODO 6, TODO 7, TODO 8, TODO 15

---

### Step 3: Gateway 설정 (`gateway/setup_outbound_gateway.py`)

Lambda 함수를 AgentCore Gateway에 MCP Target으로 등록합니다.

```bash
cd gateway
./deploy.sh your-verified-email@example.com   # Lambda 배포
uv run python setup_outbound_gateway.py        # Gateway + Target 생성
```

**학습 포인트:**
- Gateway Target의 `targetConfiguration.mcp.lambda` 구조
- `credentialProviderType`으로 인증 방식 지정
- Lambda를 MCP 도구로 노출하는 패턴

**관련 TODO:** TODO 16, TODO 17

---

### Step 4: Runtime 엔트리포인트 (`agent/invoke.py`)

Memory, Gateway, Identity를 통합한 Runtime 엔트리포인트를 완성합니다.

**학습 포인트:**
- `@app.entrypoint` 데코레이터로 Runtime 함수 등록
- Memory의 list_events/create_event로 대화 맥락 관리
- Cognito client_credentials 플로우로 Gateway 인증
- streamablehttp_client로 Gateway MCP 연결

배포는 **configure → deploy** 두 단계로 진행합니다.

**(1) configure — 배포 설정 생성**

`agentcore configure`는 `.bedrock_agentcore.yaml` 설정 파일을 생성합니다.
이 파일에는 엔트리포인트, 런타임 타입, 실행 역할, Memory 설정(`memory_id`) 등이 기록되며,
`deploy` 단계는 이 파일을 읽어 실제 배포를 수행합니다. (deploy는 이 파일을 생성하지 않습니다.)

```bash
cd agent
uv run agentcore configure \
  --entrypoint ./invoke.py \
  --name cost_estimator_agent \
  --requirements-file ./requirements.txt \
  --deployment-type direct_code_deploy \
  --region us-west-2
```

**(2) deploy — 런타임 배포**

```bash
uv run agentcore deploy --env AWS_REGION=us-west-2
```

> **팁:** `MEMORY_ID`와 `GATEWAY_URL`을 환경변수로 함께 주입하면, `.bedrock_agentcore.yaml`이
> 런타임 패키지에 포함되지 않는 상황에서도 Memory·Gateway가 안정적으로 동작합니다.
> (자세한 내용은 하단 [트러블슈팅](#트러블슈팅) 참고)
>
> ```bash
> uv run agentcore deploy \
>   --env AWS_REGION=us-west-2 \
>   --env MEMORY_ID=<your-memory-id> \
>   --env GATEWAY_URL=<your-gateway-mcp-url>
> ```

**관련 TODO:** TODO 1, TODO 2, TODO 3, TODO 4, TODO 5

---

### Step 5: 웹 백엔드 (`web/app.py`)

배포된 에이전트를 호출하는 웹 인터페이스를 완성합니다.

**학습 포인트:**
- `invoke_agent_runtime` API의 파라미터 구조
- `runtimeSessionId`로 세션 연속성 확보
- 스트리밍 응답 처리

```bash
cd web
uv run uvicorn app:app --reload --port 8080
```

**관련 TODO:** TODO 9, TODO 10, TODO 11, TODO 14

---

### Step 6: 동작 확인

http://127.0.0.1:8080 에 접속하여 순서대로 테스트합니다.

1. **Runtime 동작 확인** — "서울 리전의 EC2 t3.micro 24/7 비용 견적" 입력

![Runtime 동작 확인](asset/01.runtime.png)

2. **Memory 동작 확인** — "버지니아 리전은 어떤가요?" 입력 (이전 대화 맥락을 기억하는지 확인)

![Memory 동작 확인](asset/02.memory.png)

3. **Gateway 동작 확인** — "버지니아 리전과 서울 리전을 비교한 견적을 your-verified-email@example.com으로 보내주세요" 입력

![Gateway 동작 확인](asset/03.gateway.png)

![Gateway 이메일 수신 확인](asset/03.gateway-2.png)

## 소요 시간

| 단계 | 예상 소요 시간 | 비고 |
|------|---------------|------|
| 환경 설정 (Python, uv, AWS CLI) | 10분 | 사전 준비 완료 시 생략 가능 |
| Step 1: Identity 설정 | 15분 | TODO 2개 |
| Step 2: 에이전트 핵심 로직 | 25분 | TODO 4개 |
| Step 3: Gateway 설정 | 15분 | TODO 2개 + Lambda 배포 대기 |
| Step 4: Runtime 엔트리포인트 | 30분 | TODO 5개 (핵심 통합 단계) |
| Step 5: 웹 백엔드 | 20분 | TODO 4개 |
| Step 6: 동작 확인 및 테스트 | 10분 | 3가지 시나리오 검증 |
| **합계** | **약 2시간 ~ 2시간 30분** | |

## 빈칸 규칙

| 표기 | 의미 | 예시 |
|------|------|------|
| `"_____"` (따옴표 + 밑줄 5개) | 문자형 값을 채워야 함 | `"entrypoint"`, `"client_credentials"` |
| `____` (밑줄 4개) | 숫자형 값을 채워야 함 | `6`, `900` |

## Prerequisites

- Python 3.12+
- AWS 계정 (Bedrock AgentCore 접근 권한)
- AWS CLI 또는 환경변수로 자격증명 설정
- `uv` 패키지 매니저
- AWS SAM CLI (Gateway Lambda 배포 시 필요)

## Project Structure

```
.
├── agent/                              # AgentCore Runtime에 배포되는 코드
│   ├── invoke.py                       # [TODO 1~5] 엔트리포인트
│   ├── requirements.txt                # 런타임 의존성
│   ├── inbound_authorizer.json         # Cognito/Identity 설정 (자동 생성)
│   └── cost_estimator_agent/
│       ├── config.py                   # 시스템 프롬프트, 모델 설정
│       └── cost_estimator_agent.py     # [TODO 6~8, 15] 에이전트 핵심 로직
├── web/                                # 웹 UI
│   ├── app.py                          # [TODO 9~11, 14] FastAPI 백엔드
│   └── static/index.html              # 채팅 프론트엔드
├── identity/
│   └── setup_identity.py              # [TODO 12~13] Identity 설정
├── gateway/
│   ├── deploy.sh                      # Lambda 배포 스크립트 (SAM)
│   ├── setup_outbound_gateway.py      # [TODO 16~17] Gateway 설정
│   ├── src/app.py                     # Lambda 함수 (markdown_to_email)
│   └── template.yaml                  # SAM 템플릿
├── solutions/                          # 정답 코드 (스스로 풀어본 후 참고)
├── pyproject.toml                      # 프로젝트 의존성
└── README.md                           # 이 파일 (워크샵 가이드)
```

## 트러블슈팅

워크샵 진행 중 자주 마주치는 문제와 해결 방법입니다. 대부분 **(1) 스크립트 실행 위치(상대경로)**
또는 **(2) 자동 생성된 IAM 역할의 권한 부족**에서 비롯됩니다.

### 1. Gateway 설정 — `KeyError: 'lambda_arn'`

- **증상**: `setup_outbound_gateway.py` 실행 시 `config["lambda_arn"]`에서 `KeyError` 발생
- **원인**: `lambda_arn`은 `deploy.sh`가 Lambda 배포 후 `outbound_gateway.json`에 기록합니다.
  이 파일이 없는 폴더에서 스크립트를 실행하면 config가 비어 있어 키를 찾지 못합니다.
- **해결**: `deploy.sh`를 실행한 폴더와 동일한 위치에서 `setup_outbound_gateway.py`를 실행하거나,
  `outbound_gateway.json`을 실행 폴더로 복사합니다.

### 2. Gateway Target 생성 — `execution role lacks permission to invoke Lambda`

- **증상**: `CreateGatewayTarget` 호출 시 `ValidationException: Gateway execution role lacks permission to invoke Lambda function ...`
- **원인**: Gateway를 `role_arn=None`으로 생성하면 SDK가 실행 역할을 자동 생성하지만,
  특정 Lambda를 호출할 `lambda:InvokeFunction` 권한은 포함되지 않습니다.
- **해결**: Gateway 실행 역할에 Lambda 호출 권한을 인라인 정책으로 추가합니다.

  ```bash
  aws iam put-role-policy \
    --role-name <GATEWAY_EXECUTION_ROLE> \
    --policy-name AllowInvokeGatewayLambdaTarget \
    --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": "lambda:InvokeFunction",
        "Resource": "<LAMBDA_ARN>"
      }]
    }'
  ```

### 3. Gateway 재실행 — 생성이 스킵되거나 삭제에 실패

- **증상 A**: 재실행 시 아무 작업 없이 config만 출력됨 (config에 `gateway` 키가 남아 있어 "이미 있음"으로 판단)
- **증상 B**: `--force` 실행 시 `'GatewayClient' object has no attribute 'delete_mcp_gateway'`
- **원인**: 로컬 config에 이미 삭제된 Gateway 정보가 잔존 / SDK 삭제 메서드명이 다름
- **해결**: `outbound_gateway.json`에서 `gateway` 키를 제거한 뒤 재실행합니다.
  SDK의 올바른 삭제 메서드는 `delete_gateway(gateway_identifier=..., skip_resource_in_use=True)`이며,
  `skip_resource_in_use=True`는 연결된 target을 먼저 삭제한 뒤 Gateway를 삭제합니다.

### 4. Gateway 설정 — `Identity configuration file not found`

- **증상**: `../agent/inbound_authorizer.json`을 찾지 못함
- **원인**: 이 파일은 Step 1(Identity 설정)에서 생성됩니다. 스크립트가 실행 폴더 기준 상대경로로
  파일을 찾으므로, 실행 위치가 다르면 엉뚱한 `agent/` 폴더를 참조합니다.
- **해결**: Step 1을 먼저 완료하여 `agent/inbound_authorizer.json`을 생성하고,
  스크립트를 올바른 폴더에서 실행합니다.

### 5. 웹앱 채팅 — `MCPClientInitializationError: Session terminated`

- **증상**: 채팅 시도 시 Gateway MCP 연결이 즉시 종료됨
- **원인**: `invoke.py`의 `GATEWAY_URL`이 실제 Gateway와 다른(삭제된) URL을 가리킴.
  Gateway를 재생성하면 URL이 바뀌는데 코드의 기본값이 갱신되지 않은 경우입니다.
- **해결**: 배포 시 실제 Gateway URL을 환경변수로 주입합니다.

  ```bash
  uv run agentcore deploy \
    --env AWS_REGION=us-west-2 \
    --env GATEWAY_URL=<your-gateway-mcp-url>
  ```

### 6. 가격 조회 — 실제 가격 대신 추정치가 나옴

- **증상**: 견적 응답에 "가격 API 접근에 제한이 있어 추정치를 제공합니다"류의 안내가 나옴
- **원인**: 런타임 실행 역할에 `pricing:GetProducts` 권한이 없어 AWS Pricing API 호출이
  `AccessDeniedException`으로 거부됨. LLM이 이를 감지하고 추정치로 대체한 것입니다.
- **해결**: 런타임 실행 역할에 Pricing 읽기 권한을 부여합니다. (IAM 변경은 실행 중인 런타임에
  즉시 반영되므로 재배포 불필요)

  ```bash
  aws iam put-role-policy \
    --role-name <RUNTIME_EXECUTION_ROLE> \
    --policy-name AllowAWSPricingAPI \
    --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": ["pricing:GetProducts","pricing:DescribeServices","pricing:GetAttributeValues"],
        "Resource": "*"
      }]
    }'
  ```

  > 실행 역할 이름은 런타임 로그의 `assumed-role/AmazonBedrockAgentCoreSDKRuntime-...` 또는
  > `.bedrock_agentcore.yaml`의 `execution_role`에서 확인할 수 있습니다.

### 7. 메모리 — 이전 대화 맥락을 기억하지 못함

- **증상**: 후속 질문("도쿄 리전은?")에 이전 대화 내용을 반영하지 못하고 처음부터 다시 물어봄
- **원인**: `direct_code_deploy` 배포 시 숨김 파일 `.bedrock_agentcore.yaml`이 런타임 패키지에
  포함되지 않아, 런타임에서 `MEMORY_ID`가 `None`이 됩니다. 이 경우 조회/저장 로직이 조용히 스킵됩니다.
- **확인**: 런타임 로그에 `MEMORY_ID not configured - memory features will be disabled`가 있으면 이 문제입니다.
- **해결**: 배포 시 `MEMORY_ID`를 환경변수로 주입합니다. (`memory_id`는 `.bedrock_agentcore.yaml`의
  `memory.memory_id`에서 확인)

  ```bash
  uv run agentcore deploy \
    --env AWS_REGION=us-west-2 \
    --env MEMORY_ID=<your-memory-id>
  ```

### 8. 이메일 발송 — 발송되지 않음

- **경로**: 에이전트(`markdown_to_email` 호출) → Gateway → Lambda → SES → 수신함
- **확인 순서**:
  1. **런타임 로그** — 에이전트가 `markdown_to_email` 도구를 실제로 호출했는지 확인
     (사용자가 명시적으로 "이메일로 보내달라"고 요청해야 호출됩니다)
  2. **Lambda 로그** — `Received event`, `Sending email to`, SES 응답 확인
  3. **SES 인증 상태** — 신규 계정의 SES는 샌드박스 모드라 **발신자와 수신자 모두** 인증되어야 발송됩니다.

  ```bash
  # 수신자/발신자 이메일 인증 상태 확인
  aws ses list-identities --region us-west-2 --output table
  aws ses verify-email-identity --email-address <recipient@example.com> --region us-west-2
  ```

- **자주 나오는 원인**: SES 샌드박스에서 **수신자 이메일 미인증** (`MessageRejected`),
  또는 Lambda 실행 역할에 `ses:SendEmail` 권한 없음

---

## 참고 자료

| 서비스 | 공식 문서 |
|--------|----------|
| AgentCore Runtime | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-getting-started-toolkit.html |
| AgentCore Memory | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/short-term-memory-operations.html |
| AgentCore Code Interpreter | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-execute-code.html |
| Code Interpreter 세션 시작 | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-start-session.html |
| AgentCore Identity | https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore-control/client/create_oauth2_credential_provider.html |
| AgentCore Control Plane (boto3) | https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore-control.html |
| AgentCore Data Plane (boto3) | https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore.html |
| AgentCore Gateway | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-connect-mcp.html |
| Gateway Target 생성 | https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-create-target.html |
| invoke_agent_runtime API | https://docs.aws.amazon.com/botocore/latest/reference/services/bedrock-agentcore/client/invoke_agent_runtime.html |
| Cognito Token Endpoint | https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html |
| Strands Agents MCP | https://strandsagents.com/latest/user-guide/concepts/tools/mcp/ |
| AWS Pricing MCP Server | https://awslabs.github.io/mcp/servers/aws-pricing-mcp-server/ |

## 제작 도구

- **원본 프로젝트**: [sample-amazon-bedrock-agentcore-onboarding](https://github.com/aws-samples/sample-amazon-bedrock-agentcore-onboarding) — Amazon Bedrock AgentCore 온보딩 샘플 코드
- **웹 애플리케이션 통합 및 워크샵 컨텐츠 생성**: [Kiro](https://kiro.dev) (AI-powered IDE)를 활용하여 개별 샘플 코드를 하나의 웹 애플리케이션으로 통합하고, 빈칸 채우기 워크샵 형식으로 변환
- **컨텐츠 검수**: Human-in-the-Loop (HITL) 방식으로 빈칸 난이도, 힌트 정확성, 진행 순서를 검증 및 조정

## License

This project is licensed under the MIT-0 License.
